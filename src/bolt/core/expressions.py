from __future__ import annotations

import builtins
import functools
import math
import re
from collections.abc import Mapping
from types import CodeType
from typing import Any

from bolt.core.errors import ExpressionError

missing: Any = type("Missing", (), {"__repr__": lambda self: "<missing>"})()

_token_pattern = re.compile(r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)|`([^`]*)`")
_variable_pattern = re.compile(r"\$\(([A-Za-z_][A-Za-z0-9_]*)\)")
_single_expression_pattern = re.compile(r"`([^`]*)`")

_safe_builtins = {
    name: getattr(builtins, name)
    for name in ("abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float", "int", "len", "list",
                 "map", "max", "min", "pow", "range", "reversed", "round", "set", "sorted", "str", "sum", "tuple", "zip")
}

_globals: dict[str, Any] = {name: value for name, value in vars(math).items() if not name.startswith("_")}
_globals["math"] = math
_globals["__builtins__"] = _safe_builtins


@functools.lru_cache(maxsize=4096)
def _compile(source: str) -> CodeType:
    return compile(source, "<expression>", "eval")


class Expander:
    """Expands `$(VARIABLE)` references and backtick Python expressions, recording the variables it reads."""

    __slots__ = ("variables", "used")

    def __init__(self, variables: Mapping[str, Any], used: dict[str, Any] | None = None) -> None:
        self.variables = variables
        self.used = used

    def lookup(self, name: str) -> Any:
        value = self.variables.get(name, missing)

        if self.used is not None:
            self.used[name] = value

        if value is missing:
            raise ExpressionError(f"undefined variable '{name}'")

        return value

    def evaluate(self, source: str) -> Any:
        if "$(" in source:
            source = _variable_pattern.sub(self._substitute, source)

        try:
            code = _compile(source)
        except SyntaxError as error:
            raise ExpressionError(f"invalid expression `{source}`: {error.msg}") from None

        scope = dict(_globals)

        for name in code.co_names:
            if name in self.variables:
                scope[name] = self.lookup(name)

        try:
            return eval(code, scope)
        except ExpressionError:
            raise
        except NameError as error:
            raise ExpressionError(f"undefined variable '{error.name}' in `{source}`") from None
        except Exception as error:
            raise ExpressionError(f"expression `{source}` failed: {error}") from error

    def __call__(self, text: str) -> Any:
        single = _single_expression_pattern.fullmatch(text)

        if single is not None:
            return self.evaluate(single.group(1))

        return _token_pattern.sub(self._replace_token, text)

    def _substitute(self, match: re.Match[str]) -> str:
        return str(self.lookup(match.group(1)))

    def _replace_token(self, match: re.Match[str]) -> str:
        name = match.group(1)

        if name is not None:
            return str(self.lookup(name))

        return str(self.evaluate(match.group(2)))


def expand(text: str, variables: Mapping[str, Any], used: dict[str, Any] | None = None) -> Any:
    return Expander(variables, used)(text)
