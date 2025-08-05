"""Turn a pydantic model into a desktop form.

Declare the shape once, as types, and get the dialog for free::

    import datetime
    from pydantic import BaseModel
    import brayer


    class Person(BaseModel):
        name: str
        age: int
        birthday: datetime.date


    person = brayer.ask(Person)  # a form appears; returns a Person

``ask`` blocks until the dialog closes and returns a **validated**
instance, or ``None`` if the user cancelled.

To embed the same form in an application that already runs a Qt event
loop, use :class:`ModelDialog` directly. To support a type the package
does not know about, register a handler for it -- see
:func:`register_handler`.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from . import handlers
from ._dialog import ModelDialog
from ._errors import (
    InputError,
    UnresolvedAnnotationError,
    UnsupportedTypeError,
    WidgetBuildError,
)
from ._prompt import ask, edit
from ._registry import Bound, FieldHandler, dispatch, register_handler
from .widgets import DictEditWidget, ListEditWidget


# Importing `handlers` above is what registers every built-in type
# with the dispatcher; the module is re-exported so the import is not
# mistaken for an unused one.


try:
    __version__ = version("brayer")
except PackageNotFoundError:  # pragma: no cover - running from a checkout
    __version__ = "0.0.0"


__all__ = [
    "Bound",
    "DictEditWidget",
    "FieldHandler",
    "InputError",
    "ListEditWidget",
    "ModelDialog",
    "UnresolvedAnnotationError",
    "UnsupportedTypeError",
    "WidgetBuildError",
    "__version__",
    "ask",
    "dispatch",
    "edit",
    "handlers",
    "register_handler",
]
