import pytest
from nameko.rpc import rpc
from nameko.testing.services import entrypoint_hook
from nameko.web.handlers import http

from nameko_prometheus import PrometheusMetrics


@pytest.fixture
def config(rabbit_config, web_config):
    # merge nameko-provided fixtures in one config for container_factory
    config = rabbit_config.copy()
    config.update(web_config)
    return config


class MyService:
    name = "my_service"
    metrics = PrometheusMetrics(prefix="my_service")

    @rpc
    def update_counter(self):
        pass

    @http("GET", "/metrics")
    def expose_metrics(self, request):
        return self.metrics.expose_metrics(request)


def test_expose_default_metrics(config, container_factory, web_session):
    container = container_factory(MyService, config)
    container.start()
    with entrypoint_hook(container, "update_counter") as update_counter:
        update_counter()
        update_counter()
    response = web_session.get("/metrics")
    # assert that default metrics are exposed in Prometheus text format
    assert f"TYPE {MyService.name}_rpc_requests_total counter" in response.text
    assert (
        f'{MyService.name}_rpc_requests_total{{method_name="update_counter"}} 2.0'
        in response.text
    )
