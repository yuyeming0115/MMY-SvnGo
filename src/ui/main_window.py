"""
主窗口 UI - 连接各模块信号
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QFrame, QMessageBox, QApplication, QMenu, QFileDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from src.ui.file_list_panel import FileListPanel
from src.ui.diff_list_panel import DiffListPanel
from src.ui.preview_panel import PreviewPanel
from src.ui.backup_dialog import BackupDialog
from src.ui.transfer_dialog import TransferPreviewDialog
from src.core.file_comparator import FileComparator
from src.core.history_manager import HistoryManager
from src.core.favorite_manager import FavoriteManager
from src.core.svn_manager import SVNManager
from src.models.file_info import FileStatus


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.comparator = FileComparator()
        self.history_manager = HistoryManager()
        self.favorite_manager = FavoriteManager()
        self.svn_manager = SVNManager()
        self._was_inactive = False
        # SVN 模式相关属性
        self.svn_mode = True  # 默认启用 SVN 模式
        self.svn_parent_path: Path | None = None  # SVN 父级目录
        # 加载保存的 SVN 父级目录
        saved_svn_parent = self.history_manager.get_svn_parent_dir()
        if saved_svn_parent and saved_svn_parent.exists():
            self.svn_parent_path = saved_svn_parent
        self.init_ui()
        self.load_last_used()
        # 监听应用激活状态变化
        QApplication.instance().applicationStateChanged.connect(self.on_app_state_changed)

    def on_app_state_changed(self, state):
        """应用状态变化时刷新"""
        if state == Qt.ApplicationState.ApplicationActive:
            if self._was_inactive and (self.local_panel.current_path or self.svn_panel.current_path):
                print("[窗口] 从其他应用切回来，自动刷新")
                # SVN 模式下执行 SVN 更新
                if self.svn_mode and self.svn_panel.current_path:
                    print("[SVN模式] 执行 SVN 更新")
                    self.svn_manager.update(self.svn_panel.current_path)
                self.on_refresh()
            self._was_inactive = False
        elif state == Qt.ApplicationState.ApplicationInactive:
            self._was_inactive = True

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("MMY SvnGo - 文件同步工具")
        self.setMinimumSize(700, 500)
        self.resize(800, 700)

        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 顶部按钮区域
        self.create_top_bar(main_layout)

        # 列表对比区域（三列布局）
        self.create_list_area(main_layout)

        # 预览图区域
        self.create_preview_area(main_layout)

        # 连接信号
        self.connect_signals()

    def create_top_bar(self, parent_layout: QVBoxLayout):
        """创建顶部按钮区域"""
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 手动更新按钮
        self.btn_refresh = QPushButton("手动更新")
        self.btn_refresh.setToolTip("刷新左右两侧文件列表")
        self.btn_refresh.setMinimumWidth(100)
        top_layout.addWidget(self.btn_refresh)

        # 备份按钮
        self.btn_backup = QPushButton("备份")
        self.btn_backup.setToolTip("备份当前 SVN 目录到压缩包")
        self.btn_backup.setMinimumWidth(80)
        top_layout.addWidget(self.btn_backup)

        # 传输按钮
        self.btn_transfer = QPushButton("传输")
        self.btn_transfer.setToolTip("预览并执行文件复制到 SVN 目录")
        self.btn_transfer.setMinimumWidth(80)
        top_layout.addWidget(self.btn_transfer)

        # 分隔
        top_layout.addSpacing(20)

        # 模式切换按钮（默认启用 SVN 模式）
        self.btn_mode = QPushButton("常规模式")
        self.btn_mode.setCheckable(True)
        self.btn_mode.setChecked(True)
        self.btn_mode.setStyleSheet("QPushButton { background: #4a90d9; color: white; }")
        self.btn_mode.setToolTip("切换 SVN 模式/常规模式\nSVN模式：左侧拖入后右侧自动处理")
        self.btn_mode.setMinimumWidth(90)
        self.btn_mode.clicked.connect(self.toggle_mode)
        top_layout.addWidget(self.btn_mode)

        # 分隔
        top_layout.addSpacing(10)

        # 收藏夹按钮（带下拉三角）
        favorites_widget = QWidget()
        favorites_layout = QHBoxLayout(favorites_widget)
        favorites_layout.setContentsMargins(0, 0, 0, 0)
        favorites_layout.setSpacing(0)

        self.btn_favorites = QPushButton("收藏夹")
        self.btn_favorites.setToolTip("预设和历史目录")
        self.btn_favorites.setMinimumWidth(80)
        favorites_layout.addWidget(self.btn_favorites)

        self.btn_favorites_menu = QPushButton("▼")
        self.btn_favorites_menu.setMaximumWidth(25)
        self.btn_favorites_menu.setToolTip("选择历史路径对")
        self.btn_favorites_menu.clicked.connect(self.show_favorites_menu)
        favorites_layout.addWidget(self.btn_favorites_menu)

        top_layout.addWidget(favorites_widget)

        top_layout.addStretch()

        parent_layout.addWidget(top_bar)

        # 更新信息输入区域
        info_bar = QWidget()
        info_layout = QHBoxLayout(info_bar)
        info_layout.setContentsMargins(0, 0, 0, 0)

        info_label = QLabel("更新说明：")
        info_layout.addWidget(info_label)

        self.update_info_edit = QLineEdit()
        self.update_info_edit.setPlaceholderText("输入本次更新的说明（传输时自动填充到 SVN 提交信息）")
        self.update_info_edit.setStyleSheet("QLineEdit { padding: 3px; }")
        info_layout.addWidget(self.update_info_edit)

        parent_layout.addWidget(info_bar)

    def create_list_area(self, parent_layout: QVBoxLayout):
        """创建列表对比区域"""
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：本地文件列表（传入历史管理器）
        self.local_panel = FileListPanel("本地文件", "local", self.history_manager)
        splitter.addWidget(self.local_panel)

        # 中间：差异列表（宽度较窄）
        self.diff_panel = DiffListPanel()
        splitter.addWidget(self.diff_panel)

        # 右侧：SVN 文件列表（传入历史管理器）
        self.svn_panel = FileListPanel("SVN 文件", "svn", self.history_manager)
        splitter.addWidget(self.svn_panel)

        # 设置分割比例（左:中:右 = 40:15:45）
        splitter.setSizes([400, 150, 450])

        parent_layout.addWidget(splitter, stretch=1)

    def create_preview_area(self, parent_layout: QVBoxLayout):
        """创建预览图区域"""
        preview_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧预览
        self.local_preview = PreviewPanel("本地预览")
        preview_splitter.addWidget(self.local_preview)

        # 右侧预览
        self.svn_preview = PreviewPanel("SVN 预览")
        preview_splitter.addWidget(self.svn_preview)

        # 设置分割比例
        preview_splitter.setSizes([550, 550])

        # 预览区域高度固定
        preview_splitter.setMaximumHeight(220)

        parent_layout.addWidget(preview_splitter)

    def connect_signals(self):
        """连接信号"""
        # 左右面板拖入文件夹信号
        self.local_panel.folder_dropped.connect(self.on_local_folder_dropped)
        self.svn_panel.folder_dropped.connect(self.on_svn_folder_dropped)

        # 文件选中信号（使用相对路径同步）
        self.local_panel.file_selected.connect(self.on_local_file_selected)
        self.local_panel.file_selected_relative.connect(self.on_local_file_relative)
        self.svn_panel.file_selected.connect(self.on_svn_file_selected)
        self.svn_panel.file_selected_relative.connect(self.on_svn_file_relative)
        self.diff_panel.file_selected.connect(self.on_diff_file_selected)

        # 按钮点击信号
        self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_backup.clicked.connect(self.on_backup)
        self.btn_transfer.clicked.connect(self.on_transfer)
        self.btn_favorites.clicked.connect(self.on_favorites)

    def load_last_used(self):
        """加载上次使用的文件夹对"""
        last_pair = self.history_manager.get_last_used()
        if last_pair:
            if last_pair.local_path.exists():
                self.local_panel.load_folder(last_pair.local_path)
            if last_pair.svn_path.exists():
                self.svn_panel.load_folder(last_pair.svn_path)
            # 如果两边都有文件，自动对比
            if self.local_panel.get_file_list() and self.svn_panel.get_file_list():
                self.update_diff_list()

    # === 文件选中同步处理 ===

    def on_local_file_selected(self, path: Path):
        """本地文件选中时，更新预览（完整路径）"""
        self.local_preview.load_image(path)

    def on_local_file_relative(self, relative_path: str):
        """本地文件选中时，同步其他列（使用相对路径）"""
        self.svn_panel.select_by_relative_path(relative_path)
        self.diff_panel.select_by_filename(relative_path)
        self.local_panel.scrollToSelectedRow()
        svn_path = self.svn_panel.get_file_path_by_relative(relative_path)
        if svn_path:
            self.svn_preview.load_image(svn_path)

    def on_svn_file_selected(self, path: Path):
        """SVN 文件选中时，更新预览（完整路径）"""
        self.svn_preview.load_image(path)

    def on_svn_file_relative(self, relative_path: str):
        """SVN 文件选中时，同步其他列（使用相对路径）"""
        self.local_panel.select_by_relative_path(relative_path)
        self.diff_panel.select_by_filename(relative_path)
        self.svn_panel.scrollToSelectedRow()
        local_path = self.local_panel.get_file_path_by_relative(relative_path)
        if local_path:
            self.local_preview.load_image(local_path)

    def on_diff_file_selected(self, filename: str):
        """中间列选中时，同步左右两列并更新预览"""
        self.local_panel.select_by_relative_path(filename)
        self.svn_panel.select_by_relative_path(filename)
        self.diff_panel.scrollToSelectedRow()
        local_path = self.local_panel.get_file_path_by_relative(filename)
        svn_path = self.svn_panel.get_file_path_by_relative(filename)
        if local_path:
            self.local_preview.load_image(local_path)
        if svn_path:
            self.svn_preview.load_image(svn_path)

    # === 文件夹拖入处理 ===

    def on_local_folder_dropped(self, path: Path):
        """本地文件夹拖入"""
        print(f"[本地] 拖入: {path}")

        if self.svn_mode and self.svn_parent_path:
            # SVN 模式：自动处理右侧
            folder_name = path.name
            svn_target = self.svn_parent_path / folder_name

            if svn_target.exists() and svn_target.is_dir():
                # 同名文件夹存在，直接进入
                print(f"[SVN模式] 找到同名文件夹: {svn_target}")
                self.svn_panel.load_folder(svn_target)
            else:
                # 同名文件夹不存在，自动新建
                svn_target.mkdir(parents=True, exist_ok=True)
                print(f"[SVN模式] 新建文件夹: {svn_target}")
                self.svn_panel.load_folder(svn_target)

            self.update_diff_list()
            self.save_history()
        else:
            # 常规模式：需要手动拖入右侧
            if self.svn_panel.current_path:
                self.update_diff_list()
                self.save_history()

    def on_svn_folder_dropped(self, path: Path):
        """SVN 文件夹拖入"""
        print(f"[SVN] 拖入: {path}")
        if self.local_panel.current_path:
            self.update_diff_list()
            self.save_history()

    def update_diff_list(self):
        """更新差异列表"""
        local_files = self.local_panel.get_file_list()
        svn_files = self.svn_panel.get_file_list()

        if not local_files or not svn_files:
            return

        # 执行对比
        result = self.comparator.compare(local_files, svn_files)

        # 转换为差异列表格式
        diff_items = []
        for filename, (file_info, status) in result.items():
            diff_items.append((filename, status.value))

        self.diff_panel.set_diff_list(diff_items)

        # 打印统计
        summary = self.comparator.get_status_summary(result)
        print(f"[对比完成] 共 {len(diff_items)} 个文件")
        print(f"  - 已修改: {summary.get('modified', 0)}")
        print(f"  - 相同: {summary.get('same', 0)}")
        print(f"  - SVN较新: {summary.get('svn_newer', 0)}")
        print(f"  - 新文件: {summary.get('new_file', 0)}")

    def save_history(self):
        """保存历史记录"""
        if self.local_panel.current_path and self.svn_panel.current_path:
            self.history_manager.add(
                self.local_panel.current_path,
                self.svn_panel.current_path
            )
            print(f"[历史] 已保存: {self.local_panel.current_path.name} <-> {self.svn_panel.current_path.name}")

    # === 按钮事件处理 ===

    def toggle_mode(self):
        """切换 SVN 模式/常规模式"""
        self.svn_mode = self.btn_mode.isChecked()
        if self.svn_mode:
            self.btn_mode.setText("常规模式")
            self.btn_mode.setStyleSheet("QPushButton { background: #4a90d9; color: white; }")
            print("[模式] 切换到 SVN 模式")
            if not self.svn_parent_path:
                QMessageBox.information(self, "提示", "SVN 模式已启用\n请在收藏夹下拉菜单中设置 SVN 父级目录")
        else:
            self.btn_mode.setText("SVN模式")
            self.btn_mode.setStyleSheet("")
            print("[模式] 切换到常规模式")

    def set_svn_parent_path(self):
        """设置 SVN 父级目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择 SVN 父级目录",
            str(self.svn_parent_path or Path.home())
        )
        if dir_path:
            self.svn_parent_path = Path(dir_path)
            self.history_manager.set_svn_parent_dir(self.svn_parent_path)
            print(f"[SVN] 父级目录设置为: {self.svn_parent_path}")
            QMessageBox.information(self, "设置成功", f"SVN 父级目录已设置为:\n{self.svn_parent_path}")

    def on_refresh(self):
        """手动更新按钮点击"""
        print("[按钮] 手动更新")
        if self.local_panel.current_path:
            self.local_panel.scan_and_display(self.local_panel.current_path)
            print(f"  - 本地列表已刷新: {len(self.local_panel.file_list)} 个文件")
        if self.svn_panel.current_path:
            self.svn_panel.scan_and_display(self.svn_panel.current_path)
            print(f"  - SVN列表已刷新: {len(self.svn_panel.file_list)} 个文件")
        if self.local_panel.file_list and self.svn_panel.file_list:
            self.update_diff_list()

    def on_backup(self):
        """备份按钮点击"""
        print("[按钮] 备份")
        if not self.svn_panel.current_path:
            QMessageBox.warning(self, "提示", "请先拖入 SVN 目录")
            return

        # 打开备份对话框
        dialog = BackupDialog(self.svn_panel.current_path, self.history_manager, self)
        if dialog.exec():
            print(f"[备份] 完成: {dialog.result_path}")

    def on_transfer(self):
        """传输按钮点击"""
        print("[按钮] 传输")
        local_files = self.local_panel.get_file_list()
        svn_files = self.svn_panel.get_file_list()

        if not local_files:
            QMessageBox.warning(self, "提示", "请先拖入本地目录")
            return

        if not self.svn_panel.current_path:
            QMessageBox.warning(self, "提示", "请先拖入 SVN 目录")
            return

        # 如果 SVN 目录是空的，把所有本地文件视为新文件
        if not svn_files:
            print("[传输] SVN 目录为空，所有本地文件视为新文件")
            transfer_list = [(f, FileStatus.NEW_FILE) for f in local_files]
        else:
            # 正常对比
            result = self.comparator.compare(local_files, svn_files)
            transfer_list = [(file_info, status) for filename, (file_info, status) in result.items()
                            if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE)]

        if not transfer_list:
            QMessageBox.information(self, "提示", "没有需要传输的文件（所有文件都已同步）")
            return

        # 打开传输预览对话框（传递更新信息）
        update_info = self.update_info_edit.text().strip()
        dialog = TransferPreviewDialog(
            transfer_list,
            self.local_panel.current_path,
            self.svn_panel.current_path,
            update_info,  # 初始提交信息
            self
        )
        if dialog.exec():
            confirmed_files = dialog.get_confirmed_files()
            commit_msg = dialog.get_commit_message()
            print(f"[传输] 确认传输 {len(confirmed_files)} 个文件")
            self.execute_transfer(confirmed_files, commit_msg)

    def execute_transfer(self, confirmed_files: list, commit_msg: str):
        """执行传输操作"""
        import shutil

        print(f"[执行传输] 开始复制文件...")
        print(f"[执行传输] 本地目录: {self.local_panel.current_path}")
        print(f"[执行传输] SVN目录: {self.svn_panel.current_path}")
        copied_count = 0

        for file_info, status in confirmed_files:
            if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE):
                src_path = file_info.path
                print(f"[执行传输] 源文件路径: {src_path}")

                # 计算目标路径（保持相对路径结构）
                try:
                    rel_path = src_path.relative_to(self.local_panel.current_path)
                    print(f"[执行传输] 相对路径: {rel_path}")
                    dst_path = self.svn_panel.current_path / rel_path
                except ValueError as e:
                    print(f"[执行传输] 相对路径计算失败: {e}")
                    # fallback：保持子目录结构
                    # 找出本地目录名后面的路径部分
                    path_parts = list(src_path.parts)
                    local_parts = list(self.local_panel.current_path.parts)
                    if len(path_parts) > len(local_parts):
                        # 取本地目录后面的部分
                        rel_parts = path_parts[len(local_parts):]
                        dst_path = self.svn_panel.current_path.joinpath(*rel_parts)
                    else:
                        dst_path = self.svn_panel.current_path / src_path.name

                print(f"[执行传输] 目标路径: {dst_path}")

                # 确保目标目录存在
                dst_path.parent.mkdir(parents=True, exist_ok=True)

                # 复制文件
                try:
                    shutil.copy2(src_path, dst_path)
                    copied_count += 1
                    print(f"  - 复制成功: {src_path.name} -> {dst_path}")
                except Exception as e:
                    print(f"  - 复制失败: {src_path.name} - {e}")

        print(f"[执行传输] 复制完成: {copied_count} 个文件")

        # 提交 SVN
        if copied_count > 0:
            QMessageBox.information(
                self,
                "传输完成",
                f"已复制 {copied_count} 个文件到 SVN 目录\n\n请使用 TortoiseSVN 完成提交"
            )
            # 提示用户使用 TortoiseSVN 提交
            self.svn_manager.tortoise_commit(self.svn_panel.current_path, commit_msg)
            # 传输完成后自动刷新列表
            self.on_refresh()

    def on_favorites(self):
        """收藏夹按钮点击"""
        print("[按钮] 收藏夹")
        try:
            favorites = self.favorite_manager.get_all()
            print(f"  - 收藏夹数量: {len(favorites)}")
            for fav in favorites:
                exists = "✓" if fav.path.exists() else "✗"
                print(f"    [{exists}] {fav.name}: {fav.path}")
        except Exception as e:
            print(f"  - 错误: {e}")

    def show_favorites_menu(self):
        """显示收藏夹/历史路径选择菜单"""
        menu = QMenu(self)

        # SVN 模式设置（在顶部显示）
        if self.svn_mode:
            svn_header = menu.addAction("── SVN 模式设置 ──")
            svn_header.setEnabled(False)

            svn_parent_action = menu.addAction("设置 SVN 父级目录")
            svn_parent_action.triggered.connect(self.set_svn_parent_path)

            if self.svn_parent_path:
                current_action = menu.addAction(f"当前: {self.svn_parent_path.name}")
                current_action.setToolTip(str(self.svn_parent_path))
                current_action.setEnabled(False)

            menu.addSeparator()

        # 添加历史路径对
        history = self.history_manager.get_all()
        if history:
            history_header = menu.addAction("── 历史路径对 ──")
            history_header.setEnabled(False)

            for item in history:
                local_exists = "✓" if item.local_path.exists() else "✗"
                svn_exists = "✓" if item.svn_path.exists() else "✗"
                action = menu.addAction(f"📁 {item.local_path.name} [{local_exists}|{svn_exists}]")
                action.setToolTip(f"本地: {item.local_path}\nSVN: {item.svn_path}")
                action.triggered.connect(
                    lambda checked, local=item.local_path, svn=item.svn_path:
                    self.load_folder_pair(local, svn)
                )

        menu.addSeparator()
        clear_action = menu.addAction("清空历史")
        clear_action.triggered.connect(self.clear_history)

        menu.exec(self.btn_favorites_menu.mapToGlobal(self.btn_favorites_menu.rect().bottomLeft()))

    def load_folder_pair(self, local_path: Path, svn_path: Path):
        """加载文件夹对（同时设置本地和SVN路径）"""
        if local_path.exists():
            self.local_panel.load_folder(local_path)
        if svn_path.exists():
            self.svn_panel.load_folder(svn_path)
        if local_path.exists() and svn_path.exists():
            self.update_diff_list()
            self.save_history()

    def clear_history(self):
        """清空历史记录"""
        self.history_manager.clear()
        self.local_panel.clear_files()
        self.svn_panel.clear_files()
        self.diff_panel.clear_diff()
        print("[历史] 已清空")