"""
Protein Table Widget
Displays proteins in a grid/table layout with visual property encoding.
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                                QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import (QFont, QPainter, QColor, QBrush, QPen,
                            QRadialGradient, QLinearGradient)

from periodica_app.ui.theme_constants import ThemeColors
from periodica.core.protein_enums import (ProteinFunction, CellularLocalization,
                                 SecondaryStructureType)


class ProteinCard(QFrame):
    """Individual protein card widget."""

    clicked = Signal(dict)

    def __init__(self, protein, parent=None):
        super().__init__(parent)
        self.protein = protein
        self._selected = False
        self._base_size = 130
        self._current_size = 130
        self._color_property = "function"

        self.setMinimumSize(QSize(80, 80))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def set_selected(self, selected):
        """Set selection state."""
        self._selected = selected
        self.update_style()

    def set_size(self, size):
        """Set card size."""
        self._current_size = size
        self.setFixedSize(QSize(int(size), int(size)))
        self.update()

    def set_color_property(self, prop):
        """Set which property determines card color."""
        self._color_property = prop
        self.update_style()

    def update_style(self):
        """Update card styling based on properties."""
        color = self._get_property_color()
        border_color = ThemeColors.ACCENT if self._selected else color
        border_width = 3 if self._selected else 2

        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(30, 30, 50, 220),
                    stop:1 rgba(40, 40, 70, 220));
                border: {border_width}px solid {border_color};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {ThemeColors.ACCENT};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(40, 40, 70, 220),
                    stop:1 rgba(50, 50, 90, 220));
            }}
        """)
        self.update()

    def _get_property_color(self):
        """Get color based on current color property."""
        if self._color_property == "function":
            func = self.protein.get('function', 'structural')
            return ProteinFunction.get_color(func)
        elif self._color_property == "localization":
            loc = self.protein.get('localization', 'cytoplasm')
            return CellularLocalization.get_color(loc)
        elif self._color_property == "secondary_structure":
            ss = self.protein.get('secondary_structure', {})
            helix = ss.get('helix_percent', 0)
            sheet = ss.get('sheet_percent', 0)
            if helix > sheet and helix > 30:
                return "#FF4081"  # Pink for helix-rich
            elif sheet > helix and sheet > 30:
                return "#448AFF"  # Blue for sheet-rich
            return "#9E9E9E"  # Grey for mixed
        elif self._color_property == "hydropathy":
            gravy = self.protein.get('gravy', 0)
            if gravy > 0:
                return "#FF9800"  # Orange for hydrophobic
            return "#2196F3"  # Blue for hydrophilic
        elif self._color_property == "charge":
            charge = self.protein.get('charge_pH7', 0)
            if charge > 1:
                return "#2196F3"  # Blue for positive
            elif charge < -1:
                return "#F44336"  # Red for negative
            return "#9E9E9E"  # Grey for neutral
        elif self._color_property == "mass":
            mass = self.protein.get('molecular_mass', 0)
            # Color scale from small (light) to large (dark)
            intensity = min(255, int(mass / 100))
            return f"#{intensity:02x}{200-intensity//2:02x}{100+intensity//2:02x}"
        else:
            return ThemeColors.ACCENT

    def paintEvent(self, event):
        """Custom paint for protein card."""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2

        # Draw protein name (abbreviated)
        name = self.protein.get('name', '?')
        # Abbreviate long names
        if len(name) > 12:
            words = name.split()
            if len(words) > 1:
                name = ''.join(w[0] for w in words[:4])
            else:
                name = name[:10] + ".."

        color = QColor(self._get_property_color())
        painter.setPen(QPen(color, 2))
        font_size = max(8, int(self._current_size * 0.12))
        painter.setFont(QFont("Arial", font_size, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, name)

        # Draw secondary structure indicator at bottom
        ss = self.protein.get('secondary_structure', {})
        helix = ss.get('helix_percent', 0)
        sheet = ss.get('sheet_percent', 0)

        bar_height = 4
        bar_y = h - 10

        # Helix bar (pink)
        if helix > 0:
            helix_width = int((w - 20) * helix / 100)
            painter.fillRect(10, bar_y, helix_width, bar_height, QColor("#FF4081"))

        # Sheet bar (blue)
        if sheet > 0:
            sheet_width = int((w - 20) * sheet / 100)
            painter.fillRect(10, bar_y + bar_height + 2, sheet_width, bar_height,
                           QColor("#448AFF"))

        # Draw mass at top right
        mass = self.protein.get('molecular_mass', 0)
        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.setFont(QFont("Arial", max(7, int(self._current_size * 0.08))))
        mass_str = f"{mass/1000:.1f}k" if mass > 1000 else f"{mass:.0f}"
        painter.drawText(w - 35, 15, mass_str)

        # Draw length at top left
        length = self.protein.get('length', 0)
        painter.drawText(5, 15, f"{length}aa")

        painter.end()

    def mousePressEvent(self, event):
        """Handle click events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.protein)


class ProteinTableWidget(QWidget):
    """Widget displaying proteins in a configurable grid layout."""

    protein_selected = Signal(dict)
    protein_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proteins = []
        self._cards = []
        self._selected_card = None
        self._layout_mode = "grid"
        self._color_property = "function"
        self._size_property = "none"
        self._function_filters = []
        self._search_filter = ""

        self.setup_ui()
        self.load_proteins()

    def setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for the grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollBar:vertical {{
                background: rgba(40, 40, 60, 100);
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(102, 187, 106, 150);
                border-radius: 5px;
            }}
        """)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

    def load_proteins(self):
        """Load protein data from JSON files."""
        protein_dir = Path(__file__).parent.parent / "data" / "active" / "proteins"
        self._proteins = []

        if protein_dir.exists():
            for json_file in sorted(protein_dir.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._proteins.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        self._rebuild_grid()

    def _rebuild_grid(self):
        """Rebuild the grid with current layout mode."""
        # Clear existing cards
        for card in self._cards:
            card.deleteLater()
        self._cards = []

        # Filter proteins
        filtered = self._get_filtered_proteins()

        # Sort based on layout mode
        sorted_proteins = self._sort_proteins(filtered)

        # Calculate grid dimensions
        cols = self._get_column_count()

        # Create cards
        for i, protein in enumerate(sorted_proteins):
            card = ProteinCard(protein)
            card.set_color_property(self._color_property)

            # Set size based on size property
            size = self._calculate_card_size(protein)
            card.set_size(size)

            card.clicked.connect(self._on_card_clicked)

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def _get_filtered_proteins(self):
        """Apply filters to proteins."""
        filtered = self._proteins

        # Apply search filter
        if self._search_filter:
            filtered = [
                protein for protein in filtered
                if self._search_filter in protein.get('name', '').lower()
                or self._search_filter in protein.get('abbreviation', '').lower()
            ]

        # Apply function filter
        if self._function_filters:
            filtered = [
                protein for protein in filtered
                if any(f in protein.get('function', 'structural').lower()
                       for f in self._function_filters)
            ]

        return filtered if filtered else self._proteins

    def _sort_proteins(self, proteins):
        """Sort proteins based on layout mode."""
        if self._layout_mode == "grid":
            return sorted(proteins, key=lambda x: x.get('name', 'Z'))
        elif self._layout_mode == "mass":
            return sorted(proteins, key=lambda x: x.get('molecular_mass', 0))
        elif self._layout_mode == "function":
            return sorted(proteins, key=lambda x: x.get('function', ''))
        elif self._layout_mode == "structure":
            return sorted(proteins,
                         key=lambda x: x.get('secondary_structure', {}).get('helix_percent', 0),
                         reverse=True)
        elif self._layout_mode == "localization":
            return sorted(proteins, key=lambda x: x.get('localization', ''))
        elif self._layout_mode == "organism":
            return sorted(proteins, key=lambda x: x.get('organism', ''))
        else:
            return proteins

    def _get_column_count(self):
        """Get number of columns based on layout mode."""
        return 4  # Default columns

    def _calculate_card_size(self, protein):
        """Calculate card size based on size property."""
        base = 130

        if self._size_property == "none":
            return base
        elif self._size_property == "molecular_mass":
            mass = protein.get('molecular_mass', 10000)
            # Scale from small proteins (~5k) to large (~50k) -> 100-180px
            return int(100 + (mass / 50000) * 80)
        elif self._size_property == "length":
            length = protein.get('length', 100)
            return int(100 + (length / 500) * 80)
        elif self._size_property == "helix_content":
            ss = protein.get('secondary_structure', {})
            helix = ss.get('helix_percent', 0)
            return int(100 + helix * 0.8)
        elif self._size_property == "sheet_content":
            ss = protein.get('secondary_structure', {})
            sheet = ss.get('sheet_percent', 0)
            return int(100 + sheet * 0.8)
        else:
            return base

    def _on_card_clicked(self, protein):
        """Handle card click."""
        # Deselect previous
        if self._selected_card:
            self._selected_card.set_selected(False)

        # Find and select new card
        for card in self._cards:
            if card.protein == protein:
                card.set_selected(True)
                self._selected_card = card
                break

        self.protein_selected.emit(protein)

    # === Public API ===

    def set_layout_mode(self, mode):
        """Set layout mode."""
        self._layout_mode = mode
        self._rebuild_grid()

    def set_color_property(self, prop):
        """Set color property."""
        self._color_property = prop
        for card in self._cards:
            card.set_color_property(prop)

    def set_size_property(self, prop):
        """Set size property."""
        self._size_property = prop
        self._rebuild_grid()

    def set_function_filters(self, functions):
        """Set function filters."""
        self._function_filters = functions
        self._rebuild_grid()

    def get_selected_protein(self):
        """Get currently selected protein."""
        if self._selected_card:
            return self._selected_card.protein
        return None

    def get_protein_count(self):
        """Get total protein count."""
        return len(self._proteins)

    def set_search_filter(self, text: str):
        """Set search filter by name."""
        self._search_filter = text.lower().strip()
        self._rebuild_grid()

    def get_filtered_count(self):
        """Get count of currently filtered proteins."""
        return len(self._get_filtered_proteins())

    def add_protein(self, protein_data):
        """Add a new protein to the table."""
        self._proteins.append(protein_data)
        self._rebuild_grid()

    def refresh(self):
        """Refresh data from files."""
        self.load_proteins()
