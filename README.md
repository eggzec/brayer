![brayer](https://raw.githubusercontent.com/eggzec/brayer/main/docs/assets/brayer-banner.png)

# brayer

**Turn a Pydantic model into a desktop form — declare the shape, get a validated object back.**

[![Tests](https://github.com/eggzec/brayer/actions/workflows/code_test.yml/badge.svg)](https://github.com/eggzec/brayer/actions/workflows/code_test.yml)
[![Documentation](https://github.com/eggzec/brayer/actions/workflows/docs_build.yml/badge.svg)](https://github.com/eggzec/brayer/actions/workflows/docs_build.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[![codecov](https://codecov.io/github/eggzec/brayer/graph/badge.svg)](https://codecov.io/github/eggzec/brayer)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=eggzec_brayer&metric=alert_status)](https://sonarcloud.io/project/overview?id=eggzec_brayer)
[![License](https://img.shields.io/badge/license-GPL%203.0-blue.svg)](./LICENSE)

[![PyPI Downloads](https://img.shields.io/pypi/dm/brayer.svg?label=PyPI%20downloads)](https://pypi.org/project/brayer/)
[![Python versions](https://img.shields.io/pypi/pyversions/brayer.svg)](https://pypi.org/project/brayer/)

You already described your data once, in types. `brayer` reads that description and
builds the dialog for you: one labelled widget per field, your defaults filled in,
your constraints enforced, and a validated model instance handed back on OK.

## Quick example

```python
import datetime
from pydantic import BaseModel
import brayer


class Person(BaseModel):
    name: str
    age: int
    birthday: datetime.date


person = brayer.ask(Person)  # a form appears
if person is not None:
    print(person.name, person.age)
```

## What it looks like

A slightly larger model, and the form it produces:

![The generated form](https://raw.githubusercontent.com/eggzec/brayer/main/docs/assets/example-form.png)

Nothing in that window was written by hand. The spin box range comes from
`Field(ge=1, le=50)`, the two decimal places from `decimal_places=2`, the drop-down
entries from an `Enum`, the pre-filled tag from a `default_factory`, the type
selector from `int | None`, and the **Edit Database…** button from a nested
`BaseModel`.

## Why "brayer"?

A brayer is the hand roller a printer uses to lay ink evenly across a forme before
taking an impression. This library does the equivalent for a schema: it rolls your
model out into a form, and what comes back is a clean impression of it.

## What you get

- **Validated results.** The dialog will not close on OK until the values pass
  `model_validate`; failures are shown per field. A non-`None` return is always
  a valid instance.
- **Cancel is distinguishable.** Cancelling returns `None`, never an empty dict
  that looks like a fieldless success.
- **Embeddable.** `ModelDialog` is a plain `QDialog`. It reuses an existing
  `QApplication`, so it works inside an app that already runs a Qt event loop —
  and `ask()` can be called as many times as you like.
- **Extensible.** A type it does not know about is one `@register_handler` away,
  with no edit to this package.

## Supported types

Primitives, `Decimal`, `bytes`, dates and times, `timedelta`, `UUID`, `Path`,
IP addresses, `Enum` (including `IntEnum` and `auto()`), `Literal`, `list`, `set`,
`frozenset`, `tuple`, `dict`, `Optional`, unions in both spellings, `Annotated`,
and nested `BaseModel`s — composed to any depth.

`Field(...)` constraints reach the widgets: `ge`/`gt`/`le`/`lt` set spin box
ranges, `max_length` caps line edits, `decimal_places` sets precision,
`title` and `description` become the label and tooltip, and `default` /
`default_factory` pre-fill the form.

See the [full table](https://eggzec.github.io/brayer/supported-types/).

## Installation

```bash
pip install brayer
```

Requires Python 3.10+. On a bare Linux container you may also need Qt's runtime
libraries — see the [installation guide](https://eggzec.github.io/brayer/installation/)
for that, and for uv, poetry, pdm and source builds.

## Documentation

- [Quickstart](https://eggzec.github.io/brayer/quickstart/) — runnable examples, flat models through to nested ones
- [Supported types](https://eggzec.github.io/brayer/supported-types/) — every annotation that maps to a widget
- [How it works](https://eggzec.github.io/brayer/how-it-works/) — the dispatch and handler architecture, and how to add a type
- [API reference](https://eggzec.github.io/brayer/api/) — the full public surface

## Contributing

The test suite runs headlessly, so no display is needed:

```bash
git clone https://github.com/eggzec/brayer.git
cd brayer
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --diff .
```

Brand assets and the documentation screenshot are generated, not committed by
hand — `uv run python tools/make_assets.py` and
`uv run python tools/make_screenshot.py` regenerate them.

## License

GNU General Public License v3 or later — see [LICENSE](LICENSE).
