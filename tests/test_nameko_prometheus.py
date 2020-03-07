from nameko.web.handlers import http

from nameko_prometheus import PrometheusMetrics


class MyService:
    name = "my_service"
    metrics = PrometheusMetrics(prefix="my_service")

    @http("GET", "/metrics")
    def serve_metrics(self, request):
        return self.metrics.expose_metrics(request)


def test_dependency_provider(rabbit_config, container_factory):
    container = container_factory(MyService, rabbit_config)
    container.start()
    # TODO: collect some metrics, hit /metrics and check that they are exposed
