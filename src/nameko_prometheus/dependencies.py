import logging
import os
import platform
import time
from dataclasses import dataclass
from typing import Any, MutableMapping, Optional, Tuple
from weakref import WeakKeyDictionary

try:
    from functools import singledispatchmethod
except ImportError:
    from singledispatchmethod import singledispatchmethod  # type: ignore

from nameko.containers import WorkerContext
from nameko.events import EventHandler
from nameko.extensions import DependencyProvider, Entrypoint
from nameko.rpc import Rpc
from nameko.web.handlers import HttpRequestHandler
from prometheus_client import Counter, Gauge, Histogram
from prometheus_client.exposition import choose_encoder
from prometheus_client.registry import REGISTRY
from werkzeug.wrappers import Request, Response

logger = logging.getLogger(__name__)


START_TIME = time.time()


class MetricsServer:
    """
    Serves metrics in a format readable by Prometheus scraper.

    Call :meth:`~expose_metrics()` from a service method decorated with `@http`_
    entrypoint to present metrics to Prometheus over HTTP.

    .. _@http: https://nameko.readthedocs.io/en/stable/built_in_extensions.html#http
    """

    def expose_metrics(self, request: Request) -> Response:
        """
        Returns metrics as a HTTP response in Prometheus text format.
        """
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
            message = "Failed to generate metrics"
            logger.exception(message)
            return Response(message, status=500)


@dataclass(frozen=True)
class WorkerSummary:
    """
    Represents the final result (or error) of a worker, including duration.

    This simplifies method signatures for singledispatch overrides.
    """

    duration: float
    result: Any
    exc_info: Optional[Tuple]


class PrometheusMetrics(DependencyProvider):
    """
    Dependency provider which measures RPC, event handler and HTTP endpoint
    latency.

    On service start, a few default metrics are declared. These are:

    - ``<prefix>_http_requests_total``
    - ``<prefix>_http_request_latency_seconds``
    - ``<prefix>_rpc_requests_total``
    - ``<prefix>_rpc_request_latency_seconds``
    - ``<prefix>_events_total``
    - ``<prefix>_events_latency_seconds``

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
        # read application version from an environment variable
        app_version_key = config.get("APP_VERSION_KEY", "APP_VERSION")
        self.app_version = os.environ.get(app_version_key, "unknown")
        self.python_version = platform.python_version()
        # initialize default metrics exposed for every service
        self.service_info = Gauge(
            f"{prefix}_service_info",
            "Always 1; see https://www.robustperception.io/exposing-the-software-version-to-prometheus",
            ["service_version", "python_version"],
        )
        self.service_uptime_seconds = Gauge(
            f"{prefix}_service_uptime_seconds",
            "Uptime of service in seconds",
        )
        self.service_max_workers = Gauge(
            f"{prefix}_service_max_workers",
            "Maximum number of available nameko workers",
        )
        self.service_running_workers = Gauge(
            f"{prefix}_service_running_workers",
            "Number of currently running nameko workers",
        )
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
        self.events_total_counter = Counter(
            f"{prefix}_events_total",
            "Total number of handled events",
            ["source_service", "event_type"],
        )
        self.events_latency_histogram = Histogram(
            f"{prefix}_events_latency_seconds",
            "Event handler duration in seconds",
            ["source_service", "event_type"],
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
        except KeyError:
            logger.warning("No worker_ctx in request start dictionary")
            return
        worker_summary = WorkerSummary(
            duration=time.perf_counter() - start,
            result=result,
            exc_info=exc_info,
        )
        self.observe_entrypoint(worker_ctx.entrypoint, worker_summary)
        self.observe_state_metrics()

    @singledispatchmethod
    def observe_entrypoint(
        self, entrypoint: Entrypoint, worker_summary: WorkerSummary
    ) -> None:
        logger.warning(f"Entrypoint {entrypoint} is not traceable by nameko_prometheus")

    @observe_entrypoint.register(Rpc)
    def _observe_rpc(self, entrypoint: Rpc, worker_summary: WorkerSummary) -> None:
        logger.info(f"Collect metrics from RPC entrypoint {entrypoint}")
        method_name = entrypoint.method_name
        self.rpc_request_total_counter.labels(method_name=method_name).inc()
        self.rpc_request_latency_histogram.labels(method_name=method_name).observe(
            worker_summary.duration
        )

    @observe_entrypoint.register(HttpRequestHandler)
    def _observe_http(
        self, entrypoint: HttpRequestHandler, worker_summary: WorkerSummary
    ) -> None:
        logger.info(f"Collect metrics from HTTP entrypoint {entrypoint}")
        http_method = entrypoint.method
        url = entrypoint.url
        if worker_summary.exc_info:
            _, exc, _ = worker_summary.exc_info
            status_code = entrypoint.response_from_exception(exc).status_code
        else:
            status_code = entrypoint.response_from_result(
                worker_summary.result
            ).status_code
        logger.debug(f"Tracing HTTP request: {http_method} {url} {status_code}")
        self.http_request_total_counter.labels(
            http_method=http_method, endpoint=url, status_code=status_code
        ).inc()
        self.http_request_latency_histogram.labels(
            http_method=http_method, endpoint=url, status_code=status_code
        ).observe(worker_summary.duration)

    @observe_entrypoint.register(EventHandler)
    def _observe_event_handler(
        self, entrypoint: EventHandler, worker_summary: WorkerSummary
    ) -> None:
        logger.info(f"Collect metrics from event handler entrypoint {entrypoint}")
        source_service = entrypoint.source_service
        event_type = entrypoint.event_type
        self.events_total_counter.labels(
            source_service=source_service, event_type=event_type
        ).inc()
        self.events_latency_histogram.labels(
            source_service=source_service, event_type=event_type
        ).observe(worker_summary.duration)

    def observe_state_metrics(self) -> None:
        self.service_info.labels(
            service_version=self.app_version, python_version=self.python_version
        ).set(1)
        self.service_uptime_seconds.set(time.time() - START_TIME)
        self.service_max_workers.set(self.container.max_workers)
        self.service_running_workers.set(len(self.container._worker_threads))
