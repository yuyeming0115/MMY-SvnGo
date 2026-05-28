"""
传输预览对话框 - 子文件夹分组显示、自动生成提交信息
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QWidget, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush

from src.models.file_info import FileStatus


class TransferPreviewDialog(QDialog):
    """传输预览对话框 - 支持子文件夹分组显示"""

    STATUS_COLORS = {
        FileStatus.MODIFIED: QColor(255, 100, 100),
        FileStatus.NEW_FILE: QColor(255, 150, 100),
        FileStatus.SVN_NEWER: QColor(255, 180, 100),
        FileStatus.SAME: QColor(100, 200, 100),
    }

    def __init__(self, transfer_list: list, local_path: Path, svn_path: Path, initial_commit_msg: str = "", parent=None):
        super().__init__(parent)
        self.transfer_list = transfer_list
        self.local_path = local_path
        self.svn_path = svn_path
        self.initial_commit_msg = initial_commit_msg
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

        # 变更列表（树形分组显示）
        tree_widget = QWidget()
        tree_layout = QVBoxLayout(tree_widget)
        tree_layout.setContentsMargins(0, 0, 0, 0)

        tree_label = QLabel("变更文件列表（勾选文件夹或文件确认传输）：")
        tree_layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["文件名", "状态", "数量"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.itemChanged.connect(self.on_tree_item_changed)

        self.populate_tree()
        tree_layout.addWidget(self.tree)
        splitter.addWidget(tree_widget)

        # 提交信息编辑区
        commit_widget = QWidget()
        commit_layout = QVBoxLayout(commit_widget)
        commit_layout.setContentsMargins(0, 0, 0, 0)

        commit_label = QLabel("SVN 提交信息（可编辑）：")
        commit_layout.addWidget(commit_label)

        self.commit_edit = QTextEdit()
        self.commit_edit.setPlaceholderText("输入提交说明...")
        self.commit_edit.setMaximumHeight(120)
        self.commit_edit.setText(self.initial_commit_msg if self.initial_commit_msg else self.generate_commit_message())
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

        # 用于存储子文件夹节点数据
        self.folder_items = {}  # folder_name -> (folder_item, files_list)

    def populate_tree(self):
        """按子文件夹分组填充树形列表"""
        self.tree.blockSignals(True)  # 阻止信号，避免填充时触发

        # 按子文件夹分组
        folder_groups = {}
        for file_info, status in self.transfer_list:
            # 从 relative_path 提取子文件夹名（第一级目录）
            rel_path = file_info.relative_path or file_info.name
            parts = rel_path.replace('\\', '/').split('/')
            if len(parts) > 1:
                folder_name = parts[0]  # 子文件夹名
            else:
                folder_name = "(根目录)"

            if folder_name not in folder_groups:
                folder_groups[folder_name] = []
            folder_groups[folder_name].append((file_info, status))

        # 创建子文件夹节点
        for folder_name, files in folder_groups.items():
            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, f"📁 {folder_name}")

            # 计算文件夹状态统计
            modified_count = len([f for f, s in files if s == FileStatus.MODIFIED])
            new_count = len([f for f, s in files if s == FileStatus.NEW_FILE])
            total_count = len(files)

            status_text = f"修改{modified_count} / 新增{new_count}" if modified_count or new_count else f"共{total_count}"
            folder_item.setText(1, status_text)
            folder_item.setText(2, str(total_count))

            # 检查文件夹是否有更新文件
            has_update = any(s in (FileStatus.MODIFIED, FileStatus.NEW_FILE) for _, s in files)

            folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            folder_item.setCheckState(0, Qt.CheckState.Checked if has_update else Qt.CheckState.Unchecked)

            # 设置文件夹背景色
            if has_update:
                folder_item.setBackground(0, QBrush(QColor(255, 240, 230)))  # 浅橙色
            else:
                folder_item.setBackground(0, QBrush(QColor(230, 244, 230)))  # 浅绿色

            # 存储文件夹数据
            self.folder_items[folder_name] = (folder_item, files)

            # 添加文件子节点
            for file_info, status in files:
                file_item = QTreeWidgetItem(folder_item)
                file_item.setText(0, file_info.name)
                file_item.setToolTip(0, str(file_info.path))

                # 状态文字
                status_text = {
                    FileStatus.MODIFIED: "已修改",
                    FileStatus.NEW_FILE: "新文件",
                    FileStatus.SVN_NEWER: "SVN较新",
                    FileStatus.SAME: "相同",
                }.get(status, "未知")
                file_item.setText(1, status_text)
                file_item.setText(2, "复制" if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE) else "跳过")

                file_item.setFlags(file_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                file_item.setCheckState(0, Qt.CheckState.Checked if has_update else Qt.CheckState.Unchecked)
                file_item.setData(0, Qt.ItemDataRole.UserRole, (file_info, status))  # 存储数据

                # 设置文件背景色
                if status == FileStatus.MODIFIED:
                    file_item.setBackground(0, QBrush(QColor(255, 230, 230)))  # 浅红色
                elif status == FileStatus.NEW_FILE:
                    file_item.setBackground(0, QBrush(QColor(255, 240, 200)))  # 浅黄色
                else:
                    file_item.setBackground(0, QBrush(QColor(230, 244, 230)))  # 浅绿色

        self.tree.expandAll()
        self.tree.blockSignals(False)

    def on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """树形项变化时处理复选框联动"""
        if column != 0:  # 只处理第一列（复选框列）
            return

        self.tree.blockSignals(True)

        check_state = item.checkState(0)

        # 如果是文件夹节点，同步子文件
        if item.parent() is None:  # 顶级节点（文件夹）
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, check_state)
        else:  # 文件节点，更新父文件夹状态
            parent = item.parent()
            if parent:
                # 计算父文件夹下所有子文件的勾选状态
                checked_count = 0
                for i in range(parent.childCount()):
                    if parent.child(i).checkState(0) == Qt.CheckState.Checked:
                        checked_count += 1

                total_count = parent.childCount()
                if checked_count == 0:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
                elif checked_count == total_count:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                else:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

        self.tree.blockSignals(False)

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

        # 从树形控件中获取勾选的文件
        for i in range(self.tree.topLevelItemCount()):
            folder_item = self.tree.topLevelItem(i)
            for j in range(folder_item.childCount()):
                file_item = folder_item.child(j)
                if file_item.checkState(0) == Qt.CheckState.Checked:
                    # 获取存储的数据
                    data = file_item.data(0, Qt.ItemDataRole.UserRole)
                    if data:
                        file_info, status = data
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