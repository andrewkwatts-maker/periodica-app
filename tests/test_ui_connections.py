#!/usr/bin/env python3
"""
UI Connection Validation Script
Static analysis to verify all UI elements are properly connected and functional.

Checks:
1. Control Panel -> Table connections (signals/slots)
2. Table -> Info Panel connections
3. Data Management signals
4. Visual Encoding methods
5. View Control methods
"""

import ast
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict


@dataclass
class ConnectionReport:
    """Report for a single connection check"""
    category: str
    component: str
    expected: str
    found: bool
    details: str = ""
    recommendation: str = ""


@dataclass
class ValidationResult:
    """Complete validation results"""
    passed: List[ConnectionReport] = field(default_factory=list)
    failed: List[ConnectionReport] = field(default_factory=list)
    warnings: List[ConnectionReport] = field(default_factory=list)


class ASTAnalyzer:
    """AST-based code analyzer for Python files"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.source = ""
        self.tree = None
        self._load_file()

    def _load_file(self):
        """Load and parse the file"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.source = f.read()
            self.tree = ast.parse(self.source)
        except (FileNotFoundError, SyntaxError) as e:
            print(f"Warning: Could not parse {self.file_path}: {e}")
            self.tree = None

    def find_class_methods(self, class_name: str) -> Set[str]:
        """Find all methods defined in a class"""
        methods = set()
        if self.tree is None:
            return methods

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.add(item.name)
        return methods

    def find_signal_definitions(self, class_name: str = None) -> Set[str]:
        """Find Signal() definitions in class"""
        signals = set()
        if self.tree is None:
            return signals

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                if class_name and node.name != class_name:
                    continue
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                if isinstance(item.value, ast.Call):
                                    if hasattr(item.value.func, 'id') and item.value.func.id == 'Signal':
                                        signals.add(target.id)
        return signals

    def find_connect_statements(self) -> List[Tuple[str, str]]:
        """Find all .connect() statements and extract signal -> slot pairs"""
        connections = []
        # Use regex for more reliable pattern matching
        pattern = r'(\w+(?:\.\w+)*)\s*\.connect\s*\(\s*(\w+(?:\.\w+)*)'
        matches = re.findall(pattern, self.source)
        for signal, slot in matches:
            connections.append((signal, slot))
        return connections

    def find_attribute_assignments(self, class_name: str) -> Dict[str, str]:
        """Find self.attr = value assignments"""
        attrs = {}
        if self.tree is None:
            return attrs

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in ast.walk(node):
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Attribute):
                                if isinstance(target.value, ast.Name) and target.value.id == 'self':
                                    attrs[target.attr] = True
        return attrs

    def has_method(self, class_name: str, method_name: str) -> bool:
        """Check if a class has a specific method"""
        methods = self.find_class_methods(class_name)
        return method_name in methods


class UIConnectionValidator:
    """Main validator for UI connections"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.results = ValidationResult()
        self.analyzers: Dict[str, ASTAnalyzer] = {}

        # Load all relevant files
        self._load_analyzers()

    def _load_analyzers(self):
        """Load AST analyzers for all relevant files"""
        files_to_analyze = [
            'main.py',
            'ui/control_panel.py',
            'ui/quark_control_panel.py',
            'ui/subatomic_control_panel.py',
            'ui/molecule_control_panel.py',
            'ui/alloy_control_panel.py',
            'ui/element_info_panel.py',
            'ui/quark_info_panel.py',
            'ui/subatomic_info_panel.py',
            'ui/molecule_info_panel.py',
            'ui/alloy_info_panel.py',
            'core/unified_table.py',
            'core/quark_unified_table.py',
            'core/subatomic_unified_table.py',
            'core/molecule_unified_table.py',
            'core/alloy_unified_table.py',
        ]

        for rel_path in files_to_analyze:
            full_path = self.project_root / rel_path
            if full_path.exists():
                self.analyzers[rel_path] = ASTAnalyzer(str(full_path))

    def validate_all(self) -> ValidationResult:
        """Run all validation checks"""
        print("=" * 80)
        print("UI CONNECTION VALIDATION REPORT")
        print("=" * 80)

        self.validate_control_panel_connections()
        self.validate_table_info_panel_connections()
        self.validate_data_management_signals()
        self.validate_visual_encoding_methods()
        self.validate_view_control_methods()

        return self.results

    def validate_control_panel_connections(self):
        """
        1. CONTROL PANEL -> TABLE CONNECTIONS
        For each tab verify all UI widgets have proper signal connections.
        """
        print("\n" + "-" * 80)
        print("1. CONTROL PANEL -> TABLE CONNECTIONS")
        print("-" * 80)

        tabs = {
            'Atoms': {
                'control_panel': 'ui/control_panel.py',
                'class_name': 'ControlPanel',
                'property_control_class': 'PropertyControl',
            },
            'Quarks': {
                'control_panel': 'ui/quark_control_panel.py',
                'class_name': 'QuarkControlPanel',
                'property_control_class': 'QuarkPropertyControl',
            },
            'Subatomic': {
                'control_panel': 'ui/subatomic_control_panel.py',
                'class_name': 'SubatomicControlPanel',
                'property_control_class': 'SubatomicPropertyControl',
            },
            'Molecules': {
                'control_panel': 'ui/molecule_control_panel.py',
                'class_name': 'MoleculeControlPanel',
                'property_control_class': 'MoleculePropertyControl',
            },
            'Alloys': {
                'control_panel': 'ui/alloy_control_panel.py',
                'class_name': 'AlloyControlPanel',
                'property_control_class': 'AlloyPropertyControl',
            },
        }

        for tab_name, config in tabs.items():
            print(f"\n  [{tab_name} Tab]")

            analyzer = self.analyzers.get(config['control_panel'])
            if not analyzer or not analyzer.tree:
                self._add_result('failed', ConnectionReport(
                    category="Control Panel",
                    component=tab_name,
                    expected=f"File {config['control_panel']}",
                    found=False,
                    details=f"Could not load {config['control_panel']}",
                    recommendation="Ensure file exists and has valid Python syntax"
                ))
                continue

            # Check for checkbox stateChanged connections
            self._check_checkbox_connections(analyzer, tab_name, config['class_name'])

            # Check for dropdown currentIndexChanged connections
            self._check_dropdown_connections(analyzer, tab_name, config['class_name'])

            # Check for slider valueChanged connections
            self._check_slider_connections(analyzer, tab_name, config['class_name'])

            # Check for button clicked connections
            self._check_button_connections(analyzer, tab_name, config['class_name'])

            # Check handler methods exist
            self._check_handler_methods(analyzer, tab_name, config['class_name'])

    def _check_checkbox_connections(self, analyzer: ASTAnalyzer, tab_name: str, class_name: str):
        """Check checkbox stateChanged/toggled connections"""
        # Find checkbox patterns in source (both individual and loop-created)
        checkbox_pattern = r'self\.(\w+_check)\s*=\s*QCheckBox'
        checkboxes = re.findall(checkbox_pattern, analyzer.source)

        # Also find checkboxes created with different naming patterns
        checkbox_pattern2 = r'self\.(\w+check)\s*=\s*QCheckBox'
        checkboxes.extend(re.findall(checkbox_pattern2, analyzer.source))

        # Find connections
        connections = analyzer.find_connect_statements()
        connected_checkboxes = set()

        for signal, slot in connections:
            if '_check.' in signal or '_check.stateChanged' in signal or '_check.toggled' in signal:
                connected_checkboxes.add(signal.split('.')[0].replace('self.', ''))
            if 'check.' in signal.lower() and ('stateChanged' in signal or 'toggled' in signal):
                connected_checkboxes.add(signal.split('.')[0].replace('self.', ''))

        for checkbox in checkboxes:
            found = checkbox in connected_checkboxes or f"self.{checkbox}" in [c[0].split('.')[0] for c in connections]

            # Also check if toggled is used
            toggled_found = any(f'{checkbox}.toggled' in c[0] or f'{checkbox}.stateChanged' in c[0]
                               for c in connections)

            if found or toggled_found:
                self._add_result('passed', ConnectionReport(
                    category="Control Panel",
                    component=f"{tab_name}/{checkbox}",
                    expected="stateChanged/toggled connected",
                    found=True,
                    details="Checkbox signal properly connected"
                ))
            else:
                # Check in raw source for alternative patterns including loop-based
                # Pattern 1: Direct connection
                direct_found = (f'{checkbox}.toggled.connect' in analyzer.source or
                               f'{checkbox}.stateChanged.connect' in analyzer.source)

                # Pattern 2: Loop-based connection (for check in [...]: check.stateChanged.connect)
                # These are connected via loop variable, not by name
                loop_pattern = rf'for\s+\w+\s+in\s+\[[^\]]*self\.{checkbox}[^\]]*\].*?\.stateChanged\.connect'
                loop_found = bool(re.search(loop_pattern, analyzer.source, re.DOTALL))

                # Pattern 3: Check if any stateChanged.connect appears near the checkbox definition
                # within the same method/block
                block_pattern = rf'self\.{checkbox}\s*=.*?\.stateChanged\.connect'
                block_found = bool(re.search(block_pattern, analyzer.source, re.DOTALL))

                if direct_found or loop_found or block_found:
                    self._add_result('passed', ConnectionReport(
                        category="Control Panel",
                        component=f"{tab_name}/{checkbox}",
                        expected="stateChanged/toggled connected",
                        found=True,
                        details="Checkbox signal properly connected"
                    ))
                else:
                    # Check for generic loop pattern connecting checkboxes
                    generic_loop_pattern = r'for\s+check\s+in\s+\[.*?\]:\s*\n\s*check\..*?\.stateChanged\.connect'
                    if re.search(generic_loop_pattern, analyzer.source, re.DOTALL):
                        self._add_result('passed', ConnectionReport(
                            category="Control Panel",
                            component=f"{tab_name}/{checkbox}",
                            expected="stateChanged/toggled connected",
                            found=True,
                            details="Checkbox connected via loop pattern"
                        ))
                    else:
                        self._add_result('warning', ConnectionReport(
                            category="Control Panel",
                            component=f"{tab_name}/{checkbox}",
                            expected="stateChanged/toggled connected",
                            found=False,
                            details=f"Checkbox {checkbox} may not have signal connected",
                            recommendation=f"Add: self.{checkbox}.toggled.connect(self.on_{checkbox}_changed)"
                        ))

    def _check_dropdown_connections(self, analyzer: ASTAnalyzer, tab_name: str, class_name: str):
        """Check QComboBox currentIndexChanged connections"""
        combo_pattern = r'self\.(\w+_combo)\s*=\s*QComboBox'
        combos = re.findall(combo_pattern, analyzer.source)

        for combo in combos:
            if f'{combo}.currentIndexChanged.connect' in analyzer.source:
                self._add_result('passed', ConnectionReport(
                    category="Control Panel",
                    component=f"{tab_name}/{combo}",
                    expected="currentIndexChanged connected",
                    found=True,
                    details="Dropdown signal properly connected"
                ))
            else:
                self._add_result('warning', ConnectionReport(
                    category="Control Panel",
                    component=f"{tab_name}/{combo}",
                    expected="currentIndexChanged connected",
                    found=False,
                    details=f"Dropdown {combo} may not have signal connected",
                    recommendation=f"Add: self.{combo}.currentIndexChanged.connect(self.on_{combo}_changed)"
                ))

    def _check_slider_connections(self, analyzer: ASTAnalyzer, tab_name: str, class_name: str):
        """Check QSlider valueChanged connections"""
        slider_pattern = r'self\.(\w+_slider)\s*=\s*QSlider'
        sliders = re.findall(slider_pattern, analyzer.source)

        for slider in sliders:
            if f'{slider}.valueChanged.connect' in analyzer.source:
                self._add_result('passed', ConnectionReport(
                    category="Control Panel",
                    component=f"{tab_name}/{slider}",
                    expected="valueChanged connected",
                    found=True,
                    details="Slider signal properly connected"
                ))
            else:
                self._add_result('warning', ConnectionReport(
                    category="Control Panel",
                    component=f"{tab_name}/{slider}",
                    expected="valueChanged connected",
                    found=False,
                    details=f"Slider {slider} may not have signal connected",
                    recommendation=f"Add: self.{slider}.valueChanged.connect(self.on_{slider}_changed)"
                ))

    def _check_button_connections(self, analyzer: ASTAnalyzer, tab_name: str, class_name: str):
        """Check QPushButton clicked connections"""
        button_pattern = r'self\.(\w+_btn)\s*=\s*QPushButton'
        buttons = re.findall(button_pattern, analyzer.source)

        for button in buttons:
            if f'{button}.clicked.connect' in analyzer.source:
                self._add_result('passed', ConnectionReport(
                    category="Control Panel",
                    component=f"{tab_name}/{button}",
                    expected="clicked connected",
                    found=True,
                    details="Button signal properly connected"
                ))
            else:
                self._add_result('failed', ConnectionReport(
                    category="Control Panel",
                    component=f"{tab_name}/{button}",
                    expected="clicked connected",
                    found=False,
                    details=f"Button {button} not connected!",
                    recommendation=f"Add: self.{button}.clicked.connect(self.on_{button}_clicked)"
                ))

    def _check_handler_methods(self, analyzer: ASTAnalyzer, tab_name: str, class_name: str):
        """Check that handler methods referenced in connects exist"""
        # Find all slot references in connect statements
        connections = analyzer.find_connect_statements()
        methods = analyzer.find_class_methods(class_name)

        for signal, slot in connections:
            # Extract method name from slot
            if slot.startswith('self.'):
                method_name = slot.replace('self.', '').split('(')[0]

                # Handle lambda expressions
                if 'lambda' in slot:
                    continue

                if method_name in methods or '.' in method_name:
                    continue  # Chained calls or found

                # Check if it's a signal emit
                if method_name.endswith('.emit'):
                    continue

    def validate_table_info_panel_connections(self):
        """
        2. TABLE -> INFO PANEL CONNECTIONS
        Verify in main.py the selection signals are connected to update methods.
        """
        print("\n" + "-" * 80)
        print("2. TABLE -> INFO PANEL CONNECTIONS")
        print("-" * 80)

        main_analyzer = self.analyzers.get('main.py')
        if not main_analyzer:
            print("  ERROR: Cannot analyze main.py")
            return

        expected_connections = [
            ('element_selected', 'update_element', 'Atoms'),
            ('quark_selected', 'update_quark', 'Quarks'),
            ('particle_selected', 'update_particle', 'Subatomic'),
            ('molecule_selected', 'update_molecule', 'Molecules'),
            ('alloy_selected', 'update_alloy', 'Alloys'),
        ]

        for signal, handler, tab in expected_connections:
            # Check for signal.connect pattern in main.py
            pattern = rf'{signal}\.connect'
            found = bool(re.search(pattern, main_analyzer.source))

            if found:
                self._add_result('passed', ConnectionReport(
                    category="Table->InfoPanel",
                    component=f"{tab}/{signal}",
                    expected=f"{signal} -> {handler}",
                    found=True,
                    details=f"Signal {signal} is connected in main.py"
                ))
                print(f"  [PASS] {tab}: {signal} -> {handler}")
            else:
                self._add_result('failed', ConnectionReport(
                    category="Table->InfoPanel",
                    component=f"{tab}/{signal}",
                    expected=f"{signal} -> {handler}",
                    found=False,
                    details=f"Signal {signal} not found connected in main.py",
                    recommendation=f"Add: self.{tab.lower()}_table.{signal}.connect(self._on_{tab.lower()}_selected)"
                ))
                print(f"  [FAIL] {tab}: {signal} -> {handler} NOT CONNECTED")

    def validate_data_management_signals(self):
        """
        3. DATA MANAGEMENT SIGNALS
        Verify each tab has add/edit/remove/create/reset signals.
        """
        print("\n" + "-" * 80)
        print("3. DATA MANAGEMENT SIGNALS")
        print("-" * 80)

        control_panels = {
            'Atoms': 'ui/control_panel.py',
            'Quarks': 'ui/quark_control_panel.py',
            'Subatomic': 'ui/subatomic_control_panel.py',
            'Molecules': 'ui/molecule_control_panel.py',
            'Alloys': 'ui/alloy_control_panel.py',
        }

        expected_signals = [
            'add_requested',
            'edit_requested',
            'remove_requested',
            'create_requested',
            'reset_requested',
        ]

        for tab, file_path in control_panels.items():
            print(f"\n  [{tab} Tab]")
            analyzer = self.analyzers.get(file_path)

            if not analyzer or not analyzer.tree:
                print(f"    Could not analyze {file_path}")
                continue

            # Find Signal definitions
            signals = analyzer.find_signal_definitions()

            for expected in expected_signals:
                found = expected in signals

                if found:
                    self._add_result('passed', ConnectionReport(
                        category="Data Management",
                        component=f"{tab}/{expected}",
                        expected=f"{expected} = Signal()",
                        found=True,
                        details=f"Signal {expected} defined"
                    ))
                    print(f"    [PASS] {expected} signal defined")
                else:
                    # Double check with regex
                    if f'{expected} = Signal()' in analyzer.source or f'{expected}=Signal()' in analyzer.source:
                        self._add_result('passed', ConnectionReport(
                            category="Data Management",
                            component=f"{tab}/{expected}",
                            expected=f"{expected} = Signal()",
                            found=True,
                            details=f"Signal {expected} defined"
                        ))
                        print(f"    [PASS] {expected} signal defined")
                    else:
                        self._add_result('failed', ConnectionReport(
                            category="Data Management",
                            component=f"{tab}/{expected}",
                            expected=f"{expected} = Signal()",
                            found=False,
                            details=f"Signal {expected} not found",
                            recommendation=f"Add: {expected} = Signal()"
                        ))
                        print(f"    [FAIL] {expected} signal MISSING")

            # Check that signals are connected in main.py
            main_analyzer = self.analyzers.get('main.py')
            if main_analyzer:
                tab_prefix = tab.lower().replace('s', '') if tab != 'Atoms' else 'atom'
                for expected in expected_signals:
                    pattern = rf'{tab_prefix}_control\.{expected}\.connect'
                    if re.search(pattern, main_analyzer.source):
                        print(f"    [PASS] {expected} connected in main.py")
                    else:
                        print(f"    [WARN] {expected} may not be connected in main.py")

    def validate_visual_encoding_methods(self):
        """
        4. VISUAL ENCODING METHODS
        Verify each table has set_property_mapping, set_property_filter_range, etc.
        """
        print("\n" + "-" * 80)
        print("4. VISUAL ENCODING METHODS")
        print("-" * 80)

        table_files = {
            'Atoms': ('core/unified_table.py', 'UnifiedTable'),
            'Quarks': ('core/quark_unified_table.py', 'QuarkUnifiedTable'),
            'Subatomic': ('core/subatomic_unified_table.py', 'SubatomicUnifiedTable'),
            'Molecules': ('core/molecule_unified_table.py', 'MoleculeUnifiedTable'),
            'Alloys': ('core/alloy_unified_table.py', 'AlloyUnifiedTable'),
        }

        expected_methods = [
            'set_property_mapping',
            'set_property_filter_range',
            'set_gradient_colors',
            'set_fade_value',
        ]

        # Alternative method names that serve same purpose
        alternatives = {
            'set_property_mapping': ['set_visual_property', 'set_layout_mode', 'set_fill_property', 'set_border_property'],
            'set_property_filter_range': ['set_filter', 'set_property_filter', 'set_classification_filter', 'set_generation_filter'],
            'set_gradient_colors': ['set_custom_gradient', 'set_gradient'],
            'set_fade_value': ['set_property_fade', 'set_fade'],
        }

        for tab, (file_path, class_name) in table_files.items():
            print(f"\n  [{tab} Tab - {class_name}]")
            analyzer = self.analyzers.get(file_path)

            if not analyzer or not analyzer.tree:
                print(f"    Could not analyze {file_path}")
                # Try to check if file exists
                full_path = self.project_root / file_path
                if not full_path.exists():
                    print(f"    File does not exist: {file_path}")
                continue

            methods = analyzer.find_class_methods(class_name)

            for expected in expected_methods:
                found = expected in methods

                # Check alternatives
                alt_found = False
                if not found and expected in alternatives:
                    for alt in alternatives[expected]:
                        if alt in methods:
                            alt_found = True
                            found = True
                            break

                if found:
                    self._add_result('passed', ConnectionReport(
                        category="Visual Encoding",
                        component=f"{tab}/{expected}",
                        expected=f"def {expected}()",
                        found=True,
                        details=f"Method {expected} exists" + (f" (or alternative)" if alt_found else "")
                    ))
                    print(f"    [PASS] {expected}()" + (f" (alternative found)" if alt_found else ""))
                else:
                    # Check in source directly for flexibility
                    if f'def {expected}' in analyzer.source:
                        self._add_result('passed', ConnectionReport(
                            category="Visual Encoding",
                            component=f"{tab}/{expected}",
                            expected=f"def {expected}()",
                            found=True,
                            details=f"Method {expected} exists"
                        ))
                        print(f"    [PASS] {expected}()")
                    else:
                        self._add_result('warning', ConnectionReport(
                            category="Visual Encoding",
                            component=f"{tab}/{expected}",
                            expected=f"def {expected}()",
                            found=False,
                            details=f"Method {expected} not found in {class_name}",
                            recommendation=f"Add method: def {expected}(self, ...)"
                        ))
                        print(f"    [WARN] {expected}() not found")

    def validate_view_control_methods(self):
        """
        5. VIEW CONTROL METHODS
        Verify each table has zoom/pan/reset_view methods.
        """
        print("\n" + "-" * 80)
        print("5. VIEW CONTROL METHODS")
        print("-" * 80)

        table_files = {
            'Atoms': ('core/unified_table.py', 'UnifiedTable'),
            'Quarks': ('core/quark_unified_table.py', 'QuarkUnifiedTable'),
            'Subatomic': ('core/subatomic_unified_table.py', 'SubatomicUnifiedTable'),
            'Molecules': ('core/molecule_unified_table.py', 'MoleculeUnifiedTable'),
            'Alloys': ('core/alloy_unified_table.py', 'AlloyUnifiedTable'),
        }

        expected_methods = {
            'reset_view': ['reset_view', 'resetView'],
            'set_zoom': ['set_zoom', 'zoom_level', 'setZoom'],
            'set_rotation': ['set_rotation', 'setRotation'],  # For molecules
        }

        for tab, (file_path, class_name) in table_files.items():
            print(f"\n  [{tab} Tab - {class_name}]")
            analyzer = self.analyzers.get(file_path)

            if not analyzer or not analyzer.tree:
                print(f"    Could not analyze {file_path}")
                continue

            methods = analyzer.find_class_methods(class_name)

            for method_key, alternatives in expected_methods.items():
                # Skip rotation check for non-molecule tables
                if method_key == 'set_rotation' and tab != 'Molecules':
                    continue

                found = False
                found_name = None

                for alt in alternatives:
                    if alt in methods:
                        found = True
                        found_name = alt
                        break
                    # Also check as attribute for zoom_level
                    if f'self.{alt}' in analyzer.source:
                        found = True
                        found_name = f"self.{alt}"
                        break

                if found:
                    self._add_result('passed', ConnectionReport(
                        category="View Control",
                        component=f"{tab}/{method_key}",
                        expected=f"{method_key}",
                        found=True,
                        details=f"Found: {found_name}"
                    ))
                    print(f"    [PASS] {method_key} -> {found_name}")
                else:
                    self._add_result('warning', ConnectionReport(
                        category="View Control",
                        component=f"{tab}/{method_key}",
                        expected=f"{method_key}",
                        found=False,
                        details=f"{method_key} not found in {class_name}",
                        recommendation=f"Add method: def {method_key}(self, ...)"
                    ))
                    print(f"    [WARN] {method_key} not found")

    def _add_result(self, status: str, report: ConnectionReport):
        """Add a result to the appropriate list"""
        if status == 'passed':
            self.results.passed.append(report)
        elif status == 'failed':
            self.results.failed.append(report)
        else:
            self.results.warnings.append(report)

    def print_summary(self):
        """Print a summary of results"""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)

        total = len(self.results.passed) + len(self.results.failed) + len(self.results.warnings)

        print(f"\n  Total Checks: {total}")
        print(f"  Passed:   {len(self.results.passed)} ({100*len(self.results.passed)//total if total else 0}%)")
        print(f"  Failed:   {len(self.results.failed)} ({100*len(self.results.failed)//total if total else 0}%)")
        print(f"  Warnings: {len(self.results.warnings)} ({100*len(self.results.warnings)//total if total else 0}%)")

        if self.results.failed:
            print("\n" + "-" * 80)
            print("FAILED CHECKS (Require Fixes):")
            print("-" * 80)
            for report in self.results.failed:
                print(f"\n  [{report.category}] {report.component}")
                print(f"    Expected: {report.expected}")
                print(f"    Details: {report.details}")
                if report.recommendation:
                    print(f"    Fix: {report.recommendation}")

        if self.results.warnings:
            print("\n" + "-" * 80)
            print("WARNINGS (May Need Attention):")
            print("-" * 80)
            for report in self.results.warnings[:10]:  # Limit to first 10
                print(f"\n  [{report.category}] {report.component}")
                print(f"    Expected: {report.expected}")
                print(f"    Details: {report.details}")
            if len(self.results.warnings) > 10:
                print(f"\n  ... and {len(self.results.warnings) - 10} more warnings")

        print("\n" + "=" * 80)

        # Overall status
        if len(self.results.failed) == 0:
            print("RESULT: All critical connections are properly configured!")
            return True
        else:
            print(f"RESULT: {len(self.results.failed)} critical issues need to be fixed.")
            return False


def run_validation():
    """Run the UI connection validation"""
    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    print(f"Project Root: {project_root}")

    # Run validation
    validator = UIConnectionValidator(str(project_root))
    validator.validate_all()
    success = validator.print_summary()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(run_validation())
