# Quickstart

Every example on this page is complete and runnable.

## A flat model

The smallest useful case. Declare the fields, ask for them.

```python
import datetime

from pydantic import BaseModel

import brayer


class Person(BaseModel):
    name: str
    age: int
    birthday: datetime.date


person = brayer.ask(Person)
if person is None:
    print("cancelled")
else:
    print(f"{person.name} is {person.age}")
```

`ask` blocks until the dialog closes. It returns a **validated**
`Person`, or `None` if the user cancelled or closed the window.

!!! note "Cancel is not an empty result"
    `None` means "the user declined". It is never confused with a model
    that happens to have no fields, and never with a widget that failed
    to read.

## Defaults, labels and help text

Anything you tell Pydantic about a field, the form uses.

```python
from pydantic import BaseModel, Field


class ServerSettings(BaseModel):
    workers: int = Field(default=4, ge=1, le=64)
    hostname: str = Field(
        default="localhost",
        max_length=253,
        title="Host name",
        description="Interface the server binds to",
    )
    debug: bool = False
```

- `default=` pre-fills the widget.
- `ge` / `gt` / `le` / `lt` become the spin box's range. Exclusive bounds
  are converted to inclusive ones, so `gt=0, lt=10` yields `1..9`.
- `max_length` caps the line edit.
- `title=` becomes the row label; without one, the attribute name is
  used with underscores turned into spaces.
- `description=` becomes the placeholder and the tooltip.

## Choices

An `Enum` or a `Literal` becomes a drop-down. The **member itself** comes
back, not its display text.

```python
import enum
from typing import Literal

from pydantic import BaseModel


class Environment(str, enum.Enum):
    staging = "Staging"
    production = "Production"


class Deploy(BaseModel):
    environment: Environment = Environment.staging
    strategy: Literal["rolling", "blue-green"] = "rolling"


deploy = brayer.ask(Deploy)
assert isinstance(deploy.environment, Environment)  # a member, not a str
```

`IntEnum`, `StrEnum` and `enum.auto()` all work. A string-valued member
is labelled by its value; anything else is labelled by its name.

## Optional and union fields

A union renders as a type selector beside the matching widget. Pick the
type, then enter the value.

```python
from pydantic import BaseModel


class Endpoint(BaseModel):
    timeout: int | None = None  # selector offers "int" and "None"
    retries: str | int  # both spellings of union work
```

If the field has a default, the form opens on that branch with the value
already filled in.

## Collections

`list`, `set`, `frozenset`, `dict` and `tuple` each get an editor with
the right widget for their element type.

```python
import datetime

from pydantic import BaseModel, Field


class Service(BaseModel):
    tags: list[str] = Field(default_factory=list)
    deployed_on: list[datetime.date] = Field(default_factory=list)
    rate_limits: dict[str, int] = Field(default_factory=dict)
    listen: tuple[str, int] = ("0.0.0.0", 8080)
```

- **list / set / frozenset** — an add/remove list with a widget for one
  element and an **Add** button. Items reorder by dragging and are
  removed with <kbd>Delete</kbd> or the right-click menu.
- **dict** — a two-column key/value table. Keys must be hashable and
  unique; a duplicate is refused rather than silently overwriting.
- **tuple** — a fixed-arity `tuple[str, int]` gets one widget per
  position; a variadic `tuple[int, ...]` gets the list editor.

Values keep their real types. A `list[datetime.date]` gives you back
`date` objects, not strings.

## Nested models

A `BaseModel`-typed field becomes a button that opens its own sub-form.

```python
from pydantic import BaseModel


class Database(BaseModel):
    host: str
    port: int


class Deployment(BaseModel):
    service: str
    database: Database  # -> an "Edit Database..." button
```

The sub-form is built the first time you open it, so deeply nested — even
self-referential — models cost nothing until you actually navigate into
them. Cancelling the sub-dialog discards that edit and restores the
previous values.

## Editing an existing object

`edit` pre-fills the form from an instance and returns a new one.

```python
person = Person(name="Grace", age=45, birthday=datetime.date(1906, 12, 9))

updated = brayer.edit(person)
if updated is not None:
    print(updated.age)
```

The original is never mutated.

## Embedding in a Qt application

`ask` is a thin wrapper over `ModelDialog`, which is an ordinary
`QDialog`. Use it directly when you already have an event loop.

```python
from PySide6 import QtWidgets

import brayer


class MainWindow(QtWidgets.QMainWindow):
    def collect_person(self) -> None:
        dialog = brayer.ModelDialog(Person, parent=self)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.use(dialog.value)
```

Because the dialog reuses the running `QApplication`, this composes with
whatever your application already has open.

## Validation failures

The dialog refuses to close while the values are invalid, and lists the
problems underneath the form.

```python
from pydantic import BaseModel, Field, field_validator


class Account(BaseModel):
    username: str = Field(min_length=3)

    @field_validator("username")
    @classmethod
    def no_spaces(cls, value: str) -> str:
        if " " in value:
            raise ValueError("must not contain spaces")
        return value
```

Entering `a b` shows `username: Value error, must not contain spaces`
and keeps the dialog open. Your own validators work exactly as they do
anywhere else in Pydantic.

## Running headless

For tests and CI, set Qt's offscreen platform before importing anything
Qt-related:

```python
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

The whole widget layer works without a display, which is how this
project's own test suite runs.
