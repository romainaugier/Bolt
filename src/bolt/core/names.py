from __future__ import annotations

import re

from bolt.core.errors import InvalidNameError

name_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
type_name_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*")

_invalid_characters = re.compile(r"[^A-Za-z0-9_]+")
_camel_boundary = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_numbered_suffix = re.compile(r"_\d+$")


def validate_name(name: str, what: str = "name") -> str:
    if not isinstance(name, str) or name_pattern.fullmatch(name) is None:
        raise InvalidNameError(f"invalid {what} {name!r}: expected letters, digits and underscores, not starting with a digit")

    return name


def validate_type_name(type_name: str) -> str:
    if not isinstance(type_name, str) or type_name_pattern.fullmatch(type_name) is None:
        raise InvalidNameError(f"invalid node type name {type_name!r}: expected dotted identifiers such as 'math.add'")

    return type_name


def sanitize_name(text: str) -> str:
    name = _invalid_characters.sub("_", _camel_boundary.sub("_", text)).strip("_").lower()

    if not name:
        return "node"

    if name[0].isdigit():
        return f"_{name}"

    return name


def name_root(name: str) -> str:
    return _numbered_suffix.sub("", name) or name
