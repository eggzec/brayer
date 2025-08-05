"""Handlers for the typing special forms.

Special forms are the constructs from :mod:`typing` with their own
syntax rather than a plain class:

* ``Union[X, Y]`` and its ``X | Y`` spelling
* ``Optional[X]``, which is ``Union[X, None]``
* ``Literal[...]``

``Annotated`` is handled in the registry rather than here: it is peeled
off before dispatch, so no handler ever sees it.

See https://docs.python.org/3/library/typing.html#special-forms
"""

from __future__ import annotations

import typing

from pydantic import fields
from pydantic_core import PydanticUndefined
from PySide6 import QtWidgets

from brayer._registry import Bound, bind_annotation, register_handler


__all__ = ["handle_literal", "handle_union"]


def _type_label(annotation: object) -> str:
    """Return the name shown for one branch of a union.

    Args:
        annotation: The branch's annotation.

    Returns:
        ``"None"`` for the null type, the class name for a plain class,
        and the annotation's string form for anything generic.
    """
    if annotation is type(None):
        return "None"
    name = getattr(annotation, "__name__", None)
    if isinstance(name, str):
        return name
    return str(annotation).replace("typing.", "")


@register_handler(origin=[typing.Union])
def handle_union(field: fields.FieldInfo) -> Bound:
    """Build a type selector backed by one widget per union member.

    The getter indexes the member widgets *positionally* by the stack's
    current index. An earlier version kept a dict keyed by widget object
    and zipped it against the type list, which coupled correctness to
    dict ordering and broke whenever two members produced equal widgets.

    Args:
        field: The field being rendered.

    Returns:
        The selector and stacked widgets, with accessors that read from
        whichever member is currently selected.
    """
    members = typing.get_args(field.annotation)
    bounds = [bind_annotation(member) for member in members]

    container = QtWidgets.QWidget()
    selector = QtWidgets.QComboBox()
    stack = QtWidgets.QStackedWidget()

    for member, bound in zip(members, bounds, strict=True):
        selector.addItem(_type_label(member))
        stack.addWidget(bound.widget)

    selector.currentIndexChanged.connect(stack.setCurrentIndex)

    layout = QtWidgets.QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(selector)
    layout.addWidget(stack, 1)

    def get() -> object:
        return bounds[stack.currentIndex()].get()

    def set_(value: object) -> None:
        index = _branch_for(members, value)
        if index is None:
            return
        selector.setCurrentIndex(index)
        stack.setCurrentIndex(index)
        setter = bounds[index].set
        if setter is not None:
            setter(value)

    _preselect(field, members, set_)
    return Bound(container, get, set_)


def _branch_for(members: tuple[object, ...], value: object) -> int | None:
    """Find the union branch a value belongs to.

    Args:
        members: The union's member annotations.
        value: The value to place.

    Returns:
        The index of the first matching branch, or ``None``.
    """
    if value is None:
        for index, member in enumerate(members):
            if member is type(None):
                return index
        return None
    for index, member in enumerate(members):
        origin = typing.get_origin(member) or member
        if isinstance(origin, type) and isinstance(value, origin):
            return index
    return None


def _preselect(
    field: fields.FieldInfo,
    members: tuple[object, ...],
    apply: typing.Callable[[object], None],
) -> None:
    """Open the union on its default, with that default filled in.

    Selecting the right branch is not enough on its own: the branch's
    own widget still holds whatever it was built with, so a field
    declaring ``int = 7`` would open on the integer branch showing 0.
    Routing through the setter selects *and* fills.

    Args:
        field: The field being rendered.
        members: The union's member annotations.
        apply: The union's setter, which selects a branch and writes the
            value into it.
    """
    if field.is_required():
        return
    default = field.get_default(call_default_factory=True)
    if default is PydanticUndefined:
        return
    if _branch_for(members, default) is not None:
        apply(default)


@register_handler(origin=[typing.Literal])
def handle_literal(field: fields.FieldInfo) -> Bound:
    """Build a drop-down over a literal's permitted values.

    Each value is carried as the item's data rather than being looked up
    by its display text. Keying on text collapsed distinct values that
    share a string form -- ``Literal[1, "1"]`` became a single entry,
    and the getter could return the wrong one of the two.

    Args:
        field: The field being rendered.

    Returns:
        The combo box with its accessors.
    """
    values = typing.get_args(field.annotation)
    labels = _disambiguate([str(value) for value in values], values)

    widget = QtWidgets.QComboBox()
    for label, value in zip(labels, values, strict=True):
        widget.addItem(label, value)

    def set_(value: object) -> None:
        index = widget.findData(value)
        if index >= 0:
            widget.setCurrentIndex(index)

    bound = Bound(widget, widget.currentData, set_)

    if not field.is_required():
        default = field.get_default(call_default_factory=True)
        if default is not PydanticUndefined:
            set_(default)
    return bound


def _disambiguate(labels: list[str], values: tuple[object, ...]) -> list[str]:
    """Make repeated labels distinguishable by appending their type.

    Args:
        labels: The display strings, which may contain duplicates.
        values: The values the labels describe, positionally aligned.

    Returns:
        Labels of the same length, with duplicates qualified.
    """
    seen = [labels.count(label) > 1 for label in labels]
    return [
        f"{label} ({type(value).__name__})" if repeated else label
        for label, value, repeated in zip(labels, values, seen, strict=True)
    ]
