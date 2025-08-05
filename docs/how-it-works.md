# How it works

The whole library is built on one idea: **a handler turns a field into a
widget plus the two callables that drive it.**

## The contract

Every handler returns a `Bound`:

```python
class Bound(NamedTuple):
    widget: QWidget  # what to put in the form
    get: Callable[[], Any]  # read the value out
    set: Callable[[Any], None] | None  # write a value in (optional)
```

That is the entire abstraction. Nesting, recursion and extensibility all
fall out of it: a container handler builds its element's `Bound` and
composes it, and a model handler builds one `Bound` per field.

!!! warning "Getters are called later, not now"
    `get` must read the widget **when it is invoked**, not capture a value
    while the widget is being built.

    ```python
    # Wrong: evaluates date() immediately and binds .toPython to that
    # frozen snapshot, so everything the user types is discarded.
    return Bound(widget, widget.date().toPython)

    # Right: reads the widget at the moment the form is accepted.
    return Bound(widget, lambda: widget.date().toPython())
    ```

    The first form is a real bug this project shipped before release. It
    lost every date the user entered, silently, with no error.

## Dispatch

`dispatch(annotation)` resolves an annotation to a handler, trying four
strategies in order:

1. **Exact identity** — `int`, `str`, `datetime.date`. A dict lookup, and
   it never matches a subclass.
2. **Generic origin** — `typing.get_origin`, so `list[str]` finds the
   `list` handler. `X | Y` is normalised to `typing.Union` so one handler
   serves both spellings.
3. **Subclass** — `issubclass`, in registration order.
4. **Predicate** — an arbitrary test, for shapes the first three cannot
   express. `Enum` and `BaseModel` are matched this way.

Nothing matches? `UnsupportedTypeError`, naming the type.

### Annotated is stripped first

`typing.get_origin(Annotated[int, Gt(0)])` returns `Annotated`, not
`int` — so an un-stripped annotation matches nothing at all. Pydantic
unwraps `Annotated` at the *top* level of a model, but a nested one such
as `list[Annotated[int, Gt(0)]]` reaches the dispatcher still wrapped.

Two things prevent that:

- `strip_annotated` peels every layer before matching.
- Recursion routes through `FieldInfo.from_annotation`, which moves the
  metadata onto `FieldInfo.metadata` — so a constraint declared on an
  element type still reaches that element's widget.

## Registration, not a chain

Handlers register themselves:

```python
@register_handler(exact=[int])
def handle_int(field: FieldInfo) -> Bound:
    widget = QtWidgets.QSpinBox()
    low, high = read_constraints(field).int_range()
    widget.setRange(low, high)
    return Bound(widget, widget.value, lambda v: widget.setValue(int(v)))
```

This replaced a central `if`/`elif` chain, which had three problems: it
could not be extended without editing the package, it created an import
cycle (handlers imported the package that imported the handlers), and it
grew a lint suppression for its own complexity. The registry lives in a
leaf module that imports nothing from its callers, so the cycle is gone.

## Adding a type

Say you want `complex` supported. Nothing in this package needs to
change:

```python
from PySide6 import QtWidgets

import brayer


@brayer.register_handler(exact=[complex])
def handle_complex(field):
    container = QtWidgets.QWidget()
    real = QtWidgets.QDoubleSpinBox()
    imag = QtWidgets.QDoubleSpinBox()
    layout = QtWidgets.QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(real)
    layout.addWidget(QtWidgets.QLabel("+"))
    layout.addWidget(imag)
    layout.addWidget(QtWidgets.QLabel("i"))

    def get() -> complex:
        return complex(real.value(), imag.value())

    def set_(value: complex) -> None:
        real.setValue(value.real)
        imag.setValue(value.imag)

    return brayer.Bound(container, get, set_)
```

Import that module once and `complex` fields work everywhere, including
inside `list[complex]` and `dict[str, complex]`, because containers
recurse through the same dispatcher.

Use `origin=` for a generic, `subclass=` for a base class, and
`predicate=` for anything else.

## Building the form

`build_model_form` walks `model.__pydantic_fields__`, binds each field,
and adds a labelled row. It returns the container, a `collect` callable,
and the per-field setters used for pre-filling.

Two details are worth knowing:

- **Values are keyed for validation, not for display.** A field with an
  alias is collected under that alias, so a model that can only be built
  from its aliases still validates.
- **Getter failures are not swallowed.** Qt discards exceptions raised
  inside a slot, so a failing getter used to make the whole call return
  an empty dict — indistinguishable from Cancel. Collection happens
  outside any slot and wraps failures in `WidgetBuildError`.

## Accepting

`ModelDialog._try_accept` collects, then calls `model_validate`. On
success it stores the instance and closes. On failure it renders the
Pydantic errors as `field: message` lines beneath the form and **stays
open**, so the returned value is either a valid model or nothing at all.

## The application singleton

Qt permits one `QApplication` per process. `ask` reuses
`QApplication.instance()` when there is one and creates it otherwise,
keeping the created instance alive for the process lifetime.

The dialog runs its own modal loop via `QDialog.exec()`, so the library
never calls `app.exec()` or `app.quit()`. That is what lets it be called
repeatedly, and from inside a host application that already owns the
event loop.

## Testing it

The suite runs headlessly with `QT_QPA_PLATFORM=offscreen` and drives
widgets directly — set a value, call the getter, assert.

One trap is worth recording. A `QMenu` opened with `exec()` is a
**popup**, not a modal widget, so it never appears in
`QApplication.activeModalWidget()`. A test that waits on that will hang
forever rather than fail. Use `activePopupWidget()`, and bound the number
of attempts so a change in Qt's behaviour fails the test instead of
stalling the run.
