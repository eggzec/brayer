"""Shared fixtures.

``QT_QPA_PLATFORM`` is set before PySide6 is imported anywhere, so the
whole suite runs without a display. Qt reads the variable once, when the
platform plugin is loaded, which is why this happens at import time
rather than in a fixture.
"""

from __future__ import annotations

import os


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Silence the "could not connect to display" chatter some runners emit.
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

import pytest
from PySide6 import QtWidgets


@pytest.fixture(scope="session")
def qapp() -> QtWidgets.QApplication:
    """Return the process-wide QApplication.

    Qt allows exactly one per process, so this is session-scoped and
    reused. It is deliberately never destroyed: tearing it down while
    widgets still exist crashes the interpreter rather than failing a
    test.

    Returns:
        The application instance.
    """
    existing = QtWidgets.QApplication.instance()
    if existing is not None:
        return existing
    return QtWidgets.QApplication([])


@pytest.fixture()
def widgets(qapp: QtWidgets.QApplication) -> list[QtWidgets.QWidget]:
    """Collect widgets for deletion at the end of a test.

    Args:
        qapp: The session application.

    Yields:
        A list to append widgets to. Everything in it is scheduled for
        deletion when the test ends, which keeps a long run from
        accumulating thousands of live top-level windows.
    """
    created: list[QtWidgets.QWidget] = []
    yield created
    for widget in created:
        widget.deleteLater()
    qapp.processEvents()
