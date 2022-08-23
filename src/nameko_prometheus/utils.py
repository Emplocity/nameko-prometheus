from prometheus_client import REGISTRY


def reset_prometheus_registry(service_name: str) -> None:
    """
    Unregister metrics to avoid 'duplicated timeseries' errors in tests.
    """
    collectors_to_unregister = []
    for collector, names in REGISTRY._collector_to_names.items():
        if any(name.startswith(service_name) for name in names):
            collectors_to_unregister.append(collector)
    for collector in collectors_to_unregister:
        REGISTRY.unregister(collector)
