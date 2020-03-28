import logging
import time
from typing import MutableMapping
from weakref import WeakKeyDictionary

from nameko.containers import WorkerContext
from nameko.extensions import DependencyProvider
from nameko.rpc import Rpc
from nameko.web.handlers import HttpRequestHandler
from prometheus_client import Counter, Histogram
from prometheus_client.exposition import choose_encoder
from prometheus_client.registry import REGISTRY
from werkzeug.wrappers import Request, Response

logger = logging.getLogger(__name__)


class MetricsServer:
    """
    Serves metrics in a format readable by Prometheus scraper.

    Call :meth:`~MetricsServer.expose_metrics()` from a service method decorated with `@http`
    entrypoint to present metrics to Prometheus over HTTP.
    """

    def expose_metrics(self, request: Request) -> Response:
        if "name" not in request.args:
            logger.debug(
                "Registry name(s) not found in query string, using global registry"
            )
            registry = REGISTRY
        else:
            names = request.args.getlist("name")
            registry = REGISTRY.restricted_registry(names)
        encoder, content_type = choose_encoder(request.headers["Accept"])
        try:
            output = encoder(registry)
            return Response(output, status=200, content_type=content_type)
        except Exception:
            message = f"Failed to generate metrics"
            logger.exception(message)
            return Response(message, status=500)


class PrometheusMetrics(DependencyProvider):
    """
    Dependency provider which measures RPC and HTTP endpoint latency.

    On service start, a few default metrics are declared. These are:

    - ``<prefix>_http_requests_total``
    - ``<prefix>_http_request_latency_seconds``
    - ``<prefix>_rpc_requests_total``
    - ``<prefix>_rpc_request_latency_seconds``

    where ``prefix`` is either derived from ``name`` attribute of the service
    class, or :ref:`configured manually <configuration>`.
    """

    def __init__(self):
        self.worker_starts: MutableMapping[WorkerContext, float] = WeakKeyDictionary()

    def setup(self) -> None:
        """
        Configures the dependency provider and declares default metrics.
        """
        # read config from container, use service name as default prefix
        service_name = self.container.service_name
        config = self.container.config.get("PROMETHEUS", {})
        service_config = config.get(service_name, {})
        prefix = service_config.get("prefix", service_name)
        # initialize default metrics exposed for every service
        self.http_request_total_counter = Counter(
            f"{prefix}_http_requests_total",
            "Total number of HTTP requests",
            ["http_method", "endpoint", "status_code"],
        )
        self.http_request_latency_histogram = Histogram(
            f"{prefix}_http_request_latency_seconds",
            "HTTP request duration in seconds",
            ["http_method", "endpoint", "status_code"],
        )
        self.rpc_request_total_counter = Counter(
            f"{prefix}_rpc_requests_total",
            "Total number of RPC requests",
            ["method_name"],
        )
        self.rpc_request_latency_histogram = Histogram(
            f"{prefix}_rpc_request_latency_seconds",
            "RPC request duration in seconds",
            ["method_name"],
        )

    def get_dependency(self, worker_ctx: WorkerContext) -> MetricsServer:
        """
        Returns an instance of
        :class:`~nameko_prometheus.dependencies.MetricsServer` to be injected
        into the worker.
        """
        return MetricsServer()

    def worker_setup(self, worker_ctx: WorkerContext) -> None:
        """
        Called before service worker starts.
        """
        self.worker_starts[worker_ctx] = time.perf_counter()

    def worker_result(
        self, worker_ctx: WorkerContext, result=None, exc_info=None
    ) -> None:
        """
        Called after service worker completes.

        At this point the default metrics such as worker latency are observed,
        regardless of whether the worker finished successfully or raised an
        exception.
        """
        try:
            start = self.worker_starts.pop(worker_ctx)
            entrypoint = worker_ctx.entrypoint
            duration = time.perf_counter() - start
            if isinstance(entrypoint, HttpRequestHandler):
                http_method = entrypoint.method
                url = entrypoint.url
                if exc_info:
                    _, exc, _ = exc_info
                    status_code = entrypoint.response_from_exception(exc).status_code
                else:
                    status_code = entrypoint.response_from_result(result).status_code
                logger.debug(f"Tracing HTTP request: {http_method} {url} {status_code}")
                self.http_request_total_counter.labels(
                    http_method=http_method, endpoint=url, status_code=status_code
                ).inc()
                self.http_request_latency_histogram.labels(
                    http_method=http_method, endpoint=url, status_code=status_code
                ).observe(duration)
            elif isinstance(entrypoint, Rpc):
                method_name = entrypoint.method_name
                logger.debug(f"Tracing RPC request: {method_name}")
                self.rpc_request_total_counter.labels(method_name=method_name).inc()
                self.rpc_request_latency_histogram.labels(
                    method_name=method_name
                ).observe(duration)
        except KeyError:
            logger.info("No worker_ctx in request start dictionary")
