"""
差异列表面板
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QTableWidget, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush


class DiffListPanel(QWidget):
    """差异列表面板"""

    # 状态颜色映射
    STATUS_COLORS = {
        "modified": QColor(255, 100, 100),    # 红色：本地已修改
        "same": QColor(100, 200, 100),        # 绿色：无需更新
        "svn_newer": QColor(255, 180, 100),   # 橙色：SVN 较新
        "new_file": QColor(255, 100, 100),    # 红色：新文件
    }

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题
        title_label = QLabel("传输差异")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

        # 差异列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["文件名", "状态"])

        # 设置表头
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 80)

        # 设置选择模式
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        layout.addWidget(self.table)

    def set_diff_list(self, diff_items: list):
        """设置差异列表
        Args:
            diff_items: [(filename, status), ...]
            status: "modified", "same", "svn_newer", "new_file"
        """
        self.table.setRowCount(len(diff_items))

        for row, (filename, status) in enumerate(diff_items):
            from PyQt6.QtWidgets import QTableWidgetItem

            # 文件名
            name_item = QTableWidgetItem(filename)
            self.table.setItem(row, 0, name_item)

            # 状态
            status_text = {
                "modified": "已修改",
                "same": "相同",
                "svn_newer": "SVN较新",
                "new_file": "新文件",
            }.get(status, status)

            status_item = QTableWidgetItem(status_text)

            # 设置背景色
            color = self.STATUS_COLORS.get(status)
            if color:
                status_item.setBackground(QBrush(color))

            self.table.setItem(row, 1, status_item)

    def clear_diff(self):
        """清空差异列表"""
        self.table.setRowCount(0)