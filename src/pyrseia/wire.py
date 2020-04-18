"""Dealing with data on the wire."""
from typing import Any

import attr


@attr.s(slots=True)
class Call:
    name: str = attr.ib()
    args: Any = attr.ib()
