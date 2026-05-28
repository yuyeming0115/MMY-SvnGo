"""
文件列表面板 - 支持拖拽、文件扫描、预览信号、历史路径选择
"""

from pathlib import Path
from re import match
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QHeaderView, QAbstractItemView, QTableWidgetItem,
    QLineEdit, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QBrush

from src.core.file_scanner import FileScanner


class FileListPanel(QWidget):
    """文件列表面板（支持拖拽）"""

    folder_dropped = pyqtSignal(Path)
    file_selected = pyqtSignal(Path)  # 发送完整路径
    file_selected_relative = pyqtSignal(str)  # 发送相对路径（用于同步）

    HIGHLIGHT_COLOR = QColor(100, 150, 255, 100)

    def __init__(self, title: str, side: str, history_manager=None):
        super().__init__()
        self.title = title
        self.side = side
        self.current_path: Path | None = None
        self.file_list: list = []
        self.scanner = FileScanner()
        self.history_manager = history_manager
        self._sync_selecting = False
        self._last_selected_row = -1
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题栏（文件计数放在尾部）
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 文件计数（放在标题行尾部）
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: #666; font-size: 12px;")
        title_layout.addWidget(self.count_label)

        layout.addWidget(title_bar)

        # 路径选择区域（移除下拉按钮）
        path_bar = QWidget()
        path_layout = QHBoxLayout(path_bar)
        path_layout.setContentsMargins(0, 0, 0, 0)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("拖入文件夹...")
        self.path_edit.setStyleSheet("QLineEdit { padding: 2px; background: #f0f0f0; }")
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit)

        # 不再显示下拉按钮（由收藏夹统一控制）
        self.history_btn = None

        layout.addWidget(path_bar)

        # 文件列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["文件名", "修改时间"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 100)

        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(False)

        self.table.itemSelectionChanged.connect(self.on_selection_changed)

        layout.addWidget(self.table)

        # 底部显示选中文件路径（截取到数字ID层级）
        self.selected_path_label = QLabel("")
        self.selected_path_label.setStyleSheet("color: #555; font-size: 11px; background: #e8e8e8; padding: 2px;")
        self.selected_path_label.setWordWrap(False)
        layout.addWidget(self.selected_path_label)

        self.setAcceptDrops(True)

    def show_history_menu(self):
        """显示历史路径选择菜单"""
        menu = QMenu(self)

        if self.history_manager:
            history = self.history_manager.get_all()
            for item in history:
                path = item.local_path if self.side == "local" else item.svn_path
                if path.exists():
                    action = menu.addAction(f"📁 {path.name}")
                    action.setToolTip(str(path))
                    action.triggered.connect(lambda checked, p=path: self.load_folder(p))

        menu.addSeparator()
        clear_action = menu.addAction("清空列表")
        clear_action.triggered.connect(self.clear_files)

        menu.exec(self.history_btn.mapToGlobal(self.history_btn.rect().bottomLeft()))

    def load_folder(self, path: Path):
        """加载指定文件夹"""
        self.current_path = path
        self.path_edit.setText(path.name)
        self.path_edit.setToolTip(str(path))
        self.scan_and_display(path)
        self.folder_dropped.emit(path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if Path(url.toLocalFile()).is_dir():
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.load_folder(path)
                event.acceptProposedAction()
                return
        event.ignore()

    def scan_and_display(self, path: Path):
        self.file_list = self.scanner.scan_folder(path)
        self.display_files()
        self.count_label.setText(str(len(self.file_list)))
        self.selected_path_label.setText("")
        self._last_selected_row = -1

    def display_files(self):
        self.table.setRowCount(len(self.file_list))
        for row, file_info in enumerate(self.file_list):
            name_item = QTableWidgetItem(file_info.name)
            name_item.setToolTip(str(file_info.path))
            self.table.setItem(row, 0, name_item)

            time_str = file_info.modify_time.strftime("%m-%d %H:%M")
            time_item = QTableWidgetItem(time_str)
            self.table.setItem(row, 1, time_item)

    def get_display_path(self, file_path: Path) -> str:
        """获取显示路径，从数字ID层级开始"""
        parts = list(file_path.parts)
        # 从前往后找数字ID层级（如503080）
        start_index = 0
        for i, part in enumerate(parts):
            # 检查是否是数字ID（纯数字，5-6位）
            if match(r'^\d{5,6}$', part):
                start_index = i
                break
        # 从数字ID开始截取路径
        result_parts = parts[start_index:]
        return '/'.join(result_parts) if result_parts else file_path.name

    def highlight_row(self, row: int):
        """高亮选中行"""
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(QBrush(self.HIGHLIGHT_COLOR))

    def clear_highlight(self):
        """清除高亮"""
        for row in range(self.table.rowCount()):
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QBrush(QColor(255, 255, 255)))

    def on_selection_changed(self):
        """选中变化时"""
        if self._sync_selecting:
            return
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            if row < len(self.file_list) and row != self._last_selected_row:
                self._last_selected_row = row
                self.clear_highlight()
                self.highlight_row(row)
                file_info = self.file_list[row]
                # 更新底部路径显示
                display_path = self.get_display_path(file_info.path)
                self.selected_path_label.setText(display_path)
                # 发送完整路径信号（用于预览）
                self.file_selected.emit(file_info.path)
                # 发送相对路径信号（用于同步匹配）
                self.file_selected_relative.emit(file_info.relative_path)

    def select_file_by_name(self, filename: str):
        """根据文件名选中（不触发同步信号）- 兼容旧接口"""
        self.select_by_relative_path(filename)

    def select_by_relative_path(self, relative_path: str):
        """根据相对路径选中（不触发同步信号）"""
        for row, file_info in enumerate(self.file_list):
            # 先尝试相对路径匹配，再尝试文件名匹配（兼容）
            if file_info.relative_path == relative_path or file_info.name == relative_path:
                self._sync_selecting = True
                self._last_selected_row = row
                self.table.selectRow(row)
                self.clear_highlight()
                self.highlight_row(row)
                # 更新底部路径显示
                display_path = self.get_display_path(file_info.path)
                self.selected_path_label.setText(display_path)
                self._sync_selecting = False
                self.scrollToRow(row)
                return

    def get_file_path_by_relative(self, relative_path: str) -> Path | None:
        """根据相对路径获取完整路径"""
        for file_info in self.file_list:
            if file_info.relative_path == relative_path or file_info.name == relative_path:
                return file_info.path
        return None

    def scrollToRow(self, row: int):
        """滚动到指定行（居中显示）"""
        item = self.table.item(row, 0)
        if item:
            self.table.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)

    def scrollToSelectedRow(self):
        """滚动到当前选中行（居中显示）"""
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            self.scrollToRow(row)

    def get_file_path_by_name(self, filename: str) -> Path | None:
        """根据文件名获取完整路径（兼容旧接口）"""
        return self.get_file_path_by_relative(filename)

    def get_file_list(self) -> list:
        return self.file_list

    def clear_files(self):
        self.table.setRowCount(0)
        self.file_list = []
        self.current_path = None
        self.path_edit.setText("")
        self.path_edit.setToolTip("")
        self.count_label.setText("0")
        self.selected_path_label.setText("")
        self._last_selected_row = -1