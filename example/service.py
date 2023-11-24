import random
import time

from nameko.events import EventDispatcher, event_handler
from nameko.rpc import RpcProxy, rpc
from nameko.testing.services import once
from nameko.web.handlers import http
from prometheus_client import Counter

from nameko_prometheus import PrometheusMetrics

work_units = Counter(
    "my_service_work_units_total", "Total number of work units", ["work_type"]
)


class MyService:
    name = "my_service"
    my_service = RpcProxy(name)
    dispatcher = EventDispatcher()
    metrics = PrometheusMetrics()

    @http("GET", "/metrics")
    def expose_metrics(self, request):
        return self.metrics.expose_metrics(request)

    @rpc
    def say_hello(self):
        return "Hello!"

    @once
    def start_all_the_things(self):
        """
        Called once at the start - starts dispatching RPC calls and events.
        """
        print("Starting!")
        delay = random.uniform(0.5, 5)
        self.my_service.do_work.call_async(delay)

    @rpc
    def do_work(self, delay: float):
        """
        Simulates some work using time.sleep() and calls itself at the end.

        Approximately half the time this method emits a 'my_event' event.
        """
        print(f"Working for {delay:.2f} seconds!")
        time.sleep(delay)
        new_delay = random.uniform(0.5, 5)
        self.my_service.do_work.call_async(new_delay)
        work_units.labels(work_type="hard").inc()
        if random.choice([True, False]):
            self.dispatcher("my_event", {"delay": 0.7 * new_delay})

    @event_handler("my_service", "my_event")
    def handle_event(self, payload):
        """
        Simulates handling a business event using time.sleep().
        """
        delay = payload["delay"]
        print(f"Handling event for {delay:.2f} seconds!")
        time.sleep(delay)
        work_units.labels(work_type="easy").inc()
