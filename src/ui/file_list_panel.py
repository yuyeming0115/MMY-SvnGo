"""
文件列表面板
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor


class FileListPanel(QWidget):
    """文件列表面板（支持拖拽）"""

    # 信号：文件夹拖入
    folder_dropped = pyqtSignal(Path)

    def __init__(self, title: str, side: str):
        """
        Args:
            title: 面板标题
            side: "local" 或 "svn"
        """
        super().__init__()
        self.title = title
        self.side = side
        self.current_path: Path | None = None
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # 标题栏
        title_bar = QWidget()
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title_label)

        # 当前路径显示
        self.path_label = QLabel("拖入文件夹...")
        self.path_label.setStyleSheet("color: #666; font-size: 11px;")
        self.path_label.setWordWrap(True)
        title_layout.addWidget(self.path_label)

        title_layout.addStretch()

        layout.addWidget(title_bar)

        # 文件列表表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["文件名", "路径", "修改时间"])

        # 设置表头
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)

        # 设置选择模式
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # 启用拖拽
        self.table.setAcceptDrops(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

        layout.addWidget(self.table)

        # 设置拖拽事件（需要在整个面板上处理）
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            # 检查是否为文件夹
            urls = event.mimeData().urls()
            for url in urls:
                path = Path(url.toLocalFile())
                if path.is_dir():
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        for url in urls:
            path = Path(url.toLocalFile())
            if path.is_dir():
                self.current_path = path
                self.path_label.setText(str(path))
                self.folder_dropped.emit(path)
                event.acceptProposedAction()
                return
        event.ignore()

    def set_files(self, files: list):
        """设置文件列表"""
        self.table.setRowCount(len(files))

        for row, file_info in enumerate(files):
            # 文件名
            name_item = self.table.item(row, 0)
            if name_item is None:
                name_item = self.create_table_item(file_info.name)
                self.table.setItem(row, 0, name_item)
            else:
                name_item.setText(file_info.name)

            # 相对路径
            rel_path_item = self.table.item(row, 1)
            rel_path = ""
            if self.current_path:
                try:
                    rel_path = str(file_info.relative_to(self.current_path).parent)
                    if rel_path == ".":
                        rel_path = ""
                except ValueError:
                    rel_path = str(file_info.parent)
            if rel_path_item is None:
                rel_path_item = self.create_table_item(rel_path)
                self.table.setItem(row, 1, rel_path_item)
            else:
                rel_path_item.setText(rel_path)

            # 修改时间
            time_item = self.table.item(row, 2)
            time_str = file_info.stat().st_mtime
            from datetime import datetime
            time_display = datetime.fromtimestamp(time_str).strftime("%Y-%m-%d %H:%M:%S")
            if time_item is None:
                time_item = self.create_table_item(time_display)
                self.table.setItem(row, 2, time_item)
            else:
                time_item.setText(time_display)

    def create_table_item(self, text: str):
        """创建表格项"""
        from PyQt6.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(text)
        return item

    def clear_files(self):
        """清空文件列表"""
        self.table.setRowCount(0)