"""Interaction paths: nested dialogs, setters, and widget behaviour."""

from __future__ import annotations

import datetime
import typing

import pytest
from PySide6 import QtCore, QtWidgets

import brayer
from brayer import _errors
from brayer._registry import bind_annotation, field_for
from tests import models


pytestmark = pytest.mark.usefixtures("qapp")


def _close_modal(*, accept: bool) -> None:
    """Close whatever modal dialog is currently on screen."""
    dialog = QtWidgets.QApplication.activeModalWidget()
    if dialog is None:
        return
    if accept:
        dialog.accept()
    else:
        dialog.reject()


def _dismiss_popup(attempts: int = 40) -> None:
    """Close the open context menu, retrying until it appears.

    A QMenu is a *popup*, not a modal widget, so it never shows up in
    ``activeModalWidget()`` -- a timer waiting on that would never fire
    and the menu's own event loop would run forever. Retrying against
    ``activePopupWidget()`` closes it whenever it opens, and giving up
    after a bounded number of attempts means a change in Qt's behaviour
    fails the test rather than hanging the whole suite.
    """
    popup = QtWidgets.QApplication.activePopupWidget()
    if popup is not None:
        popup.close()
        return
    if attempts > 0:
        QtCore.QTimer.singleShot(5, lambda: _dismiss_popup(attempts - 1))


# ------------------------------------------------------- nested models


def test_nested_dialog_opens_and_accepts():
    bound = bind_annotation(models.Address)
    QtCore.QTimer.singleShot(0, lambda: _close_modal(accept=True))
    bound.widget.click()
    assert bound.get() == {"street": "Main St", "postcode": "0000"}


def test_nested_cancel_restores_previous_values():
    bound = bind_annotation(models.Address)

    # Open once, edit, accept -> the edit is kept.
    def edit_and_accept():
        dialog = QtWidgets.QApplication.activeModalWidget()
        dialog.findChild(QtWidgets.QLineEdit).setText("Changed")
        dialog.accept()

    QtCore.QTimer.singleShot(0, edit_and_accept)
    bound.widget.click()
    assert bound.get()["street"] == "Changed"

    # Open again, edit, cancel -> the edit is discarded.
    def edit_and_reject():
        dialog = QtWidgets.QApplication.activeModalWidget()
        dialog.findChild(QtWidgets.QLineEdit).setText("Discarded")
        dialog.reject()

    QtCore.QTimer.singleShot(0, edit_and_reject)
    bound.widget.click()
    assert bound.get()["street"] == "Changed", "cancel kept the edit"


def test_nested_setter_accepts_a_model():
    bound = bind_annotation(models.Address)
    bound.set(models.Address(street="Elm", postcode="1234"))
    assert bound.get()["street"] == "Elm"


def test_nested_setter_accepts_a_mapping():
    bound = bind_annotation(models.Address)
    bound.set({"street": "Oak", "postcode": "9999"})
    assert bound.get()["street"] == "Oak"


def test_unresolved_forward_reference_is_reported():
    import pydantic

    # A reference to a name that is never importable. pydantic leaves
    # the model incomplete rather than raising at class-creation time,
    # so the failure only surfaces when the form is built.
    broken = pydantic.create_model(
        "Broken", other=(typing.ForwardRef("NeverDefinedAnywhere"), ...)
    )
    with pytest.raises(brayer.UnresolvedAnnotationError):
        brayer.ModelDialog(broken)


# ------------------------------------------------------- special forms


def test_union_setter_selects_the_matching_branch():
    bound = bind_annotation(typing.Union[str, int])
    bound.set(42)
    assert bound.get() == 42
    bound.set("text")
    assert bound.get() == "text"


def test_union_setter_ignores_a_value_with_no_branch():
    bound = bind_annotation(typing.Union[str, int])
    before = bound.get()
    bound.set(datetime.date(2020, 1, 1))
    assert bound.get() == before


def test_optional_setter_selects_none():
    bound = bind_annotation(typing.Optional[str])
    bound.set(None)
    assert bound.get() is None


def test_union_preselects_a_non_none_default():
    annotation = typing.Union[str, int]
    bound = brayer.dispatch(annotation)(field_for(annotation, default=7))
    assert bound.get() == 7


def test_literal_setter_selects_the_value():
    annotation = typing.Literal["a", "b", "c"]
    bound = bind_annotation(annotation)
    bound.set("c")
    assert bound.get() == "c"


def test_literal_default_is_preselected():
    annotation = typing.Literal["a", "b"]
    bound = brayer.dispatch(annotation)(field_for(annotation, default="b"))
    assert bound.get() == "b"


# ------------------------------------------------------------- widgets


def test_list_editor_set_values_replaces_contents():
    editor = brayer.ListEditWidget()
    editor.add_value("old")
    editor.set_values(["a", "b"])
    assert editor.get_values() == ["a", "b"]


def test_list_editor_remove_selected():
    editor = brayer.ListEditWidget()
    editor.set_values(["a", "b", "c"])
    editor.item(1).setSelected(True)
    editor.remove_selected()
    assert editor.get_values() == ["a", "c"]


def test_list_editor_clear_values():
    editor = brayer.ListEditWidget()
    editor.set_values(["a", "b"])
    editor.clear_values()
    assert editor.get_values() == []


def test_list_editor_emits_on_change():
    editor = brayer.ListEditWidget()
    seen = []
    editor.contents_changed.connect(lambda: seen.append(1))
    editor.add_value("x")
    assert seen


def test_dict_editor_set_mapping():
    editor = brayer.DictEditWidget()
    editor.set_mapping({"a": 1, "b": 2})
    assert editor.get_dict() == {"a": 1, "b": 2}


def test_dict_editor_reports_rejection_reason():
    editor = brayer.DictEditWidget()
    reasons = []
    editor.rejected_key.connect(reasons.append)
    editor.add_pair("k", 1)
    editor.add_pair("k", 2)
    assert reasons and "already exists" in reasons[0]


def test_dict_editor_keys():
    editor = brayer.DictEditWidget()
    editor.set_mapping({"a": 1})
    assert editor.keys() == ["a"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("plain", "plain"),
        (models.Colour.red, "Red"),
        (b"bytes", "bytes"),
        (models.Priority.high, "high"),
        (7, "7"),
    ],
)
def test_format_value(value, expected):
    from brayer.widgets import format_value

    assert format_value(value) == expected


def test_list_context_menu_builds():
    editor = brayer.ListEditWidget()
    editor.set_values(["a"])
    editor.item(0).setSelected(True)
    QtCore.QTimer.singleShot(0, _dismiss_popup)
    editor._show_context_menu(QtCore.QPoint(1, 1))
    assert editor.get_values() == ["a"]


def test_dict_context_menu_builds():
    editor = brayer.DictEditWidget()
    editor.set_mapping({"a": 1})
    editor.selectRow(0)
    QtCore.QTimer.singleShot(0, _dismiss_popup)
    editor._show_context_menu(QtCore.QPoint(1, 1))
    assert editor.keys() == ["a"]


# -------------------------------------------------------------- errors


def test_unsupported_type_error_names_the_type():
    error = _errors.UnsupportedTypeError(complex)
    assert "complex" in str(error)
    assert error.field_type is complex


def test_unresolved_annotation_error_names_the_model():
    error = _errors.UnresolvedAnnotationError(models.Person, "detail here")
    assert "Person" in str(error)
    assert "detail here" in str(error)
    assert "model_rebuild" in str(error)


def test_widget_build_error_names_the_field():
    error = _errors.WidgetBuildError("age", ValueError("bad"))
    assert "age" in str(error)
    assert "bad" in str(error)


def test_widget_build_error_without_cause():
    assert "age" in str(_errors.WidgetBuildError("age"))


def test_field_label_prefers_the_title():
    class HasTitle:
        title = "Nice Name"

    assert _errors.field_label(HasTitle()) == "Nice Name"
    assert _errors.field_label(object(), "fallback") == "fallback"


# ------------------------------------------------------------- prompts


def test_ask_returns_the_validated_model(monkeypatch):
    def fake_exec(self):
        for edit in self._form.widget.findChildren(QtWidgets.QLineEdit):
            edit.setText("Ada")
        self._try_accept()
        return QtWidgets.QDialog.DialogCode.Accepted

    monkeypatch.setattr(brayer._prompt.ModelDialog, "exec", fake_exec)
    person = brayer.ask(models.Person)
    assert isinstance(person, models.Person)
    assert person.name == "Ada"


def test_edit_prefills_from_the_instance(monkeypatch):
    original = models.Person(
        name="Grace", age=45, birthday=datetime.date(1906, 12, 9)
    )
    captured = {}

    def fake_exec(self):
        captured.update(self._collect())
        return QtWidgets.QDialog.DialogCode.Rejected

    monkeypatch.setattr(brayer._prompt.ModelDialog, "exec", fake_exec)
    assert brayer.edit(original) is None
    assert captured["name"] == "Grace"


# --------------------------------------------------------- constraints


def test_constraints_of_an_object_without_metadata_are_empty():
    from brayer._constraints import read_constraints

    assert read_constraints(object()).ge is None


def test_float_range_steps_inward_from_exclusive_bounds():
    from brayer._constraints import Constraints

    low, high = Constraints(gt=0.0, lt=10.0).float_range(step=0.5)
    assert low == 0.5
    assert high == 9.5


def test_reversed_bounds_are_normalised():
    from brayer._constraints import Constraints

    assert Constraints(ge=10, le=1).int_range() == (1, 10)


def test_multiple_of_becomes_the_step():
    from brayer._constraints import Constraints

    assert Constraints(multiple_of=0.25).step() == 0.25


def test_decimal_places_drive_precision_and_step():
    from brayer._constraints import Constraints

    limits = Constraints(decimal_places=3)
    assert limits.decimals() == 3
    assert limits.step() == pytest.approx(0.001)
