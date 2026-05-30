import abc
from typing import Any, Dict, List


class WebSearchProvider(abc.ABC):
    @abc.abstractmethod
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Executes a web search query.
        Each result in the list must be a dictionary with keys:
        - title: str
        - snippet: str
        - url: str
        - provider: str
        - confidence: float
        - retrieved_at: datetime
        """
        pass
