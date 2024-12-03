import logging
import sys
from typing import Optional, Set

from PySide6.QtCore import (
    QAbstractTableModel,
    QItemSelectionModel,
    QModelIndex,
    Qt
)
from PySide6.QtGui import (
    QAction,
    QKeySequence,
    QShortcut,
    QUndoCommand,
    QUndoStack
)
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QPushButton,
    QTableView,
    QUndoView,
    QVBoxLayout,
    QWidget
)

# Logger setup
def create_logger(name="TableUndoRedoLogger", log_level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.handlers.clear()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger


logger = create_logger()

# Selection state management
class SelectionState:
    def __init__(self, selection_model: Optional[QItemSelectionModel] = None):
        self.selected_rows: Set[int] = set()
        self.selected_indexes: Set[QModelIndex] = set()
        if selection_model:
            self.capture_selection(selection_model)

    def capture_selection(self, selection_model: QItemSelectionModel):
        self.selected_rows.clear()
        for index in selection_model.selectedIndexes():
            if index.isValid():
                self.selected_rows.add(index.row())

    def apply_selection(self, selection_model: QItemSelectionModel):
        selection_model.clearSelection()
        for row in sorted(self.selected_rows):
            index = selection_model.model().index(row, 0)
            selection_model.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)

# Undo/Redo commands
class SelectionUndoCommand(QUndoCommand):
    def __init__(self, selection_model: QItemSelectionModel, old_state: SelectionState, new_state: SelectionState):
        super().__init__("Selection Change")
        self.selection_model = selection_model
        self.old_state = old_state
        self.new_state = new_state

    def undo(self):
        self.old_state.apply_selection(self.selection_model)

    def redo(self):
        self.new_state.apply_selection(self.selection_model)

class EditRowCommand(QUndoCommand):
    def __init__(self, model, row, old_values, new_values):
        super().__init__(f"Edit Row {row}")
        self.model = model
        self.row = row
        self.old_values = old_values
        self.new_values = new_values

    def undo(self):
        for col, value in enumerate(self.old_values):
            index = self.model.index(self.row, col)
            self.model.setData(index, value)

    def redo(self):
        for col, value in enumerate(self.new_values):
            index = self.model.index(self.row, col)
            self.model.setData(index, value)

class MyTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self.data_array = data or [["Item 1", "Description 1"], ["Item 2", "Description 2"]]

    def rowCount(self, parent=QModelIndex()):
        return len(self.data_array)

    def columnCount(self, parent=QModelIndex()):
        return len(self.data_array[0]) if self.data_array else 0

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            return self.data_array[index.row()][index.column()]
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            self.data_array[index.row()][index.column()] = value
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def flags(self, index):
        return Qt.ItemIsEditable | super().flags(index)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.undo_stack = QUndoStack(self)
        self.model = MyTableModel()
        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setStyleSheet("""
            QTableView {
                border: 1px solid #dcdcdc;
                background-color: #f9f9f9;
                gridline-color: #e0e0e0;
                selection-background-color: #c8e6c9;
            }
            QTableView::item {
                padding: 10px;
            }
            QTableView::item:selected {
                background-color: #8bc34a;
                color: white;
            }
            QTableView QTableCornerButton::section {
                background-color: #e0e0e0;
                border: none;
            }
        """)
        self.table_view.setAlternatingRowColors(True)

        self.selection_model = self.table_view.selectionModel()
        self.previous_selection = SelectionState(self.selection_model)
        self.selection_model.selectionChanged.connect(self.handle_selection_change)

        undo_view = QUndoView(self.undo_stack)
        undo_button = QPushButton("Undo")
        undo_button.setStyleSheet("background-color: #8bc34a; color: white; padding: 5px; font-size: 16px;")
        undo_button.clicked.connect(self.undo_stack.undo)

        redo_button = QPushButton("Redo")
        redo_button.setStyleSheet("background-color: #8bc34a; color: white; padding: 5px; font-size: 16px;")
        redo_button.clicked.connect(self.undo_stack.redo)

        layout = QVBoxLayout()
        layout.addWidget(self.table_view)
        layout.addWidget(undo_view)
        layout.addWidget(undo_button)
        layout.addWidget(redo_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.setWindowTitle("Table Undo/Redo Example")
        self.setGeometry(100, 100, 800, 600)

        # Add keyboard shortcuts for Undo and Redo
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.undo_shortcut.activated.connect(self.undo_stack.undo)
        self.redo_shortcut.activated.connect(self.undo_stack.redo)

    def handle_selection_change(self):
        current_selection = SelectionState(self.selection_model)
        if current_selection.selected_rows != self.previous_selection.selected_rows:
            command = SelectionUndoCommand(
                self.selection_model, self.previous_selection, current_selection
            )
            self.undo_stack.push(command)
        self.previous_selection = current_selection


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
