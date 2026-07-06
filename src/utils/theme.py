"""
Panther Development — Shared Theme System
==========================================
Reusable PyQt6 stylesheet generator supporting light and dark mode.

Usage in any Panther program:
    from src.utils.theme import apply_theme, get_palette
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    # Apply theme (call once on startup and on colorSchemeChanged)
    def apply_styles(self):
        dark = QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
        self.setStyleSheet(apply_theme(
            primary=self.config.primary_color,
            secondary=self.config.secondary_color,
            dark_mode=dark
        ))

    # Connect live OS theme changes
    QApplication.styleHints().colorSchemeChanged.connect(self.apply_styles)

    # Get individual palette colors for scattered setStyleSheet() calls
    palette = get_palette(dark_mode=dark)
    some_label.setStyleSheet(f"color: {palette['text_muted']}; font-size: 12px;")
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


# ── Palette definitions ───────────────────────────────────────────────────────

_LIGHT = {
    'background':      '#FFFFFF',
    'surface':         '#F5F5F5',   # Group boxes, input backgrounds
    'surface_alt':     '#EEEEEE',   # Alternate rows, hover backgrounds
    'border':          '#CBCCCE',   # Default border (overridden by secondary)
    'text':            '#333333',   # Primary text
    'text_muted':      '#666666',   # Secondary/hint text
    'text_disabled':   '#999999',   # Disabled text
    'text_on_primary': '#FFFFFF',   # Text on primary color backgrounds
    'input_bg':        '#FFFFFF',   # Input field background
    'hover_dark':      '#5A0000',   # Button hover (darkened primary)
    'hover_light':     '#F5F5F5',   # Light hover for non-primary elements
    'pressed':         '#3D0000',   # Button pressed state
    'disabled_bg':     '#CCCCCC',   # Disabled button background
    'error_text':      '#C62828',   # Error / warning text
    'error_bg':        '#FFEBEE',   # Error background
    'success_text':    '#2E7D32',   # Success text
    'info_bg':         '#FFF8DC',   # Info/disclaimer background
    'info_border':     '#CC6600',   # Info border
    'scrollbar_bg':    '#F0F0F0',
    'scrollbar_handle':'#AAAAAA',
}

_DARK = {
    'background':      '#1E1E1E',
    'surface':         '#2D2D2D',
    'surface_alt':     '#3A3A3A',
    'border':          '#555555',
    'text':            '#E0E0E0',
    'text_muted':      '#AAAAAA',
    'text_disabled':   '#666666',
    'text_on_primary': '#FFFFFF',
    'input_bg':        '#2D2D2D',
    'hover_dark':      '#A03030',   # Lighter maroon for dark bg
    'hover_light':     '#3A3A3A',
    'pressed':         '#C04040',
    'disabled_bg':     '#444444',
    'error_text':      '#EF9A9A',   # Lighter red readable on dark bg
    'error_bg':        '#4E1C1C',
    'success_text':    '#81C784',   # Lighter green readable on dark bg
    'info_bg':         '#3A3020',
    'info_border':     '#CC8800',
    'scrollbar_bg':    '#2D2D2D',
    'scrollbar_handle':'#555555',
}


def get_palette(primary: str = '#770000',
                secondary: str = '#CBCCCE',
                dark_mode: bool = False) -> dict:
    """
    Return a complete color palette dict for use in individual setStyleSheet calls.
    Includes brand colors merged with the light or dark base palette.
    """
    palette = dict(_DARK if dark_mode else _LIGHT)
    palette['primary'] = primary
    palette['secondary'] = secondary if not dark_mode else '#888888'

    # Derive hover colors from primary if using default maroon
    # Programs with different primaries will use the palette defaults
    return palette


def apply_theme(primary: str = '#770000',
                secondary: str = '#CBCCCE',
                dark_mode: bool = False) -> str:
    """
    Generate and return a complete PyQt6 stylesheet string.

    Args:
        primary:   Brand primary color (hex). Default: FIT maroon.
        secondary: Brand secondary color (hex). Default: FIT gray.
        dark_mode: True for dark palette, False for light.

    Returns:
        Complete stylesheet string ready to pass to setStyleSheet().
    """
    p = get_palette(primary, secondary, dark_mode)

    return f"""
        /* ── Base ─────────────────────────────────────────────────── */
        QMainWindow, QDialog {{
            background-color: {p['background']};
        }}
        QWidget {{
            background-color: {p['background']};
            color: {p['text']};
        }}

        /* ── Labels ───────────────────────────────────────────────── */
        QLabel {{
            color: {p['text']};
            font-size: 16px;
            background-color: transparent;
        }}

        /* ── Group Boxes ──────────────────────────────────────────── */
        QGroupBox {{
            font-weight: bold;
            font-size: 17px;
            border: 2px solid {p['secondary']};
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 10px;
            color: {p['text']};
            background-color: {p['background']};
        }}
        QGroupBox::title {{
            color: {p['primary']};
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            background-color: {p['background']};
        }}

        /* ── Buttons ──────────────────────────────────────────────── */
        QPushButton {{
            background-color: {p['primary']};
            color: {p['text_on_primary']};
            border: none;
            padding: 12px 24px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 16px;
        }}
        QPushButton:hover {{
            background-color: {p['hover_dark']};
        }}
        QPushButton:pressed {{
            background-color: {p['pressed']};
        }}
        QPushButton:disabled {{
            background-color: {p['disabled_bg']};
            color: {p['text_disabled']};
        }}

        /* ── Text Inputs ──────────────────────────────────────────── */
        QLineEdit {{
            padding: 8px;
            border: 2px solid {p['secondary']};
            border-radius: 4px;
            font-size: 16px;
            min-height: 25px;
            background-color: {p['input_bg']};
            color: {p['text']};
        }}
        QLineEdit:focus {{
            border-color: {p['primary']};
        }}
        QLineEdit:disabled {{
            background-color: {p['surface']};
            color: {p['text_disabled']};
        }}

        QTextEdit, QPlainTextEdit {{
            padding: 8px;
            border: 2px solid {p['secondary']};
            border-radius: 4px;
            font-size: 16px;
            background-color: {p['input_bg']};
            color: {p['text']};
        }}
        QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {p['primary']};
        }}

        /* ── Combo Boxes ──────────────────────────────────────────── */
        QComboBox {{
            padding-left: 12px;
            padding-right: 30px;
            padding-top: 8px;
            padding-bottom: 8px;
            border: 2px solid {p['secondary']};
            border-radius: 4px;
            font-size: 16px;
            min-height: 25px;
            background-color: {p['input_bg']};
            color: {p['text']};
        }}
        QComboBox:focus {{
            border-color: {p['primary']};
        }}
        QComboBox:disabled {{
            background-color: {p['surface']};
            color: {p['text_disabled']};
        }}
        QComboBox QAbstractItemView {{
            border: 2px solid {p['secondary']};
            background-color: {p['input_bg']};
            color: {p['text']};
            selection-background-color: {p['primary']};
            selection-color: {p['text_on_primary']};
            font-size: 16px;
        }}

        /* ── List Widgets ─────────────────────────────────────────── */
        QListWidget {{
            border: 2px solid {p['secondary']};
            border-radius: 4px;
            font-size: 16px;
            padding: 5px;
            background-color: {p['input_bg']};
            color: {p['text']};
        }}
        QListWidget::item {{
            padding: 2px;
        }}
        QListWidget::item:selected {{
            background-color: {p['primary']};
            color: {p['text_on_primary']};
        }}
        QListWidget::item:selected:!active {{
            background-color: {p['primary']};
            color: {p['text_on_primary']};
        }}
        QListWidget::item:hover:!selected {{
            background-color: {p['surface_alt']};
            color: {p['text']};
        }}

        /* ── Checkboxes ───────────────────────────────────────────── */
        QCheckBox {{
            spacing: 10px;
            font-size: 16px;
            color: {p['text']};
        }}
        QCheckBox::indicator {{
            width: 22px;
            height: 22px;
            border: 2px solid {p['secondary']};
            border-radius: 3px;
            background-color: {p['input_bg']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {p['primary']};
            border-color: {p['primary']};
        }}
        QCheckBox::indicator:disabled {{
            background-color: {p['surface']};
            border-color: {p['border']};
        }}

        /* ── Radio Buttons ────────────────────────────────────────── */
        QRadioButton {{
            font-size: 16px;
            color: {p['text']};
            spacing: 10px;
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {p['secondary']};
            border-radius: 9px;
            background-color: {p['input_bg']};
        }}
        QRadioButton::indicator:checked {{
            background-color: {p['primary']};
            border-color: {p['primary']};
        }}

        /* ── Spin Boxes ───────────────────────────────────────────── */
        QSpinBox, QDoubleSpinBox {{
            padding: 6px;
            border: 2px solid {p['secondary']};
            border-radius: 4px;
            font-size: 16px;
            background-color: {p['input_bg']};
            color: {p['text']};
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {p['primary']};
        }}

        /* ── Tab Widgets ──────────────────────────────────────────── */
        QTabWidget::pane {{
            border: 2px solid {p['secondary']};
            border-radius: 4px;
            background-color: {p['background']};
        }}
        QTabBar::tab {{
            background-color: {p['surface']};
            color: {p['text']};
            padding: 8px 16px;
            border: 1px solid {p['secondary']};
            border-bottom: none;
            border-radius: 4px 4px 0 0;
            font-size: 15px;
        }}
        QTabBar::tab:selected {{
            background-color: {p['primary']};
            color: {p['text_on_primary']};
            font-weight: bold;
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {p['surface_alt']};
        }}

        /* ── Scroll Bars ──────────────────────────────────────────── */
        QScrollBar:vertical {{
            background-color: {p['scrollbar_bg']};
            width: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:vertical {{
            background-color: {p['scrollbar_handle']};
            border-radius: 6px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background-color: {p['primary']};
        }}
        QScrollBar:horizontal {{
            background-color: {p['scrollbar_bg']};
            height: 12px;
            border-radius: 6px;
        }}
        QScrollBar::handle:horizontal {{
            background-color: {p['scrollbar_handle']};
            border-radius: 6px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background-color: {p['primary']};
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{
            width: 0px;
            height: 0px;
        }}

        /* ── Menu Bar ─────────────────────────────────────────────── */
        QMenuBar {{
            background-color: {p['surface']};
            color: {p['text']};
            font-size: 15px;
        }}
        QMenuBar::item:selected {{
            background-color: {p['primary']};
            color: {p['text_on_primary']};
        }}
        QMenu {{
            background-color: {p['surface']};
            color: {p['text']};
            border: 1px solid {p['secondary']};
            font-size: 15px;
        }}
        QMenu::item:selected {{
            background-color: {p['primary']};
            color: {p['text_on_primary']};
        }}

        /* ── Progress Bar ─────────────────────────────────────────── */
        QProgressBar {{
            border: 2px solid {p['secondary']};
            border-radius: 4px;
            background-color: {p['surface']};
            color: {p['text']};
            text-align: center;
            font-size: 14px;
        }}
        QProgressBar::chunk {{
            background-color: {p['primary']};
            border-radius: 3px;
        }}

        /* ── Dialogs ──────────────────────────────────────────────── */
        QMessageBox {{
            background-color: {p['background']};
        }}
        QMessageBox QLabel {{
            color: {p['text']};
        }}

        /* ── Tooltips ─────────────────────────────────────────────── */
        QToolTip {{
            background-color: {p['surface']};
            color: {p['text']};
            border: 1px solid {p['secondary']};
            font-size: 14px;
            padding: 4px;
        }}
    """


def is_dark_mode() -> bool:
    """Convenience function to check current OS color scheme."""
    try:
        return QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False
