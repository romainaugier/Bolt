import pytest

from bolt.core.errors import ExpressionError
from bolt.core.expressions import expand, missing


def test_variable_substitution():
    assert expand("$(ROOT)/shots/$(SHOT)", {"ROOT": "/prod", "SHOT": "sh010"}) == "/prod/shots/sh010"


def test_single_expression_keeps_python_type():
    assert expand("`FRAME * 2`", {"FRAME": 12}) == 24
    assert expand("`[i for i in range(3)]`", {}) == [0, 1, 2]


def test_embedded_expressions_are_stringified():
    assert expand("frame_`FRAME + 1`.exr", {"FRAME": 9}) == "frame_10.exr"


def test_variables_inside_expressions():
    assert expand("`$(START) + 10`", {"START": "1001"}) == 1011


def test_math_functions_are_available():
    assert expand("`floor(sqrt(17))`", {}) == 4


def test_used_variables_are_recorded():
    used = {}
    expand("$(A) `B + 1` $(C)", {"A": "a", "B": 1, "C": "c", "D": "d"}, used)
    assert used == {"A": "a", "B": 1, "C": "c"}


def test_undefined_variable_raises_and_is_recorded():
    used = {}
    with pytest.raises(ExpressionError, match="undefined variable 'NOPE'"):
        expand("$(NOPE)", {}, used)
    assert used == {"NOPE": missing}


def test_invalid_expression_raises():
    with pytest.raises(ExpressionError, match="invalid expression"):
        expand("`1 +`", {})
    with pytest.raises(ExpressionError, match="failed"):
        expand("`1 / 0`", {})


def test_builtins_are_restricted():
    with pytest.raises(ExpressionError):
        expand("`__import__('os')`", {})
    with pytest.raises(ExpressionError):
        expand("`open('/etc/passwd')`", {})


def test_walrus_does_not_leak_between_evaluations():
    expand("`(leak := 1)`", {})
    with pytest.raises(ExpressionError):
        expand("`leak`", {})
