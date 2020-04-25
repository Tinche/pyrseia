"""Dealing with data on the wire."""
from typing import Any, Tuple

import attr


@attr.s(slots=True, frozen=True)
class Call:
    name: str = attr.ib()
    args: Tuple[Any, ...] = attr.ib()
