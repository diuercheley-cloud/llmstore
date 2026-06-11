from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Generic, List, Optional, TypeVar

T = TypeVar("T")
R = TypeVar("R")


@dataclass
class ImportResult(Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class ConvertResult(Generic[R]):
    success: bool
    data: Optional[R] = None
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class BaseAdapter(ABC):
    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        ...


class BaseImporter(ABC, Generic[T]):
    @abstractmethod
    def from_source(self, source_code: str, target_variable: str = ...) -> ImportResult[T]:
        ...

    @abstractmethod
    def from_file(self, file_path: str, target_variable: str = ...) -> ImportResult[T]:
        ...


class BaseConverter(ABC, Generic[T, R]):
    @abstractmethod
    def convert(self, source: T, **kwargs: Any) -> ConvertResult[R]:
        ...

    @abstractmethod
    def convert_batch(self, sources: List[T], **kwargs: Any) -> List[ConvertResult[R]]:
        ...
