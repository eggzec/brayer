"""The dialog that renders a model and validates what comes back."""

from __future__ import annotations

import typing

import pydantic
from PySide6 import QtCore, QtWidgets

from ._errors import WidgetBuildError
from .handlers.pydantic_types import build_model_form


__all__ = ["ModelDialog"]

ModelT = typing.TypeVar("ModelT", bound=pydantic.BaseModel)

_MAX_INITIAL_HEIGHT = 720
_MAX_INITIAL_WIDTH = 900


class ModelDialog(QtWidgets.QDialog, typing.Generic[ModelT]):
    """A modal form generated from a pydantic model.

    Use this directly to embed the form in an application that already
    runs a Qt event loop. :func:`brayer.ask` is a thin wrapper for the
    one-shot case.

    The dialog only closes on OK once the collected values validate. If
    they do not, the pydantic errors are shown beneath the form and the
    dialog stays open so the entries can be corrected.

    Example:
        >>> dialog = ModelDialog(Person)  # doctest: +SKIP
        >>> if dialog.exec():  # doctest: +SKIP
        ...     print(dialog.value)  # doctest: +SKIP
    """

    def __init__(
        self,
        model: type[ModelT],
        *,
        initial: ModelT | None = None,
        title: str | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Build a dialog for a model.

        Args:
            model: The model class to render.
            initial: An existing instance to pre-fill the form with.
            title: Window title. Defaults to the model's class name.
            parent: The owning widget, if any.

        Raises:
            UnresolvedAnnotationError: The model has unresolved forward
                references.
            UnsupportedTypeError: A field's type has no handler.
        """
        super().__init__(parent)
        self._model = model
        self._value: ModelT | None = None

        self.setWindowTitle(title or getattr(model, "__name__", "Input"))

        self._form = build_model_form(model, self)
        self._collect = self._form.collect
        if initial is not None:
            self._prefill(initial)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(self._form.widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)

        self._errors = QtWidgets.QLabel()
        self._errors.setWordWrap(True)
        self._errors.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self._errors.setStyleSheet("color: palette(bright-text);")
        self._errors.hide()

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._try_accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._errors)
        layout.addWidget(buttons)

        self._size_to_content()

    @property
    def value(self) -> ModelT | None:
        """The validated model, or ``None`` if the dialog was cancelled."""
        return self._value

    def _prefill(self, initial: ModelT) -> None:
        """Show an existing instance's values in the form.

        Pre-filling is best-effort: a handler need not provide a setter,
        and a value that will not load is not a reason to refuse to open
        the dialog at all.

        Args:
            initial: The instance whose values should be shown.
        """
        for name, setter in self._form.setters.items():
            if not hasattr(initial, name):
                continue
            try:
                setter(getattr(initial, name))
            except (TypeError, ValueError, OverflowError, AttributeError):
                continue

    def _size_to_content(self) -> None:
        """Open at the form's natural size, capped to the screen."""
        hint = self.sizeHint()
        width = min(max(hint.width(), 420), _MAX_INITIAL_WIDTH)
        height = min(max(hint.height(), 240), _MAX_INITIAL_HEIGHT)
        screen = QtWidgets.QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            width = min(width, available.width() - 80)
            height = min(height, available.height() - 80)
        self.resize(width, height)

    def _try_accept(self) -> None:
        """Validate the form and close only if it passes."""
        try:
            values = self._collect()
        except WidgetBuildError as exc:
            self._show_errors(str(exc))
            return

        try:
            self._value = self._model.model_validate(values)
        except pydantic.ValidationError as exc:
            self._show_errors(_format_errors(exc))
            return

        self._errors.hide()
        self.accept()

    def _show_errors(self, text: str) -> None:
        """Display a validation message beneath the form.

        Args:
            text: The message to show.
        """
        self._errors.setText(text)
        self._errors.show()


def _format_errors(error: pydantic.ValidationError) -> str:
    """Render a validation error as short per-field lines.

    Args:
        error: The error pydantic raised.

    Returns:
        One ``field: message`` line per problem.
    """
    lines = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "?"
        lines.append(f"{location}: {item.get('msg', 'invalid')}")
    return "\n".join(lines)
