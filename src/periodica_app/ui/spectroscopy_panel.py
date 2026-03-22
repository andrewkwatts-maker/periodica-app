#!/usr/bin/env python3
"""
Spectroscopy Panel - Element Information Display
Shows detailed atomic properties and spectroscopic data for selected elements
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit
from PySide6.QtGui import QFont
from periodica_app.utils.calculations import wavelength_to_rgb


class SpectroscopyPanel(QWidget):
    """Panel displaying detailed element information and spectroscopic data"""

    def __init__(self):
        super().__init__()
        self.element = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("⚛️ Element Analysis")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        layout.addWidget(title)

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
        layout.addWidget(self.info_text)
        self.show_default()

    def show_default(self):
        """Show default message when no element is selected"""
        self.info_text.setHtml("""
            <h3 style='color: #4fc3f7;'>Click any element to view:</h3>
            <ul>
                <li><b>Ionization Energy</b> (eV)</li>
                <li><b>Electronegativity</b> (Pauling scale)</li>
                <li><b>Atomic Radius</b> (picometers)</li>
                <li><b>Melting Point</b> (Kelvin)</li>
                <li><b>Emission Spectrum</b> (frequency & wavelength)</li>
                <li><b>Orbital Block</b> (s, p, d, f)</li>
                <li><b>Stable Isotopes</b> (mass & abundance)</li>
            </ul>
            <p style='background: rgba(255,200,0,0.2); padding: 10px; border-radius: 5px;'>
            <b>⚠️ Scientific Note:</b> All frequencies shown are <b>electromagnetic</b>
            (ionization threshold), measured in PetaHertz (10<sup>15</sup> Hz),
            not audible sound frequencies.
            </p>
        """)

    def update_element(self, elem):
        """Update panel with element data"""
        if not elem:
            self.show_default()
            return

        w = elem['wavelength_nm']
        f = elem['freq_phz']
        color = wavelength_to_rgb(w)
        block_color = elem['block_color']

        isotope_html = ""
        if elem['isotopes']:
            isotope_html = "<h3 style='color: #4fc3f7; margin-top: 15px;'>☢️ Stable Isotopes:</h3><table style='width: 100%; color: white; line-height: 1.6;'>"
            for isotope in elem['isotopes']:
                # Handle both tuple (mass, abundance) and dict {'mass': ..., 'abundance': ...} formats
                if isinstance(isotope, dict):
                    mass = isotope['mass']
                    abundance = isotope['abundance']
                else:
                    mass, abundance = isotope
                neutrons = mass - elem['z']
                isotope_html += f"<tr><td><b>{elem['symbol']}-{mass}</b></td><td>{neutrons}n</td><td><b style='color: #00ff88;'>{abundance:.2f}%</b></td></tr>"
            isotope_html += "</table>"

        html = f"""
            <h2 style='color: {color.name()};'>{elem['symbol']}</h2>
            <div style='color: #aaa; font-size: 11px; margin-top: -5px;'>
                Atomic Number: {elem['z']} • Period: {elem['period']}
            </div>
            <hr style='border-color: #4fc3f7;'>

            <h3 style='color: #4fc3f7;'>⚛️ Atomic Properties:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Orbital Block:</b></td>
                    <td><span style='background: {block_color.name()}; padding: 3px 10px;
                    border-radius: 5px;'>{elem['block']}-block</span></td>
                </tr>
                <tr>
                    <td><b>Electronegativity (χ):</b></td>
                    <td><b style='color: #00ff88;'>{elem['electronegativity']:.2f}</b> (Pauling)</td>
                </tr>
                <tr>
                    <td><b>Atomic Radius:</b></td>
                    <td><b style='color: #00ff88;'>{elem['atomic_radius']}</b> pm</td>
                </tr>
                <tr>
                    <td><b>Melting Point:</b></td>
                    <td><b style='color: #00ff88;'>{elem['melting_point']:.0f}</b> K
                    ({elem['melting_point'] - 273:.0f} °C)</td>
                </tr>
            </table>

            <h3 style='color: #4fc3f7; margin-top: 15px;'>🔬 Spectroscopic Data:</h3>
            <table style='width: 100%; color: white; line-height: 1.8;'>
                <tr>
                    <td><b>Ionization Energy:</b></td>
                    <td><b style='color: #ff8800;'>{elem['ie']:.5f} eV</b></td>
                </tr>
                <tr>
                    <td><b>Frequency (ν):</b></td>
                    <td><b style='color: #ff8800;'>{f:.3f} PHz</b> (10<sup>15</sup> Hz)</td>
                </tr>
                <tr>
                    <td><b>Wavelength (λ):</b></td>
                    <td><b style='color: #ff8800;'>{w:.2f} nm</b></td>
                </tr>
                <tr>
                    <td><b>Spectrum Range:</b></td>
                    <td>{"<b>Visible</b>" if 380 <= w <= 780 else "UV/IR (non-visible)"}</td>
                </tr>
                <tr>
                    <td><b>Emission Color:</b></td>
                    <td><span style='background: {color.name()}; padding: 8px 20px;
                    border: 1px solid white;'>&nbsp;</span></td>
                </tr>
            </table>

            {isotope_html}

            <div style='background: rgba(100,200,255,0.15); padding: 12px; border-radius: 8px;
            border-left: 4px solid #4fc3f7; margin-top: 15px;'>
                <p style='margin: 0;'><b>🌌 Quantum Context:</b> The ionization energy represents
                the photon energy needed to remove one electron. This corresponds to
                <b>ultraviolet electromagnetic radiation</b>, not sound waves.</p>
            </div>
        """
        self.info_text.setHtml(html)
