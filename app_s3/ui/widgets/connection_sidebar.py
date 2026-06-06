"""Panel lateral de cuentas y buckets."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app_s3.domain.models import CredentialProfile
from app_s3.ui.theme import SLATE_500, apply_panel_background

_PROFILE_ROLE = Qt.ItemDataRole.UserRole
_PLACEHOLDER_COLOR = QColor(SLATE_500)
_LIST_MIN_HEIGHT = 88


class ConnectionSidebar(QWidget):
    """Panel lateral para seleccionar cuenta, bucket y acciones de conexión."""

    profile_selected = Signal(str)
    bucket_selected = Signal(str)
    add_credential_requested = Signal()
    edit_credential_requested = Signal()
    set_default_credential_requested = Signal()
    delete_credential_requested = Signal()
    add_bucket_requested = Signal()
    lock_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("connectionSidebar")
        apply_panel_background(self)
        self.setMinimumWidth(280)
        self.setMaximumWidth(380)
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Expanding,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._section_title("Cuentas"))
        self._profile_list = self._create_list_widget()
        self._profile_list.currentItemChanged.connect(self._on_profile_item_changed)
        layout.addWidget(self._profile_list, stretch=2)

        profile_btns = QHBoxLayout()
        self._add_cred_btn = QPushButton("+ Cuenta")
        self._add_cred_btn.setToolTip(
            "Registrar una nueva cuenta de Amazon con claves de acceso"
        )
        self._add_cred_btn.clicked.connect(self.add_credential_requested.emit)
        profile_btns.addWidget(self._add_cred_btn)
        self._edit_cred_btn = QPushButton("Editar")
        self._edit_cred_btn.setToolTip("Modificar la cuenta seleccionada en la lista")
        self._edit_cred_btn.clicked.connect(self.edit_credential_requested.emit)
        profile_btns.addWidget(self._edit_cred_btn)
        layout.addLayout(profile_btns)

        self._default_cred_btn = QPushButton("Por defecto")
        self._default_cred_btn.setToolTip(
            "Usar esta cuenta al abrir la aplicación"
        )
        self._default_cred_btn.clicked.connect(
            self.set_default_credential_requested.emit
        )
        layout.addWidget(self._default_cred_btn)

        self._delete_cred_btn = QPushButton("Eliminar cuenta")
        self._delete_cred_btn.setToolTip("Eliminar la cuenta seleccionada")
        self._delete_cred_btn.clicked.connect(self.delete_credential_requested.emit)
        layout.addWidget(self._delete_cred_btn)

        layout.addWidget(self._separator())

        layout.addWidget(self._section_title("Buckets"))
        self._bucket_list = self._create_list_widget()
        self._bucket_list.currentItemChanged.connect(self._on_bucket_item_changed)
        layout.addWidget(self._bucket_list, stretch=2)

        self._add_bucket_btn = QPushButton("+ Bucket")
        self._add_bucket_btn.setToolTip(
            "Agregar un bucket escribiendo su nombre exacto"
        )
        self._add_bucket_btn.clicked.connect(self.add_bucket_requested.emit)
        layout.addWidget(self._add_bucket_btn)

        layout.addStretch(1)

        self._lock_btn = QPushButton("Bloquear")
        self._lock_btn.setObjectName("footerAction")
        self._lock_btn.setToolTip(
            "Cerrar sesión y volver a pedir la contraseña maestra al abrir"
        )
        self._lock_btn.clicked.connect(self.lock_requested.emit)
        layout.addWidget(self._lock_btn)

        self._blocking_profile_signal = False
        self._blocking_bucket_signal = False
        self._profiles: list[CredentialProfile] = []
        self._default_profile_id: str | None = None

    def _create_list_widget(self) -> QListWidget:
        widget = QListWidget()
        widget.setObjectName("sidebarList")
        widget.setSpacing(2)
        widget.setMinimumHeight(_LIST_MIN_HEIGHT)
        apply_panel_background(widget)
        return widget

    @staticmethod
    def _section_title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    @staticmethod
    def _separator() -> QFrame:
        line = QFrame()
        line.setObjectName("sidebarSeparator")
        line.setFrameShape(QFrame.Shape.NoFrame)
        line.setFixedHeight(1)
        return line

    @staticmethod
    def _add_placeholder(list_widget: QListWidget, text: str) -> None:
        placeholder = QListWidgetItem(text)
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        placeholder.setForeground(QBrush(_PLACEHOLDER_COLOR))
        list_widget.addItem(placeholder)

    def set_profiles(
        self,
        profiles: list[CredentialProfile],
        active_id: str | None = None,
        default_id: str | None = None,
    ) -> None:
        self._blocking_profile_signal = True
        self._profile_list.clear()
        self._profiles = profiles
        self._default_profile_id = default_id
        if not profiles:
            self._add_placeholder(self._profile_list, "Agrega una cuenta")
            self._edit_cred_btn.setEnabled(False)
            self._default_cred_btn.setEnabled(False)
            self._delete_cred_btn.setEnabled(False)
        else:
            select_row = 0
            for i, profile in enumerate(profiles):
                label = profile.alias
                if profile.id == default_id:
                    label = f"★ {profile.alias}"
                item = QListWidgetItem(label)
                item.setData(_PROFILE_ROLE, profile.id)
                self._profile_list.addItem(item)
                if active_id and profile.id == active_id:
                    select_row = i
            self._profile_list.setCurrentRow(select_row)
            self._update_profile_action_states(profiles, active_id, default_id)
        self._blocking_profile_signal = False

    def _update_profile_action_states(
        self,
        profiles: list[CredentialProfile],
        active_id: str | None,
        default_id: str | None,
    ) -> None:
        has_selection = active_id is not None
        self._edit_cred_btn.setEnabled(has_selection)
        is_default = has_selection and active_id == default_id
        self._default_cred_btn.setEnabled(has_selection and not is_default)
        if is_default:
            self._default_cred_btn.setText("Predeterminada")
            self._default_cred_btn.setToolTip(
                "Esta cuenta se abre al iniciar la aplicación"
            )
        else:
            self._default_cred_btn.setText("Por defecto")
            self._default_cred_btn.setToolTip(
                "Usar esta cuenta al abrir la aplicación"
            )

        can_delete = has_selection
        delete_tooltip = "Eliminar la cuenta seleccionada"
        if has_selection and len(profiles) > 1 and active_id == default_id:
            can_delete = False
            delete_tooltip = (
                "Elige otra cuenta como predeterminada antes de eliminar esta"
            )
        self._delete_cred_btn.setEnabled(can_delete)
        self._delete_cred_btn.setToolTip(delete_tooltip)

    def set_buckets(
        self,
        bucket_names: list[str],
        active_name: str | None = None,
    ) -> None:
        self._blocking_bucket_signal = True
        self._bucket_list.clear()
        self._add_bucket_btn.setEnabled(self.current_profile_id() is not None)
        if not bucket_names:
            self._add_placeholder(self._bucket_list, "Agrega un bucket")
        else:
            select_row = 0
            for i, name in enumerate(bucket_names):
                self._bucket_list.addItem(QListWidgetItem(name))
                if active_name and name == active_name:
                    select_row = i
            self._bucket_list.setCurrentRow(select_row)
        self._blocking_bucket_signal = False

    def clear_buckets(self) -> None:
        self.set_buckets([])

    def current_profile_id(self) -> str | None:
        item = self._profile_list.currentItem()
        if item is None:
            return None
        profile_id = item.data(_PROFILE_ROLE)
        return profile_id if profile_id else None

    def current_profile_alias(self) -> str:
        item = self._profile_list.currentItem()
        return item.text() if item else ""

    def current_bucket_name(self) -> str | None:
        item = self._bucket_list.currentItem()
        if item is None or not (item.flags() & Qt.ItemFlag.ItemIsSelectable):
            return None
        return item.text()

    def _on_profile_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if self._blocking_profile_signal:
            return
        if current is None:
            return
        profile_id = current.data(_PROFILE_ROLE)
        if not profile_id:
            return
        self._update_profile_action_states(
            self._profiles,
            profile_id,
            self._default_profile_id,
        )
        self.profile_selected.emit(profile_id)

    def _on_bucket_item_changed(
        self,
        current: QListWidgetItem | None,
        _previous: QListWidgetItem | None,
    ) -> None:
        if self._blocking_bucket_signal or current is None:
            return
        if not (current.flags() & Qt.ItemFlag.ItemIsSelectable):
            return
        self.bucket_selected.emit(current.text())
