"""
传输预览对话框 - 子文件夹分组显示、自动生成提交信息
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QTreeWidget, QTreeWidgetItem,
    QWidget, QMessageBox, QSplitter, QScrollArea, QFrame
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

    # 按钮样式
    BUTTON_SELECTED_STYLE = "QPushButton { background: #4a90d9; color: white; padding: 5px 10px; border-radius: 3px; }"
    BUTTON_NORMAL_STYLE = "QPushButton { background: #e0e0e0; color: #333; padding: 5px 10px; border-radius: 3px; }"

    def __init__(self, transfer_list: list, local_path: Path, svn_path: Path, initial_commit_msg: str = "", history_manager=None, parent=None):
        super().__init__(parent)
        self.transfer_list = transfer_list
        self.local_path = local_path
        self.svn_path = svn_path
        self.initial_commit_msg = initial_commit_msg
        self.history_manager = history_manager
        self.confirmed_files: list = []
        self.folder_items = {}  # 用于存储子文件夹节点数据
        self.folder_buttons = {}  # 存储子文件夹按钮和选中状态
        self.folder_groups = {}  # 按子文件夹分组的文件数据
        self.folder_hierarchy = {}  # 文件夹层级结构 {一级: {二级: [文件]}}
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("传输预览 - 确认变更")
        self.setMinimumSize(500, 650)

        # 加载保存的对话框尺寸
        if self.history_manager:
            saved_size = self.history_manager.get_transfer_dialog_size()
            self.resize(saved_size[0], saved_size[1])
        else:
            self.resize(500, 650)

        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(10, 8, 10, 8)

        # 左右对比区域（紧凑显示）
        compare_bar = QWidget()
        compare_bar.setMaximumHeight(35)
        compare_layout = QHBoxLayout(compare_bar)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(5)

        local_label = QLabel(f"本地: {self.local_path.name}")
        local_label.setStyleSheet("color: #333; background: #e8f4e8; padding: 2px 6px; border-radius: 2px;")
        compare_layout.addWidget(local_label)

        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #4a90d9;")
        compare_layout.addWidget(arrow_label)

        svn_label = QLabel(f"SVN: {self.svn_path.name}")
        svn_label.setStyleSheet("color: #333; background: #f4e8e8; padding: 2px 6px; border-radius: 2px;")
        compare_layout.addWidget(svn_label)

        compare_layout.addStretch()
        layout.addWidget(compare_bar)

        # 子文件夹按钮区域（自适应高度显示全部按钮）
        folder_hint = QLabel("点击切换传输状态（高亮=传输，常规=不传输）：")
        folder_hint.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(folder_hint)

        # 按钮容器（直接显示，自适应高度）
        self.button_container = QWidget()
        self.button_container.setMinimumHeight(250)
        self.button_container.setStyleSheet("QWidget { background: #fafafa; border: 1px solid #ddd; }")
        self.button_row_layout = QHBoxLayout(self.button_container)
        self.button_row_layout.setSpacing(12)
        self.button_row_layout.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(self.button_container)  # 按钮区域自适应高度

        # 文件详情列表（固定高度200px）
        tree_label = QLabel("文件详情：")
        tree_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(tree_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["文件名", "状态", "数量"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setAnimated(True)
        self.tree.setFixedHeight(200)

        self.populate_tree()
        layout.addWidget(self.tree)

        # 提交信息编辑区（紧凑）
        commit_label = QLabel("SVN 提交信息：")
        commit_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(commit_label)

        self.commit_edit = QTextEdit()
        self.commit_edit.setPlaceholderText("输入提交说明...")
        self.commit_edit.setMaximumHeight(80)
        self.commit_edit.setText(self.initial_commit_msg if self.initial_commit_msg else self.generate_commit_message())
        layout.addWidget(self.commit_edit)

        # 统计信息（紧凑）
        self.stats_label = QLabel(self.get_stats_text())
        self.stats_label.setStyleSheet("color: #555; font-size: 11px;")
        layout.addWidget(self.stats_label)

        # 按钮（紧凑）
        btn_bar = QWidget()
        btn_bar.setMaximumHeight(30)
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.transfer_btn = QPushButton("确认传输")
        self.transfer_btn.setStyleSheet("QPushButton { background: #4a90d9; color: white; padding: 4px 12px; }")
        self.transfer_btn.clicked.connect(self.confirm_transfer)
        btn_layout.addWidget(self.transfer_btn)

        layout.addWidget(btn_bar)

    def populate_tree(self):
        """按子文件夹分组填充树形列表，同时创建层级按钮"""
        # 先按子文件夹分组，并解析层级结构
        for file_info, status in self.transfer_list:
            rel_path = file_info.relative_path or file_info.name
            parts = rel_path.replace('\\', '/').split('/')

            if len(parts) > 1:
                folder_name = '/'.join(parts[:-1])
                # 解析一级和二级子文件夹
                if len(parts) >= 3:
                    # 有二级子文件夹：parts[0]是一级，parts[1]是二级
                    level1 = parts[0]
                    level2 = parts[1]
                    full_level2 = f"{level1}/{level2}"
                else:
                    # 只有一级子文件夹
                    level1 = parts[0]
                    level2 = None
                    full_level2 = None

                # 存储层级结构
                if level1 not in self.folder_hierarchy:
                    self.folder_hierarchy[level1] = {}
                if level2:
                    if full_level2 not in self.folder_hierarchy[level1]:
                        self.folder_hierarchy[level1][full_level2] = []
                    self.folder_hierarchy[level1][full_level2].append((file_info, status))
                else:
                    # 一级目录下的直接文件
                    if folder_name not in self.folder_hierarchy[level1]:
                        self.folder_hierarchy[level1][folder_name] = []
                    self.folder_hierarchy[level1][folder_name].append((file_info, status))
            else:
                folder_name = "(根目录)"
                if "(根目录)" not in self.folder_hierarchy:
                    self.folder_hierarchy["(根目录)"] = {}
                if "(根目录)" not in self.folder_hierarchy["(根目录)"]:
                    self.folder_hierarchy["(根目录)"]["(根目录)"] = []
                self.folder_hierarchy["(根目录)"]["(根目录)"].append((file_info, status))

            # 同时存储到 folder_groups（用于树形列表）
            if folder_name not in self.folder_groups:
                self.folder_groups[folder_name] = []
            self.folder_groups[folder_name].append((file_info, status))

        # 创建层级按钮布局
        for level1, level2_dict in self.folder_hierarchy.items():
            # 创建一列（包含一级按钮 + 二级按钮列表）
            column_widget = QWidget()
            column_layout = QVBoxLayout(column_widget)
            column_layout.setSpacing(4)
            column_layout.setContentsMargins(0, 0, 0, 0)

            # 一级按钮（汇总所有二级文件夹的文件）
            level1_files = []
            for level2_path, files in level2_dict.items():
                level1_files.extend(files)
            level1_has_change = any(s in (FileStatus.MODIFIED, FileStatus.NEW_FILE) for _, s in level1_files)

            level1_btn = QPushButton(f"{level1} ({len(level1_files)})")
            level1_btn.setToolTip(f"{level1}\n包含 {len(level1_files)} 个文件")
            level1_btn.clicked.connect(lambda checked, l1=level1: self.toggle_level1_folder(l1))

            self.folder_buttons[level1] = {'button': level1_btn, 'selected': level1_has_change, 'level': 1}
            if level1_has_change:
                level1_btn.setStyleSheet(self.BUTTON_SELECTED_STYLE)
            else:
                level1_btn.setStyleSheet(self.BUTTON_NORMAL_STYLE)

            column_layout.addWidget(level1_btn)

            # 二级按钮列表（竖向排列）
            for level2_path, files in level2_dict.items():
                level2_has_change = any(s in (FileStatus.MODIFIED, FileStatus.NEW_FILE) for _, s in files)

                # 显示简短的二级名称（只取最后一级）
                level2_display = level2_path.split('/')[-1] if '/' in level2_path else level2_path

                level2_btn = QPushButton(f"  {level2_display} ({len(files)})")
                level2_btn.setToolTip(f"{level2_path}\n包含 {len(files)} 个文件")
                level2_btn.clicked.connect(lambda checked, l2=level2_path: self.toggle_folder_button(l2))

                self.folder_buttons[level2_path] = {'button': level2_btn, 'selected': level2_has_change, 'level': 2, 'parent': level1}
                if level2_has_change:
                    level2_btn.setStyleSheet(self.BUTTON_SELECTED_STYLE)
                else:
                    level2_btn.setStyleSheet(self.BUTTON_NORMAL_STYLE)

                column_layout.addWidget(level2_btn)

            column_layout.addStretch()
            self.button_row_layout.addWidget(column_widget)

        self.button_row_layout.addStretch()

        # 填充树形列表（不使用勾选框，仅展示详情）
        for folder_name, files in self.folder_groups.items():
            # 创建文件夹节点
            folder_item = QTreeWidgetItem(self.tree)
            folder_item.setText(0, f"📁 {folder_name}")

            # 计算状态统计
            modified_count = len([f for f, s in files if s == FileStatus.MODIFIED])
            new_count = len([f for f, s in files if s == FileStatus.NEW_FILE])
            same_count = len([f for f, s in files if s == FileStatus.SAME])
            svn_newer_count = len([f for f, s in files if s == FileStatus.SVN_NEWER])
            total_count = len(files)

            status_text = f"修改{modified_count} / 新增{new_count}" if modified_count or new_count else f"共{total_count}"
            folder_item.setText(1, status_text)
            folder_item.setText(2, str(total_count))

            # 文件夹背景色：有变更=浅橙色，无变更=浅绿色
            has_change = modified_count or new_count
            if has_change:
                folder_item.setBackground(0, QBrush(QColor(255, 240, 230)))
            else:
                folder_item.setBackground(0, QBrush(QColor(230, 244, 230)))

            # 存储文件夹节点引用
            self.folder_items[folder_name] = folder_item

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

                # 操作提示
                action_text = "传输" if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE) else "跳过"
                file_item.setText(2, action_text)

                # 文件背景色
                if status == FileStatus.MODIFIED:
                    file_item.setBackground(0, QBrush(QColor(255, 230, 230)))
                elif status == FileStatus.NEW_FILE:
                    file_item.setBackground(0, QBrush(QColor(255, 240, 200)))
                elif status == FileStatus.SVN_NEWER:
                    file_item.setBackground(0, QBrush(QColor(255, 245, 220)))
                else:
                    file_item.setBackground(0, QBrush(QColor(230, 244, 230)))

                # 存储文件数据（用于确认传输时获取）
                file_item.setData(0, Qt.ItemDataRole.UserRole, (file_info, status, folder_name))

        self.tree.expandAll()

    def toggle_level1_folder(self, level1: str):
        """切换一级文件夹及其所有二级文件夹的选中状态"""
        if level1 not in self.folder_buttons:
            return

        btn_info = self.folder_buttons[level1]
        new_selected = not btn_info['selected']
        btn_info['selected'] = new_selected

        # 更新一级按钮样式
        if new_selected:
            btn_info['button'].setStyleSheet(self.BUTTON_SELECTED_STYLE)
        else:
            btn_info['button'].setStyleSheet(self.BUTTON_NORMAL_STYLE)

        # 同步更新所有二级按钮
        for key, info in self.folder_buttons.items():
            if info.get('level') == 2 and info.get('parent') == level1:
                info['selected'] = new_selected
                if new_selected:
                    info['button'].setStyleSheet(self.BUTTON_SELECTED_STYLE)
                else:
                    info['button'].setStyleSheet(self.BUTTON_NORMAL_STYLE)

        # 更新统计信息
        self.stats_label.setText(self.get_stats_text())

    def toggle_folder_button(self, folder_name: str):
        """切换二级子文件夹按钮的选中状态"""
        if folder_name not in self.folder_buttons:
            return

        btn_info = self.folder_buttons[folder_name]
        btn_info['selected'] = not btn_info['selected']

        # 更新按钮样式
        if btn_info['selected']:
            btn_info['button'].setStyleSheet(self.BUTTON_SELECTED_STYLE)
        else:
            btn_info['button'].setStyleSheet(self.BUTTON_NORMAL_STYLE)

        # 同步更新一级按钮状态（如果所有二级都选中/取消）
        parent_level1 = btn_info.get('parent')
        if parent_level1 and parent_level1 in self.folder_buttons:
            # 检查该一级下所有二级的状态
            all_selected = True
            any_selected = False
            for key, info in self.folder_buttons.items():
                if info.get('level') == 2 and info.get('parent') == parent_level1:
                    if info['selected']:
                        any_selected = True
                    else:
                        all_selected = False

            parent_btn = self.folder_buttons[parent_level1]
            parent_btn['selected'] = all_selected
            if all_selected:
                parent_btn['button'].setStyleSheet(self.BUTTON_SELECTED_STYLE)
            elif any_selected:
                # 部分选中：使用不同样式或保持选中状态
                parent_btn['button'].setStyleSheet(self.BUTTON_SELECTED_STYLE)
            else:
                parent_btn['button'].setStyleSheet(self.BUTTON_NORMAL_STYLE)

        # 更新统计信息
        self.stats_label.setText(self.get_stats_text())

    def generate_commit_message(self) -> str:
        """自动生成提交信息"""
        # 只统计选中文件夹中的变更文件
        modified = []
        new_files = []

        for level1, level2_dict in self.folder_hierarchy.items():
            for level2_path, files in level2_dict.items():
                if level2_path in self.folder_buttons and self.folder_buttons[level2_path]['selected']:
                    for f, s in files:
                        if s == FileStatus.MODIFIED:
                            modified.append(f)
                        elif s == FileStatus.NEW_FILE:
                            new_files.append(f)

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
        """获取统计信息（只统计选中的文件夹）"""
        total_selected = 0
        modified_selected = 0
        new_selected = 0
        same_selected = 0

        # 遍历层级结构，统计选中文件夹的文件
        for level1, level2_dict in self.folder_hierarchy.items():
            for level2_path, files in level2_dict.items():
                # 检查二级文件夹是否选中
                if level2_path in self.folder_buttons and self.folder_buttons[level2_path]['selected']:
                    for f, s in files:
                        total_selected += 1
                        if s == FileStatus.MODIFIED:
                            modified_selected += 1
                        elif s == FileStatus.NEW_FILE:
                            new_selected += 1
                        elif s == FileStatus.SAME:
                            same_selected += 1

        return f"选中 {total_selected} 个文件：修改 {modified_selected}，新增 {new_selected}，相同 {same_selected}"

    def confirm_transfer(self):
        """确认传输"""
        self.confirmed_files = []

        # 根据按钮选中状态收集要传输的文件
        for level1, level2_dict in self.folder_hierarchy.items():
            for level2_path, files in level2_dict.items():
                # 检查二级文件夹是否选中
                if level2_path in self.folder_buttons and self.folder_buttons[level2_path]['selected']:
                    for file_info, status in files:
                        # 只传输修改和新文件
                        if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE):
                            self.confirmed_files.append((file_info, status))

        if not self.confirmed_files:
            QMessageBox.warning(self, "提示", "请选中要传输的文件夹（高亮状态）")
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

    def closeEvent(self, event):
        """对话框关闭时保存尺寸"""
        if self.history_manager:
            size = self.size()
            self.history_manager.set_transfer_dialog_size(size.width(), size.height())
            print(f"[传输预览] 保存尺寸: {size.width()}x{size.height()}")
        event.accept()