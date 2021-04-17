import pytest
from nameko.events import EventDispatcher, event_handler
from nameko.rpc import rpc
from nameko.testing.services import entrypoint_hook, entrypoint_waiter
from nameko.web.handlers import http
from prometheus_client import REGISTRY, Counter

from nameko_prometheus import PrometheusMetrics


@pytest.fixture
def config(rabbit_config, web_config):
    # merge nameko-provided fixtures in one config for container_factory
    config = rabbit_config.copy()
    config.update(web_config)
    return config


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    collectors_to_unregister = []
    for collector, names in REGISTRY._collector_to_names.items():
        if any(name.startswith("my_service") for name in names):
            collectors_to_unregister.append(collector)
    for collector in collectors_to_unregister:
        REGISTRY.unregister(collector)


my_counter = Counter("my_counter", "My counter")


class MyService:
    name = "my_service"
    metrics = PrometheusMetrics()
    dispatcher = EventDispatcher()

    @rpc
    def update_counter(self):
        my_counter.inc()

    @http("GET", "/metrics")
    def expose_metrics(self, request):
        return self.metrics.expose_metrics(request)

    @http("GET", "/error")
    def raise_error(self, request):
        raise ValueError("poof")

    @rpc
    def emit_event(self):
        self.dispatcher("my_event", {"foo": "bar"})

    @event_handler("my_service", "my_event")
    def handle_event(self, payload):
        return f"handled: {payload}"


def test_expose_default_metrics(config, container_factory, web_session):
    container = container_factory(MyService, config)
    container.start()
    with entrypoint_hook(container, "update_counter") as update_counter:
        update_counter()
        update_counter()
    response = web_session.get("/metrics")
    # assert that default metrics are exposed in Prometheus text format
    assert f"TYPE {MyService.name}_rpc_requests_total counter" in response.text
    assert f"TYPE {MyService.name}_service_max_workers gauge" in response.text
    assert (
        f'{MyService.name}_rpc_requests_total{{method_name="update_counter"}} 2.0'
        in response.text
    )


def test_expose_custom_metrics(config, container_factory, web_session):
    container = container_factory(MyService, config)
    container.start()
    with entrypoint_hook(container, "update_counter") as update_counter:
        update_counter()
        update_counter()
    response = web_session.get("/metrics")
    assert "my_counter_total" in response.text


def test_expose_event_handler_metrics(config, container_factory, web_session):
    container = container_factory(MyService, config)
    container.start()
    with entrypoint_waiter(container, "handle_event"):
        with entrypoint_hook(container, "emit_event") as emit_event:
            emit_event()
    response = web_session.get("/metrics")
    assert f"TYPE {MyService.name}_events_total counter" in response.text
    assert f"TYPE {MyService.name}_events_latency_seconds histogram" in response.text
    assert (
        f'{MyService.name}_events_total{{event_type="my_event",source_service="my_service"}} 1.0'
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


def test_override_default_metric_prefix(config, container_factory, web_session):
    prefix = "my_prefix"
    config.update({"PROMETHEUS": {MyService.name: {"prefix": prefix}}})
    container = container_factory(MyService, config)
    container.start()
    with entrypoint_hook(container, "update_counter") as update_counter:
        update_counter()
    response = web_session.get("/metrics")
    assert f"TYPE {prefix}_rpc_requests_total counter" in response.text
