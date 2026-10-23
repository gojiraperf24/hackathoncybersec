"""
Stage contract.

A Stage is a single, self-contained transform: it receives a RawItem,
does one thing to it (or to external systems via ctx), and returns it.
Stages are composed by the orchestrator in order.

Rules for implementing a Stage:
  1. Idempotent-ish: re-running the same stage on the same item should not
     corrupt state. Network calls are fine; don't append to item.raw['history'].
  2. Log, don't crash: catch exceptions inside process(); use ctx.logger.warning
     and return the item unchanged so downstream stages still run.
  3. Single responsibility: one stage does one thing.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

import structlog

from src.models import RawItem

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
    from src.config import Settings


@dataclass
class StageContext:
    """
    Shared state passed to every stage.

    Stages may READ from ctx, but should not MUTATE it except for ctx.stats,
    which exists so stages can record counters (e.g. scraped, classified).
    """
    session: "Session"
    logger: Any = field(default_factory=structlog.get_logger)
    stats: dict[str, int] = field(default_factory=dict)
    settings: Optional["Settings"] = None


class BaseStage(ABC):
    """
    A transform from one RawItem to one RawItem.

    Subclasses must set `name` (used for logging) and implement `process`.
    """
    name: str = "unnamed"

    @abstractmethod
    async def process(self, item: RawItem, ctx: StageContext) -> RawItem:
        """
        Input: one RawItem, possibly enriched by prior stages.
        Output: the same RawItem, possibly further enriched.

        May persist to the database via ctx.session.
        Must not raise on expected failures — log via ctx.logger and return
        the item unchanged.
        """
        ...
