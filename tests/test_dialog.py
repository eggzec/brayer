"""The dialog: validation, cancellation, pre-fill and the CLI."""

from __future__ import annotations

import datetime

import pytest
from PySide6 import QtCore, QtWidgets

import brayer
from brayer import _cli
from tests import models


pytestmark = pytest.mark.usefixtures("qapp")


def _accept_soon(dialog):
    """Click OK once the modal loop is running."""
    QtCore.QTimer.singleShot(0, dialog._try_accept)


def _reject_soon(dialog):
    """Click Cancel once the modal loop is running."""
    QtCore.QTimer.singleShot(0, dialog.reject)


def test_accepting_returns_a_validated_model():
    dialog = brayer.ModelDialog(models.Person)
    for edit in dialog._form.widget.findChildren(QtWidgets.QLineEdit):
        edit.setText("Ada")
    _accept_soon(dialog)
    assert dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
    assert isinstance(dialog.value, models.Person)
    assert dialog.value.name == "Ada"


def test_cancelling_leaves_value_none():
    dialog = brayer.ModelDialog(models.Person)
    _reject_soon(dialog)
    assert dialog.exec() == QtWidgets.QDialog.DialogCode.Rejected
    assert dialog.value is None


def test_invalid_input_keeps_the_dialog_open():
    dialog = brayer.ModelDialog(models.Person)
    # `name` is required and the line edit starts empty, which is fine;
    # force a real failure by driving age below its ge=0 bound.
    spin = dialog._form.widget.findChild(QtWidgets.QSpinBox)
    spin.setMinimum(-100)
    spin.setValue(-1)
    dialog._try_accept()
    assert dialog.value is None
    assert dialog._errors.isVisibleTo(dialog)
    assert "age" in dialog._errors.text()


def test_validation_errors_clear_after_a_fix():
    dialog = brayer.ModelDialog(models.Person)
    spin = dialog._form.widget.findChild(QtWidgets.QSpinBox)
    spin.setMinimum(-100)
    spin.setValue(-1)
    dialog._try_accept()
    assert dialog._errors.isVisibleTo(dialog)
    spin.setValue(30)
    dialog._try_accept()
    assert dialog.value is not None


def test_prefill_shows_an_existing_instance():
    original = models.Person(
        name="Grace", age=45, birthday=datetime.date(1906, 12, 9)
    )
    dialog = brayer.ModelDialog(models.Person, initial=original)
    values = dialog._collect()
    assert values["name"] == "Grace"
    assert values["age"] == 45
    assert values["birthday"] == datetime.date(1906, 12, 9)


def test_title_defaults_to_the_model_name():
    assert brayer.ModelDialog(models.Person).windowTitle() == "Person"


def test_title_can_be_overridden():
    dialog = brayer.ModelDialog(models.Person, title="Who are you?")
    assert dialog.windowTitle() == "Who are you?"


def test_dialog_is_wide_enough_to_show_its_buttons():
    dialog = brayer.ModelDialog(models.Collections)
    assert dialog.width() >= 420
    assert dialog.height() >= 240


def test_aliased_model_validates():
    dialog = brayer.ModelDialog(models.Aliased)
    assert "givenName" in dialog._collect()
    dialog._try_accept()
    assert dialog.value is not None


def test_self_referential_model_does_not_recurse():
    # The nested form is built lazily, so a cycle costs nothing until
    # the user actually opens it.
    dialog = brayer.ModelDialog(models.Node)
    assert dialog is not None


def test_nested_model_collects_a_mapping():
    dialog = brayer.ModelDialog(models.Person)
    assert isinstance(dialog._collect()["address"], dict)


def test_ask_returns_none_when_cancelled(monkeypatch):
    monkeypatch.setattr(
        brayer._prompt.ModelDialog,
        "exec",
        lambda self: QtWidgets.QDialog.DialogCode.Rejected,
    )
    assert brayer.ask(models.Person) is None


def test_ask_reuses_the_existing_application():
    before = QtWidgets.QApplication.instance()
    brayer._prompt._ensure_app()
    assert QtWidgets.QApplication.instance() is before


# ------------------------------------------------------------------ CLI


def test_debug_info_reports_the_environment():
    report = _cli.debug_info()
    assert "Python version:" in report
    assert "Dependencies:" in report


def test_dependency_versions_uses_public_metadata():
    versions = _cli.dependency_versions("pydantic")
    assert isinstance(versions, dict)


def test_dependency_versions_of_missing_package_is_empty():
    assert _cli.dependency_versions("no-such-distribution-xyz") == {}


def test_cli_version(capsys):
    assert _cli.main(["--version"]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_debug(capsys):
    assert _cli.main(["--debug"]) == 0
    assert "Architecture:" in capsys.readouterr().out


def test_cli_no_args_prints_help(capsys):
    assert _cli.main([]) == 0
    assert "usage" in capsys.readouterr().out.lower()


# -------------------------------------------------------- public surface


def test_every_export_is_importable():
    for name in brayer.__all__:
        assert hasattr(brayer, name), name


def test_version_is_a_string():
    assert isinstance(brayer.__version__, str)
    assert brayer.__version__
