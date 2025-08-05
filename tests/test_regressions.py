"""Regression locks for defects found in the pre-release code.

Each test here corresponds to a bug that shipped silently -- the values
were wrong but nothing raised, so only an assertion catches a return.
"""

from __future__ import annotations

import datetime
import decimal

import pytest
from PySide6 import QtCore, QtWidgets

import brayer
from tests import models


pytestmark = pytest.mark.usefixtures("qapp")


def _find(widget, kind):
    """Return the first descendant widget of a given type.

    Returns:
        The matching child widget.
    """
    found = widget.findChild(kind)
    assert found is not None, f"no {kind.__name__} in form"
    return found


# -------------------------------------------------------------------
# The date/time getters were bound at construction time, so every value
# the user entered was discarded and the widget's initial value returned.
# -------------------------------------------------------------------


def test_date_getter_follows_the_widget():
    dialog = brayer.ModelDialog(models.Primitives)
    edit = _find(dialog._form.widget, QtWidgets.QDateEdit)
    edit.setDate(QtCore.QDate(1995, 6, 15))
    assert dialog._collect()["day"] == datetime.date(1995, 6, 15)


def test_time_getter_follows_the_widget():
    dialog = brayer.ModelDialog(models.Primitives)
    edit = _find(dialog._form.widget, QtWidgets.QTimeEdit)
    edit.setTime(QtCore.QTime(21, 45))
    assert dialog._collect()["clock"] == datetime.time(21, 45)


def test_datetime_getter_follows_the_widget():
    dialog = brayer.ModelDialog(models.Primitives)
    edit = _find(dialog._form.widget, QtWidgets.QDateTimeEdit)
    edit.setDateTime(
        QtCore.QDateTime(QtCore.QDate(2001, 2, 3), QtCore.QTime(4, 5))
    )
    assert dialog._collect()["when"] == datetime.datetime(2001, 2, 3, 4, 5)


# -------------------------------------------------------------------
# Non-string enums rendered as blank combo rows and the getter returned
# the display text rather than the member.
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("enum_type", "expected"),
    [
        (models.Colour, models.Colour.red),
        (models.Priority, models.Priority.low),
        (models.Shade, models.Shade.dark),
    ],
)
def test_enum_returns_the_member_not_a_string(enum_type, expected):
    bound = brayer.dispatch(enum_type)(brayer._registry.field_for(enum_type))
    assert bound.get() is expected


@pytest.mark.parametrize(
    "enum_type", [models.Colour, models.Priority, models.Shade]
)
def test_every_enum_member_has_a_visible_label(enum_type):
    bound = brayer.dispatch(enum_type)(brayer._registry.field_for(enum_type))
    combo = bound.widget
    assert combo.count() == len(list(enum_type))
    for index in range(combo.count()):
        assert combo.itemText(index).strip(), "blank combo entry"


# -------------------------------------------------------------------
# Annotated survived to the dispatcher when nested, matching no handler.
# -------------------------------------------------------------------


def test_nested_annotated_does_not_raise():
    dialog = brayer.ModelDialog(models.Collections)
    assert "positives" in dialog._collect()


def test_annotated_is_stripped_before_dispatch():
    import typing

    import annotated_types as at

    handler = brayer.dispatch(typing.Annotated[int, at.Gt(0)])
    assert handler is brayer.dispatch(int)


# -------------------------------------------------------------------
# A single QApplication is a process-wide singleton; building a second
# one raised and left the process unusable.
# -------------------------------------------------------------------


def test_two_dialogs_in_one_process():
    first = brayer.ModelDialog(models.Person)
    second = brayer.ModelDialog(models.Person)
    assert first is not second


# -------------------------------------------------------------------
# Field defaults and constraints were never read at all.
# -------------------------------------------------------------------


def test_defaults_prefill_widgets():
    dialog = brayer.ModelDialog(models.Primitives)
    values = dialog._collect()
    assert values["text"] == "hello"
    assert values["count"] == 7
    assert values["money"] == decimal.Decimal("2.50")
    assert values["day"] == datetime.date(2020, 1, 2)


def test_inclusive_constraints_reach_the_spinbox():
    dialog = brayer.ModelDialog(models.Constrained)
    spins = dialog._form.widget.findChildren(QtWidgets.QSpinBox)
    ranges = {(s.minimum(), s.maximum()) for s in spins}
    assert (0, 150) in ranges


def test_exclusive_constraints_are_converted_to_inclusive():
    dialog = brayer.ModelDialog(models.Constrained)
    spins = dialog._form.widget.findChildren(QtWidgets.QSpinBox)
    ranges = {(s.minimum(), s.maximum()) for s in spins}
    assert (1, 9) in ranges, "gt=0, lt=10 should become 1..9"


def test_max_length_reaches_the_line_edit():
    dialog = brayer.ModelDialog(models.Constrained)
    edits = dialog._form.widget.findChildren(QtWidgets.QLineEdit)
    assert any(edit.maxLength() == 8 for edit in edits)


# -------------------------------------------------------------------
# Literal values sharing a str() collapsed into one combo entry.
# -------------------------------------------------------------------


def test_literals_with_equal_text_stay_distinct():
    import typing

    bound = brayer.dispatch(typing.Literal[1, "1"])(
        brayer._registry.field_for(typing.Literal[1, "1"])
    )
    combo = bound.widget
    assert combo.count() == 2
    assert combo.itemText(0) != combo.itemText(1)
    combo.setCurrentIndex(0)
    assert bound.get() == 1
    combo.setCurrentIndex(1)
    assert bound.get() == "1"


# -------------------------------------------------------------------
# Collection editors round-tripped through repr()/ast.literal_eval,
# which destroyed any value that is not a Python literal.
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        datetime.date(2020, 5, 6),
        decimal.Decimal("1.25"),
        models.Colour.green,
        models.Priority.high,
        datetime.timedelta(seconds=30),
    ],
)
def test_list_editor_preserves_non_literal_values(value):
    editor = brayer.ListEditWidget()
    editor.add_value(value)
    assert editor.get_values() == [value]


def test_dict_editor_preserves_non_literal_values():
    editor = brayer.DictEditWidget()
    editor.add_pair("when", datetime.date(2020, 5, 6))
    assert editor.get_dict() == {"when": datetime.date(2020, 5, 6)}


def test_removed_dict_key_can_be_added_again():
    editor = brayer.DictEditWidget()
    assert editor.add_pair("k", 1)
    editor.selectRow(0)
    editor.remove_selected()
    assert editor.rowCount() == 0
    assert editor.add_pair("k", 2), "key set leaked the removed key"
    assert editor.get_dict() == {"k": 2}


def test_duplicate_dict_key_is_rejected():
    editor = brayer.DictEditWidget()
    assert editor.add_pair("k", 1)
    assert not editor.add_pair("k", 2)
    assert editor.get_dict() == {"k": 1}


def test_unhashable_dict_key_is_rejected():
    editor = brayer.DictEditWidget()
    assert not editor.add_pair(["not", "hashable"], 1)
    assert editor.rowCount() == 0
