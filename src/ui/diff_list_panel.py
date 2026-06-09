"""
差异列表面板 - 点击同步左右列表
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QBrush


class DiffListPanel(QWidget):
    """差异列表面板"""

    # 信号：文件选中（用于同步左右列表）
    file_selected = pyqtSignal(str)  # 发送完整文件名

    # 状态颜色映射
    STATUS_COLORS = {
        "modified": QColor(255, 100, 100),    # 红色：本地已修改
        "same": QColor(100, 200, 100),        # 绿色：无需更新
        "svn_newer": QColor(255, 180, 100),   # 橙色：SVN 较新
        "new_file": QColor(255, 100, 100),    # 红色：新文件
    }

    # 选中高亮颜色
    SELECT_COLOR = QColor(100, 150, 255)

    # 状态文字映射
    STATUS_TEXT = {
        "modified": "已修改",
        "same": "相同",
        "svn_newer": "SVN较新",
        "new_file": "新文件",
    }

    FILTERS = {
        "action": ("待处理", {"modified", "new_file"}),
        "risk": ("风险", {"svn_newer"}),
        "all": ("全部", None),
    }

    def __init__(self):
        super().__init__()
        self.file_names: list = []
        self.diff_items: list = []
        self.current_filter = "action"
        self.filter_buttons = {}
        self._sync_selecting = False
        self._last_row = -1
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题栏（和左右两列对齐）
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("传输差异")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title_label)

        title_layout.addStretch()

        # 文件计数（和左右两列格式一致）
        self.count_label = QLabel("0")
        self.count_label.setStyleSheet("color: #666; font-size: 12px;")
        title_layout.addWidget(self.count_label)

        layout.addWidget(title_bar)

        # 筛选栏（和左右两列路径栏对齐）
        path_bar = QWidget()
        path_bar.setFixedHeight(24)
        path_layout = QHBoxLayout(path_bar)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(4)

        for key in ("action", "risk", "all"):
            label, _ = self.FILTERS[key]
            button = QPushButton(label)
            button.setFixedHeight(22)
            button.setCheckable(True)
            button.clicked.connect(lambda checked, k=key: self.set_filter(k))
            self.filter_buttons[key] = button
            path_layout.addWidget(button)

        layout.addWidget(path_bar)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        layout.addWidget(self.list_widget)

        # 底部占位（和左右两列对齐）
        bottom_bar = QWidget()
        bottom_bar.setFixedHeight(18)  # 和左右两列的底部路径显示高度一致
        layout.addWidget(bottom_bar)

        self.update_filter_buttons()

    def on_row_changed(self, row: int):
        """选中行变化时，立即发送信号（不延迟，实现快速切换预览效果）"""
        if self._sync_selecting:
            return
        if row >= 0 and row < len(self.file_names) and row != self._last_row:
            self._last_row = row
            # 立即发送信号（让预览同步更及时，实现动画效果）
            self.file_selected.emit(self.file_names[row])

    def _emit_selection(self, row: int):
        """延迟发送选中信号（保留兼容）"""
        if row >= 0 and row < len(self.file_names) and row == self._last_row:
            self.file_selected.emit(self.file_names[row])

    def set_filter(self, filter_key: str):
        """切换差异筛选。"""
        if filter_key not in self.FILTERS:
            return
        self.current_filter = filter_key
        self.update_filter_buttons()
        self.refresh_visible_items()

    def update_filter_buttons(self):
        """更新筛选按钮状态。"""
        for key, button in self.filter_buttons.items():
            checked = key == self.current_filter
            button.setChecked(checked)
            if checked:
                button.setStyleSheet("QPushButton { background: #4a90d9; color: white; border-radius: 3px; }")
            else:
                button.setStyleSheet("QPushButton { background: #e8e8e8; color: #333; border-radius: 3px; }")

    def _matches_filter(self, status: str) -> bool:
        """判断状态是否匹配当前筛选。"""
        _, allowed = self.FILTERS[self.current_filter]
        return allowed is None or status in allowed

    def set_diff_list(self, diff_items: list):
        """设置差异列表"""
        self.diff_items = diff_items
        self.refresh_visible_items()

    def refresh_visible_items(self):
        """根据当前筛选刷新列表。"""
        self.list_widget.clear()
        self.file_names = []

        for filename, status in self.diff_items:
            if not self._matches_filter(status):
                continue

            self.file_names.append(filename)
            display_name = Path(filename).stem
            item = QListWidgetItem(display_name)

            color = self.STATUS_COLORS.get(status)
            if color:
                item.setBackground(QBrush(color))

            status_text = self.STATUS_TEXT.get(status, status)
            item.setToolTip(f"{filename} - {status_text}")

            self.list_widget.addItem(item)

        # 更新计数
        total = len(self.diff_items)
        visible = len(self.file_names)
        self.count_label.setText(f"{visible}/{total}")

    def select_by_filename(self, filename: str):
        """根据完整文件名选中对应行（不触发同步）"""
        all_names = [name for name, _ in self.diff_items]
        if filename not in self.file_names and filename in all_names:
            self.set_filter("all")

        if filename in self.file_names:
            row = self.file_names.index(filename)
            self._sync_selecting = True
            self._last_row = row
            self.list_widget.setCurrentRow(row)
            self.scrollToRow(row)
            self._sync_selecting = False

    def scrollToRow(self, row: int):
        """滚动到指定行（居中显示）"""
        item = self.list_widget.item(row)
        if item:
            self.list_widget.scrollToItem(item, self.list_widget.ScrollHint.PositionAtCenter)

    def scrollToSelectedRow(self):
        """滚动到当前选中行（居中显示）"""
        row = self.list_widget.currentRow()
        if row >= 0:
            self.scrollToRow(row)

    def clear_diff(self):
        """清空差异列表"""
        self.list_widget.clear()
        self.file_names = []
        self.diff_items = []
        self._last_row = -1
        self.count_label.setText("0")
