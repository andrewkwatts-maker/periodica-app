#!/usr/bin/env python3
"""
Quark Info Panel
Displays detailed information about selected particles.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QStackedWidget
from PySide6.QtGui import QFont

from periodica.core.quark_enums import ParticleType
from periodica.data.data_manager import DataCategory
from periodica_app.ui.inline_editor import InlineDataEditor


class QuarkInfoPanel(QWidget):
    """Panel displaying detailed particle information"""

    data_saved = Signal(dict)
    edit_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.particle = None
        self._editor = None
        self.setup_ui()

    def setup_ui(self):
        """Set up the panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create stacked widget for switching between display and edit modes
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # Display widget (index 0)
        display_widget = QWidget()
        display_layout = QVBoxLayout(display_widget)
        display_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Particle Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        display_layout.addWidget(title)

        # Info display
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setStyleSheet("""
            QTextEdit {
                background: rgba(25, 25, 45, 200);
                color: white;
                border: 2px solid #4fc3f7;
                border-radius: 12px;
                padding: 15px;
                font-size: 13px;
            }
        """)
        display_layout.addWidget(self.info_text)

        self.stack.addWidget(display_widget)

        self.show_default()

    def show_default(self):
        """Show default message when no particle is selected"""
        self.info_text.setHtml("""
            <h3 style='color: #4fc3f7;'>Click any particle to view:</h3>
            <ul>
                <li><b>Classification</b> (Quark, Lepton, Boson)</li>
                <li><b>Charge</b> (in units of e)</li>
                <li><b>Mass</b> (MeV/c<sup>2</sup>)</li>
                <li><b>Spin</b> (in units of h-bar)</li>
                <li><b>Interaction Forces</b></li>
                <li><b>Stability & Decay Products</b></li>
                <li><b>Antiparticle</b></li>
            </ul>
            <p style='background: rgba(100,200,255,0.15); padding: 10px; border-radius: 5px;'>
            <b>Standard Model:</b> The Standard Model of particle physics describes
            all known fundamental particles and three of the four fundamental forces.
            </p>
        """)

    def update_quark(self, particle):
        """Update panel with quark/particle data"""
        if not particle:
            self.show_default()
            return

        self.particle = particle

        # Get particle type color
        ptype = particle.get('particle_type', ParticleType.UNKNOWN)
        r, g, b = ParticleType.get_color(ptype)
        type_color = f"rgb({r}, {g}, {b})"

        # Build HTML content
        name = particle.get('Name', 'Unknown')
        symbol = particle.get('Symbol', '?')
        classification = particle.get('Classification', [])
        classification_str = ", ".join(classification) if classification else "Unknown"

        charge_display = particle.get('charge_display', 'N/A')
        mass_display = particle.get('mass_display', 'N/A')
        spin_display = particle.get('spin_display', 'N/A')
        statistics = particle.get('statistics', 'Unknown')

        # Interaction forces
        forces = particle.get('InteractionForces', [])
        forces_html = ""
        force_colors = {
            'Strong': '#ff6464',
            'Electromagnetic': '#6496ff',
            'Weak': '#ffc864',
            'Gravitational': '#96ff96'
        }
        for force in forces:
            color = force_colors.get(force, '#999')
            forces_html += f"<span style='background: {color}; padding: 2px 8px; border-radius: 3px; margin-right: 5px;'>{force}</span>"

        if not forces_html:
            forces_html = "None specified"

        # Stability and decay
        stability = particle.get('Stability', 'Unknown')
        stability_color = '#64ff64' if stability == 'Stable' else '#ff6464' if stability == 'Unstable' else '#ffff64'
        half_life = particle.get('HalfLife_s')
        decay_products = particle.get('DecayProducts', [])

        decay_html = ""
        if half_life:
            if half_life < 1e-20:
                decay_html += f"<b>Half-life:</b> {half_life:.2e} s<br>"
            elif half_life < 1:
                decay_html += f"<b>Half-life:</b> {half_life:.3e} s<br>"
            else:
                decay_html += f"<b>Half-life:</b> {half_life:.2f} s<br>"

        if decay_products:
            decay_html += f"<b>Decay Products:</b> {', '.join(decay_products[:5])}"
            if len(decay_products) > 5:
                decay_html += "..."

        # Antiparticle
        antiparticle = particle.get('Antiparticle', {})
        anti_name = antiparticle.get('Name', 'Unknown')
        anti_symbol = antiparticle.get('Symbol', '?')

        # Quantum numbers
        baryon_num = particle.get('BaryonNumber_B', 0)
        lepton_num = particle.get('LeptonNumber_L', 0)
        isospin = particle.get('Isospin_I', 0)
        isospin_z = particle.get('Isospin_I3', 0)
        parity = particle.get('Parity_P')

        quantum_html = f"""
            <tr><td><b>Baryon Number:</b></td><td>{baryon_num}</td></tr>
            <tr><td><b>Lepton Number:</b></td><td>{lepton_num}</td></tr>
            <tr><td><b>Isospin (I):</b></td><td>{isospin}</td></tr>
            <tr><td><b>Isospin (I<sub>3</sub>):</b></td><td>{isospin_z}</td></tr>
        """
        if parity is not None:
            quantum_html += f"<tr><td><b>Parity:</b></td><td>{'+' if parity > 0 else '-'}</td></tr>"

        # Generation
        generation = particle.get('generation_num', -1)
        gen_names = {1: 'First', 2: 'Second', 3: 'Third', 0: 'Force Carrier', -1: 'N/A'}
        gen_str = gen_names.get(generation, 'Unknown')

        # Build final HTML
        html = f"""
            <h2 style='color: {type_color}; margin-bottom: 5px;'>{symbol}</h2>
            <h3 style='color: white; margin-top: 0;'>{name}</h3>
            <div style='color: #aaa; font-size: 11px; margin-bottom: 10px;'>
                {classification_str}
            </div>
            <hr style='border-color: #4fc3f7; margin: 10px 0;'>

            <h3 style='color: #4fc3f7;'>Basic Properties</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Charge:</b></td>
                    <td><span style='color: #00ff88; font-weight: bold;'>{charge_display} e</span></td>
                </tr>
                <tr>
                    <td><b>Mass:</b></td>
                    <td><span style='color: #00ff88;'>{mass_display}</span></td>
                </tr>
                <tr>
                    <td><b>Spin:</b></td>
                    <td>{spin_display} h-bar ({statistics})</td>
                </tr>
                <tr>
                    <td><b>Generation:</b></td>
                    <td>{gen_str}</td>
                </tr>
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Interaction Forces</h3>
            <div style='margin: 10px 0;'>
                {forces_html}
            </div>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Stability</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Status:</b></td>
                    <td><span style='color: {stability_color}; font-weight: bold;'>{stability}</span></td>
                </tr>
            </table>
            {decay_html}

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Quantum Numbers</h3>
            <table style='width: 100%; color: white; line-height: 1.6; font-size: 12px;'>
                {quantum_html}
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>Antiparticle</h3>
            <div style='background: rgba(100,100,150,0.2); padding: 10px; border-radius: 5px;'>
                <b>{anti_name}</b> ({anti_symbol})
            </div>
        """

        # Add composition if it's a composite particle
        composition = particle.get('Composition', [])
        if composition:
            html += f"""
            <h3 style='color: #4fc3f7; margin-top: 15px;'>Composition</h3>
            <div style='color: white;'>
                {', '.join(composition)}
            </div>
            """

        # Add context note
        html += """
            <div style='background: rgba(100,200,255,0.15); padding: 12px; border-radius: 8px;
            border-left: 4px solid #4fc3f7; margin-top: 15px;'>
                <p style='margin: 0;'><b>Note:</b> Properties shown are theoretical values
                from the Standard Model. Some particles like quarks are never observed in isolation
                due to color confinement.</p>
            </div>
        """

        self.info_text.setHtml(html)

    def start_add(self, template_data=None):
        """Start add mode with the inline editor"""
        self._editor = InlineDataEditor(DataCategory.QUARKS, template_data)
        self._editor.saved.connect(self._on_editor_saved)
        self._editor.cancelled.connect(self._on_editor_cancelled)
        self.stack.addWidget(self._editor)
        self.stack.setCurrentWidget(self._editor)

    def start_edit(self, data):
        """Start edit mode with the inline editor"""
        self._editor = InlineDataEditor(DataCategory.QUARKS, data, edit_mode=True)
        self._editor.saved.connect(self._on_editor_saved)
        self._editor.cancelled.connect(self._on_editor_cancelled)
        self.stack.addWidget(self._editor)
        self.stack.setCurrentWidget(self._editor)

    def _on_editor_saved(self, data):
        """Handle editor save - switch back to display and emit signal"""
        self.stack.setCurrentIndex(0)
        if self._editor:
            self.stack.removeWidget(self._editor)
            self._editor.deleteLater()
            self._editor = None
        self.data_saved.emit(data)

    def _on_editor_cancelled(self):
        """Handle editor cancel - switch back to display and emit signal"""
        self.stack.setCurrentIndex(0)
        if self._editor:
            self.stack.removeWidget(self._editor)
            self._editor.deleteLater()
            self._editor = None
        self.edit_cancelled.emit()
