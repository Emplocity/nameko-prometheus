========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis|
        |
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/nameko-prometheus/badge/?style=flat
    :target: https://readthedocs.org/projects/nameko-prometheus
    :alt: Documentation Status

.. |travis| image:: https://api.travis-ci.org/emplocity/nameko-prometheus.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/emplocity/nameko-prometheus

.. |version| image:: https://img.shields.io/pypi/v/nameko-prometheus.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/nameko-prometheus

.. |wheel| image:: https://img.shields.io/pypi/wheel/nameko-prometheus.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/nameko-prometheus

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/nameko-prometheus.svg
    :alt: Supported versions
    :target: https://pypi.org/project/nameko-prometheus

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/nameko-prometheus.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/nameko-prometheus

.. |commits-since| image:: https://img.shields.io/github/commits-since/emplocity/nameko-prometheus/v0.1.svg
    :alt: Commits since latest release
    :target: https://github.com/emplocity/nameko-prometheus/compare/v0.1...master



.. end-badges

``nameko-prometheus`` is a dependency for the nameko_ microservice framework
which allows application metrics collection with Prometheus_.

.. _nameko: https://www.nameko.io/
.. _Prometheus: https://prometheus.io/


Features
========

 - automatic collection of request latency metrics for RPC and HTTP endpoints
 - HTTP endpoint exposing metrics to be scraped by Prometheus


Installation
============

::

    pip install nameko-prometheus

You can also install the in-development version with::

    pip install https://github.com/emplocity/nameko-prometheus/archive/master.zip


Usage
=====

.. code-block:: python

   from nameko.rpc import rpc
   from nameko.web.handlers import http
   from nameko_prometheus import PrometheusMetrics


   class MyService:
      metrics = PrometheusMetrics(prefix="myservice")

      @rpc
      def say_hello(self):
         return "Hello!"

      @http("GET", "/")
      def index(self, request):
         return "OK"

      @http("GET", "/metrics")
      def serve_metrics(self, request):
         return self.metrics.serve(request)


Documentation
=============


https://nameko-prometheus.readthedocs.io/


Development
===========

To run the all tests run::

    tox

Note, to combine the coverage data from all the tox environments run:

.. list-table::
    :widths: 10 90
    :stub-columns: 1

    - - Windows
      - ::

            set PYTEST_ADDOPTS=--cov-append
            tox

    - - Other
      - ::

            PYTEST_ADDOPTS=--cov-append tox


Development roadmap
===================

Things we'd like to have in the future:

 - automatic registration of ``/metrics`` HTTP endpoint
 - decorator to exclude specific methods from tracing


Authors
=======

``nameko-prometheus`` is developed and maintained by `Emplocity`_.

.. _Emplocity: https://emplocity.com/


License
=======

This work is released under the Apache 2.0 license.
