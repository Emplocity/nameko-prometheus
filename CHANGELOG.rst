
Changelog
=========

1.4.0 (2022-07-20)
------------------

* Add support for nameko 3.0 RC.

1.3.0 (2022-04-19)
------------------

* Drop support for Python 3.6 and 3.7.
* Add support for Python 3.10.
* Add compatibility with prometheus-client >= 0.14.

1.2.0 (2021-10-13)
------------------

* Added support for Python 3.9.
* Moved CI infrastructure to Github Actions.

1.1.1 (2021-04-28)
------------------

* Lowered log level for debug messages to actually DEBUG.

1.1.0 (2021-04-19)
------------------

* Added metrics related to service state: version, uptime, number of
  running/max workers.

1.0.0 (2020-07-29)
------------------

* Added default performance metrics for event handlers.
* Added a full-stack example in the repository.
* Expanded the usage documentation.

0.2.0 (2020-03-28)
------------------

* *[BREAKING CHANGE]* ``PrometheusMetrics`` dependency doesn't support the
  ``prefix`` argument anymore. If you need to customize prefix for the generic
  metrics (such as total requests/latency), do it in the YAML config file
  for your service.

0.1.1 (2020-02-13)
------------------

* Fixed crash when HTTP entrypoint raised an exception.

0.1 (2019-10-01)
----------------

* First release on PyPI.
