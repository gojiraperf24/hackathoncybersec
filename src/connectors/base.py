from abc import ABC, abstractmethod
from typing import AsyncIterator
from src.models import RawItem


class BaseConnector(ABC):
    name: str

    @abstractmethod
    async def fetch(self) -> AsyncIterator[RawItem]:
        """Yield RawItem objects. Must be idempotent and resumable."""
        ...
