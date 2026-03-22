"""
Action Handler Module
SOLID-compliant action handlers for data management operations.
Eliminates code duplication by providing a unified interface for all data categories.

Principles applied:
- Single Responsibility: Each class has one reason to change
- Open/Closed: Extensible via strategy pattern without modification
- Liskov Substitution: Handlers are interchangeable for their interfaces
- Interface Segregation: Small, focused protocols
- Dependency Inversion: Depends on abstractions, not concretions
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any, Callable, Dict, List, Optional, Protocol, Type, TypeVar, Union
)
import csv
import json
import copy

from PySide6.QtWidgets import QWidget, QMessageBox, QFileDialog
from PySide6.QtCore import QObject, Signal


# Type variable for generic typing
T = TypeVar('T', bound=Dict[str, Any])


# =============================================================================
# Protocols (Interface Segregation Principle)
# =============================================================================

class DataManagerProtocol(Protocol):
    """Protocol for data management operations"""

    def add_item(self, category: Any, name: str, data: Dict) -> bool:
        """Add a new item to the category"""
        ...

    def edit_item(self, category: Any, name: str, data: Dict) -> bool:
        """Edit an existing item"""
        ...

    def remove_item(self, category: Any, name: str) -> bool:
        """Remove an item from the category"""
        ...

    def reset_category(self, category: Any) -> bool:
        """Reset a category to defaults"""
        ...

    def get_item(self, category: Any, name: str) -> Optional[Dict]:
        """Get an item by name"""
        ...

    def get_all_items(self, category: Any) -> List[Dict]:
        """Get all items in a category"""
        ...


class TableWidgetProtocol(Protocol):
    """Protocol for table/visualization widgets"""

    def reload_data(self) -> None:
        """Reload data from the data source"""
        ...


class InfoPanelProtocol(Protocol):
    """Protocol for info panel widgets"""

    def show_default(self) -> None:
        """Show the default state"""
        ...

    def start_add(self, template_data: Optional[Dict] = None) -> None:
        """Start add mode"""
        ...

    def start_edit(self, data: Dict) -> None:
        """Start edit mode"""
        ...


class ControlPanelProtocol(Protocol):
    """Protocol for control panel widgets"""

    def set_item_selected(self, selected: bool) -> None:
        """Update selection state"""
        ...

    def update_item_count(self, count: int) -> None:
        """Update item count display"""
        ...


# =============================================================================
# Data Classes (Single Responsibility Principle)
# =============================================================================

@dataclass
class DataActionContext:
    """
    Context object containing all dependencies needed for data actions.

    This is the configuration object that defines how the handler should
    interact with a specific data category's UI components.

    Attributes:
        category: The DataCategory enum value for this context
        table: The visualization table widget
        info_panel: The info panel widget for displaying/editing items
        control_panel: The control panel widget with action buttons
        creation_dialog_class: Optional dialog class for creation operations
        name_key: The key used to get item name from data dict (e.g., 'name', 'Name')
        filename_generator: Function to generate filename from item data
        selected_item_attr: Attribute name on table for selected item
        items_attr: Attribute name on table for base items list
        category_display_name: Human-readable name for the category
        remove_confirm_title: Title for remove confirmation dialog
        reset_confirm_title: Title for reset confirmation dialog
        reset_confirm_message: Message for reset confirmation dialog
    """
    category: Any  # DataCategory enum
    table: QWidget
    info_panel: QWidget
    control_panel: QWidget
    creation_dialog_class: Optional[Type] = None
    name_key: str = 'name'
    filename_generator: Callable[[Dict], str] = field(
        default_factory=lambda: lambda item: item.get('name', 'Unknown').replace(' ', '_')
    )
    selected_item_attr: str = 'selected_item'
    items_attr: str = 'base_items'
    category_display_name: str = 'Item'
    remove_confirm_title: str = 'Remove Item'
    reset_confirm_title: str = 'Reset Items'
    reset_confirm_message: str = 'Are you sure you want to reset all items to defaults?'


@dataclass
class ActionResult:
    """
    Result of a data action operation.

    Attributes:
        success: Whether the operation succeeded
        message: Optional message (error or success)
        data: Optional resulting data
    """
    success: bool
    message: Optional[str] = None
    data: Optional[Dict] = None


# =============================================================================
# Command Pattern for Undo/Redo (Open/Closed Principle)
# =============================================================================

class Command(ABC):
    """Abstract base class for undoable commands"""

    @abstractmethod
    def execute(self) -> ActionResult:
        """Execute the command"""
        pass

    @abstractmethod
    def undo(self) -> ActionResult:
        """Undo the command"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of the command"""
        pass


class AddItemCommand(Command):
    """Command for adding an item"""

    def __init__(
        self,
        data_manager: DataManagerProtocol,
        category: Any,
        name: str,
        data: Dict
    ):
        self._data_manager = data_manager
        self._category = category
        self._name = name
        self._data = data
        self._executed = False

    def execute(self) -> ActionResult:
        success = self._data_manager.add_item(self._category, self._name, self._data)
        self._executed = success
        return ActionResult(
            success=success,
            message=f"Added '{self._name}'" if success else f"Failed to add '{self._name}'"
        )

    def undo(self) -> ActionResult:
        if not self._executed:
            return ActionResult(success=False, message="Cannot undo: command was not executed")

        success = self._data_manager.remove_item(self._category, self._name)
        if success:
            self._executed = False
        return ActionResult(
            success=success,
            message=f"Removed '{self._name}'" if success else f"Failed to remove '{self._name}'"
        )

    @property
    def description(self) -> str:
        return f"Add {self._name}"


class RemoveItemCommand(Command):
    """Command for removing an item"""

    def __init__(
        self,
        data_manager: DataManagerProtocol,
        category: Any,
        name: str,
        backup_data: Dict
    ):
        self._data_manager = data_manager
        self._category = category
        self._name = name
        self._backup_data = backup_data
        self._executed = False

    def execute(self) -> ActionResult:
        success = self._data_manager.remove_item(self._category, self._name)
        self._executed = success
        return ActionResult(
            success=success,
            message=f"Removed '{self._name}'" if success else f"Failed to remove '{self._name}'"
        )

    def undo(self) -> ActionResult:
        if not self._executed:
            return ActionResult(success=False, message="Cannot undo: command was not executed")

        success = self._data_manager.add_item(self._category, self._name, self._backup_data)
        if success:
            self._executed = False
        return ActionResult(
            success=success,
            message=f"Restored '{self._name}'" if success else f"Failed to restore '{self._name}'"
        )

    @property
    def description(self) -> str:
        return f"Remove {self._name}"


class EditItemCommand(Command):
    """Command for editing an item"""

    def __init__(
        self,
        data_manager: DataManagerProtocol,
        category: Any,
        name: str,
        old_data: Dict,
        new_data: Dict
    ):
        self._data_manager = data_manager
        self._category = category
        self._name = name
        self._old_data = old_data
        self._new_data = new_data
        self._executed = False

    def execute(self) -> ActionResult:
        success = self._data_manager.edit_item(self._category, self._name, self._new_data)
        self._executed = success
        return ActionResult(
            success=success,
            message=f"Edited '{self._name}'" if success else f"Failed to edit '{self._name}'"
        )

    def undo(self) -> ActionResult:
        if not self._executed:
            return ActionResult(success=False, message="Cannot undo: command was not executed")

        success = self._data_manager.edit_item(self._category, self._name, self._old_data)
        if success:
            self._executed = False
        return ActionResult(
            success=success,
            message=f"Reverted '{self._name}'" if success else f"Failed to revert '{self._name}'"
        )

    @property
    def description(self) -> str:
        return f"Edit {self._name}"


class CommandHistory:
    """
    Manages command history for undo/redo operations.

    Implements a simple stack-based undo/redo system with configurable
    maximum history size.
    """

    def __init__(self, max_history: int = 50):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self._max_history = max_history

    def execute(self, command: Command) -> ActionResult:
        """Execute a command and add it to the undo stack"""
        result = command.execute()

        if result.success:
            self._undo_stack.append(command)
            self._redo_stack.clear()  # Clear redo stack on new command

            # Trim history if needed
            if len(self._undo_stack) > self._max_history:
                self._undo_stack.pop(0)

        return result

    def undo(self) -> Optional[ActionResult]:
        """Undo the last command"""
        if not self._undo_stack:
            return None

        command = self._undo_stack.pop()
        result = command.undo()

        if result.success:
            self._redo_stack.append(command)
        else:
            # Restore to undo stack if undo failed
            self._undo_stack.append(command)

        return result

    def redo(self) -> Optional[ActionResult]:
        """Redo the last undone command"""
        if not self._redo_stack:
            return None

        command = self._redo_stack.pop()
        result = command.execute()

        if result.success:
            self._undo_stack.append(command)
        else:
            # Restore to redo stack if redo failed
            self._redo_stack.append(command)

        return result

    def can_undo(self) -> bool:
        """Check if there are commands to undo"""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if there are commands to redo"""
        return len(self._redo_stack) > 0

    def get_undo_description(self) -> Optional[str]:
        """Get the description of the next undo command"""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get the description of the next redo command"""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None

    def clear(self) -> None:
        """Clear all history"""
        self._undo_stack.clear()
        self._redo_stack.clear()


# =============================================================================
# Export/Import Handlers (Single Responsibility Principle)
# =============================================================================

class ExportHandler:
    """
    Handles export operations for items.

    Supports JSON and CSV export formats with proper error handling.
    """

    @staticmethod
    def export_json(item: Dict, filepath: Path) -> bool:
        """
        Export a single item to JSON format.

        Args:
            item: The item data to export
            filepath: The target file path

        Returns:
            True if export succeeded, False otherwise
        """
        try:
            # Remove internal fields before export
            export_data = {k: v for k, v in item.items() if not k.startswith('_')}

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, OSError, TypeError, ValueError) as e:
            print(f"Error exporting to JSON: {e}")
            return False

    @staticmethod
    def export_csv(items: List[Dict], filepath: Path) -> bool:
        """
        Export multiple items to CSV format.

        Args:
            items: List of item data dictionaries
            filepath: The target file path

        Returns:
            True if export succeeded, False otherwise
        """
        if not items:
            return False

        try:
            # Collect all unique keys across all items (excluding internal fields)
            all_keys = set()
            for item in items:
                all_keys.update(k for k in item.keys() if not k.startswith('_'))

            # Sort keys for consistent output
            fieldnames = sorted(all_keys)

            with open(filepath, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()

                for item in items:
                    # Filter out internal fields and flatten complex values
                    row = {}
                    for k, v in item.items():
                        if not k.startswith('_'):
                            if isinstance(v, (list, dict)):
                                row[k] = json.dumps(v)
                            else:
                                row[k] = v
                    writer.writerow(row)

            return True
        except (IOError, OSError, csv.Error) as e:
            print(f"Error exporting to CSV: {e}")
            return False

    @staticmethod
    def import_json(filepath: Path) -> Optional[Dict]:
        """
        Import an item from JSON format.

        Args:
            filepath: The source file path

        Returns:
            The imported item data, or None if import failed
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except (IOError, OSError, json.JSONDecodeError) as e:
            print(f"Error importing from JSON: {e}")
            return None


# =============================================================================
# Duplicate Handler (Single Responsibility Principle)
# =============================================================================

class DuplicateHandler:
    """
    Handles item duplication operations.

    Creates deep copies of items with modified identifiers to avoid conflicts.
    """

    @staticmethod
    def duplicate_item(
        item: Dict,
        name_key: str = 'name',
        suffix: str = ' (Copy)'
    ) -> Dict:
        """
        Create a duplicate of an item with a modified name.

        Args:
            item: The item data to duplicate
            name_key: The key used for the item's name
            suffix: Suffix to append to the duplicated item's name

        Returns:
            A new dictionary containing the duplicated item data
        """
        # Deep copy the item
        duplicated = copy.deepcopy(item)

        # Remove internal fields that shouldn't be duplicated
        keys_to_remove = [k for k in duplicated.keys() if k.startswith('_')]
        for key in keys_to_remove:
            del duplicated[key]

        # Modify the name
        original_name = duplicated.get(name_key, 'Unknown')
        duplicated[name_key] = f"{original_name}{suffix}"

        # Handle specific fields that might need modification
        # For elements: atomic_number should be incremented or cleared
        if 'atomic_number' in duplicated:
            # Mark as custom element by clearing atomic number
            # or setting to a high value
            duplicated['atomic_number'] = 999

        # For items with unique IDs, generate a new one
        if 'id' in duplicated:
            import uuid
            duplicated['id'] = str(uuid.uuid4())

        return duplicated


# =============================================================================
# Main Data Action Handler (Dependency Inversion Principle)
# =============================================================================

class DataActionHandler(QObject):
    """
    Unified handler for data management actions.

    This class eliminates code duplication by providing a single implementation
    for add, edit, remove, reset, and create operations that works across all
    data categories (atoms, quarks, subatomic, molecules, alloys).

    The handler uses dependency injection to remain decoupled from specific
    implementations, following the Dependency Inversion Principle.

    Signals:
        data_changed: Emitted when data has been modified
        item_selected: Emitted when item selection changes
        action_completed: Emitted after any action completes with result
    """

    # Signals
    data_changed = Signal()
    item_selected = Signal(object)  # Emits the selected item or None
    action_completed = Signal(ActionResult)

    def __init__(
        self,
        parent: QWidget,
        context: DataActionContext,
        data_manager: Optional[DataManagerProtocol] = None,
        enable_undo: bool = True
    ):
        """
        Initialize the action handler.

        Args:
            parent: Parent widget for dialogs
            context: Context object with category-specific configuration
            data_manager: Data manager instance (uses global if not provided)
            enable_undo: Whether to enable undo/redo functionality
        """
        super().__init__(parent)
        self._parent = parent
        self._context = context

        # Get data manager (dependency injection with fallback)
        if data_manager is None:
            from periodica.data.data_manager import get_data_manager
            self._data_manager = get_data_manager()
        else:
            self._data_manager = data_manager

        # Command history for undo/redo
        self._command_history = CommandHistory() if enable_undo else None

        # Export/Import and Duplicate handlers
        self._export_handler = ExportHandler()
        self._duplicate_handler = DuplicateHandler()

    # =========================================================================
    # Core Actions
    # =========================================================================

    def add(self) -> None:
        """
        Handle add request.

        Shows the inline editor in add mode, optionally using the currently
        selected item as a template.
        """
        template = self._get_selected_item()

        # Check if info panel supports inline editing
        info_panel = self._context.info_panel
        if hasattr(info_panel, 'start_add'):
            info_panel.start_add(template)
        else:
            # Fall back to dialog-based editing
            from periodica_app.ui.data_editor_dialog import DataEditorDialog
            dialog = DataEditorDialog(self._context.category, parent=self._parent)
            if dialog.exec():
                self._refresh_after_change()

    def edit(self) -> None:
        """
        Handle edit request.

        Shows the inline editor in edit mode for the currently selected item.
        """
        selected = self._get_selected_item()
        if not selected:
            return

        # Check if info panel supports inline editing
        info_panel = self._context.info_panel
        if hasattr(info_panel, 'start_edit'):
            info_panel.start_edit(selected)
        else:
            # Fall back to dialog-based editing
            from periodica_app.ui.data_editor_dialog import DataEditorDialog
            dialog = DataEditorDialog(
                self._context.category,
                existing_data=selected,
                parent=self._parent
            )
            if dialog.exec():
                self._refresh_after_change()

    def remove(self) -> None:
        """
        Handle remove request.

        Shows a confirmation dialog and removes the selected item if confirmed.
        """
        selected = self._get_selected_item()
        if not selected:
            return

        name = selected.get(self._context.name_key, 'Unknown')

        reply = QMessageBox.question(
            self._parent,
            self._context.remove_confirm_title,
            f"Are you sure you want to remove '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        filename = self._context.filename_generator(selected)

        # Use command pattern if undo is enabled
        if self._command_history is not None:
            command = RemoveItemCommand(
                self._data_manager,
                self._context.category,
                filename,
                selected
            )
            result = self._command_history.execute(command)
        else:
            success = self._data_manager.remove_item(
                self._context.category,
                filename
            )
            result = ActionResult(success=success)

        if result.success:
            self._refresh_after_change()
            self._context.info_panel.show_default()
            self._context.control_panel.set_item_selected(False)

        self.action_completed.emit(result)

    def reset(self) -> None:
        """
        Handle reset request.

        Shows a confirmation dialog and resets the category to defaults if confirmed.
        """
        reply = QMessageBox.question(
            self._parent,
            self._context.reset_confirm_title,
            self._context.reset_confirm_message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        success = self._data_manager.reset_category(self._context.category)
        result = ActionResult(success=success)

        if success:
            self._refresh_after_change()
            self._context.info_panel.show_default()
            QMessageBox.information(
                self._parent,
                "Success",
                f"{self._context.category_display_name}s reset to defaults."
            )

            # Clear command history on reset
            if self._command_history is not None:
                self._command_history.clear()

        self.action_completed.emit(result)

    def create(self) -> None:
        """
        Handle create request.

        Shows the creation dialog if one is configured for this context.
        If no dialog is configured, falls back to add mode.
        """
        if self._context.creation_dialog_class is None:
            # No creation dialog, fall back to add
            self.add()
            return

        dialog = self._context.creation_dialog_class(self._parent)

        # Connect creation signal if available
        signal_names = ['atom_created', 'particle_created', 'molecule_created', 'alloy_created']
        for signal_name in signal_names:
            if hasattr(dialog, signal_name):
                signal = getattr(dialog, signal_name)
                signal.connect(lambda: self.on_data_saved(None))
                break

        dialog.exec()

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def on_data_saved(self, data: Optional[Dict]) -> None:
        """
        Handle data saved event from inline editor or creation dialog.

        Args:
            data: The saved data (may be None for some creation flows)
        """
        self._refresh_after_change()
        self._context.info_panel.show_default()
        self.data_changed.emit()

    def on_selection_changed(self, item: Optional[Dict]) -> None:
        """
        Handle selection change event from the table widget.

        Args:
            item: The newly selected item, or None if deselected
        """
        # Update info panel
        info_panel = self._context.info_panel
        update_methods = ['update_element', 'update_quark', 'update_particle',
                         'update_molecule', 'update_alloy']

        for method_name in update_methods:
            if hasattr(info_panel, method_name):
                getattr(info_panel, method_name)(item)
                break
        else:
            # Fallback: call show_default if item is None
            if item is None:
                info_panel.show_default()

        # Update control panel
        self._context.control_panel.set_item_selected(item is not None)

        self.item_selected.emit(item)

    # =========================================================================
    # Undo/Redo Support
    # =========================================================================

    def undo(self) -> Optional[ActionResult]:
        """
        Undo the last action.

        Returns:
            The result of the undo operation, or None if nothing to undo
        """
        if self._command_history is None:
            return None

        result = self._command_history.undo()
        if result and result.success:
            self._refresh_after_change()

        return result

    def redo(self) -> Optional[ActionResult]:
        """
        Redo the last undone action.

        Returns:
            The result of the redo operation, or None if nothing to redo
        """
        if self._command_history is None:
            return None

        result = self._command_history.redo()
        if result and result.success:
            self._refresh_after_change()

        return result

    def can_undo(self) -> bool:
        """Check if undo is available"""
        return self._command_history is not None and self._command_history.can_undo()

    def can_redo(self) -> bool:
        """Check if redo is available"""
        return self._command_history is not None and self._command_history.can_redo()

    # =========================================================================
    # Export/Import Operations
    # =========================================================================

    def export_selected_json(self) -> bool:
        """
        Export the currently selected item to JSON.

        Returns:
            True if export succeeded, False otherwise
        """
        selected = self._get_selected_item()
        if not selected:
            QMessageBox.warning(
                self._parent,
                "No Selection",
                "Please select an item to export."
            )
            return False

        name = selected.get(self._context.name_key, 'export')
        default_filename = f"{name.replace(' ', '_')}.json"

        filepath, _ = QFileDialog.getSaveFileName(
            self._parent,
            f"Export {self._context.category_display_name}",
            default_filename,
            "JSON Files (*.json)"
        )

        if not filepath:
            return False

        success = self._export_handler.export_json(selected, Path(filepath))

        if success:
            QMessageBox.information(
                self._parent,
                "Export Successful",
                f"Exported to {filepath}"
            )
        else:
            QMessageBox.warning(
                self._parent,
                "Export Failed",
                "Failed to export the item."
            )

        return success

    def export_all_csv(self) -> bool:
        """
        Export all items to CSV.

        Returns:
            True if export succeeded, False otherwise
        """
        items = self._get_all_items()
        if not items:
            QMessageBox.warning(
                self._parent,
                "No Data",
                "No items to export."
            )
            return False

        default_filename = f"{self._context.category_display_name.lower()}s.csv"

        filepath, _ = QFileDialog.getSaveFileName(
            self._parent,
            f"Export All {self._context.category_display_name}s",
            default_filename,
            "CSV Files (*.csv)"
        )

        if not filepath:
            return False

        success = self._export_handler.export_csv(items, Path(filepath))

        if success:
            QMessageBox.information(
                self._parent,
                "Export Successful",
                f"Exported {len(items)} items to {filepath}"
            )
        else:
            QMessageBox.warning(
                self._parent,
                "Export Failed",
                "Failed to export items."
            )

        return success

    def import_json(self) -> bool:
        """
        Import an item from JSON.

        Returns:
            True if import succeeded, False otherwise
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self._parent,
            f"Import {self._context.category_display_name}",
            "",
            "JSON Files (*.json)"
        )

        if not filepath:
            return False

        data = self._export_handler.import_json(Path(filepath))

        if data is None:
            QMessageBox.warning(
                self._parent,
                "Import Failed",
                "Failed to read the JSON file."
            )
            return False

        # Use filename as item name if not present
        name = data.get(self._context.name_key)
        if not name:
            name = Path(filepath).stem
            data[self._context.name_key] = name

        filename = self._context.filename_generator(data)
        success = self._data_manager.add_item(self._context.category, filename, data)

        if success:
            self._refresh_after_change()
            QMessageBox.information(
                self._parent,
                "Import Successful",
                f"Imported '{name}'"
            )
        else:
            QMessageBox.warning(
                self._parent,
                "Import Failed",
                f"Failed to import '{name}'. It may already exist."
            )

        return success

    # =========================================================================
    # Duplicate Operation
    # =========================================================================

    def duplicate_selected(self) -> bool:
        """
        Duplicate the currently selected item.

        Returns:
            True if duplication succeeded, False otherwise
        """
        selected = self._get_selected_item()
        if not selected:
            QMessageBox.warning(
                self._parent,
                "No Selection",
                "Please select an item to duplicate."
            )
            return False

        duplicated = self._duplicate_handler.duplicate_item(
            selected,
            self._context.name_key
        )

        filename = self._context.filename_generator(duplicated)
        success = self._data_manager.add_item(
            self._context.category,
            filename,
            duplicated
        )

        if success:
            self._refresh_after_change()
            name = duplicated.get(self._context.name_key, 'Unknown')
            QMessageBox.information(
                self._parent,
                "Duplicate Successful",
                f"Created '{name}'"
            )
        else:
            QMessageBox.warning(
                self._parent,
                "Duplicate Failed",
                "Failed to create duplicate."
            )

        return success

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_selected_item(self) -> Optional[Dict]:
        """Get the currently selected item from the table"""
        table = self._context.table
        attr = self._context.selected_item_attr

        # Try the configured attribute
        if hasattr(table, attr):
            return getattr(table, attr)

        # Try common attribute names
        common_attrs = [
            'selected_element', 'selected_quark', 'selected_particle',
            'selected_molecule', 'selected_alloy', 'selected_item'
        ]

        for common_attr in common_attrs:
            if hasattr(table, common_attr):
                return getattr(table, common_attr)

        return None

    def _get_all_items(self) -> List[Dict]:
        """Get all items from the data manager"""
        return self._data_manager.get_all_items(self._context.category)

    def _get_item_count(self) -> int:
        """Get the count of items"""
        table = self._context.table
        attr = self._context.items_attr

        # Try the configured attribute
        if hasattr(table, attr):
            items = getattr(table, attr)
            if items is not None:
                return len(items)

        # Try common attribute names
        common_attrs = [
            'base_elements', 'base_particles', 'particles',
            'base_molecules', 'base_alloys', 'items'
        ]

        for common_attr in common_attrs:
            if hasattr(table, common_attr):
                items = getattr(table, common_attr)
                if items is not None:
                    return len(items)

        # Fall back to data manager
        return len(self._data_manager.get_all_items(self._context.category))

    def _refresh_after_change(self) -> None:
        """Refresh UI after a data change"""
        # Reload table data
        if hasattr(self._context.table, 'reload_data'):
            self._context.table.reload_data()

        # Update item count
        count = self._get_item_count()
        self._context.control_panel.update_item_count(count)

        self.data_changed.emit()


# =============================================================================
# Factory Functions
# =============================================================================

def create_element_context(
    table: QWidget,
    info_panel: QWidget,
    control_panel: QWidget
) -> DataActionContext:
    """Create a DataActionContext for elements (atoms)"""
    from periodica_app.ui.creation_dialog import AtomCreationDialog

    def element_filename_generator(item: Dict) -> str:
        z = item.get('atomic_number', 0)
        symbol = item.get('symbol', 'X')
        return f"{z:03d}_{symbol}"

    return DataActionContext(
        category=None,  # Will be set by caller with DataCategory.ELEMENTS
        table=table,
        info_panel=info_panel,
        control_panel=control_panel,
        creation_dialog_class=AtomCreationDialog,
        name_key='name',
        filename_generator=element_filename_generator,
        selected_item_attr='selected_element',
        items_attr='base_elements',
        category_display_name='Element',
        remove_confirm_title='Remove Element',
        reset_confirm_title='Reset Elements',
        reset_confirm_message='Are you sure you want to reset all elements to defaults?'
    )


def create_quark_context(
    table: QWidget,
    info_panel: QWidget,
    control_panel: QWidget
) -> DataActionContext:
    """Create a DataActionContext for quarks"""

    def quark_filename_generator(item: Dict) -> str:
        name = item.get('Name', 'Unknown')
        return name.replace(' ', '_')

    return DataActionContext(
        category=None,  # Will be set by caller with DataCategory.QUARKS
        table=table,
        info_panel=info_panel,
        control_panel=control_panel,
        creation_dialog_class=None,  # Quarks are fundamental
        name_key='Name',
        filename_generator=quark_filename_generator,
        selected_item_attr='selected_quark',
        items_attr='base_particles',
        category_display_name='Quark',
        remove_confirm_title='Remove Quark',
        reset_confirm_title='Reset Quarks',
        reset_confirm_message='Are you sure you want to reset all quarks to defaults?'
    )


def create_subatomic_context(
    table: QWidget,
    info_panel: QWidget,
    control_panel: QWidget
) -> DataActionContext:
    """Create a DataActionContext for subatomic particles"""
    from periodica_app.ui.creation_dialog import SubatomicCreationDialog

    def subatomic_filename_generator(item: Dict) -> str:
        name = item.get('Name', 'Unknown')
        return name.replace(' ', '_')

    return DataActionContext(
        category=None,  # Will be set by caller with DataCategory.SUBATOMIC
        table=table,
        info_panel=info_panel,
        control_panel=control_panel,
        creation_dialog_class=SubatomicCreationDialog,
        name_key='Name',
        filename_generator=subatomic_filename_generator,
        selected_item_attr='selected_particle',
        items_attr='particles',
        category_display_name='Particle',
        remove_confirm_title='Remove Particle',
        reset_confirm_title='Reset Subatomic Particles',
        reset_confirm_message='Are you sure you want to reset all subatomic particles to defaults?'
    )


def create_molecule_context(
    table: QWidget,
    info_panel: QWidget,
    control_panel: QWidget
) -> DataActionContext:
    """Create a DataActionContext for molecules"""
    from periodica_app.ui.creation_dialog import MoleculeCreationDialog

    def molecule_filename_generator(item: Dict) -> str:
        name = item.get('Name', 'Unknown')
        return name.replace(' ', '_')

    return DataActionContext(
        category=None,  # Will be set by caller with DataCategory.MOLECULES
        table=table,
        info_panel=info_panel,
        control_panel=control_panel,
        creation_dialog_class=MoleculeCreationDialog,
        name_key='Name',
        filename_generator=molecule_filename_generator,
        selected_item_attr='selected_molecule',
        items_attr='base_molecules',
        category_display_name='Molecule',
        remove_confirm_title='Remove Molecule',
        reset_confirm_title='Reset Molecules',
        reset_confirm_message='Are you sure you want to reset all molecules to defaults?'
    )


def create_alloy_context(
    table: QWidget,
    info_panel: QWidget,
    control_panel: QWidget
) -> DataActionContext:
    """Create a DataActionContext for alloys"""
    from periodica_app.ui.alloy_creation_dialog import AlloyCreationDialog

    def alloy_filename_generator(item: Dict) -> str:
        name = item.get('name', item.get('Name', 'Unknown'))
        return item.get('_filename', name.replace(' ', '_'))

    return DataActionContext(
        category=None,  # Will be set by caller with DataCategory.ALLOYS
        table=table,
        info_panel=info_panel,
        control_panel=control_panel,
        creation_dialog_class=AlloyCreationDialog,
        name_key='name',
        filename_generator=alloy_filename_generator,
        selected_item_attr='selected_alloy',
        items_attr='base_alloys',
        category_display_name='Alloy',
        remove_confirm_title='Remove Alloy',
        reset_confirm_title='Reset Alloys',
        reset_confirm_message=(
            'Are you sure you want to reset all alloys to defaults?\n'
            'This will remove any custom alloys.'
        )
    )
