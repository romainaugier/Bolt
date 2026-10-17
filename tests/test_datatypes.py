import pathlib

import pytest

from bolt.core.datatypes import (bool_type, code_type, dict_type, float_type, int_type, list_type, path_type,
                                 string_type)
from bolt.core.errors import InvalidValueError


def identity(text):
    return text


@pytest.mark.parametrize("raw, expected", [(True, True), ("yes", True), ("off", False), ("0", False), (2, True)])
def test_bool_coercion(raw, expected):
    assert bool_type.coerce(raw) is expected


def test_bool_rejects_unknown_strings():
    with pytest.raises(InvalidValueError):
        bool_type.coerce("maybe")


@pytest.mark.parametrize("raw, expected", [(3, 3), ("12", 12), ("4.0", 4), (2.0, 2), (True, 1)])
def test_int_coercion(raw, expected):
    assert int_type.coerce(raw) == expected


@pytest.mark.parametrize("raw", [2.5, "2.5", "abc", [1]])
def test_int_rejects_lossy_or_invalid_values(raw):
    with pytest.raises(InvalidValueError):
        int_type.coerce(raw)


def test_float_and_string_coercion():
    assert float_type.coerce("1.5") == 1.5
    assert float_type.coerce(2) == 2.0
    assert string_type.coerce(12) == "12"


def test_path_accepts_path_like():
    assert path_type.coerce(pathlib.PurePosixPath("/a/b")) == "/a/b"


def test_list_and_dict_coercion():
    assert list_type.coerce((1, 2)) == [1, 2]
    assert dict_type.coerce({"a": 1}.items().mapping) == {"a": 1}
    with pytest.raises(InvalidValueError):
        list_type.coerce("abc")
    with pytest.raises(InvalidValueError):
        dict_type.coerce([1, 2])


def test_defaults_are_fresh_instances():
    assert list_type.default() == []
    assert list_type.default() is not list_type.default()


def test_needs_expansion():
    assert string_type.needs_expansion("$(SHOT)/file")
    assert not string_type.needs_expansion("plain")
    assert not code_type.needs_expansion("print(`x`)")
    assert int_type.needs_expansion("`1 + 1`")
    assert not int_type.needs_expansion("12")
    assert list_type.needs_expansion(["a", "$(B)"])
    assert dict_type.needs_expansion({"key": "`2`"})


def test_list_resolution_expands_items():
    resolved = list_type.resolve(["a", "$(X)"], lambda text: text.replace("$(X)", "x"))
    assert resolved == ["a", "x"]
