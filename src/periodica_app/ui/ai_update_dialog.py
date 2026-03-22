"""
AI Update Dialog for refining existing assets using Gemini AI.
Provides an interface for users to describe how they want to modify an existing asset
and shows a side-by-side diff preview before applying changes.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTextEdit, QProgressBar,
    QMessageBox, QFrame, QScrollArea, QWidget, QSplitter,
    QTreeWidget, QTreeWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor, QBrush

# Add scripts directory to path for importing generator
scripts_dir = Path(__file__).parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))


class UpdateWorker(QObject):
    """Worker thread for running Gemini update/refinement."""

    progress = Signal(str, int)  # message, percentage
    finished = Signal(dict)  # result config
    error = Signal(str)  # error message

    def __init__(self, asset_type: str, current_config: Dict[str, Any],
                 update_prompt: str):
        super().__init__()
        self.asset_type = asset_type
        self.current_config = current_config
        self.update_prompt = update_prompt
        self._cancelled = False

    def cancel(self):
        """Cancel the update process."""
        self._cancelled = True

    def run(self):
        """Run the update process using Gemini."""
        try:
            from gemini_asset_generator import GeminiAssetGenerator

            self.progress.emit("Initializing Gemini...", 5)

            if self._cancelled:
                return

            generator = GeminiAssetGenerator(self.asset_type, verbose=False)

            self.progress.emit("Analyzing current configuration...", 15)

            if self._cancelled:
                return

            # Build the update prompt
            update_request = self._build_update_prompt()

            self.progress.emit("Generating refined configuration...", 30)

            if self._cancelled:
                return

            # Call Gemini to refine the configuration
            result = generator._call_gemini(update_request, use_thinking=False)

            if self._cancelled:
                return

            self.progress.emit("Processing response...", 80)

            if "error" in result:
                self.error.emit(f"AI returned error: {result['error']}")
                return

            # Extract the updated configuration
            updated_config = result.get("updated_config", result.get("config", {}))

            if not updated_config:
                # Try to find any config-like structure in the response
                for key in ["refined_config", "new_config", "modified_config", "result"]:
                    if key in result and isinstance(result[key], dict):
                        updated_config = result[key]
                        break

            if not updated_config:
                self.error.emit("AI did not return a valid configuration")
                return

            self.progress.emit("Update complete!", 100)
            self.finished.emit(updated_config)

        except InterruptedError:
            self.error.emit("Update cancelled")
        except ImportError as e:
            self.error.emit(f"Missing dependency: {e}\n\nInstall with: pip install google-generativeai")
        except Exception as e:
            self.error.emit(f"Update failed: {str(e)}")

    def _build_update_prompt(self) -> str:
        """Build the prompt for updating the configuration."""
        from gemini_asset_generator import GeminiAssetGenerator

        schema = GeminiAssetGenerator.ASSET_SCHEMAS.get(self.asset_type, {})
        requirements = schema.get("planning_requirements", "")

        return f"""You are an expert scientific configuration editor for a {self.asset_type} visualization application.

## Current Configuration
{json.dumps(self.current_config, indent=2)}

## User's Update Request
{self.update_prompt}

## Domain Requirements
{requirements}

## Your Task
Modify the current configuration according to the user's request while:
1. Preserving fields that don't need to change
2. Ensuring all required fields remain valid
3. Maintaining scientific accuracy and validity
4. Making only the changes necessary to fulfill the request

Respond with this JSON structure:
{{
    "analysis": {{
        "understood_request": "What you understood the user wants",
        "changes_needed": ["list of specific changes to make"],
        "fields_affected": ["list of field names that will change"]
    }},
    "updated_config": {{
        // The complete updated configuration with changes applied
    }},
    "change_summary": "Brief summary of what was changed and why",
    "scientific_notes": "Any relevant scientific notes about the changes"
}}

Respond with valid JSON only."""


class DiffTreeWidget(QTreeWidget):
    """Custom tree widget for displaying configuration diffs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Field", "Old Value", "New Value"])
        self.setAlternatingRowColors(True)
        self.setRootIsDecorated(True)

        # Configure header
        header = self.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        self.setStyleSheet("""
            QTreeWidget {
                background-color: rgb(30, 30, 50);
                color: white;
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 4px;
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:alternate {
                background-color: rgb(35, 35, 55);
            }
            QHeaderView::section {
                background-color: rgb(45, 45, 65);
                color: white;
                padding: 6px;
                border: none;
                border-right: 1px solid rgba(100, 100, 120, 100);
                font-weight: bold;
            }
        """)

    def populate_diff(self, old_config: Dict[str, Any], new_config: Dict[str, Any]):
        """Populate the tree with diff between old and new configs."""
        self.clear()
        self._add_diff_items(None, "", old_config, new_config)
        self.expandAll()

    def _add_diff_items(self, parent_item: Optional[QTreeWidgetItem],
                        prefix: str, old_value: Any, new_value: Any):
        """Recursively add diff items to the tree."""
        # Colors for highlighting
        added_color = QBrush(QColor(76, 175, 80, 80))  # Green
        removed_color = QBrush(QColor(244, 67, 54, 80))  # Red
        changed_color = QBrush(QColor(255, 193, 7, 80))  # Yellow/amber

        # Handle dict comparison
        if isinstance(old_value, dict) or isinstance(new_value, dict):
            old_dict = old_value if isinstance(old_value, dict) else {}
            new_dict = new_value if isinstance(new_value, dict) else {}

            all_keys = set(old_dict.keys()) | set(new_dict.keys())

            for key in sorted(all_keys):
                old_val = old_dict.get(key)
                new_val = new_dict.get(key)

                field_name = f"{prefix}.{key}" if prefix else key

                if key not in old_dict:
                    # New field added
                    item = self._create_item(parent_item, key, "",
                                            self._format_value(new_val))
                    for col in range(3):
                        item.setBackground(col, added_color)
                    item.setToolTip(0, "Added")

                elif key not in new_dict:
                    # Field removed
                    item = self._create_item(parent_item, key,
                                            self._format_value(old_val), "")
                    for col in range(3):
                        item.setBackground(col, removed_color)
                    item.setToolTip(0, "Removed")

                elif isinstance(old_val, dict) or isinstance(new_val, dict):
                    # Nested dict - create parent item and recurse
                    item = self._create_item(parent_item, key, "{...}", "{...}")
                    self._add_diff_items(item, field_name, old_val, new_val)

                elif isinstance(old_val, list) or isinstance(new_val, list):
                    # List comparison
                    old_list = old_val if isinstance(old_val, list) else []
                    new_list = new_val if isinstance(new_val, list) else []

                    if old_list != new_list:
                        item = self._create_item(parent_item, key,
                                                self._format_value(old_list),
                                                self._format_value(new_list))
                        for col in range(3):
                            item.setBackground(col, changed_color)
                        item.setToolTip(0, "Modified")
                    else:
                        item = self._create_item(parent_item, key,
                                                self._format_value(old_list),
                                                self._format_value(new_list))

                elif old_val != new_val:
                    # Value changed
                    item = self._create_item(parent_item, key,
                                            self._format_value(old_val),
                                            self._format_value(new_val))
                    for col in range(3):
                        item.setBackground(col, changed_color)
                    item.setToolTip(0, "Modified")

                else:
                    # Unchanged
                    item = self._create_item(parent_item, key,
                                            self._format_value(old_val),
                                            self._format_value(new_val))

        else:
            # Primitive value comparison
            if old_value != new_value:
                item = self._create_item(parent_item, prefix or "value",
                                        self._format_value(old_value),
                                        self._format_value(new_value))
                for col in range(3):
                    item.setBackground(col, changed_color)

    def _create_item(self, parent: Optional[QTreeWidgetItem],
                     field: str, old_val: str, new_val: str) -> QTreeWidgetItem:
        """Create a tree widget item."""
        if parent is None:
            item = QTreeWidgetItem(self)
        else:
            item = QTreeWidgetItem(parent)

        item.setText(0, field)
        item.setText(1, old_val)
        item.setText(2, new_val)
        return item

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if value is None:
            return "<none>"
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            if isinstance(value, float):
                return f"{value:.6g}"
            return str(value)
        elif isinstance(value, str):
            if len(value) > 50:
                return f'"{value[:47]}..."'
            return f'"{value}"'
        elif isinstance(value, list):
            if len(value) > 5:
                items = ", ".join(self._format_value(v) for v in value[:5])
                return f"[{items}, ...]"
            return f"[{', '.join(self._format_value(v) for v in value)}]"
        elif isinstance(value, dict):
            return "{...}"
        else:
            return str(value)


class AIUpdateDialog(QDialog):
    """Dialog for AI-powered asset updating/refinement."""

    # Emitted when user accepts the updated configuration
    asset_updated = Signal(dict)

    # Asset type display names
    ASSET_TYPE_NAMES = {
        "alloy": "Alloy",
        "protein": "Protein",
        "nucleic_acid": "Nucleic Acid",
        "molecule": "Molecule",
        "cell": "Cell",
        "biomaterial": "Biomaterial",
        "material": "Material",
        "subatomic": "Subatomic Particle",
        "quark": "Quark/Particle",
        "amino_acid": "Amino Acid",
        "cell_component": "Cell Component",
        "element": "Element"
    }

    def __init__(self, asset_type: str, current_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.asset_type = asset_type
        self.current_config = current_config.copy()
        self.updated_config = None
        self.worker = None
        self.thread = None

        asset_name = self.ASSET_TYPE_NAMES.get(asset_type, asset_type.title())
        self.setWindowTitle(f"AI Update - {asset_name}")
        self.setMinimumSize(900, 700)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        self.setStyleSheet("""
            QDialog {
                background-color: rgb(20, 20, 35);
            }
            QLabel {
                color: white;
            }
            QLineEdit, QTextEdit {
                background-color: rgb(45, 45, 65);
                color: white;
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 4px;
                padding: 8px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #667eea;
            }
            QGroupBox {
                color: white;
                border: 2px solid #667eea;
                border-radius: 8px;
                margin-top: 10px;
                padding: 15px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        asset_name = self.ASSET_TYPE_NAMES.get(self.asset_type, self.asset_type.title())
        title = QLabel(f"Update {asset_name} with AI")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #667eea;")
        layout.addWidget(title)

        # Description
        desc = QLabel("Describe how you want to modify this asset. "
                     "The AI will analyze your request and suggest changes.")
        desc.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 11px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top section: Current config and prompt input
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Current configuration (read-only)
        current_group = QGroupBox("Current Configuration")
        current_group.setStyleSheet("""
            QGroupBox {
                border-color: #607D8B;
            }
        """)
        current_layout = QVBoxLayout()

        self.current_text = QTextEdit()
        self.current_text.setReadOnly(True)
        self.current_text.setStyleSheet("""
            QTextEdit {
                font-family: Consolas, Monaco, monospace;
                font-size: 11px;
                background-color: rgb(35, 35, 55);
            }
        """)
        self.current_text.setPlainText(json.dumps(self.current_config, indent=2))
        self.current_text.setMaximumHeight(200)
        current_layout.addWidget(self.current_text)

        current_group.setLayout(current_layout)
        top_layout.addWidget(current_group)

        # Update prompt input
        prompt_group = QGroupBox("Update Request")
        prompt_layout = QVBoxLayout()

        prompt_label = QLabel("Describe the changes you want:")
        prompt_label.setStyleSheet("font-weight: bold;")
        prompt_layout.addWidget(prompt_label)

        self.prompt_input = QTextEdit()
        self.prompt_input.setPlaceholderText(
            "Examples:\n"
            "- 'Make this more stable'\n"
            "- 'Increase the melting point by 50 degrees'\n"
            "- 'Add more hydrophobic residues'\n"
            "- 'Optimize for higher tensile strength'"
        )
        self.prompt_input.setMaximumHeight(150)
        prompt_layout.addWidget(self.prompt_input)

        prompt_group.setLayout(prompt_layout)
        top_layout.addWidget(prompt_group)

        splitter.addWidget(top_widget)

        # Bottom section: Diff preview
        diff_group = QGroupBox("Changes Preview")
        diff_group.setStyleSheet("""
            QGroupBox {
                border-color: #4CAF50;
            }
        """)
        diff_layout = QVBoxLayout()

        # Legend
        legend_layout = QHBoxLayout()

        added_label = QLabel("Added")
        added_label.setStyleSheet(
            "background-color: rgba(76, 175, 80, 80); "
            "padding: 4px 8px; border-radius: 3px; font-size: 10px;"
        )
        legend_layout.addWidget(added_label)

        removed_label = QLabel("Removed")
        removed_label.setStyleSheet(
            "background-color: rgba(244, 67, 54, 80); "
            "padding: 4px 8px; border-radius: 3px; font-size: 10px;"
        )
        legend_layout.addWidget(removed_label)

        changed_label = QLabel("Changed")
        changed_label.setStyleSheet(
            "background-color: rgba(255, 193, 7, 80); "
            "padding: 4px 8px; border-radius: 3px; font-size: 10px;"
        )
        legend_layout.addWidget(changed_label)

        legend_layout.addStretch()
        diff_layout.addLayout(legend_layout)

        # Diff tree
        self.diff_tree = DiffTreeWidget()
        self.diff_tree.setMinimumHeight(200)
        diff_layout.addWidget(self.diff_tree)

        # Change summary
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(
            "color: rgba(255, 255, 255, 180); font-size: 11px; font-style: italic;"
        )
        self.summary_label.setWordWrap(True)
        diff_layout.addWidget(self.summary_label)

        diff_group.setLayout(diff_layout)
        splitter.addWidget(diff_group)

        splitter.setSizes([300, 400])
        layout.addWidget(splitter)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(100, 100, 120, 150);
                border-radius: 4px;
                background: rgb(45, 45, 65);
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #667eea, stop:1 #764ba2);
                border-radius: 3px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: rgba(255, 255, 255, 180); font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Buttons
        button_row = QHBoxLayout()
        button_row.addStretch()

        self.update_btn = QPushButton("Generate Update")
        self.update_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                           stop:0 #7b8fed, stop:1 #8b5cb5);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.update_btn.clicked.connect(self.start_update)
        button_row.addWidget(self.update_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(100, 100, 120, 150);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(120, 120, 140, 180);
            }
        """)
        self.cancel_btn.clicked.connect(self.on_cancel)
        button_row.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76, 175, 80, 180);
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(76, 175, 80, 220);
            }
            QPushButton:disabled {
                background: rgba(100, 100, 100, 100);
                color: rgba(255, 255, 255, 100);
            }
        """)
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_changes)
        button_row.addWidget(self.apply_btn)

        layout.addLayout(button_row)

    def start_update(self):
        """Start the AI update process."""
        prompt = self.prompt_input.toPlainText().strip()

        if not prompt:
            QMessageBox.warning(
                self, "Missing Input",
                "Please describe how you want to update the asset."
            )
            return

        # Disable UI during update
        self.update_btn.setEnabled(False)
        self.prompt_input.setEnabled(False)
        self.apply_btn.setEnabled(False)

        # Clear previous diff
        self.diff_tree.clear()
        self.summary_label.setText("")

        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting update...")

        # Create worker and thread
        self.thread = QThread()
        self.worker = UpdateWorker(
            self.asset_type, self.current_config, prompt
        )
        self.worker.moveToThread(self.thread)

        # Connect signals
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)

        # Start
        self.thread.start()

    def on_progress(self, message: str, percentage: int):
        """Handle progress update."""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)

    def on_finished(self, updated_config: dict):
        """Handle update completion."""
        self.updated_config = updated_config

        # Populate the diff tree
        self.diff_tree.populate_diff(self.current_config, updated_config)

        # Count changes
        changes = self._count_changes(self.current_config, updated_config)
        self.summary_label.setText(
            f"Changes: {changes['modified']} modified, "
            f"{changes['added']} added, {changes['removed']} removed"
        )

        self.status_label.setText(
            "Update generated! Review the changes and click 'Apply Changes' to accept."
        )
        self.apply_btn.setEnabled(True)
        self.reset_ui_state()

    def on_error(self, error_message: str):
        """Handle update error."""
        self.status_label.setText(f"Error: {error_message}")
        self.reset_ui_state()
        QMessageBox.critical(self, "Update Failed", error_message)

    def reset_ui_state(self):
        """Reset UI to editable state."""
        self.update_btn.setEnabled(True)
        self.prompt_input.setEnabled(True)
        self.progress_bar.setVisible(False)

    def on_cancel(self):
        """Handle cancel button."""
        if self.worker:
            self.worker.cancel()
        if self.thread and self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        self.reject()

    def apply_changes(self):
        """Apply the updated configuration."""
        if self.updated_config:
            self.asset_updated.emit(self.updated_config)
            self.accept()

    def closeEvent(self, event):
        """Handle dialog close."""
        self.on_cancel()
        event.accept()

    def _count_changes(self, old_config: Dict[str, Any],
                       new_config: Dict[str, Any]) -> Dict[str, int]:
        """Count the number of changes between configs."""
        counts = {"modified": 0, "added": 0, "removed": 0}
        self._count_changes_recursive(old_config, new_config, counts)
        return counts

    def _count_changes_recursive(self, old_value: Any, new_value: Any,
                                  counts: Dict[str, int]):
        """Recursively count changes."""
        if isinstance(old_value, dict) and isinstance(new_value, dict):
            all_keys = set(old_value.keys()) | set(new_value.keys())
            for key in all_keys:
                if key not in old_value:
                    counts["added"] += 1
                elif key not in new_value:
                    counts["removed"] += 1
                elif isinstance(old_value[key], dict) and isinstance(new_value[key], dict):
                    self._count_changes_recursive(old_value[key], new_value[key], counts)
                elif old_value[key] != new_value[key]:
                    counts["modified"] += 1
        elif isinstance(old_value, dict):
            counts["removed"] += len(old_value)
        elif isinstance(new_value, dict):
            counts["added"] += len(new_value)
        elif old_value != new_value:
            counts["modified"] += 1
