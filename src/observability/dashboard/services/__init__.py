__all__ = ["ConfigService", "DataService", "TraceService"]


def __getattr__(name: str):
    if name == "ConfigService":
        from .config_service import ConfigService

        return ConfigService
    if name == "DataService":
        from .data_service import DataService

        return DataService
    if name == "TraceService":
        from .trace_service import TraceService

        return TraceService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
