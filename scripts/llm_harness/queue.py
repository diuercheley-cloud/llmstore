import abc
import asyncio
from typing import Any


class TaskQueue(abc.ABC):
    """
    Interface for task queues.
    """

    @abc.abstractmethod
    async def push(self, task: dict[str, Any]):
        pass

    @abc.abstractmethod
    async def pop(self) -> dict[str, Any] | None:
        pass


class InMemoryQueue(TaskQueue):
    """
    Simple in-memory implementation of TaskQueue.
    """

    def __init__(self):
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    async def push(self, task: dict[str, Any]):
        await self._queue.put(task)

    async def pop(self) -> dict[str, Any] | None:
        try:
            return await self._queue.get()
        except asyncio.QueueEmpty:
            return None

    def qsize(self):
        return self._queue.qsize()
