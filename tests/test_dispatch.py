"""Dispatch, registration, and the behaviour of each handler family."""

from __future__ import annotations

import datetime
import decimal
import ipaddress
import pathlib
import typing
import uuid

import pytest
from PySide6 import QtWidgets

import brayer
from brayer._registry import bind_annotation, field_for
from tests import models


pytestmark = pytest.mark.usefixtures("qapp")


@pytest.mark.parametrize(
    ("annotation", "widget_type"),
    [
        (int, QtWidgets.QSpinBox),
        (float, QtWidgets.QDoubleSpinBox),
        (decimal.Decimal, QtWidgets.QDoubleSpinBox),
        (str, QtWidgets.QLineEdit),
        (bool, QtWidgets.QCheckBox),
        (bytes, QtWidgets.QLineEdit),
        (datetime.datetime, QtWidgets.QDateTimeEdit),
        (datetime.date, QtWidgets.QDateEdit),
        (datetime.time, QtWidgets.QTimeEdit),
        (datetime.timedelta, QtWidgets.QDoubleSpinBox),
        (uuid.UUID, QtWidgets.QLineEdit),
        (models.Colour, QtWidgets.QComboBox),
        (typing.Literal["a", "b"], QtWidgets.QComboBox),
        (models.Address, QtWidgets.QPushButton),
    ],
)
def test_annotation_maps_to_expected_widget(annotation, widget_type):
    bound = bind_annotation(annotation)
    assert isinstance(bound.widget, widget_type)


@pytest.mark.parametrize(
    ("annotation", "expected_type"),
    [
        (int, int),
        (float, float),
        (decimal.Decimal, decimal.Decimal),
        (str, str),
        (bool, bool),
        (bytes, bytes),
        (datetime.date, datetime.date),
        (datetime.time, datetime.time),
        (datetime.timedelta, datetime.timedelta),
        (uuid.UUID, uuid.UUID),
        (pathlib.Path, pathlib.Path),
        (ipaddress.IPv4Address, ipaddress.IPv4Address),
        (list[str], list),
        (set[str], set),
        (frozenset[str], frozenset),
        (dict[str, int], dict),
        (tuple[int, str], tuple),
    ],
)
def test_getter_returns_the_declared_type(annotation, expected_type):
    bound = bind_annotation(annotation)
    assert isinstance(bound.get(), expected_type)


def test_none_type_returns_none():
    assert bind_annotation(type(None)).get() is None


def test_unsupported_type_raises():
    with pytest.raises(brayer.UnsupportedTypeError) as excinfo:
        brayer.dispatch(complex)
    assert "complex" in str(excinfo.value)


def test_unsupported_error_is_a_notimplementederror():
    # Code written against the pre-rename releases caught this.
    assert issubclass(brayer.UnsupportedTypeError, NotImplementedError)


def test_model_with_unsupported_field_raises():
    with pytest.raises(brayer.UnsupportedTypeError):
        brayer.ModelDialog(models.Unsupported)


def test_register_handler_extends_dispatch():
    class Custom:
        pass

    @brayer.register_handler(exact=[Custom])
    def handle_custom(field):
        widget = QtWidgets.QLineEdit()
        return brayer.Bound(widget, Custom, None)

    try:
        assert isinstance(bind_annotation(Custom).get(), Custom)
    finally:
        brayer._registry._EXACT.pop(Custom, None)


def test_bare_container_annotations_work():
    listing = bind_annotation(list)
    mapping = bind_annotation(dict)
    assert listing.get() == []
    assert mapping.get() == {}


def test_union_selector_switches_type():
    bound = bind_annotation(typing.Union[str, int])
    combo = bound.widget.findChild(QtWidgets.QComboBox)
    stack = bound.widget.findChild(QtWidgets.QStackedWidget)
    combo.setCurrentIndex(0)
    assert isinstance(bound.get(), str)
    combo.setCurrentIndex(1)
    assert stack.currentIndex() == 1
    assert isinstance(bound.get(), int)


def test_optional_labels_the_none_branch():
    bound = bind_annotation(typing.Optional[str])
    combo = bound.widget.findChild(QtWidgets.QComboBox)
    labels = [combo.itemText(i) for i in range(combo.count())]
    assert "None" in labels


def test_optional_defaults_to_the_none_branch():
    bound = brayer.dispatch(typing.Optional[str])(
        field_for(typing.Optional[str], default=None)
    )
    assert bound.get() is None


def test_pipe_union_matches_typing_union():
    assert brayer.dispatch(str | int) is brayer.dispatch(typing.Union[str, int])


def test_fixed_tuple_has_one_widget_per_slot():
    bound = bind_annotation(tuple[int, str])
    assert isinstance(bound.get(), tuple)
    assert len(bound.get()) == 2


def test_variadic_tuple_uses_the_list_editor():
    bound = bind_annotation(tuple[int, ...])
    assert bound.widget.findChild(brayer.ListEditWidget) is not None


def test_list_editor_collects_added_items():
    bound = bind_annotation(list[str])
    editor = bound.widget.findChild(brayer.ListEditWidget)
    editor.add_value("x")
    editor.add_value("y")
    assert bound.get() == ["x", "y"]


def test_set_deduplicates():
    bound = bind_annotation(set[str])
    editor = bound.widget.findChild(brayer.ListEditWidget)
    editor.add_value("x")
    editor.add_value("x")
    assert bound.get() == {"x"}


def test_dict_editor_collects_pairs():
    bound = bind_annotation(dict[str, int])
    table = bound.widget.findChild(brayer.DictEditWidget)
    table.add_pair("a", 1)
    table.add_pair("b", 2)
    assert bound.get() == {"a": 1, "b": 2}
