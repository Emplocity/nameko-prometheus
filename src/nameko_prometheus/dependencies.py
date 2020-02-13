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
    """

    def __init__(self, prefix: str = "nameko"):
        self.prefix = prefix
        self.worker_starts: MutableMapping[WorkerContext, float] = WeakKeyDictionary()

    def setup(self) -> None:
        logger.debug(f"{self.__class__.__name__} setup")
        self.http_request_total_counter = Counter(
            f"{self.prefix}_http_requests_total",
            "Total number of HTTP requests",
            ["http_method", "endpoint", "status_code"],
        )
        self.http_request_latency_histogram = Histogram(
            f"{self.prefix}_http_request_latency_seconds",
            "HTTP request duration in seconds",
            ["http_method", "endpoint", "status_code"],
        )
        self.rpc_request_total_counter = Counter(
            f"{self.prefix}_rpc_requests_total",
            "Total number of RPC requests",
            ["method_name"],
        )
        self.rpc_request_latency_histogram = Histogram(
            f"{self.prefix}_rpc_request_latency_seconds",
            "RPC request duration in seconds",
            ["method_name"],
        )

    def get_dependency(self, worker_ctx: WorkerContext) -> MetricsServer:
        return MetricsServer()

    def worker_setup(self, worker_ctx: WorkerContext) -> None:
        logger.debug("Worker setup")
        self.worker_starts[worker_ctx] = time.perf_counter()

    def worker_result(
        self, worker_ctx: WorkerContext, result=None, exc_info=None
    ) -> None:
        """
        """
        logger.debug(f"Worker result: {result} (exc_info={exc_info})")
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
