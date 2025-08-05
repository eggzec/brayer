"""Reusable editors for collection-valued fields.

Both widgets keep the real Python objects alive in Qt's item data rather
than storing a string and parsing it back. An earlier design round-tripped
every value through ``repr()`` and ``ast.literal_eval``, which silently
destroyed anything that is not a Python literal -- a ``date``, a
``Decimal``, an ``Enum`` member or a nested model would either raise or
come back as the wrong type. Holding the object itself removes that whole
class of failure and lets the editors carry any value at all.
"""

from __future__ import annotations

import enum
import typing

from PySide6 import QtCore, QtGui, QtWidgets


__all__ = ["DictEditWidget", "ListEditWidget", "format_value"]

_VALUE_ROLE = QtCore.Qt.ItemDataRole.UserRole


def format_value(value: object) -> str:
    """Render a value for display in a list or table cell.

    Args:
        value: Any value held by one of the editors.

    Returns:
        A short human-readable string. Strings are shown unquoted, enum
        members by name, and everything else via ``str``.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, enum.Enum):
        return str(value.name)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


class ListEditWidget(QtWidgets.QListWidget):
    """An add/remove/reorder editor for a list of values.

    Items may be reordered by dragging, and removed with the Delete key
    or the right-click menu. The values themselves are stored on the
    items, so any Python object survives a round trip unchanged.
    """

    contents_changed = QtCore.Signal()
    """Emitted whenever items are added, removed or reordered."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(
            QtWidgets.QAbstractItemView.DragDropMode.InternalMove
        )
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.model().rowsMoved.connect(self.contents_changed)

        self._remove_action = QtGui.QAction("Remove", self)
        self._remove_action.setShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Delete)
        )
        self._remove_action.setShortcutContext(
            QtCore.Qt.ShortcutContext.WidgetShortcut
        )
        self._remove_action.triggered.connect(self.remove_selected)
        self.addAction(self._remove_action)

        self._clear_action = QtGui.QAction("Remove all", self)
        self._clear_action.triggered.connect(self.clear_values)

        self.setStyleSheet(
            """
            QListWidget::item {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background-color: palette(highlight);
                color: palette(highlighted-text);
            }
            """
        )

    def _show_context_menu(self, position: QtCore.QPoint) -> None:
        """Show the item menu at the cursor.

        Args:
            position: Where the menu was requested, in widget
                coordinates.
        """
        menu = QtWidgets.QMenu(self)
        menu.addAction(self._remove_action)
        menu.addAction(self._clear_action)
        self._remove_action.setEnabled(bool(self.selectedItems()))
        self._clear_action.setEnabled(self.count() > 0)
        menu.exec(self.viewport().mapToGlobal(position))

    def add_value(self, value: object) -> None:
        """Append a value to the list.

        Args:
            value: Any Python object. It is stored as-is and returned
                unchanged by :meth:`get_values`.
        """
        item = QtWidgets.QListWidgetItem(format_value(value))
        item.setData(_VALUE_ROLE, value)
        item.setToolTip(format_value(value))
        self.addItem(item)
        self.contents_changed.emit()

    def set_values(self, values: typing.Iterable[object]) -> None:
        """Replace the entire contents of the list.

        Args:
            values: The values to show, in order.
        """
        self.clear()
        for value in values:
            item = QtWidgets.QListWidgetItem(format_value(value))
            item.setData(_VALUE_ROLE, value)
            self.addItem(item)
        self.contents_changed.emit()

    def get_values(self) -> list[object]:
        """Return every value currently held, in display order.

        Returns:
            The stored objects themselves, not reconstructed copies.
        """
        return [self.item(row).data(_VALUE_ROLE) for row in range(self.count())]

    def remove_selected(self) -> None:
        """Remove every selected item."""
        rows = sorted(
            (self.row(item) for item in self.selectedItems()), reverse=True
        )
        for row in rows:
            self.takeItem(row)
        if rows:
            self.contents_changed.emit()

    def clear_values(self) -> None:
        """Remove every item."""
        if self.count():
            self.clear()
            self.contents_changed.emit()


class DictEditWidget(QtWidgets.QTableWidget):
    """A key/value editor backed by real Python objects.

    Keys stay unique. Uniqueness is checked against the rows actually
    present rather than against a set that only ever grew -- the earlier
    design leaked removed keys, so a key could never be re-added once
    deleted.
    """

    contents_changed = QtCore.Signal()
    """Emitted whenever a pair is added or removed."""

    rejected_key = QtCore.Signal(str)
    """Emitted with a reason when a pair could not be added."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(0, 2, parent)
        self.setHorizontalHeaderLabels(["Key", "Value"])
        self.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.verticalHeader().setVisible(False)

        self._remove_action = QtGui.QAction("Remove selected rows", self)
        self._remove_action.setShortcut(
            QtGui.QKeySequence(QtCore.Qt.Key.Key_Delete)
        )
        self._remove_action.setShortcutContext(
            QtCore.Qt.ShortcutContext.WidgetShortcut
        )
        self._remove_action.triggered.connect(self.remove_selected)
        self.addAction(self._remove_action)

    def _show_context_menu(self, position: QtCore.QPoint) -> None:
        """Show the row menu at the cursor.

        Args:
            position: Where the menu was requested, in viewport
                coordinates.
        """
        menu = QtWidgets.QMenu(self)
        menu.addAction(self._remove_action)
        self._remove_action.setEnabled(bool(self.selectedIndexes()))
        menu.exec(self.viewport().mapToGlobal(position))

    def keys(self) -> list[object]:
        """Return the keys currently in the table, in row order.

        Returns:
            The stored key objects.
        """
        return [
            self.item(row, 0).data(_VALUE_ROLE)
            for row in range(self.rowCount())
        ]

    def add_pair(self, key: object, value: object) -> bool:
        """Add one key/value pair.

        Args:
            key: The key. Must be hashable and not already present.
            value: Any Python object.

        Returns:
            ``True`` if the pair was added, ``False`` if it was rejected
            for being unhashable or duplicate. A reason is emitted on
            :attr:`rejected_key` either way.
        """
        try:
            hash(key)
        except TypeError:
            self.rejected_key.emit(
                f"Key of type {type(key).__name__} is not hashable"
            )
            return False

        if any(existing == key for existing in self.keys()):
            self.rejected_key.emit(f"Key {format_value(key)!r} already exists")
            return False

        row = self.rowCount()
        self.insertRow(row)
        for column, item_value in ((0, key), (1, value)):
            item = QtWidgets.QTableWidgetItem(format_value(item_value))
            item.setData(_VALUE_ROLE, item_value)
            self.setItem(row, column, item)
        self.contents_changed.emit()
        return True

    def set_mapping(self, mapping: typing.Mapping[object, object]) -> None:
        """Replace the entire contents of the table.

        Args:
            mapping: The pairs to show.
        """
        self.setRowCount(0)
        for key, value in mapping.items():
            self.add_pair(key, value)

    def get_dict(self) -> dict[object, object]:
        """Return the mapping currently held.

        Returns:
            A new dict of the stored key and value objects.
        """
        result: dict[object, object] = {}
        for row in range(self.rowCount()):
            key_item = self.item(row, 0)
            value_item = self.item(row, 1)
            if key_item is None or value_item is None:  # pragma: no cover
                continue
            result[key_item.data(_VALUE_ROLE)] = value_item.data(_VALUE_ROLE)
        return result

    def remove_selected(self) -> None:
        """Remove every selected row."""
        rows = sorted(
            {index.row() for index in self.selectedIndexes()}, reverse=True
        )
        for row in rows:
            self.removeRow(row)
        if rows:
            self.contents_changed.emit()
