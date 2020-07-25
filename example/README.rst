=========================
nameko-prometheus example
=========================

This directory provides a full working example using docker-compose.yml.

The stack includes three containers:

 - RabbitMQ (required for nameko to work)
 - Prometheus (for scraping and storing metrics)
 - my_service (an example nameko service)

Run the example with::

   docker-compose up --build

Once all containers start, browse the Prometheus web interface at
localhost:9090. Try some of these example queries:

 - ``rate(my_service_rpc_requests_total[1m])``
 - ``histogram_quantile(0.95, sum(rate(my_service_rpc_request_latency_seconds_bucket[1m])) by (le, method_name))``
 - ``histogram_quantile(0.95, sum(rate(my_service_events_latency_seconds_bucket[1m])) by (le, event_type, source_service))``
