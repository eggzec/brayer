"""Handlers for pydantic's own types.

The important one is the nested model: a ``BaseModel``-typed field is
rendered as a button that opens a sub-form, rather than being inlined.

The sub-form is built **lazily**, the first time the button is pressed.
Building eagerly meant a model referring to itself -- directly or through
a cycle -- recursed until the interpreter gave up, before the window had
even appeared. Deferring construction bounds the work to the depth the
user actually opens.
"""

from __future__ import annotations

import typing

import pydantic
from pydantic import fields
from PySide6 import QtWidgets

from brayer._errors import (
    UnresolvedAnnotationError,
    UnsupportedTypeError,
    WidgetBuildError,
)
from brayer._registry import (
    Bound,
    apply_default,
    bind,
    describe,
    is_model,
    register_handler,
)


__all__ = [
    "ModelForm",
    "build_model_form",
    "handle_nested_model",
    "payload_key",
]


class ModelForm(typing.NamedTuple):
    """A built form: the widget, how to read it, how to fill it."""

    widget: QtWidgets.QWidget
    """The container holding one labelled row per field."""

    collect: typing.Callable[[], dict[str, object]]
    """Read every widget, keyed ready for validation."""

    setters: dict[str, typing.Callable[[object], None]]
    """Per-attribute setters, for pre-filling from an instance."""


def payload_key(name: str, field: fields.FieldInfo) -> str:
    """Return the key a field's value must be submitted under.

    A model that declares an alias and does not set
    ``populate_by_name`` can only be validated from the alias, so the
    collected values have to be keyed by it rather than by the attribute
    name.

    Args:
        name: The attribute name on the model.
        field: The field's metadata.

    Returns:
        The alias when one is usable, otherwise the attribute name.
    """
    alias = field.validation_alias or field.alias
    if isinstance(alias, str) and alias:
        return alias
    return name


def build_model_form(
    model: type[pydantic.BaseModel], parent: QtWidgets.QWidget | None = None
) -> ModelForm:
    """Build a form holding one labelled row per model field.

    Args:
        model: The model class to render.
        parent: Widget to own the returned container.

    Returns:
        A :class:`ModelForm` holding the container, a callable that
        reads every widget, and the per-field setters.

    Raises:
        UnresolvedAnnotationError: The model has forward references that
            pydantic has not resolved, so its fields cannot be read.
        WidgetBuildError: A field's widget could not be built.
    """
    model_fields = _model_fields(model)

    container = QtWidgets.QWidget(parent)
    layout = QtWidgets.QFormLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setFieldGrowthPolicy(
        QtWidgets.QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
    )

    getters: dict[str, typing.Callable[[], object]] = {}
    setters: dict[str, typing.Callable[[object], None]] = {}

    for name, field in model_fields.items():
        try:
            bound = bind(field)
        except Exception as exc:  # re-raised with context below
            if isinstance(
                exc,
                (
                    UnresolvedAnnotationError,
                    UnsupportedTypeError,
                    WidgetBuildError,
                ),
            ):
                raise
            raise WidgetBuildError(name, exc) from exc

        label = QtWidgets.QLabel(describe(field, name))
        if field.description:
            label.setToolTip(field.description)
            bound.widget.setToolTip(field.description)
        layout.addRow(label, bound.widget)
        getters[payload_key(name, field)] = bound.get
        if bound.set is not None:
            setters[name] = bound.set

    def collect() -> dict[str, object]:
        values: dict[str, object] = {}
        for key, getter in getters.items():
            try:
                values[key] = getter()
            except Exception as exc:  # re-raised with context below
                raise WidgetBuildError(key, exc) from exc
        return values

    return ModelForm(container, collect, setters)


def _model_fields(
    model: type[pydantic.BaseModel],
) -> dict[str, fields.FieldInfo]:
    """Return a model's fields, rebuilding it if necessary.

    Args:
        model: The model class to inspect.

    Returns:
        The mapping of attribute name to field metadata.

    Raises:
        UnresolvedAnnotationError: The model could not be rebuilt, so
            its annotations remain unresolvable.
    """
    if not getattr(model, "__pydantic_complete__", True):
        try:
            model.model_rebuild()
        except Exception as exc:  # surfaced as our own error type
            raise UnresolvedAnnotationError(model, str(exc)) from exc
    if not getattr(model, "__pydantic_complete__", True):
        raise UnresolvedAnnotationError(model)
    return dict(model.__pydantic_fields__)


@register_handler(predicate=is_model)
def handle_nested_model(field: fields.FieldInfo) -> Bound:
    """Build a button that opens a nested model's own form.

    Cancelling the sub-dialog restores the values the sub-form held when
    it was opened, so a nested Cancel really does discard the edit
    instead of silently keeping it.

    Args:
        field: The field being rendered. Its annotation is the nested
            model class.

    Returns:
        The button with accessors reading the sub-form's values.
    """
    model = typing.cast("type[pydantic.BaseModel]", field.annotation)
    name = getattr(model, "__name__", "model")

    button = QtWidgets.QPushButton(f"Edit {name}...")
    state: dict[str, object] = {"dialog": None, "collect": None, "values": None}

    def ensure_built() -> None:
        if state["dialog"] is not None:
            return
        dialog = QtWidgets.QDialog(button)
        dialog.setWindowTitle(name)
        form = build_model_form(model, dialog)
        collect = form.collect
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(form.widget)
        layout.addWidget(buttons)
        state["dialog"] = dialog
        state["collect"] = collect

    def open_dialog() -> None:
        ensure_built()
        dialog = typing.cast("QtWidgets.QDialog", state["dialog"])
        collect = typing.cast(
            "typing.Callable[[], dict[str, object]]", state["collect"]
        )
        before = collect()
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            state["values"] = collect()
        else:
            state["values"] = before

    button.clicked.connect(open_dialog)

    def get() -> dict[str, object]:
        if state["values"] is not None:
            return typing.cast("dict[str, object]", state["values"])
        ensure_built()
        collect = typing.cast(
            "typing.Callable[[], dict[str, object]]", state["collect"]
        )
        return collect()

    def set_(value: object) -> None:
        if isinstance(value, pydantic.BaseModel):
            state["values"] = value.model_dump()
        elif isinstance(value, dict):
            state["values"] = dict(value)

    bound = Bound(button, get, set_)
    apply_default(field, bound)
    return bound
