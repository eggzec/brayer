"""The one-shot entry points: show a form, get a model back."""

from __future__ import annotations

import sys
import typing

import pydantic
from PySide6 import QtWidgets

from ._dialog import ModelDialog


__all__ = ["ask", "edit"]

ModelT = typing.TypeVar("ModelT", bound=pydantic.BaseModel)

# Keeps an application we created alive for the lifetime of the process.
# Qt destroys widgets belonging to a QApplication that gets garbage
# collected, so dropping this reference would break the next call. A
# list rather than a module-level rebind, so no `global` is needed.
_OWNED_APP: list[QtWidgets.QApplication] = []


def _ensure_app() -> QtWidgets.QApplication:
    """Return the running QApplication, creating one if needed.

    Qt permits exactly one ``QApplication`` per process. An earlier
    version constructed a fresh one on every call, so a second call
    raised ``RuntimeError`` and the library could not be used twice, nor
    from inside an application that already had an event loop.

    Returns:
        The application instance to run dialogs against.
    """
    existing = QtWidgets.QApplication.instance()
    if existing is not None:
        return typing.cast("QtWidgets.QApplication", existing)

    # argv[:1] keeps Qt from trying to interpret the caller's own flags.
    app = QtWidgets.QApplication(sys.argv[:1])
    _OWNED_APP.append(app)
    return app


def ask(
    model: type[ModelT],
    *,
    initial: ModelT | None = None,
    title: str | None = None,
    parent: QtWidgets.QWidget | None = None,
) -> ModelT | None:
    """Show a form for a model and return what the user entered.

    Blocks until the dialog is closed. The returned instance has already
    been validated by pydantic -- the dialog refuses to close on OK
    until the entries pass, so a non-``None`` result is always valid.

    Args:
        model: The model class to build the form from.
        initial: An existing instance to pre-fill the form with.
        title: Window title. Defaults to the model's class name.
        parent: Owning widget, when embedding in an existing UI.

    Returns:
        The validated instance, or ``None`` if the user cancelled or
        closed the window. Cancelling is reported distinctly rather than
        as an empty result.

    Raises:
        UnsupportedTypeError: A field's type has no registered handler.
        UnresolvedAnnotationError: The model has unresolved forward
            references.

    Example:
        >>> class Person(BaseModel):  # doctest: +SKIP
        ...     name: str
        ...     age: int
        >>> person = ask(Person)  # doctest: +SKIP
        >>> if person is not None:  # doctest: +SKIP
        ...     print(person.name)  # doctest: +SKIP
    """
    _ensure_app()
    dialog = ModelDialog(model, initial=initial, title=title, parent=parent)
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.value
    return None


def edit(
    instance: ModelT,
    *,
    title: str | None = None,
    parent: QtWidgets.QWidget | None = None,
) -> ModelT | None:
    """Show a form pre-filled from an existing instance.

    Args:
        instance: The object to edit. It is never mutated; a new
            validated instance is returned instead.
        title: Window title. Defaults to the model's class name.
        parent: Owning widget, when embedding in an existing UI.

    Returns:
        A new validated instance carrying the edits, or ``None`` if the
        user cancelled.

    Raises:
        UnsupportedTypeError: A field's type has no registered handler.

    Example:
        >>> updated = edit(person)  # doctest: +SKIP
    """
    return ask(type(instance), initial=instance, title=title, parent=parent)
