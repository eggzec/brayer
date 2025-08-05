"""The handler registry: annotation in, widget-and-accessors out.

Handlers register themselves against this module rather than being
listed in a central ``if``/``elif`` chain. That keeps the dispatch open
to extension, removes the import cycle the chain required, and lets a
user add support for their own types without editing the package.

A handler receives a pydantic ``FieldInfo`` and returns a :class:`Bound`
-- the widget to show, a callable to read the value out of it, and an
optional callable to write a value into it.
"""

from __future__ import annotations

import types
import typing
from enum import Enum

from pydantic import BaseModel, fields
from pydantic_core import PydanticUndefined
from PySide6 import QtWidgets

from ._errors import UnsupportedTypeError


__all__ = [
    "Bound",
    "FieldHandler",
    "bind",
    "bind_annotation",
    "dispatch",
    "field_for",
    "register_handler",
    "strip_annotated",
]


class Bound(typing.NamedTuple):
    """A widget together with the accessors that drive it."""

    widget: QtWidgets.QWidget
    """The widget to place in the form."""

    get: typing.Callable[[], typing.Any]
    """Read the current value. Called when the user accepts the form."""

    set: typing.Callable[[typing.Any], None] | None = None
    """Write a value in. ``None`` when the widget cannot be pre-filled."""


FieldHandler = typing.Callable[[fields.FieldInfo], Bound]
"""Builds a :class:`Bound` for one field."""


_EXACT: dict[typing.Any, FieldHandler] = {}
_ORIGIN: dict[typing.Any, FieldHandler] = {}
_SUBCLASS: list[tuple[type, FieldHandler]] = []
_PREDICATE: list[tuple[typing.Callable[[object], bool], FieldHandler]] = []


def register_handler(
    *,
    exact: typing.Iterable[typing.Any] = (),
    origin: typing.Iterable[typing.Any] = (),
    subclass: typing.Iterable[type] = (),
    predicate: typing.Callable[[object], bool] | None = None,
) -> typing.Callable[[FieldHandler], FieldHandler]:
    """Register a handler for one or more annotation shapes.

    Resolution is tried in the order the parameters are listed here:
    an exact type identity first, then a generic's origin, then a
    subclass test, then a predicate. The first match wins.

    Args:
        exact: Types matched by identity, e.g. ``int`` or ``str``. This
            is the fastest path and never matches a subclass.
        origin: Generic origins matched against ``typing.get_origin``,
            e.g. ``list``, ``dict`` or ``typing.Literal``.
        subclass: Base classes matched with ``issubclass``. Registered
            in call order, so register the most specific base first.
        predicate: Called with the bare annotation; a truthy result
            selects this handler. The escape hatch for shapes the other
            three cannot express.

    Returns:
        A decorator that registers the handler and returns it unchanged.

    Example:
        >>> @register_handler(exact=[bool])
        ... def handle_bool(field):
        ...     box = QtWidgets.QCheckBox()
        ...     return Bound(box, box.isChecked, box.setChecked)
    """

    def decorate(handler: FieldHandler) -> FieldHandler:
        for key in exact:
            _EXACT[key] = handler
        for key in origin:
            _ORIGIN[key] = handler
        for base in subclass:
            _SUBCLASS.append((base, handler))
        if predicate is not None:
            _PREDICATE.append((predicate, handler))
        return handler

    return decorate


def strip_annotated(annotation: object) -> object:
    """Remove every ``Annotated`` wrapper from an annotation.

    ``typing.get_origin(Annotated[int, Gt(0)])`` returns ``Annotated``
    rather than ``int``, so an un-stripped annotation matches no handler
    at all. Nested annotations such as ``list[PositiveInt]`` reach the
    dispatcher still wrapped, which is what made them fail.

    Args:
        annotation: Any type annotation.

    Returns:
        The annotation with all ``Annotated`` layers peeled away.
    """
    while typing.get_origin(annotation) is typing.Annotated:
        annotation = typing.get_args(annotation)[0]
    return annotation


def field_for(
    annotation: object, default: object = PydanticUndefined
) -> fields.FieldInfo:
    """Build a ``FieldInfo`` for a bare annotation.

    Used when recursing into a container's element type. Routing through
    ``FieldInfo.from_annotation`` moves any ``Annotated`` metadata onto
    ``FieldInfo.metadata``, so constraints declared on an element type
    survive into the element's widget.

    Args:
        annotation: The element or member annotation.
        default: A default to attach, if one is known.

    Returns:
        A ``FieldInfo`` describing the annotation.
    """
    info = fields.FieldInfo.from_annotation(annotation)
    if default is not PydanticUndefined:
        info.default = default
    return info


def dispatch(field_type: object) -> FieldHandler:
    """Return the handler registered for an annotation.

    Args:
        field_type: The annotation to resolve. ``Annotated`` wrappers
            are removed before matching.

    Returns:
        The handler that builds a widget for this annotation.

    Raises:
        UnsupportedTypeError: No registered handler matches. The message
            names the offending type and points at ``register_handler``.
    """
    bare = strip_annotated(field_type)

    handler = _EXACT.get(bare)
    if handler is not None:
        return handler

    origin = typing.get_origin(bare)
    if origin is not None:
        # `X | Y` and `typing.Union[X, Y]` are distinct objects that mean
        # the same thing; normalise so one handler serves both.
        if origin is types.UnionType:
            origin = typing.Union
        handler = _ORIGIN.get(origin)
        if handler is not None:
            return handler
        # A bare `list`/`dict` annotation has no origin but is still a
        # usable container; fall through to the exact table for it.
        handler = _EXACT.get(origin)
        if handler is not None:
            return handler

    if isinstance(bare, type):
        for base, candidate in _SUBCLASS:
            if issubclass(bare, base):
                return candidate

    for test, candidate in _PREDICATE:
        if test(bare):
            return candidate

    raise UnsupportedTypeError(field_type)


def bind(field: fields.FieldInfo) -> Bound:
    """Build the widget and accessors for one field.

    Args:
        field: The pydantic field to render.

    Returns:
        The :class:`Bound` produced by the matching handler.

    Raises:
        UnsupportedTypeError: No handler matches the field's annotation.
    """
    return dispatch(field.annotation)(field)


def bind_annotation(
    annotation: object, default: object = PydanticUndefined
) -> Bound:
    """Build the widget and accessors for a bare annotation.

    The recursion entry point for container handlers, which hold an
    element type rather than a field.

    Args:
        annotation: The element or member annotation.
        default: A default to pre-fill the widget with, if known.

    Returns:
        The :class:`Bound` produced by the matching handler.

    Raises:
        UnsupportedTypeError: No handler matches the annotation.
    """
    return bind(field_for(annotation, default))


def apply_default(field: fields.FieldInfo, bound: Bound) -> None:
    """Pre-fill a widget with its field's default, when there is one.

    Silently does nothing when the field is required, when the handler
    provided no setter, or when the default cannot be applied -- a
    default that will not load is not worth failing the whole form for.

    Args:
        field: The field whose default should be shown.
        bound: The widget and accessors to pre-fill.
    """
    if bound.set is None or field.is_required():
        return
    try:
        default = field.get_default(call_default_factory=True)
    except (TypeError, ValueError):  # pragma: no cover - exotic factory
        return
    if default is None or default is PydanticUndefined:
        return
    try:
        bound.set(default)
    except (TypeError, ValueError, OverflowError, AttributeError):
        return


def describe(field: fields.FieldInfo, name: str) -> str:
    """Return the label text to show beside a field's widget.

    Args:
        field: The field being rendered.
        name: The attribute name, used when no title is declared.

    Returns:
        The field's ``title`` if it declares one, otherwise the
        attribute name with underscores turned into spaces.
    """
    if field.title:
        return field.title
    return name.replace("_", " ").strip().capitalize() or name


def is_model(annotation: object) -> bool:
    """Report whether an annotation is a pydantic model class.

    Args:
        annotation: The annotation to test.

    Returns:
        ``True`` for a ``BaseModel`` subclass, ``False`` otherwise.
    """
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def is_enum(annotation: object) -> bool:
    """Report whether an annotation is an enumeration class.

    Args:
        annotation: The annotation to test.

    Returns:
        ``True`` for an ``Enum`` subclass, ``False`` otherwise.
    """
    return isinstance(annotation, type) and issubclass(annotation, Enum)
