"""Paleta y hoja de estilos global alineada con el icono de la aplicación."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QToolTip, QWidget

# Azul rey y cian del icono
BLUE_800 = "#1e40af"
BLUE_700 = "#1d4ed8"
BLUE_600 = "#2563eb"
BLUE_500 = "#3b82f6"
BLUE_200 = "#bfdbfe"
BLUE_100 = "#dbeafe"
BLUE_50 = "#eff6ff"
CYAN_600 = "#0891b2"
CYAN_500 = "#06b6d4"
CYAN_400 = "#22d3ee"
CYAN_100 = "#cffafe"
SLATE_900 = "#0f172a"
SLATE_700 = "#334155"
SLATE_500 = "#64748b"
SLATE_200 = "#e2e8f0"
SLATE_100 = "#f1f5f9"
WHITE = "#ffffff"
ERROR = "#dc2626"

SIDEBAR_BG = BLUE_800
SIDEBAR_BG_END = CYAN_600


def apply_panel_background(widget: QWidget) -> None:
    """Permite que QSS pinte el fondo del panel (requerido en Windows/Fusion)."""
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    widget.setAutoFillBackground(True)


def configure_application_theme(app: QApplication) -> None:
    """Aplica estilos globales y ajustes para tooltips visibles en Windows."""
    app.setStyleSheet(get_stylesheet())
    app.setEffectEnabled(Qt.UIEffect.UI_AnimateTooltip, False)
    tooltip_font = QFont("Segoe UI", 9)
    tooltip_font.setStyleHint(QFont.StyleHint.SansSerif)
    QToolTip.setFont(tooltip_font)


def get_stylesheet() -> str:
    """Estilos QSS globales para S3 Desktop."""
    return f"""
QWidget {{
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}}

QMainWindow {{
    background-color: {BLUE_50};
    color: {SLATE_700};
}}

QSplitter {{
    background-color: {BLUE_50};
}}

QDialog {{
    background-color: {WHITE};
    color: {SLATE_700};
}}

#connectionSidebar {{
    background-color: {SIDEBAR_BG};
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 {BLUE_700}, stop:1 {SIDEBAR_BG_END}
    );
    border-right: 1px solid {BLUE_800};
    color: {WHITE};
    margin: 0;
    padding: 0;
}}

#connectionSidebar QLabel#sectionTitle {{
    color: {WHITE};
    font-weight: 700;
    font-size: 9pt;
    padding: 6px 2px 4px 2px;
}}

#connectionSidebar QFrame#sidebarSeparator {{
    background-color: rgba(255, 255, 255, 0.35);
    min-height: 1px;
    max-height: 1px;
    border: none;
}}

#connectionSidebar QListWidget#sidebarList {{
    background-color: {WHITE};
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 8px;
    color: {SLATE_700};
    padding: 4px;
    outline: none;
}}

#connectionSidebar QListWidget#sidebarList::item {{
    padding: 8px 10px;
    border-radius: 6px;
    margin: 1px 0;
    color: {SLATE_700};
    min-height: 20px;
}}

#connectionSidebar QListWidget#sidebarList::item:hover {{
    background-color: {SLATE_100};
}}

#connectionSidebar QListWidget#sidebarList::item:selected {{
    background-color: {BLUE_100};
    color: {BLUE_800};
    border-left: 3px solid {BLUE_600};
}}

#connectionSidebar QListWidget#sidebarList::item:disabled {{
    color: {SLATE_500};
}}

#connectionSidebar QPushButton {{
    background-color: rgba(15, 23, 42, 0.45);
    color: {WHITE};
    border: 1px solid rgba(255, 255, 255, 0.35);
    border-radius: 6px;
    padding: 7px 12px;
    font-weight: 600;
}}

#connectionSidebar QPushButton:hover {{
    background-color: rgba(15, 23, 42, 0.65);
    border-color: {CYAN_400};
    color: {WHITE};
}}

#connectionSidebar QPushButton:pressed {{
    background-color: rgba(15, 23, 42, 0.85);
}}

#connectionSidebar QPushButton:disabled {{
    background-color: rgba(15, 23, 42, 0.25);
    color: rgba(255, 255, 255, 0.55);
    border-color: rgba(255, 255, 255, 0.15);
}}

#connectionSidebar QPushButton#footerAction {{
    background-color: rgba(15, 23, 42, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.3);
}}

#connectionSidebar QPushButton#footerAction:hover {{
    background-color: rgba(15, 23, 42, 0.75);
    border-color: {CYAN_400};
}}

#s3Browser {{
    background-color: transparent;
    color: {SLATE_700};
}}

#s3Browser QPushButton {{
    background-color: {BLUE_600};
    color: {WHITE};
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
    min-height: 18px;
}}

#s3Browser QPushButton:hover {{
    background-color: {BLUE_500};
}}

#s3Browser QPushButton:pressed {{
    background-color: {BLUE_700};
}}

#s3Browser QPushButton:disabled {{
    background-color: {SLATE_200};
    color: {SLATE_500};
}}

#s3Browser QPushButton#primaryButton {{
    background-color: {CYAN_600};
    color: {WHITE};
}}

#s3Browser QPushButton#primaryButton:hover {{
    background-color: {CYAN_500};
    color: {WHITE};
}}

#s3Browser QPushButton#primaryButton:pressed {{
    background-color: #0e7490;
    color: {WHITE};
}}

#s3Browser QPushButton#primaryButton:disabled {{
    background-color: {SLATE_200};
    color: {SLATE_500};
}}

#s3Browser QLabel {{
    color: {SLATE_700};
    font-weight: 500;
}}

#s3Browser QLineEdit#pathDisplay:read-only {{
    background-color: {WHITE};
    color: {SLATE_900};
    border: 1px solid {SLATE_200};
}}

#s3Browser QLineEdit#nameFilter {{
    background-color: {WHITE};
    color: {SLATE_900};
    border: 1px solid {SLATE_200};
}}

#s3Browser QPushButton#filterAction {{
    min-width: 72px;
    padding: 6px 12px;
}}

#s3Browser QLabel#folderStats {{
    color: {SLATE_500};
    font-size: 9pt;
    font-weight: 500;
    padding-left: 8px;
}}

QLineEdit {{
    background-color: {WHITE};
    border: 1px solid {SLATE_200};
    border-radius: 6px;
    padding: 7px 10px;
    color: {SLATE_700};
    selection-background-color: {BLUE_100};
}}

QLineEdit:focus {{
    border: 1px solid {BLUE_500};
}}

QLineEdit:read-only {{
    background-color: {SLATE_100};
    color: {SLATE_500};
}}

QLineEdit::placeholder {{
    color: {SLATE_500};
}}

QDialog QLabel {{
    color: {SLATE_700};
}}

QDialog QLabel#dialogHint {{
    color: {SLATE_700};
    font-size: 10pt;
    line-height: 1.4;
}}

QFormLayout QLabel {{
    color: {SLATE_700};
    font-weight: 500;
}}

QTableWidget {{
    background-color: {WHITE};
    alternate-background-color: {SLATE_100};
    color: {SLATE_700};
    border: 1px solid {SLATE_200};
}}

QTableView {{
    background-color: {WHITE};
    alternate-background-color: {SLATE_100};
    gridline-color: {SLATE_200};
    border: 1px solid {SLATE_200};
    selection-background-color: {BLUE_100};
    selection-color: {SLATE_900};
    outline: none;
    color: {SLATE_700};
}}

QTableView::item {{
    padding: 2px 4px;
}}

QTableView::indicator {{
    width: 18px;
    height: 18px;
}}

QTableView::indicator:unchecked {{
    background-color: {WHITE};
    border: 1px solid {SLATE_500};
    border-radius: 3px;
}}

QTableView::indicator:unchecked:hover {{
    border-color: {BLUE_600};
}}

QTableView::indicator:checked {{
    background-color: {BLUE_600};
    border: 1px solid {BLUE_700};
    border-radius: 3px;
}}

QHeaderView {{
    background-color: {BLUE_50};
}}

QHeaderView::section {{
    background-color: {BLUE_50};
    color: {BLUE_700};
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid {BLUE_600};
    border-right: 1px solid {SLATE_200};
    font-weight: 600;
}}

QHeaderView::section:last {{
    border-right: none;
}}

QTableCornerButton::section {{
    background-color: {BLUE_50};
    border: none;
    border-bottom: 2px solid {BLUE_600};
}}

QAbstractScrollArea::corner {{
    background-color: {BLUE_50};
    border: none;
}}

#transferPanel {{
    background-color: {WHITE};
    border: 1px solid {SLATE_200};
    border-radius: 8px;
    margin-top: 4px;
    color: {SLATE_700};
}}

#transferPanel QLabel#panelTitle {{
    color: {BLUE_700};
    font-size: 11pt;
    font-weight: 600;
    padding: 4px 0 6px 0;
}}

QSplitter::handle:horizontal {{
    background-color: {CYAN_100};
    width: 4px;
}}

QSplitter::handle:horizontal:hover {{
    background-color: {CYAN_500};
}}

QStatusBar {{
    background-color: {BLUE_50};
    color: {BLUE_700};
    border-top: 1px solid {SLATE_200};
    padding: 2px 8px;
}}

QProgressBar {{
    border: 1px solid {SLATE_200};
    border-radius: 5px;
    background-color: {SLATE_100};
    text-align: center;
    color: {SLATE_700};
    min-height: 16px;
}}

QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {BLUE_600}, stop:1 {CYAN_500}
    );
    border-radius: 4px;
}}

QDialogButtonBox QPushButton {{
    background-color: {BLUE_600};
    color: {WHITE};
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    min-width: 72px;
}}

QDialogButtonBox QPushButton:hover {{
    background-color: {BLUE_500};
}}

QDialogButtonBox QPushButton:pressed {{
    background-color: {BLUE_700};
}}

QDialog QPushButton {{
    background-color: {BLUE_600};
    color: {WHITE};
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
}}

QDialog QPushButton:hover {{
    background-color: {BLUE_500};
}}

QDialog QPushButton:pressed {{
    background-color: {BLUE_700};
}}

QDialog QPushButton:disabled {{
    background-color: {SLATE_200};
    color: {SLATE_500};
}}

QComboBox {{
    background-color: {WHITE};
    border: 1px solid {SLATE_200};
    border-radius: 6px;
    padding: 6px 10px;
    color: {SLATE_700};
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: {BLUE_500};
}}

QComboBox:focus {{
    border-color: {BLUE_600};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 24px;
    border-left: 1px solid {SLATE_200};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
    background-color: {BLUE_50};
}}

QComboBox::down-arrow {{
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {WHITE};
    color: {SLATE_700};
    border: 1px solid {SLATE_200};
    selection-background-color: {BLUE_100};
    selection-color: {SLATE_900};
    outline: none;
}}

QSpinBox {{
    background-color: {WHITE};
    border: 1px solid {SLATE_200};
    border-radius: 6px;
    padding: 6px 10px;
    color: {SLATE_700};
    min-height: 24px;
}}

QSpinBox:hover {{
    border-color: {BLUE_500};
}}

QSpinBox:focus {{
    border-color: {BLUE_600};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 18px;
    background-color: {BLUE_50};
    border: none;
}}

QCheckBox {{
    color: {SLATE_700};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
}}

QCheckBox::indicator:unchecked {{
    background-color: {WHITE};
    border: 1px solid {SLATE_500};
    border-radius: 3px;
}}

QCheckBox::indicator:checked {{
    background-color: {BLUE_600};
    border: 1px solid {BLUE_700};
    border-radius: 3px;
}}

QLabel#errorLabel {{
    color: {ERROR};
    font-weight: 500;
}}

LoadingOverlay {{
    background-color: rgba(240, 249, 255, 210);
}}

LoadingOverlay QLabel {{
    color: {BLUE_700};
    font-size: 11pt;
    font-weight: 600;
    background: transparent;
}}

QToolTip {{
    background-color: rgb(15, 23, 42);
    color: rgb(255, 255, 255);
    border: 1px solid rgb(37, 99, 235);
    padding: 6px 10px;
    font-size: 9pt;
}}

QScrollBar:vertical {{
    background: {SLATE_100};
    width: 10px;
    margin: 0;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background: {SLATE_200};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {CYAN_500};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: {SLATE_100};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background: {SLATE_200};
    border-radius: 5px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {CYAN_500};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
"""

