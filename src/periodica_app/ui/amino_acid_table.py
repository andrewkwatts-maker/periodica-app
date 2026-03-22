"""
Amino Acid Table Widget
Displays amino acids in a grid/table layout with visual property encoding.
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QLabel,
                                QScrollArea, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QSize, QPointF
from PySide6.QtGui import (QFont, QPainter, QColor, QBrush, QPen,
                            QRadialGradient, QLinearGradient)

from periodica.core.amino_acid_enums import (AminoAcidCategory, AminoAcidPolarity,
                                    ChargeState, AminoAcidLayoutMode)


class AminoAcidCard(QFrame):
    """Individual amino acid card widget"""

    clicked = Signal(dict)

    def __init__(self, amino_acid, parent=None):
        super().__init__(parent)
        self.amino_acid = amino_acid
        self._selected = False
        self._base_size = 130
        self._current_size = 130
        self._color_property = "category"
        self._pH = 7.0

        self.setMinimumSize(QSize(80, 80))
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_style()

    def set_selected(self, selected):
        """Set selection state"""
        self._selected = selected
        self.update_style()

    def set_size(self, size):
        """Set card size"""
        self._current_size = size
        self.setFixedSize(QSize(int(size), int(size)))
        self.update()

    def set_color_property(self, prop):
        """Set which property determines card color"""
        self._color_property = prop
        self.update_style()

    def set_pH(self, pH):
        """Set pH for charge calculation"""
        self._pH = pH
        self.update_style()

    def update_style(self):
        """Update card styling based on properties"""
        color = self._get_property_color()
        border_color = "#66bb6a" if self._selected else color
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
                border-color: #66bb6a;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(40, 40, 70, 220),
                    stop:1 rgba(50, 50, 90, 220));
            }}
        """)
        self.update()

    def _get_property_color(self):
        """Get color based on current color property"""
        if self._color_property == "category":
            cat = self.amino_acid.get('category', 'special')
            return AminoAcidCategory.get_color(cat)
        elif self._color_property == "polarity":
            pol = self.amino_acid.get('polarity', 'nonpolar')
            return AminoAcidPolarity.get_color(pol)
        elif self._color_property == "charge_at_ph":
            charge = self._calculate_charge()
            state = ChargeState.from_charge(charge)
            return ChargeState.get_color(state)
        elif self._color_property == "hydropathy_index":
            hydropathy = self.amino_acid.get('hydropathy_index', 0)
            if hydropathy > 0:
                # Hydrophobic - warm colors
                intensity = min(255, int(hydropathy * 56))
                return f"#{intensity:02x}{255-intensity:02x}00"
            else:
                # Hydrophilic - cool colors
                intensity = min(255, int(-hydropathy * 56))
                return f"#00{255-intensity:02x}{intensity:02x}"
        elif self._color_property == "helix_propensity":
            prop = self.amino_acid.get('helix_propensity', 1.0)
            if prop > 1.0:
                return "#FF4081"  # Pink for helix formers
            return "#9E9E9E"  # Grey for helix breakers
        elif self._color_property == "sheet_propensity":
            prop = self.amino_acid.get('sheet_propensity', 1.0)
            if prop > 1.0:
                return "#448AFF"  # Blue for sheet formers
            return "#9E9E9E"
        else:
            return "#66bb6a"  # Default green

    def _calculate_charge(self):
        """Calculate charge at current pH"""
        from periodica.utils.predictors.biological.amino_acid_predictor import AminoAcidPredictor
        predictor = AminoAcidPredictor()
        symbol = self.amino_acid.get('symbol', 'G')
        pKa_carboxyl = self.amino_acid.get('pKa_carboxyl', 2.0)
        pKa_amino = self.amino_acid.get('pKa_amino', 9.5)
        pKa_sidechain = self.amino_acid.get('pKa_sidechain')
        is_acidic = symbol.upper() in {'D', 'E', 'C', 'Y'}
        return predictor.calculate_charge_at_pH(
            self._pH, pKa_carboxyl, pKa_amino, pKa_sidechain, is_acidic
        )

    def paintEvent(self, event):
        """Custom paint for amino acid card"""
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2

        # Draw symbol
        symbol = self.amino_acid.get('symbol', '?')
        color = QColor(self._get_property_color())

        painter.setPen(QPen(color, 2))
        painter.setFont(QFont("Arial", int(self._current_size * 0.35), QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, symbol)

        # Draw small mass indicator at bottom
        mass = self.amino_acid.get('molecular_mass', 0)
        painter.setPen(QPen(QColor(180, 180, 180)))
        painter.setFont(QFont("Arial", int(self._current_size * 0.1)))
        painter.drawText(5, h - 5, f"{mass:.0f}")

        # Draw charge indicator if relevant
        if self._color_property == "charge_at_ph":
            charge = self._calculate_charge()
            charge_symbol = "+" if charge > 0.1 else ("-" if charge < -0.1 else "0")
            painter.setPen(QPen(QColor(255, 255, 255, 180)))
            painter.setFont(QFont("Arial", int(self._current_size * 0.15), QFont.Weight.Bold))
            painter.drawText(w - 15, 15, charge_symbol)

        painter.end()

    def mousePressEvent(self, event):
        """Handle click events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.amino_acid)


class AminoAcidTableWidget(QWidget):
    """Widget displaying amino acids in a configurable grid layout"""

    amino_acid_selected = Signal(dict)
    amino_acid_hovered = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._amino_acids = []
        self._cards = []
        self._selected_card = None
        self._layout_mode = "grid"
        self._color_property = "category"
        self._size_property = "none"
        self._category_filters = []
        self._search_filter = ""
        self._pH = 7.0

        self.setup_ui()
        self.load_amino_acids()

    def setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Scroll area for the grid
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical {
                background: rgba(40, 40, 60, 100);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(102, 187, 106, 150);
                border-radius: 5px;
            }
        """)

        self.grid_container = QWidget()
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)

    def load_amino_acids(self):
        """Load amino acid data from JSON files"""
        aa_dir = Path(__file__).parent.parent / "data" / "active" / "amino_acids"
        self._amino_acids = []

        if aa_dir.exists():
            for json_file in sorted(aa_dir.glob("*.json")):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._amino_acids.append(data)
                except Exception as e:
                    print(f"Error loading {json_file}: {e}")

        self._rebuild_grid()

    def _rebuild_grid(self):
        """Rebuild the grid with current layout mode"""
        # Clear existing cards
        for card in self._cards:
            card.deleteLater()
        self._cards = []

        # Filter amino acids
        filtered = self._get_filtered_amino_acids()

        # Sort based on layout mode
        sorted_aas = self._sort_amino_acids(filtered)

        # Calculate grid dimensions
        cols = self._get_column_count()

        # Create cards
        for i, aa in enumerate(sorted_aas):
            card = AminoAcidCard(aa)
            card.set_color_property(self._color_property)
            card.set_pH(self._pH)

            # Set size based on size property
            size = self._calculate_card_size(aa)
            card.set_size(size)

            card.clicked.connect(self._on_card_clicked)

            row = i // cols
            col = i % cols
            self.grid_layout.addWidget(card, row, col)
            self._cards.append(card)

    def _get_filtered_amino_acids(self):
        """Apply filters to amino acids"""
        filtered = self._amino_acids

        # Apply search filter
        if self._search_filter:
            filtered = [
                aa for aa in filtered
                if self._search_filter in aa.get('name', '').lower()
                or self._search_filter in aa.get('symbol', '').lower()
                or self._search_filter in aa.get('three_letter', '').lower()
            ]

        # Apply category filter
        if self._category_filters:
            filtered = [
                aa for aa in filtered
                if aa.get('category', 'special') in self._category_filters
            ]

        return filtered if filtered else self._amino_acids

    def _sort_amino_acids(self, aas):
        """Sort amino acids based on layout mode"""
        if self._layout_mode == "grid":
            # Alphabetical by symbol
            return sorted(aas, key=lambda x: x.get('symbol', 'Z'))
        elif self._layout_mode == "hydropathy":
            return sorted(aas, key=lambda x: x.get('hydropathy_index', 0), reverse=True)
        elif self._layout_mode == "charge":
            return sorted(aas, key=lambda x: x.get('charge_pH7', 0), reverse=True)
        elif self._layout_mode == "mass":
            return sorted(aas, key=lambda x: x.get('molecular_mass', 0))
        elif self._layout_mode == "pi_order":
            return sorted(aas, key=lambda x: x.get('isoelectric_point', 7.0))
        elif self._layout_mode == "polarity":
            # Group by polarity
            order = {'basic': 0, 'acidic': 1, 'polar': 2, 'nonpolar': 3}
            return sorted(aas, key=lambda x: order.get(x.get('polarity', 'nonpolar'), 4))
        elif self._layout_mode == "category":
            # Group by category
            order = {
                'polar_positive': 0, 'polar_negative': 1, 'polar_uncharged': 2,
                'nonpolar_aliphatic': 3, 'nonpolar_aromatic': 4, 'special': 5
            }
            return sorted(aas, key=lambda x: order.get(x.get('category', 'special'), 6))
        elif self._layout_mode == "structure":
            # Sort by helix propensity
            return sorted(aas, key=lambda x: x.get('helix_propensity', 1.0), reverse=True)
        else:
            return aas

    def _get_column_count(self):
        """Get number of columns based on layout mode"""
        if self._layout_mode in ["polarity", "category"]:
            return 5  # Grouped layouts
        return 5  # Default

    def _calculate_card_size(self, aa):
        """Calculate card size based on size property"""
        base = 130

        if self._size_property == "none":
            return base
        elif self._size_property == "molecular_mass":
            mass = aa.get('molecular_mass', 100)
            # Scale from 75 (Gly) to 204 (Trp) -> 100-160px
            return int(100 + (mass - 75) / (204 - 75) * 60)
        elif self._size_property == "hydropathy_index":
            hydro = aa.get('hydropathy_index', 0)
            # Scale from -4.5 to 4.5 -> 110-160px
            return int(110 + abs(hydro) * 10)
        elif self._size_property == "helix_propensity":
            prop = aa.get('helix_propensity', 1.0)
            return int(100 + prop * 35)
        elif self._size_property == "sheet_propensity":
            prop = aa.get('sheet_propensity', 1.0)
            return int(100 + prop * 35)
        else:
            return base

    def _on_card_clicked(self, aa):
        """Handle card click"""
        # Deselect previous
        if self._selected_card:
            self._selected_card.set_selected(False)

        # Find and select new card
        for card in self._cards:
            if card.amino_acid == aa:
                card.set_selected(True)
                self._selected_card = card
                break

        self.amino_acid_selected.emit(aa)

    # === Public API ===

    def set_layout_mode(self, mode):
        """Set layout mode"""
        self._layout_mode = mode
        self._rebuild_grid()

    def set_color_property(self, prop):
        """Set color property"""
        self._color_property = prop
        for card in self._cards:
            card.set_color_property(prop)

    def set_size_property(self, prop):
        """Set size property"""
        self._size_property = prop
        self._rebuild_grid()

    def set_category_filters(self, categories):
        """Set category filters"""
        self._category_filters = categories
        self._rebuild_grid()

    def set_pH(self, pH):
        """Set pH for charge calculations"""
        self._pH = pH
        for card in self._cards:
            card.set_pH(pH)

    def get_selected_amino_acid(self):
        """Get currently selected amino acid"""
        if self._selected_card:
            return self._selected_card.amino_acid
        return None

    def get_amino_acid_count(self):
        """Get total amino acid count"""
        return len(self._amino_acids)

    def set_search_filter(self, text: str):
        """Set search filter by name."""
        self._search_filter = text.lower().strip()
        self._rebuild_grid()

    def get_filtered_count(self):
        """Get count of currently filtered amino acids."""
        return len(self._get_filtered_amino_acids())

    def refresh(self):
        """Refresh data from files"""
        self.load_amino_acids()
