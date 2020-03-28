.. _configuration:

=============
Configuration
=============

nameko-prometheus is configured from YAML config file, as per
`nameko convention`_.

.. _nameko convention: https://nameko.readthedocs.io/en/stable/cli.html#running-a-service

All configuration options for nameko-prometheus should be under the
``PROMETHEUS`` key. Metrics are configured on a per-service basis.
(This is similar to what `nameko-sqlalchemy`_ does with ``DB_URIS``).

.. _nameko-sqlalchemy: https://github.com/nameko/nameko-sqlalchemy

For example if your project exposes two services like so:

.. code-block:: python

    class FooService:
        name = "foo_service"
        metrics = PrometheusMetrics()


    class BarService:
        name = "bar_service"
        metrics = PrometheusMetrics()

Then to provide separate prefixes for metrics, add the following to your config
file:

.. code-block:: yaml

    PROMETHEUS:
      foo_service:
        prefix: foo
      bar_service:
        prefix: bar
