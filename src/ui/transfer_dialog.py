"""
传输预览对话框 - 左右对比显示、自动生成提交信息
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QTableWidget, QHeaderView,
    QTableWidgetItem, QAbstractItemView, QWidget,
    QCheckBox, QMessageBox, QSplitter, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from src.models.file_info import FileStatus


class TransferPreviewDialog(QDialog):
    """传输预览对话框"""

    STATUS_COLORS = {
        FileStatus.MODIFIED: QColor(255, 100, 100),
        FileStatus.NEW_FILE: QColor(255, 150, 100),
        FileStatus.SVN_NEWER: QColor(255, 180, 100),
        FileStatus.SAME: QColor(100, 200, 100),
    }

    def __init__(self, transfer_list: list, local_path: Path, svn_path: Path, parent=None):
        super().__init__(parent)
        self.transfer_list = transfer_list
        self.local_path = local_path
        self.svn_path = svn_path
        self.confirmed_files: list = []
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("传输预览 - 确认变更")
        self.setMinimumSize(480, 380)
        self.resize(520, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # 左右对比区域（标题和路径垂直对齐）
        compare_bar = QWidget()
        compare_layout = QHBoxLayout(compare_bar)
        compare_layout.setContentsMargins(0, 0, 0, 0)

        # 左侧：本地目录标题 + 路径名（垂直排列）
        local_widget = QWidget()
        local_layout = QVBoxLayout(local_widget)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(2)

        local_title = QLabel("本地目录")
        local_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        local_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        local_layout.addWidget(local_title)

        local_path_label = QLabel(self.local_path.name)
        local_path_label.setStyleSheet("color: #333; background: #e8f4e8; padding: 3px 8px;")
        local_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        local_layout.addWidget(local_path_label)

        compare_layout.addWidget(local_widget)

        # 箭头
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #4a90d9;")
        arrow_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        compare_layout.addWidget(arrow_label)

        # 右侧：SVN目录标题 + 路径名（垂直排列）
        svn_widget = QWidget()
        svn_layout = QVBoxLayout(svn_widget)
        svn_layout.setContentsMargins(0, 0, 0, 0)
        svn_layout.setSpacing(2)

        svn_title = QLabel("SVN 目录")
        svn_title.setStyleSheet("font-weight: bold; font-size: 13px;")
        svn_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        svn_layout.addWidget(svn_title)

        svn_path_label = QLabel(self.svn_path.name)
        svn_path_label.setStyleSheet("color: #333; background: #f4e8e8; padding: 3px 8px;")
        svn_path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        svn_layout.addWidget(svn_path_label)

        compare_layout.addWidget(svn_widget)
        compare_layout.addStretch()

        layout.addWidget(compare_bar)

        # 分隔器
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 变更列表表格
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)

        table_label = QLabel("变更文件列表（勾选确认传输）：")
        table_layout.addWidget(table_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["确认", "本地文件", "SVN文件", "状态", "操作"])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(3, 70)
        self.table.setColumnWidth(4, 60)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.populate_table()
        table_layout.addWidget(self.table)
        splitter.addWidget(table_widget)

        # 提交信息编辑区
        commit_widget = QWidget()
        commit_layout = QVBoxLayout(commit_widget)
        commit_layout.setContentsMargins(0, 0, 0, 0)

        commit_label = QLabel("SVN 提交信息（可编辑）：")
        commit_layout.addWidget(commit_label)

        self.commit_edit = QTextEdit()
        self.commit_edit.setPlaceholderText("输入提交说明...")
        self.commit_edit.setMaximumHeight(120)
        self.commit_edit.setText(self.generate_commit_message())
        commit_layout.addWidget(self.commit_edit)

        splitter.addWidget(commit_widget)
        splitter.setSizes([280, 150])
        layout.addWidget(splitter)

        # 统计信息
        self.stats_label = QLabel(self.get_stats_text())
        self.stats_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.stats_label)

        # 按钮
        btn_bar = QWidget()
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.transfer_btn = QPushButton("确认传输")
        self.transfer_btn.setStyleSheet("QPushButton { background: #4a90d9; color: white; padding: 5px 15px; }")
        self.transfer_btn.clicked.connect(self.confirm_transfer)
        btn_layout.addWidget(self.transfer_btn)

        layout.addWidget(btn_bar)

    def populate_table(self):
        """填充变更列表表格"""
        self.table.setRowCount(len(self.transfer_list))

        for row, (file_info, status) in enumerate(self.transfer_list):
            # 确认复选框
            check_item = QTableWidgetItem()
            check_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # 默认只勾选需要传输的文件
            if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE):
                check_item.setCheckState(Qt.CheckState.Checked)
            else:
                check_item.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check_item)

            # 本地文件名（绿色背景）
            local_item = QTableWidgetItem(file_info.name)
            local_item.setToolTip(str(file_info.path))
            local_item.setBackground(QBrush(QColor(230, 244, 230)))  # 浅绿色
            self.table.setItem(row, 1, local_item)

            # SVN文件名（根据状态显示）
            if status == FileStatus.NEW_FILE:
                svn_text = "(不存在)"
                svn_item = QTableWidgetItem(svn_text)
                svn_item.setForeground(QBrush(QColor(150, 150, 150)))  # 灰色
            elif status == FileStatus.MODIFIED:
                svn_text = file_info.name  # SVN有同名文件
                svn_item = QTableWidgetItem(svn_text)
                svn_item.setBackground(QBrush(QColor(244, 230, 230)))  # 浅红色
            else:
                svn_text = file_info.name
                svn_item = QTableWidgetItem(svn_text)
            self.table.setItem(row, 2, svn_item)

            # 状态
            status_text = {
                FileStatus.MODIFIED: "已修改",
                FileStatus.NEW_FILE: "新文件",
                FileStatus.SVN_NEWER: "SVN较新",
                FileStatus.SAME: "相同",
            }.get(status, "未知")
            status_item = QTableWidgetItem(status_text)

            color = self.STATUS_COLORS.get(status)
            if color:
                status_item.setBackground(QBrush(color))
            self.table.setItem(row, 3, status_item)

            # 操作
            action_text = "复制" if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE) else "跳过"
            action_item = QTableWidgetItem(action_text)
            self.table.setItem(row, 4, action_item)

    def generate_commit_message(self) -> str:
        """自动生成提交信息"""
        modified = [f for f, s in self.transfer_list if s == FileStatus.MODIFIED]
        new_files = [f for f, s in self.transfer_list if s == FileStatus.NEW_FILE]

        total = len(modified) + len(new_files)
        if total == 0:
            return "无变更文件需要传输"

        lines = [f"更新 {total} 个文件"]

        if new_files:
            lines.append("\n新增：")
            for f in new_files[:5]:
                lines.append(f"  {f.name}")
            if len(new_files) > 5:
                lines.append(f"  ... 共 {len(new_files)} 个")

        if modified:
            lines.append("\n修改：")
            for f in modified[:5]:
                lines.append(f"  {f.name}")
            if len(modified) > 5:
                lines.append(f"  ... 共 {len(modified)} 个")

        return "\n".join(lines)

    def get_stats_text(self) -> str:
        """获取统计信息"""
        modified = len([f for f, s in self.transfer_list if s == FileStatus.MODIFIED])
        new_files = len([f for f, s in self.transfer_list if s == FileStatus.NEW_FILE])
        same = len([f for f, s in self.transfer_list if s == FileStatus.SAME])
        return f"共 {len(self.transfer_list)} 个文件：修改 {modified}，新增 {new_files}，相同 {same}"

    def confirm_transfer(self):
        """确认传输"""
        self.confirmed_files = []
        for row in range(self.table.rowCount()):
            check_item = self.table.item(row, 0)
            if check_item.checkState() == Qt.CheckState.Checked:
                file_info, status = self.transfer_list[row]
                self.confirmed_files.append((file_info, status))

        if not self.confirmed_files:
            QMessageBox.warning(self, "提示", "请勾选要传输的文件")
            return

        commit_msg = self.commit_edit.toPlainText()
        if not commit_msg or commit_msg == "无变更文件需要传输":
            QMessageBox.warning(self, "提示", "请输入提交信息")
            return

        self.accept()

    def get_confirmed_files(self) -> list:
        return self.confirmed_files

    def get_commit_message(self) -> str:
        return self.commit_edit.toPlainText()