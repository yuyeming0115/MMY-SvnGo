"""
差异列表面板 - 点击同步左右列表
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QListWidget, QListWidgetItem
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

    def __init__(self):
        super().__init__()
        self.file_names: list = []
        self._sync_selecting = False
        self._last_row = -1
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        title_label = QLabel("传输差异")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(False)
        self.list_widget.currentRowChanged.connect(self.on_row_changed)
        layout.addWidget(self.list_widget)

    def on_row_changed(self, row: int):
        """选中行变化时，延迟发送信号"""
        if self._sync_selecting:
            return
        if row >= 0 and row < len(self.file_names) and row != self._last_row:
            self._last_row = row
            QTimer.singleShot(50, lambda: self._emit_selection(row))

    def _emit_selection(self, row: int):
        """延迟发送选中信号"""
        if row >= 0 and row < len(self.file_names) and row == self._last_row:
            self.file_selected.emit(self.file_names[row])

    def set_diff_list(self, diff_items: list):
        """设置差异列表"""
        self.list_widget.clear()
        self.file_names = []

        for filename, status in diff_items:
            self.file_names.append(filename)
            display_name = Path(filename).stem
            item = QListWidgetItem(display_name)

            color = self.STATUS_COLORS.get(status)
            if color:
                item.setBackground(QBrush(color))

            status_text = self.STATUS_TEXT.get(status, status)
            item.setToolTip(f"{filename} - {status_text}")

            self.list_widget.addItem(item)

    def select_by_filename(self, filename: str):
        """根据完整文件名选中对应行（不触发同步）"""
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
        self._last_row = -1