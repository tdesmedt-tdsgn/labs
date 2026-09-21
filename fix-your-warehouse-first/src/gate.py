"""The gate: no green warehouse, no answer.

This is four lines of logic and it is the entire argument of the demo. The
expensive part of an AI data assistant is not the model, it is being able to
say what the numbers it reads are worth.
"""
from __future__ import annotations

from typing import Callable, TypeVar

from src.warehouse import TestReport

T = TypeVar("T")


class WarehouseNotTrusted(RuntimeError):
    """Raised instead of returning a number nobody should act on."""


def serve(query: Callable[[], T], report: TestReport) -> T:
    """Run `query` only if the warehouse passed its tests.

    The query is not executed on a red warehouse. Producing the wrong number
    and then discarding it still burns the credibility of whoever pastes the
    partial output into a slide.
    """
    if not report.ok:
        raise WarehouseNotTrusted(
            "refusing to answer: " + report.summary()
        )
    return query()
