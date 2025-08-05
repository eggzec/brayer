# API reference

Everything importable from `brayer`.

## Asking

### `ask(model, *, initial=None, title=None, parent=None)`

Show a form for `model` and return what the user entered.

| Parameter | Type | Meaning |
|---|---|---|
| `model` | `type[ModelT]` | The model class to build the form from |
| `initial` | `ModelT` or `None` | An instance to pre-fill the form with |
| `title` | `str` or `None` | Window title; defaults to the class name |
| `parent` | `QWidget` or `None` | Owning widget, when embedding |

**Returns** a validated `ModelT`, or `None` if the user cancelled or
closed the window.

**Raises** `UnsupportedTypeError` if a field's type has no handler, and
`UnresolvedAnnotationError` if the model has unresolved forward
references.

Blocks until the dialog closes. A non-`None` result has already passed
`model_validate`, so it is always valid.

### `edit(instance, *, title=None, parent=None)`

Show a form pre-filled from `instance` and return a **new** validated
instance carrying the edits, or `None` if cancelled. The original is
never mutated.

## Embedding

### `ModelDialog(model, *, initial=None, title=None, parent=None)`

A `QDialog` subclass rendering a model. Use it directly inside an
application that already runs a Qt event loop.

| Member | Meaning |
|---|---|
| `.value` | The validated model after `exec()`, or `None` if cancelled |
| `.exec()` | Standard `QDialog.exec()`; returns `Accepted` / `Rejected` |

The dialog only closes on OK once the values validate; failures are
listed beneath the form and it stays open.

```python
dialog = brayer.ModelDialog(Person, parent=self)
if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
    use(dialog.value)
```

## Extending

### `register_handler(*, exact=(), origin=(), subclass=(), predicate=None)`

Decorator registering a handler for one or more annotation shapes.
Resolution is tried in the order the parameters are listed.

| Parameter | Matches |
|---|---|
| `exact` | Types by identity — `int`, `str`. Never a subclass |
| `origin` | Generic origins via `typing.get_origin` — `list`, `dict` |
| `subclass` | Base classes via `issubclass`, in registration order |
| `predicate` | An arbitrary test against the bare annotation |

See [How it works](how-it-works.md#adding-a-type) for a worked example.

### `Bound(widget, get, set=None)`

What a handler returns.

| Field | Type | Meaning |
|---|---|---|
| `widget` | `QWidget` | The widget to place in the form |
| `get` | `Callable[[], Any]` | Read the current value. Called on accept |
| `set` | `Callable[[Any], None]` or `None` | Write a value in |

### `FieldHandler`

Type alias: `Callable[[FieldInfo], Bound]`.

### `dispatch(field_type)`

Return the handler registered for an annotation. Raises
`UnsupportedTypeError` if nothing matches. `Annotated` wrappers are
removed before matching.

## Widgets

### `ListEditWidget`

The add/remove/reorder editor used for `list`, `set`, `frozenset` and
variadic `tuple`.

| Method | Meaning |
|---|---|
| `add_value(value)` | Append a value |
| `set_values(values)` | Replace the contents |
| `get_values()` | Every value, in display order |
| `remove_selected()` | Remove selected items |
| `clear_values()` | Remove everything |
| `contents_changed` | Signal, emitted on any change |

### `DictEditWidget`

The key/value table used for `dict`.

| Method | Meaning |
|---|---|
| `add_pair(key, value)` | Add a pair; returns `False` if refused |
| `set_mapping(mapping)` | Replace the contents |
| `get_dict()` | The current mapping |
| `keys()` | Current keys, in row order |
| `remove_selected()` | Remove selected rows |
| `contents_changed` | Signal, emitted on any change |
| `rejected_key` | Signal carrying why a pair was refused |

Both store real Python objects, so any value survives a round trip.

## Exceptions

All derive from `InputError`, so one `except` catches the family.

| Exception | Raised when |
|---|---|
| `InputError` | Base class; never raised directly |
| `UnsupportedTypeError` | No handler matches a field's type. Also subclasses `NotImplementedError` |
| `UnresolvedAnnotationError` | A model's forward references cannot be resolved |
| `WidgetBuildError` | A widget could not be built or read |

## Module attributes

| Name | Meaning |
|---|---|
| `__version__` | The installed version, or `"0.0.0"` from a source checkout |

## Command line

```bash
brayer --version   # the installed version
brayer --debug     # OS, architecture, Python and dependency versions
```

`--debug` output is what the bug report template asks for. Neither
subcommand opens a window or needs a display.
