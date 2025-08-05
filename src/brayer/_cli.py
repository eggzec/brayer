"""The ``brayer`` command line entry point.

Its only job is reporting what is installed, so that a bug report can
carry an accurate environment. It deliberately does not open a window.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import platform
import re
import sys


__all__ = ["debug_info", "dependency_versions", "main"]

_DISTRIBUTION = "brayer"


def dependency_versions(package: str = _DISTRIBUTION) -> dict[str, str]:
    """Return the installed version of each of a package's requirements.

    Uses the public ``importlib.metadata.requires`` rather than reading
    ``METADATA`` through a distribution's private ``_path`` attribute,
    which is not part of the API and is absent for some installers.

    Args:
        package: The distribution whose requirements are reported.

    Returns:
        A mapping of requirement name to installed version, with
        ``"not installed"`` for anything missing. Empty if the package
        itself is not installed.
    """
    try:
        requirements = md.requires(package) or []
    except md.PackageNotFoundError:
        return {}

    versions: dict[str, str] = {}
    for requirement in requirements:
        # "pydantic>=2.11.7", "pytest; extra == 'test'" -> "pydantic"
        name = re.split(r"[<>=!~;\s\[]", requirement, maxsplit=1)[0].strip()
        if not name or name in versions:
            continue
        try:
            versions[name] = md.version(name)
        except md.PackageNotFoundError:
            versions[name] = "not installed"
    return versions


def debug_info() -> str:
    """Return a summary of the runtime environment.

    Returns:
        A multi-line report naming the OS, architecture, interpreter,
        package version and the version of every dependency.
    """
    try:
        installed = md.version(_DISTRIBUTION)
    except md.PackageNotFoundError:  # pragma: no cover - source checkout
        installed = "not installed"

    lines = [
        f"OS: {platform.system()} {platform.release()} ({platform.version()})",
        f"Architecture: {platform.machine()}",
        f"Python version: {platform.python_version()}",
        f"App version: {installed}",
        "Dependencies:",
    ]
    for name, installed_version in dependency_versions().items():
        lines.append(f"* {name}: {installed_version}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface.

    Args:
        argv: Arguments to parse. Defaults to ``sys.argv[1:]``.

    Returns:
        The process exit status.
    """
    parser = argparse.ArgumentParser(
        prog=_DISTRIBUTION,
        description="Turn a pydantic model into a desktop form.",
    )
    parser.add_argument(
        "--version", action="store_true", help="show the installed version"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="show environment details for a bug report",
    )
    args = parser.parse_args(argv)

    if args.version:
        # Read the metadata directly rather than importing the
        # package: `brayer` pulls in Qt, and `--version` should not
        # need a display or a Qt platform plugin to answer.
        try:
            print(md.version(_DISTRIBUTION))
        except md.PackageNotFoundError:
            print("0.0.0")
    elif args.debug:
        print(debug_info())
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
