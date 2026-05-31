from __future__ import annotations

from contextvars import ContextVar


_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
_source_ip: ContextVar[str] = ContextVar("source_ip", default="")
_tenant_id: ContextVar[str] = ContextVar("tenant_id", default="default")


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    return _correlation_id.get()


def clear_correlation_id() -> None:
    _correlation_id.set("")


def set_source_ip(value: str) -> None:
    _source_ip.set(value)


def get_source_ip() -> str:
    return _source_ip.get()


def clear_source_ip() -> None:
    _source_ip.set("")


def set_tenant_id(value: str) -> None:
    _tenant_id.set(value)


def get_tenant_id() -> str:
    return _tenant_id.get()


def clear_tenant_id() -> None:
    _tenant_id.set("default")
