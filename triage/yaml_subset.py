"""A tiny YAML subset parser/writer for the canonical ``triage.yaml`` shape."""

from __future__ import annotations

import re
from typing import Any

from .errors import UserError

SCALAR_INT = re.compile(r"^-?\d+$")


class _Parser:
    def __init__(self, text: str):
        self.lines = []
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(raw_line) - len(raw_line.lstrip(" "))
            self.lines.append((indent, raw_line[indent:]))

    def parse(self) -> Any:
        if not self.lines:
            return {}
        value, index = self._parse_block(0, self.lines[0][0])
        if index != len(self.lines):
            raise UserError("Unsupported YAML structure in triage.yaml.")
        return value

    def _parse_block(self, index: int, indent: int) -> tuple[Any, int]:
        if index >= len(self.lines):
            return {}, index
        _, content = self.lines[index]
        if content.startswith("-"):
            return self._parse_list(index, indent)
        return self._parse_mapping(index, indent)

    def _parse_mapping(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        mapping: dict[str, Any] = {}
        while index < len(self.lines):
            current_indent, content = self.lines[index]
            if current_indent < indent:
                break
            if current_indent != indent:
                raise UserError("Unsupported indentation in triage.yaml.")
            if content.startswith("-"):
                break
            if ":" not in content:
                raise UserError("Expected `key: value` mapping entry in triage.yaml.")
            key, remainder = content.split(":", 1)
            key = key.strip()
            remainder = remainder.strip()
            index += 1
            if remainder:
                mapping[key] = parse_scalar(remainder)
                continue
            if index >= len(self.lines) or self.lines[index][0] <= current_indent:
                mapping[key] = {}
                continue
            mapping[key], index = self._parse_block(index, self.lines[index][0])
        return mapping, index

    def _parse_list(self, index: int, indent: int) -> tuple[list[Any], int]:
        values: list[Any] = []
        while index < len(self.lines):
            current_indent, content = self.lines[index]
            if current_indent < indent:
                break
            if current_indent != indent or not content.startswith("-"):
                break
            remainder = content[1:].strip()
            index += 1
            if not remainder:
                if index >= len(self.lines) or self.lines[index][0] <= current_indent:
                    values.append(None)
                    continue
                item, index = self._parse_block(index, self.lines[index][0])
                values.append(item)
                continue
            if ":" in remainder:
                key, rest = remainder.split(":", 1)
                item: dict[str, Any] = {}
                key = key.strip()
                rest = rest.strip()
                if rest:
                    item[key] = parse_scalar(rest)
                else:
                    if index >= len(self.lines) or self.lines[index][0] <= current_indent:
                        item[key] = {}
                    else:
                        item[key], index = self._parse_block(index, self.lines[index][0])
                if index < len(self.lines) and self.lines[index][0] > current_indent:
                    extra, index = self._parse_mapping(index, current_indent + 2)
                    item.update(extra)
                values.append(item)
                continue
            values.append(parse_scalar(remainder))
        return values, index


def parse_scalar(value: str) -> Any:
    if value in ("null", "~"):
        return None
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value == "true":
        return True
    if value == "false":
        return False
    if SCALAR_INT.match(value):
        return int(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\'", "'")
    return value


def load_yaml(text: str) -> Any:
    return _Parser(text).parse()


def dump_yaml(value: Any, order_resolver=None) -> str:
    lines = _dump_value(value, 0, "", order_resolver)
    return "\n".join(lines) + "\n"


def _dump_value(value: Any, indent: int, path: str, order_resolver) -> list[str]:
    if isinstance(value, dict):
        if not value:
            return [" " * indent + "{}"]
        lines: list[str] = []
        for key in _ordered_keys(value, path, order_resolver):
            child = value[key]
            if _is_scalar(child):
                lines.append(f'{" " * indent}{key}: {format_scalar(child)}')
            elif isinstance(child, list) and not child:
                lines.append(f'{" " * indent}{key}: []')
            elif isinstance(child, dict) and not child:
                lines.append(f'{" " * indent}{key}: {{}}')
            else:
                lines.append(f'{" " * indent}{key}:')
                child_path = f"{path}.{key}" if path else key
                lines.extend(_dump_value(child, indent + 2, child_path, order_resolver))
        return lines
    if isinstance(value, list):
        if not value:
            return [" " * indent + "[]"]
        lines: list[str] = []
        item_path = path[:-1] if path.endswith("[]") else path
        for item in value:
            if _is_scalar(item):
                lines.append(f'{" " * indent}- {format_scalar(item)}')
                continue
            if isinstance(item, dict) and item:
                keys = _ordered_keys(item, item_path, order_resolver)
                first_key = keys[0]
                first_value = item[first_key]
                first_child_path = f"{item_path}.{first_key}" if item_path else first_key
                if _is_scalar(first_value):
                    lines.append(
                        f'{" " * indent}- {first_key}: {format_scalar(first_value)}'
                    )
                elif isinstance(first_value, list) and not first_value:
                    lines.append(f'{" " * indent}- {first_key}: []')
                elif isinstance(first_value, dict) and not first_value:
                    lines.append(f'{" " * indent}- {first_key}: {{}}')
                else:
                    lines.append(f'{" " * indent}- {first_key}:')
                    lines.extend(
                        _dump_value(first_value, indent + 4, first_child_path, order_resolver)
                    )
                for key in keys[1:]:
                    child = item[key]
                    child_path = f"{item_path}.{key}" if item_path else key
                    if _is_scalar(child):
                        lines.append(f'{" " * (indent + 2)}{key}: {format_scalar(child)}')
                    elif isinstance(child, list) and not child:
                        lines.append(f'{" " * (indent + 2)}{key}: []')
                    elif isinstance(child, dict) and not child:
                        lines.append(f'{" " * (indent + 2)}{key}: {{}}')
                    else:
                        lines.append(f'{" " * (indent + 2)}{key}:')
                        lines.extend(
                            _dump_value(child, indent + 4, child_path, order_resolver)
                        )
                continue
            lines.append(f'{" " * indent}-')
            lines.extend(_dump_value(item, indent + 2, item_path, order_resolver))
        return lines
    return [" " * indent + format_scalar(value)]


def _ordered_keys(value: dict[str, Any], path: str, order_resolver) -> list[str]:
    if order_resolver is None:
        return sorted(value.keys())
    preferred = list(order_resolver(path, value.keys()))
    seen = set(preferred)
    for key in sorted(value.keys()):
        if key not in seen:
            preferred.append(key)
    return preferred


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (bool, int, str))


def format_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if text == "":
        return '""'
    reserved = {"true", "false", "null", "~"}
    if text in reserved or SCALAR_INT.match(text):
        return f'"{text}"'
    if (
        text[0] in "-?:,[]{}#&*!|>'\"%@`"
        or ": " in text
        or text.endswith(" ")
        or text.startswith(" ")
        or "#" in text
    ):
        escaped = text.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return text
