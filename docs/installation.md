# Installation

`brayer` can be installed from PyPI or directly from source via GitHub.

It needs **Python 3.10+**. Its only runtime dependencies are `pydantic`
and `pyside6-essentials`, both of which ship wheels for every supported
platform.

---

## [PyPI](https://pypi.org/project/brayer)

For using the PyPI package in your project, add it to your configuration
file:

=== "pyproject.toml"

    ```toml
    [project]
    dependencies = [
        "brayer>=0.1.0", # (1)!
    ]
    ```

    1. Specifying a version is recommended

=== "requirements.txt"

    ```
    brayer>=0.1.0
    ```

### pip

=== "Installation for user"

    ```bash
    pip install --upgrade --user brayer # (1)!
    ```

    1. You may need to use `pip3` instead of `pip` depending on your Python installation.

=== "Installation in virtual environment"

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install --require-virtualenv --upgrade brayer # (1)!
    ```

    1. You may need to use `pip3` instead of `pip` depending on your Python installation.

    !!! note
        The command to activate the virtual environment depends on your platform and shell.
        [More info](https://docs.python.org/3/library/venv.html#how-venvs-work)

### uv

=== "Adding to uv project"

    ```bash
    uv add brayer
    uv sync
    ```

=== "Installing to uv environment"

    ```bash
    uv venv
    uv pip install brayer
    ```

### poetry

```bash
poetry add brayer
```

### pdm

```bash
pdm add brayer
```

---

## Linux: Qt runtime libraries

PySide6 links a handful of system libraries that most desktop
distributions already have, but a container or CI image usually does
not. If `import brayer` fails with an `ImportError` naming a missing
`.so`, install them:

=== "Debian / Ubuntu"

    ```bash
    sudo apt-get install -y --no-install-recommends \
      libegl1 libgl1 libdbus-1-3 libxkbcommon-x11-0 \
      libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
      libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
      libxcb-xinerama0 libxcb-xkb1
    ```

=== "Fedora / RHEL"

    ```bash
    sudo dnf install -y \
      mesa-libEGL mesa-libGL dbus-libs libxkbcommon-x11 \
      xcb-util-cursor xcb-util-wm xcb-util-image \
      xcb-util-keysyms xcb-util-renderutil
    ```

## Running without a display

Set Qt's offscreen platform before anything Qt is imported. Widgets are
then built and read entirely in memory:

```bash
export QT_QPA_PLATFORM=offscreen
```

This is how this project's own test suite runs, so the whole library is
exercised headlessly on every CI leg.

!!! warning "Fonts under offscreen"
    Some minimal images expose no font database at all, and text renders
    as empty boxes. Install any font package — `fonts-dejavu-core` on
    Debian — if you intend to capture screenshots.

---

## [GitHub](https://github.com/eggzec/brayer)

Install the latest development version directly from the repository:

```bash
pip install --upgrade "git+https://github.com/eggzec/brayer.git#egg=brayer"
```

### Building locally

Clone and build from source if you want to modify or test local changes:

```bash
git clone https://github.com/eggzec/brayer.git
cd brayer
uv sync            # or: pip install -e .
uv run pytest      # the suite runs headlessly
```

---
