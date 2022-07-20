#!/usr/bin/env python

from glob import glob
from os.path import basename, splitext

from setuptools import find_packages, setup

with open("README.rst", "r") as f:
    long_description = f.read()


setup(
    name="nameko-prometheus",
    version="1.4.0",
    license="Apache-2.0",
    description="Prometheus metrics collector and exporter for nameko microservice framework",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Emplocity",
    author_email="zbigniew.siciarz@emplocity.pl",
    url="https://github.com/emplocity/nameko-prometheus",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/*.py")],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Utilities",
    ],
    project_urls={
        "Documentation": "https://nameko-prometheus.readthedocs.io/",
        "Changelog": "https://nameko-prometheus.readthedocs.io/en/latest/changelog.html",
        "Issue Tracker": "https://github.com/emplocity/nameko-prometheus/issues",
    },
    python_requires=">=3.8.*",
    install_requires=[
        "nameko>=2,<4",
        "prometheus_client>=0.7,<1",
    ],
)
