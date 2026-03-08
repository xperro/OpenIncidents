"""Local replay helper."""

from __future__ import annotations


def read_input(path: str) -> str:
    if path == "-":
        import sys

        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()
