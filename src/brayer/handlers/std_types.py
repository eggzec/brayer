"""Widget handlers for the Python standard library types.

Each handler takes a pydantic ``FieldInfo`` and returns a
:class:`~.._registry.Bound`: the widget, a callable that reads the
current value, and a callable that writes one in.

Every getter is a callable evaluated *when the form is accepted*, never
a value captured while the widget was being built. Binding
``widget.date().toPython`` at build time -- as an earlier version did --
freezes the getter to the widget's initial value, so everything the user
subsequently types is silently discarded.
"""

from __future__ import annotations

import datetime
import decimal
import ipaddress
import pathlib
import typing
import uuid

from pydantic import fields
from PySide6 import QtCore, QtWidgets

from brayer._constraints import read_constraints
from brayer._registry import (
    Bound,
    apply_default,
    bind_annotation,
    is_enum,
    register_handler,
)
from brayer.widgets import DictEditWidget, ListEditWidget


#: A ``dict[K, V]`` annotation carries exactly two type arguments;
#: anything else is a bare ``dict`` and falls back to ``Any``.
_DICT_ARGS = 2
#: ``tuple[X, ...]`` is spelled with two arguments, the second the
#: Ellipsis, and means a variadic tuple rather than a 2-tuple.
_VARIADIC_ARGS = 2


__all__ = [
    "handle_any",
    "handle_bool",
    "handle_bytes",
    "handle_date",
    "handle_datetime",
    "handle_decimal",
    "handle_dict",
    "handle_enums",
    "handle_int",
    "handle_ip_address",
    "handle_list",
    "handle_none",
    "handle_numeric",
    "handle_path",
    "handle_set",
    "handle_str",
    "handle_time",
    "handle_timedelta",
    "handle_tuple",
    "handle_uuid",
]


# --------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------


@register_handler(exact=[int])
def handle_int(field: fields.FieldInfo) -> Bound:
    """Build a spin box for an integer field.

    Args:
        field: The field being rendered. ``ge``/``gt``/``le``/``lt``
            constraints become the spin box's range.

    Returns:
        The spin box with its accessors.
    """
    widget = QtWidgets.QSpinBox()
    low, high = read_constraints(field).int_range()
    widget.setRange(low, high)
    bound = Bound(widget, widget.value, lambda v: widget.setValue(int(v)))
    apply_default(field, bound)
    return bound


@register_handler(exact=[float])
def handle_numeric(field: fields.FieldInfo) -> Bound:
    """Build a double spin box for a float field.

    Args:
        field: The field being rendered. Numeric constraints become the
            range, and ``multiple_of`` becomes the step.

    Returns:
        The double spin box with its accessors.
    """
    widget = QtWidgets.QDoubleSpinBox()
    limits = read_constraints(field)
    widget.setDecimals(limits.decimals())
    widget.setSingleStep(limits.step())
    low, high = limits.float_range(widget.singleStep())
    widget.setRange(low, high)
    bound = Bound(widget, widget.value, lambda v: widget.setValue(float(v)))
    apply_default(field, bound)
    return bound


@register_handler(exact=[decimal.Decimal])
def handle_decimal(field: fields.FieldInfo) -> Bound:
    """Build a double spin box that reads back as a ``Decimal``.

    The value is converted through ``str`` so the returned ``Decimal``
    carries exactly the precision shown on screen, rather than the
    binary-float noise a direct ``Decimal(float)`` would introduce.

    Args:
        field: The field being rendered. ``decimal_places`` sets the
            displayed precision.

    Returns:
        The double spin box with its accessors.
    """
    widget = QtWidgets.QDoubleSpinBox()
    limits = read_constraints(field)
    widget.setDecimals(limits.decimals(default=2))
    widget.setSingleStep(limits.step())
    low, high = limits.float_range(widget.singleStep())
    widget.setRange(low, high)

    def get() -> decimal.Decimal:
        return decimal.Decimal(f"{widget.value():.{widget.decimals()}f}")

    bound = Bound(widget, get, lambda v: widget.setValue(float(v)))
    apply_default(field, bound)
    return bound


@register_handler(exact=[str])
def handle_str(field: fields.FieldInfo) -> Bound:
    """Build a line edit for a string field.

    Args:
        field: The field being rendered. ``max_length`` caps the input
            and ``description`` becomes the placeholder text.

    Returns:
        The line edit with its accessors.
    """
    widget = QtWidgets.QLineEdit()
    limits = read_constraints(field)
    if limits.max_length is not None:
        widget.setMaxLength(int(limits.max_length))
    if field.description:
        widget.setPlaceholderText(field.description)
    bound = Bound(widget, widget.text, lambda v: widget.setText(str(v)))
    apply_default(field, bound)
    return bound


@register_handler(exact=[bool])
def handle_bool(field: fields.FieldInfo) -> Bound:
    """Build a checkbox for a boolean field.

    Args:
        field: The field being rendered.

    Returns:
        The checkbox with its accessors.
    """
    widget = QtWidgets.QCheckBox()
    bound = Bound(
        widget, widget.isChecked, lambda v: widget.setChecked(bool(v))
    )
    apply_default(field, bound)
    return bound


@register_handler(exact=[bytes])
def handle_bytes(field: fields.FieldInfo) -> Bound:
    """Build a line edit that reads back as UTF-8 bytes.

    Args:
        field: The field being rendered.

    Returns:
        The line edit with its accessors.
    """
    widget = QtWidgets.QLineEdit()
    widget.setPlaceholderText("UTF-8 text")

    def get() -> bytes:
        return widget.text().encode("utf-8")

    def set_(value: object) -> None:
        if isinstance(value, (bytes, bytearray)):
            widget.setText(bytes(value).decode("utf-8", "replace"))
        else:
            widget.setText(str(value))

    bound = Bound(widget, get, set_)
    apply_default(field, bound)
    return bound


@register_handler(exact=[type(None), None])
def handle_none(field: fields.FieldInfo) -> Bound:
    """Build the placeholder shown for a ``None``-typed field.

    Args:
        field: The field being rendered. Unused; ``None`` has exactly
            one possible value.

    Returns:
        A disabled label with a getter that always returns ``None``.
    """
    widget = QtWidgets.QLabel("None")
    widget.setEnabled(False)
    return Bound(widget, lambda: None, lambda _v: None)


@register_handler(predicate=lambda t: t is typing.Any)
def handle_any(field: fields.FieldInfo) -> Bound:
    """Build a plain text box for an untyped field.

    Args:
        field: The field being rendered.

    Returns:
        A line edit whose value is returned as a string.
    """
    widget = QtWidgets.QLineEdit()
    widget.setPlaceholderText("any value (kept as text)")
    bound = Bound(widget, widget.text, lambda v: widget.setText(str(v)))
    apply_default(field, bound)
    return bound


# --------------------------------------------------------------------
# dates and times
# --------------------------------------------------------------------


@register_handler(exact=[datetime.datetime])
def handle_datetime(field: fields.FieldInfo) -> Bound:
    """Build a date-and-time picker.

    Args:
        field: The field being rendered.

    Returns:
        The picker with accessors that read the value on demand.
    """
    widget = QtWidgets.QDateTimeEdit()
    widget.setCalendarPopup(True)
    widget.setDateTime(QtCore.QDateTime.currentDateTime())

    def get() -> datetime.datetime:
        return widget.dateTime().toPython()

    def set_(value: object) -> None:
        if isinstance(value, datetime.datetime):
            widget.setDateTime(value)

    bound = Bound(widget, get, set_)
    apply_default(field, bound)
    return bound


@register_handler(exact=[datetime.date])
def handle_date(field: fields.FieldInfo) -> Bound:
    """Build a date picker.

    Args:
        field: The field being rendered.

    Returns:
        The picker with accessors that read the value on demand.
    """
    widget = QtWidgets.QDateEdit()
    widget.setCalendarPopup(True)
    widget.setDate(QtCore.QDate.currentDate())

    def get() -> datetime.date:
        return widget.date().toPython()

    def set_(value: object) -> None:
        if isinstance(value, datetime.datetime):
            widget.setDate(value.date())
        elif isinstance(value, datetime.date):
            widget.setDate(value)

    bound = Bound(widget, get, set_)
    apply_default(field, bound)
    return bound


@register_handler(exact=[datetime.time])
def handle_time(field: fields.FieldInfo) -> Bound:
    """Build a time picker.

    Args:
        field: The field being rendered.

    Returns:
        The picker with accessors that read the value on demand.
    """
    widget = QtWidgets.QTimeEdit()

    def get() -> datetime.time:
        return widget.time().toPython()

    def set_(value: object) -> None:
        if isinstance(value, datetime.time):
            widget.setTime(value)

    bound = Bound(widget, get, set_)
    apply_default(field, bound)
    return bound


@register_handler(exact=[datetime.timedelta])
def handle_timedelta(field: fields.FieldInfo) -> Bound:
    """Build a duration entry measured in seconds.

    Args:
        field: The field being rendered.

    Returns:
        A spin box whose value is returned as a ``timedelta``.
    """
    widget = QtWidgets.QDoubleSpinBox()
    widget.setDecimals(3)
    widget.setRange(-(10**9), 10**9)
    widget.setSuffix(" s")

    def get() -> datetime.timedelta:
        return datetime.timedelta(seconds=widget.value())

    def set_(value: object) -> None:
        if isinstance(value, datetime.timedelta):
            widget.setValue(value.total_seconds())

    bound = Bound(widget, get, set_)
    apply_default(field, bound)
    return bound


# --------------------------------------------------------------------
# identifiers and paths
# --------------------------------------------------------------------


@register_handler(exact=[uuid.UUID])
def handle_uuid(field: fields.FieldInfo) -> Bound:
    """Build a UUID entry pre-seeded with a fresh identifier.

    Args:
        field: The field being rendered.

    Returns:
        A line edit whose value is returned as a ``UUID``.
    """
    widget = QtWidgets.QLineEdit()
    widget.setText(str(uuid.uuid4()))
    widget.setPlaceholderText("00000000-0000-0000-0000-000000000000")

    def get() -> uuid.UUID:
        return uuid.UUID(widget.text().strip())

    bound = Bound(widget, get, lambda v: widget.setText(str(v)))
    apply_default(field, bound)
    return bound


@register_handler(
    subclass=[pathlib.PurePath], exact=[pathlib.Path, pathlib.PurePath]
)
def handle_path(field: fields.FieldInfo) -> Bound:
    """Build a path entry with a Browse button.

    Args:
        field: The field being rendered.

    Returns:
        A line edit and button pair returning a ``Path``.
    """
    container = QtWidgets.QWidget()
    line = QtWidgets.QLineEdit()
    browse = QtWidgets.QPushButton("Browse...")
    layout = QtWidgets.QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(line, 1)
    layout.addWidget(browse)

    def choose() -> None:
        chosen, _ = QtWidgets.QFileDialog.getOpenFileName(container)
        if chosen:
            line.setText(chosen)

    browse.clicked.connect(choose)

    def get() -> pathlib.Path:
        return pathlib.Path(line.text())

    bound = Bound(container, get, lambda v: line.setText(str(v)))
    apply_default(field, bound)
    return bound


@register_handler(exact=[ipaddress.IPv4Address, ipaddress.IPv6Address])
def handle_ip_address(field: fields.FieldInfo) -> Bound:
    """Build an IP address entry.

    Args:
        field: The field being rendered. Its annotation decides whether
            an IPv4 or IPv6 address is produced.

    Returns:
        A line edit returning an address of the annotated type.
    """
    widget = QtWidgets.QLineEdit()
    factory = field.annotation or ipaddress.IPv4Address
    initial = "::1" if factory is ipaddress.IPv6Address else "127.0.0.1"
    widget.setPlaceholderText(initial)
    # Seed a valid address: an empty box would make the getter raise
    # before the user has touched anything.
    widget.setText(initial)

    def get() -> object:
        return factory(widget.text().strip())

    bound = Bound(widget, get, lambda v: widget.setText(str(v)))
    apply_default(field, bound)
    return bound


# --------------------------------------------------------------------
# enumerations
# --------------------------------------------------------------------


@register_handler(predicate=is_enum)
def handle_enums(field: fields.FieldInfo) -> Bound:
    """Build a drop-down for an enumeration field.

    The member itself is stored as the item's data and returned by the
    getter. An earlier version called ``addItems([m.value ...])``, which
    requires every value to be a string: an ``IntEnum`` produced a list
    of blank rows and the getter handed back the display text instead of
    the member.

    Args:
        field: The field being rendered.

    Returns:
        The combo box with its accessors.
    """
    widget = QtWidgets.QComboBox()
    members = list(field.annotation)
    for member in members:
        widget.addItem(_enum_label(member))

    # The members are held in a Python list and looked up by index
    # rather than stored as Qt item data. Qt converts item data through
    # QVariant, which flattens a str- or int-derived Enum member back
    # into a plain str or int -- so `currentData()` returned "Red"
    # instead of Colour.red.
    def get() -> object:
        index = widget.currentIndex()
        return members[index] if 0 <= index < len(members) else None

    def set_(value: object) -> None:
        for index, member in enumerate(members):
            if member is value or member == value:
                widget.setCurrentIndex(index)
                return

    bound = Bound(widget, get, set_)
    apply_default(field, bound)
    return bound


def _enum_label(member: object) -> str:
    """Return the text shown for one enum member.

    Args:
        member: The enumeration member.

    Returns:
        Its value when that is a readable string, otherwise its name.
    """
    value = getattr(member, "value", None)
    if isinstance(value, str) and value:
        return value
    return str(getattr(member, "name", member))


# --------------------------------------------------------------------
# containers
# --------------------------------------------------------------------


def _collection_editor(
    field: fields.FieldInfo, convert: typing.Callable[[list[object]], object]
) -> Bound:
    """Build the shared add/remove editor used by the sequence types.

    Args:
        field: The container field. Its first type argument decides the
            widget used to enter one element.
        convert: Turns the accumulated list into the container type the
            field actually declares.

    Returns:
        The editor with its accessors.
    """
    args = typing.get_args(field.annotation)
    item_annotation = args[0] if args else typing.Any
    item = bind_annotation(item_annotation)

    container = QtWidgets.QWidget()
    listing = ListEditWidget()
    add = QtWidgets.QPushButton("Add")
    layout = QtWidgets.QGridLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(listing, 0, 0, 1, 2)
    layout.addWidget(item.widget, 1, 0)
    layout.addWidget(add, 1, 1)

    add.clicked.connect(lambda: listing.add_value(item.get()))

    def set_(value: object) -> None:
        if isinstance(value, typing.Iterable) and not isinstance(value, str):
            listing.set_values(list(value))

    return Bound(container, lambda: convert(listing.get_values()), set_)


@register_handler(exact=[list], origin=[list])
def handle_list(field: fields.FieldInfo) -> Bound:
    """Build an editor for a list field.

    Args:
        field: The field being rendered.

    Returns:
        The editor with its accessors.
    """
    bound = _collection_editor(field, list)
    apply_default(field, bound)
    return bound


@register_handler(exact=[set, frozenset], origin=[set, frozenset])
def handle_set(field: fields.FieldInfo) -> Bound:
    """Build an editor for a set or frozenset field.

    Args:
        field: The field being rendered.

    Returns:
        The editor with its accessors.
    """
    factory = (
        frozenset
        if typing.get_origin(field.annotation) is frozenset
        or field.annotation is frozenset
        else set
    )
    bound = _collection_editor(field, factory)
    apply_default(field, bound)
    return bound


@register_handler(exact=[tuple], origin=[tuple])
def handle_tuple(field: fields.FieldInfo) -> Bound:
    """Build an editor for a tuple field.

    A variadic ``tuple[X, ...]`` gets the same add/remove editor as a
    list. A fixed-arity ``tuple[X, Y]`` gets one widget per position,
    laid out in a row.

    Args:
        field: The field being rendered.

    Returns:
        The editor with its accessors.
    """
    args = typing.get_args(field.annotation)
    if not args or (len(args) == _VARIADIC_ARGS and args[1] is Ellipsis):
        bound = _collection_editor(field, tuple)
        apply_default(field, bound)
        return bound

    container = QtWidgets.QWidget()
    layout = QtWidgets.QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    slots = [bind_annotation(arg) for arg in args]
    for slot in slots:
        layout.addWidget(slot.widget)

    def get() -> tuple[object, ...]:
        return tuple(slot.get() for slot in slots)

    def set_(value: object) -> None:
        if not isinstance(value, typing.Sequence):
            return
        for slot, item in zip(slots, value, strict=False):
            if slot.set is not None:
                slot.set(item)

    bound = Bound(container, get, set_)
    apply_default(field, bound)
    return bound


@register_handler(exact=[dict], origin=[dict])
def handle_dict(field: fields.FieldInfo) -> Bound:
    """Build a key/value editor for a mapping field.

    Args:
        field: The field being rendered. Its two type arguments decide
            the widgets used to enter a key and a value.

    Returns:
        The editor with its accessors.
    """
    args = typing.get_args(field.annotation)
    key_annotation = args[0] if len(args) == _DICT_ARGS else typing.Any
    value_annotation = args[1] if len(args) == _DICT_ARGS else typing.Any

    key = bind_annotation(key_annotation)
    value = bind_annotation(value_annotation)

    container = QtWidgets.QWidget()
    table = DictEditWidget()
    add = QtWidgets.QPushButton("Add")
    layout = QtWidgets.QGridLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(table, 0, 0, 1, 3)
    layout.addWidget(key.widget, 1, 0)
    layout.addWidget(value.widget, 1, 1)
    layout.addWidget(add, 1, 2)

    add.clicked.connect(lambda: table.add_pair(key.get(), value.get()))

    def set_(incoming: object) -> None:
        if isinstance(incoming, typing.Mapping):
            table.set_mapping(incoming)

    bound = Bound(container, table.get_dict, set_)
    apply_default(field, bound)
    return bound
