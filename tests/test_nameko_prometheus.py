import pytest
from nameko.rpc import rpc
from nameko.testing.services import entrypoint_hook
from nameko.web.handlers import http
from prometheus_client import REGISTRY

from nameko_prometheus import PrometheusMetrics


@pytest.fixture
def config(rabbit_config, web_config):
    # merge nameko-provided fixtures in one config for container_factory
    config = rabbit_config.copy()
    config.update(web_config)
    return config


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        REGISTRY.unregister(collector)


class MyService:
    name = "my_service"
    metrics = PrometheusMetrics(prefix="my_service")

    @rpc
    def update_counter(self):
        pass

    @http("GET", "/metrics")
    def expose_metrics(self, request):
        return self.metrics.expose_metrics(request)

    @http("GET", "/error")
    def raise_error(self, request):
        raise ValueError("poof")


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


def test_http_metrics_collected_on_exception(config, container_factory, web_session):
    container = container_factory(MyService, config)
    container.start()
    web_session.get("/error")
    response = web_session.get("/metrics")
    assert (
        f'{MyService.name}_http_requests_total{{endpoint="/error",http_method="GET",status_code="500"}} 1.0'
        in response.text
    )


# TODO:
# - check custom-defined metrics (histograms etc)
