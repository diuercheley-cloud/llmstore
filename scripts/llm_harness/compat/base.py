from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class ImportResult(Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class ConvertResult(Generic[R]):
    success: bool
    data: R | None = None
    error: str | None = None
    warnings: list[str] = field(default_factory=list)


class BaseAdapter(ABC):
    @abstractmethod
    def to_dict(self) -> dict[str, Any]: ...


class BaseImporter(ABC, Generic[T]):
    @abstractmethod
    def from_source(self, source_code: str, target_variable: str = ...) -> ImportResult[T]: ...

    @abstractmethod
    def from_file(self, file_path: str, target_variable: str = ...) -> ImportResult[T]: ...


class BaseConverter(ABC, Generic[T, R]):
    @abstractmethod
    def convert(self, source: T, **kwargs: Any) -> ConvertResult[R]: ...

    @abstractmethod
    def convert_batch(self, sources: list[T], **kwargs: Any) -> list[ConvertResult[R]]: ...
