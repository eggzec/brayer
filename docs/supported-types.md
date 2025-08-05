# Supported types

Every annotation below maps to a widget. Anything not listed raises
[`UnsupportedTypeError`][err] — which you can fix without touching this
package, by [registering a handler](how-it-works.md#adding-a-type).

  [err]: api.md#exceptions

## Primitives

| Annotation | Widget | Returns |
|---|---|---|
| `int` | spin box | `int` |
| `float` | double spin box | `float` |
| `decimal.Decimal` | double spin box | `Decimal` at the displayed precision |
| `str` | line edit | `str` |
| `bool` | checkbox | `bool` |
| `bytes` | line edit | `bytes`, UTF-8 encoded |
| `None` / `NoneType` | disabled label | `None` |
| `typing.Any` | line edit | `str` |

## Dates and times

| Annotation | Widget | Returns |
|---|---|---|
| `datetime.datetime` | date-time picker with calendar | `datetime` |
| `datetime.date` | date picker with calendar | `date` |
| `datetime.time` | time picker | `time` |
| `datetime.timedelta` | spin box in seconds | `timedelta` |

## Identifiers and paths

| Annotation | Widget | Returns |
|---|---|---|
| `uuid.UUID` | line edit, seeded with a fresh `uuid4` | `UUID` |
| `pathlib.Path` | line edit with a **Browse…** button | `Path` |
| `ipaddress.IPv4Address` | line edit, seeded `127.0.0.1` | `IPv4Address` |
| `ipaddress.IPv6Address` | line edit, seeded `::1` | `IPv6Address` |

## Choices

| Annotation | Widget | Returns |
|---|---|---|
| `Enum` subclass | drop-down | the **member**, not its label |
| `IntEnum`, `StrEnum`, `auto()` | drop-down | the member |
| `Literal[...]` | drop-down | the literal value, correctly typed |

A string-valued enum member is labelled by its value; anything else by
its name. `Literal[1, "1"]` produces two distinct entries, qualified by
type, and returns whichever was chosen.

## Containers

| Annotation | Widget | Returns |
|---|---|---|
| `list[T]` | add/remove list of `T` widgets | `list` |
| `set[T]`, `frozenset[T]` | same, deduplicated | `set` / `frozenset` |
| `tuple[A, B]` | one widget per position | `tuple` |
| `tuple[T, ...]` | add/remove list | `tuple` |
| `dict[K, V]` | key/value table | `dict` |
| bare `list` / `dict` | as above, elements treated as `Any` | `list` / `dict` |

Values are stored as real Python objects, so a `list[date]` returns
`date` objects and a `dict[str, Decimal]` returns `Decimal` values.

## Composition

| Annotation | Widget | Returns |
|---|---|---|
| `BaseModel` subclass | button opening a sub-form | `dict` of that model's values |
| `X \| Y`, `Union[X, Y]` | type selector plus stacked widgets | the selected branch's value |
| `Optional[X]` | selector offering `X` and `None` | `X` or `None` |
| `Annotated[X, ...]` | whatever `X` maps to | `X`, with the metadata applied |

Nesting composes: `list[SomeModel]`, `dict[str, list[int]]` and
`Optional[list[Annotated[int, Gt(0)]]]` all work, because each container
dispatches on its element type recursively.

## Constraints

These are read from `Field(...)` and applied to the widget.

| Constraint | Effect |
|---|---|
| `ge`, `le` | spin box minimum / maximum |
| `gt`, `lt` | same, stepped one unit inward to an inclusive bound |
| `max_length` | line edit maximum length |
| `decimal_places` | displayed precision and step of a numeric widget |
| `multiple_of` | the widget's single-step |
| `title` | the row's label |
| `description` | placeholder text and tooltip |
| `default`, `default_factory` | pre-fills the widget |

A constraint the widget cannot express is still enforced: Pydantic
validates on OK, and the dialog stays open with the error shown.

## Not supported

`complex`, arbitrary classes, and anything with
`arbitrary_types_allowed` raise `UnsupportedTypeError`. The message names
the offending type. Adding support is a handful of lines — see
[How it works](how-it-works.md#adding-a-type).
