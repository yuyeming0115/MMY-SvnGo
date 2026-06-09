"""
主窗口 UI - 连接各模块信号
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QFrame, QMessageBox, QApplication, QMenu, QFileDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

from src.ui.file_list_panel import FileListPanel
from src.ui.diff_list_panel import DiffListPanel
from src.ui.preview_panel import PreviewPanel
from src.ui.backup_dialog import BackupDialog
from src.ui.transfer_dialog import TransferPreviewDialog
from src.core.file_comparator import FileComparator
from src.core.file_scanner import FileScanner
from src.core.history_manager import HistoryManager
from src.core.favorite_manager import FavoriteManager
from src.core.svn_manager import SVNManager
from src.models.file_info import FileStatus


class RefreshWorker(QThread):
    """后台刷新任务：可选 SVN 更新后扫描左右目录。"""

    status_changed = pyqtSignal(str)
    result_ready = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, local_path, svn_path, update_svn: bool = False):
        super().__init__()
        self.local_path = str(local_path) if local_path else ""
        self.svn_path = str(svn_path) if svn_path else ""
        self.update_svn = update_svn
        self.scanner = FileScanner()
        self.svn_manager = SVNManager()

    def run(self):
        try:
            result = {
                "local_path": self.local_path,
                "svn_path": self.svn_path,
                "local_files": None,
                "svn_files": None,
                "svn_updated": None,
            }

            if self.update_svn and self.svn_path:
                self.status_changed.emit("正在后台更新 SVN...")
                result["svn_updated"] = self.svn_manager.update(self.svn_path, silent=True)

            if self.local_path:
                self.status_changed.emit("正在扫描本地目录...")
                result["local_files"] = self.scanner.scan_folder(self.local_path)

            if self.svn_path:
                self.status_changed.emit("正在扫描 SVN 目录...")
                result["svn_files"] = self.scanner.scan_folder(self.svn_path)

            self.result_ready.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class TransferWorker(QThread):
    """后台复制传输任务。"""

    status_changed = pyqtSignal(str)
    result_ready = pyqtSignal(object)

    def __init__(self, confirmed_files: list, local_root, svn_root):
        super().__init__()
        self.confirmed_files = confirmed_files
        self.local_root = Path(str(local_root))
        self.svn_root = Path(str(svn_root))

    def run(self):
        import shutil

        copied_count = 0
        copied_paths = []
        new_paths = []
        failures = []

        for index, (file_info, status) in enumerate(self.confirmed_files, start=1):
            if status not in (FileStatus.MODIFIED, FileStatus.NEW_FILE):
                continue

            src_path_str = file_info.get_path_str() if hasattr(file_info, 'get_path_str') else str(file_info.path)
            src_path = Path(src_path_str)
            rel_path = Path(file_info.relative_path or src_path.name)

            try:
                rel_path = src_path.relative_to(self.local_root)
            except ValueError:
                pass

            dst_path = self.svn_root / rel_path
            self.status_changed.emit(f"正在复制 {index}/{len(self.confirmed_files)}：{src_path.name}")

            try:
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path_str, dst_path)
                copied_count += 1
                copied_paths.append(dst_path)
                if status == FileStatus.NEW_FILE:
                    new_paths.append(dst_path)
            except Exception as e:
                failures.append(f"{src_path.name}: {e}")

        self.result_ready.emit({
            "copied_count": copied_count,
            "copied_paths": copied_paths,
            "new_paths": new_paths,
            "failures": failures,
        })


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.comparator = FileComparator()
        self.history_manager = HistoryManager()
        self.favorite_manager = FavoriteManager()
        self.svn_manager = SVNManager()
        self._was_inactive = False
        self.refresh_worker = None
        self.transfer_worker = None
        self.last_comparison_result = {}
        self.pending_commit_msg = ""
        # SVN 模式相关属性
        self.svn_mode = True  # 默认启用 SVN 模式
        self.svn_parent_path: Path | None = None  # SVN 父级目录
        # 加载当前 SVN 父级目录
        saved_svn_parent = self.history_manager.get_current_svn_parent_dir()
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
                update_svn = self.svn_mode and bool(self.svn_panel.current_path)
                self.start_refresh(update_svn=update_svn)
            self._was_inactive = False
        elif state == Qt.ApplicationState.ApplicationInactive:
            self._was_inactive = True

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("MMY SvnGo - 文件同步工具")
        self.setMinimumSize(700, 700)

        # 加载保存的窗口尺寸
        saved_size = self.history_manager.get_main_window_size()
        self.resize(saved_size[0], saved_size[1])

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
        self.update_workflow_status()

    def create_top_bar(self, parent_layout: QVBoxLayout):
        """创建顶部按钮区域"""
        top_bar = QWidget()
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        # 按钮通用样式（方形按钮，带边框）
        button_style = """
            QPushButton {
                min-height: 32px;
                padding: 6px 12px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 13px;
                background: #f5f5f5;
            }
            QPushButton:hover {
                background: #e8e8e8;
                border: 1px solid #999;
            }
            QPushButton:pressed {
                background: #ddd;
            }
        """

        # 手动更新按钮
        self.btn_refresh = QPushButton("手动更新")
        self.btn_refresh.setToolTip("刷新左右两侧文件列表")
        self.btn_refresh.setStyleSheet(button_style)
        top_layout.addWidget(self.btn_refresh)

        # 备份按钮
        self.btn_backup = QPushButton("备份")
        self.btn_backup.setToolTip("备份当前 SVN 目录到压缩包")
        self.btn_backup.setStyleSheet(button_style)
        top_layout.addWidget(self.btn_backup)

        # 传输按钮
        self.btn_transfer = QPushButton("传输")
        self.btn_transfer.setToolTip("预览并执行文件复制到 SVN 目录")
        self.btn_transfer.setStyleSheet(button_style)
        top_layout.addWidget(self.btn_transfer)

        # 分隔
        top_layout.addSpacing(15)

        # 路径对按钮（历史路径对的快速加载）
        self.btn_path_pairs = QPushButton("路径对")
        self.btn_path_pairs.setToolTip("选择历史路径对快速加载")
        self.btn_path_pairs.setStyleSheet(button_style)
        self.btn_path_pairs.clicked.connect(self.show_path_pairs_menu)
        top_layout.addWidget(self.btn_path_pairs)

        # SVN目录按钮（管理SVN父级目录）
        self.btn_svn_dirs = QPushButton("SVN目录")
        self.btn_svn_dirs.setToolTip("管理 SVN 父级目录列表")
        self.btn_svn_dirs.setStyleSheet(button_style)
        self.btn_svn_dirs.clicked.connect(self.show_svn_dirs_menu)
        top_layout.addWidget(self.btn_svn_dirs)

        # 分隔后，SVN模式按钮放最右边
        top_layout.addStretch()

        # 模式切换按钮（默认启用 SVN 模式）
        self.btn_mode = QPushButton("SVN模式")
        self.btn_mode.setCheckable(True)
        self.btn_mode.setChecked(True)
        self.btn_mode.setStyleSheet("""
            QPushButton {
                min-height: 32px;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 13px;
                background: #4a90d9;
                color: white;
                border: 1px solid #3a7ab9;
            }
            QPushButton:hover {
                background: #3a7ab9;
            }
        """)
        self.btn_mode.setToolTip("切换 SVN 模式/常规模式\nSVN模式：左侧拖入后右侧自动处理")
        self.btn_mode.clicked.connect(self.toggle_mode)
        top_layout.addWidget(self.btn_mode)

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

        # 工作流状态区域
        workflow_bar = QWidget()
        workflow_layout = QHBoxLayout(workflow_bar)
        workflow_layout.setContentsMargins(0, 0, 0, 0)
        workflow_layout.setSpacing(8)

        self.workflow_status_label = QLabel("")
        self.workflow_status_label.setStyleSheet("color: #555; font-size: 12px; padding: 3px;")
        workflow_layout.addWidget(self.workflow_status_label, stretch=1)

        self.btn_setup_svn_parent = QPushButton("设置 SVN 父级目录")
        self.btn_setup_svn_parent.setStyleSheet(button_style)
        self.btn_setup_svn_parent.clicked.connect(self.set_svn_parent_path)
        workflow_layout.addWidget(self.btn_setup_svn_parent)

        parent_layout.addWidget(workflow_bar)

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
        preview_splitter.setSizes([400, 400])

        # 预览区域高度增加（接近方形）
        preview_splitter.setMinimumHeight(220)
        preview_splitter.setMaximumHeight(280)

        parent_layout.addWidget(preview_splitter, stretch=1)  # 添加 stretch 让预览区域有更多空间

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

        # 预览面板请求全局边界框信号
        self.local_preview.request_global_bbox.connect(self.on_local_unify_request)
        self.svn_preview.request_global_bbox.connect(self.on_svn_unify_request)

        # 按钮点击信号
        self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_backup.clicked.connect(self.on_backup)
        self.btn_transfer.clicked.connect(self.on_transfer)

    def set_busy(self, busy: bool, message: str = ""):
        """设置主流程忙碌状态。"""
        self.btn_refresh.setEnabled(not busy)
        self.btn_transfer.setEnabled(not busy)
        self.btn_backup.setEnabled(not busy)
        self.btn_path_pairs.setEnabled(not busy)
        self.btn_svn_dirs.setEnabled(not busy)
        self.btn_mode.setEnabled(not busy)
        self.btn_setup_svn_parent.setEnabled(not busy)
        if message:
            self.set_workflow_status(message)

    def set_workflow_status(self, message: str):
        """更新顶部工作流状态提示。"""
        if hasattr(self, "workflow_status_label"):
            self.workflow_status_label.setText(message)

    def update_workflow_status(self):
        """根据当前路径和模式刷新工作流提示。"""
        if not hasattr(self, "workflow_status_label"):
            return

        needs_svn_parent = self.svn_mode and not self.svn_parent_path
        self.btn_setup_svn_parent.setVisible(needs_svn_parent)

        if needs_svn_parent:
            self.set_workflow_status("SVN 模式：请先设置 SVN 父级目录，然后拖入本地文件夹。")
        elif not self.local_panel.current_path:
            self.set_workflow_status("准备就绪：拖入本地文件夹开始对比。")
        elif self.svn_mode and not self.svn_panel.current_path:
            self.set_workflow_status("等待 SVN 目录：将自动匹配同名目录，或从 SVN目录 手动选择。")
        elif self.last_comparison_result:
            summary = self.comparator.get_status_summary(self.last_comparison_result)
            modified = summary.get(FileStatus.MODIFIED, 0)
            new_file = summary.get(FileStatus.NEW_FILE, 0)
            risk = summary.get(FileStatus.SVN_NEWER, 0)
            self.set_workflow_status(f"已对比：待传输 {modified + new_file} 个，风险 {risk} 个。")
        else:
            self.set_workflow_status("路径已就绪：点击手动更新或选择文件查看预览。")

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
            else:
                self.update_workflow_status()
        else:
            self.update_workflow_status()

    # === 文件选中同步处理 ===

    def on_local_file_selected(self, path):
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

    def on_svn_file_selected(self, path):
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

    # === 统一裁剪请求处理 ===

    def on_local_unify_request(self):
        """本地预览请求计算全局边界框"""
        print("[统一裁剪] 计算本地全局边界框...")
        bbox = self.local_panel.compute_global_bbox_async()
        if bbox:
            self.local_preview.set_global_bbox(bbox)
            # 更新状态提示
            self.local_preview.btn_unify.setText(f"统一({bbox[2]-bbox[0]}x{bbox[3]-bbox[1]})")

    def on_svn_unify_request(self):
        """SVN预览请求计算全局边界框"""
        print("[统一裁剪] 计算 SVN 全局边界框...")
        bbox = self.svn_panel.compute_global_bbox_async()
        if bbox:
            self.svn_preview.set_global_bbox(bbox)
            self.svn_preview.btn_unify.setText(f"统一({bbox[2]-bbox[0]}x{bbox[3]-bbox[1]})")

    # === 文件夹拖入处理 ===

    def on_local_folder_dropped(self, path):
        """本地文件夹拖入"""
        # 转换为字符串避免 Path 递归
        if isinstance(path, Path):
            try:
                path_str = str(path)
            except RecursionError:
                print(f"[本地] Path转字符串递归错误")
                return
        else:
            path_str = path

        print(f"[本地] 拖入: {path_str}")

        if self.svn_mode and self.svn_parent_path:
            # SVN 模式：自动处理右侧
            # 从字符串直接提取文件夹名
            path_normalized = path_str.replace("\\", "/").rstrip("/")
            folder_name = path_normalized.split("/")[-1] if path_normalized else ""
            svn_target = self.svn_parent_path / folder_name

            try:
                svn_exists = svn_target.exists() and svn_target.is_dir()
            except RecursionError:
                print(f"[SVN模式] 检查目标路径递归错误: {svn_target}")
                svn_exists = False

            if svn_exists:
                # 同名文件夹存在，直接进入
                print(f"[SVN模式] 找到同名文件夹: {svn_target}")
                try:
                    self.svn_panel.load_folder(str(svn_target))
                except RecursionError:
                    print(f"[SVN模式] 加载目标路径递归错误")
                    return
            else:
                # 同名文件夹不存在，自动新建
                try:
                    svn_target.mkdir(parents=True, exist_ok=True)
                    print(f"[SVN模式] 新建文件夹: {svn_target}")
                    self.svn_panel.load_folder(str(svn_target))
                except Exception as e:
                    print(f"[SVN模式] 新建文件夹失败: {e}")
                    return

            self.update_diff_list()
            self.save_history()
        else:
            if self.svn_mode and not self.svn_parent_path:
                self.update_workflow_status()
                QMessageBox.information(
                    self,
                    "需要设置 SVN 父级目录",
                    "SVN 模式下请先设置 SVN 父级目录。\n设置后再次拖入本地文件夹，会自动匹配或创建右侧同名目录。"
                )
                return
            # 常规模式：需要手动拖入右侧
            if self.svn_panel.current_path:
                self.update_diff_list()
                self.save_history()

    def on_svn_folder_dropped(self, path):
        """SVN 文件夹拖入"""
        try:
            # 转换为字符串避免 Path 递归
            if isinstance(path, Path):
                try:
                    path_str = str(path)
                except RecursionError:
                    print(f"[SVN] Path转字符串递归错误，跳过")
                    return
            else:
                path_str = path

            print(f"[SVN] 拖入: {path_str}")

            # 检查是否是循环路径（最后两个部分相同）
            path_normalized = path_str.replace("\\", "/").rstrip("/")
            parts = path_normalized.split("/")
            if len(parts) >= 2 and parts[-1] == parts[-2]:
                print(f"[SVN] 检测到循环路径，跳过")
                return

            # 检查是否是父级目录（包含多个子文件夹）
            try:
                subdirs = [d for d in os.listdir(path_str)
                           if os.path.isdir(os.path.join(path_str, d)) and not d.startswith(".")]
            except Exception as e:
                print(f"[SVN] 读取目录失败: {e}")
                subdirs = []

            if self.svn_mode and len(subdirs) > 1:
                # SVN 模式下，拖入父级目录时只设置路径不扫描
                print(f"[SVN] 检测到父级目录（包含 {len(subdirs)} 个子文件夹），延迟扫描")
                self.svn_parent_path = Path(path_str)
                self.history_manager.add_svn_parent_dir(Path(path_str))
                self.svn_panel.set_path_only(path_str)
                self.update_workflow_status()
            else:
                # 单个子文件夹或常规模式，直接扫描
                self.svn_panel.load_folder(path_str)
                if self.local_panel.current_path:
                    self.update_diff_list()
                    self.save_history()
                else:
                    self.update_workflow_status()
        except RecursionError:
            print(f"[SVN] 递归错误，跳过")
        except Exception as e:
            print(f"[SVN] 错误: {e}")

    def update_diff_list(self):
        """更新差异列表"""
        local_files = self.local_panel.get_file_list()
        svn_files = self.svn_panel.get_file_list()

        if not local_files:
            self.diff_panel.clear_diff()
            self.last_comparison_result = {}
            self.update_workflow_status()
            return

        # 执行对比
        result = self.comparator.compare(local_files, svn_files)
        self.last_comparison_result = result

        # 转换为差异列表格式
        diff_items = []
        for filename, (file_info, status) in result.items():
            diff_items.append((filename, status.value))

        self.diff_panel.set_diff_list(diff_items)
        self.update_workflow_status()

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
            local_path = Path(self.local_panel.current_path)
            svn_path = Path(self.svn_panel.current_path)
            self.history_manager.add(local_path, svn_path)
            print(f"[历史] 已保存: {local_path.name} <-> {svn_path.name}")

    # === 按钮事件处理 ===

    def toggle_mode(self):
        """切换 SVN 模式/常规模式"""
        self.svn_mode = self.btn_mode.isChecked()
        if self.svn_mode:
            # SVN 模式激活：按钮显示"SVN模式" + 蓝色高亮
            self.btn_mode.setText("SVN模式")
            self.btn_mode.setStyleSheet("""
                QPushButton {
                    min-height: 32px;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 13px;
                    background: #4a90d9;
                    color: white;
                    border: 1px solid #3a7ab9;
                }
                QPushButton:hover {
                    background: #3a7ab9;
                }
            """)
            print("[模式] 切换到 SVN 模式")
            if not self.svn_parent_path:
                QMessageBox.information(self, "提示", "SVN 模式已启用\n请在 SVN目录 按钮中设置 SVN 父级目录")
        else:
            # 常规模式激活：按钮显示"常规模式" + 正常颜色
            self.btn_mode.setText("常规模式")
            self.btn_mode.setStyleSheet("""
                QPushButton {
                    min-height: 32px;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 13px;
                    background: #f5f5f5;
                    border: 1px solid #ccc;
                }
                QPushButton:hover {
                    background: #e8e8e8;
                    border: 1px solid #999;
                }
            """)
            print("[模式] 切换到常规模式")
        self.update_workflow_status()

    def set_svn_parent_path(self):
        """设置 SVN 父级目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择 SVN 父级目录",
            str(self.svn_parent_path or Path.home())
        )
        if dir_path:
            self.svn_parent_path = Path(dir_path)
            # 添加到列表并设置为当前
            self.history_manager.add_svn_parent_dir(self.svn_parent_path)
            print(f"[SVN] 父级目录设置为: {self.svn_parent_path}")
            self.update_workflow_status()
            QMessageBox.information(self, "已添加", f"SVN 父级目录已添加:\n{self.svn_parent_path}")

    def on_refresh(self):
        """手动更新按钮点击"""
        print("[按钮] 手动更新")
        self.start_refresh(update_svn=False)

    def start_refresh(self, update_svn: bool = False):
        """启动后台刷新。"""
        if self.refresh_worker and self.refresh_worker.isRunning():
            self.set_workflow_status("刷新正在进行中...")
            return

        local_path = self.local_panel.current_path
        svn_path = self.svn_panel.current_path
        if not local_path and not svn_path:
            self.update_workflow_status()
            return

        self.set_busy(True, "正在准备刷新...")
        self.refresh_worker = RefreshWorker(local_path, svn_path, update_svn)
        self.refresh_worker.status_changed.connect(self.set_workflow_status)
        self.refresh_worker.result_ready.connect(self.on_refresh_finished)
        self.refresh_worker.failed.connect(self.on_refresh_failed)
        self.refresh_worker.start()

    def on_refresh_finished(self, result: dict):
        """后台刷新完成。"""
        local_path = result.get("local_path")
        svn_path = result.get("svn_path")
        local_files = result.get("local_files")
        svn_files = result.get("svn_files")

        if local_path and local_files is not None and str(self.local_panel.current_path) == local_path:
            self.local_panel.apply_scan_result(local_path, local_files)
            self.local_preview.set_global_bbox(self.local_panel.get_global_crop_bbox())
            print(f"  - 本地列表已刷新: {len(local_files)} 个文件")

        if svn_path and svn_files is not None and str(self.svn_panel.current_path) == svn_path:
            self.svn_panel.apply_scan_result(svn_path, svn_files)
            self.svn_preview.set_global_bbox(self.svn_panel.get_global_crop_bbox())
            print(f"  - SVN列表已刷新: {len(svn_files)} 个文件")

        if self.local_panel.file_list:
            self.update_diff_list()
        else:
            self.diff_panel.clear_diff()
            self.last_comparison_result = {}

        self.set_busy(False)
        self.update_workflow_status()

    def on_refresh_failed(self, message: str):
        """后台刷新失败。"""
        self.set_busy(False)
        self.set_workflow_status(f"刷新失败：{message}")
        QMessageBox.warning(self, "刷新失败", message)

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
            comparison_result = {
                f.relative_path or f.name: (f, FileStatus.NEW_FILE)
                for f in local_files
            }
        else:
            # 正常对比，显示所有文件（包括相同的）
            comparison_result = self.comparator.compare(local_files, svn_files)
            transfer_list = [(file_info, status) for filename, (file_info, status) in comparison_result.items()]

        self.last_comparison_result = comparison_result

        if not self.confirm_transfer_risks(comparison_result):
            return

        actionable_count = len([
            1 for file_info, status in transfer_list
            if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE)
        ])

        if actionable_count == 0:
            QMessageBox.information(self, "提示", "没有需要传输的文件（所有文件都已同步）")
            return

        # 打开传输预览对话框（传递更新信息和历史管理器）
        update_info = self.update_info_edit.text().strip()
        dialog = TransferPreviewDialog(
            transfer_list,
            self.local_panel.current_path,
            self.svn_panel.current_path,
            update_info,  # 初始提交信息
            self.history_manager,  # 用于保存对话框尺寸
            self
        )
        if dialog.exec():
            confirmed_files = dialog.get_confirmed_files()
            commit_msg = dialog.get_commit_message()
            print(f"[传输] 确认传输 {len(confirmed_files)} 个文件")
            self.execute_transfer(confirmed_files, commit_msg)

    def confirm_transfer_risks(self, comparison_result: dict) -> bool:
        """传输前确认风险项。"""
        svn_newer = [
            filename for filename, (file_info, status) in comparison_result.items()
            if status == FileStatus.SVN_NEWER
        ]

        if not svn_newer:
            return True

        preview = "\n".join(f"- {name}" for name in svn_newer[:8])
        if len(svn_newer) > 8:
            preview += f"\n... 还有 {len(svn_newer) - 8} 个"

        message = (
            f"检测到 {len(svn_newer)} 个 SVN 较新的文件。\n\n"
            f"{preview}\n\n"
            "这些文件不会被传输覆盖。建议先检查风险列表或执行 SVN 更新。\n"
            "是否继续只传输本地新增/修改文件？"
        )

        reply = QMessageBox.question(
            self,
            "检测到 SVN 风险项",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes

    def execute_transfer(self, confirmed_files: list, commit_msg: str):
        """执行传输操作"""
        if self.transfer_worker and self.transfer_worker.isRunning():
            self.set_workflow_status("传输正在进行中...")
            return

        self.pending_commit_msg = commit_msg
        print(f"[执行传输] 开始复制文件...")
        print(f"[执行传输] 本地目录: {self.local_panel.current_path}")
        print(f"[执行传输] SVN目录: {self.svn_panel.current_path}")

        self.set_busy(True, "正在传输文件...")
        self.transfer_worker = TransferWorker(
            confirmed_files,
            self.local_panel.current_path,
            self.svn_panel.current_path
        )
        self.transfer_worker.status_changed.connect(self.set_workflow_status)
        self.transfer_worker.result_ready.connect(self.on_transfer_finished)
        self.transfer_worker.start()

    def on_transfer_finished(self, result: dict):
        """后台传输完成。"""
        copied_count = result.get("copied_count", 0)
        failures = result.get("failures", [])
        new_paths = result.get("new_paths", [])

        print(f"[执行传输] 复制完成: {copied_count} 个文件")
        for failure in failures:
            print(f"  - 复制失败: {failure}")

        self.set_busy(False)

        if copied_count <= 0:
            QMessageBox.warning(self, "传输失败", "没有文件被成功复制。\n" + "\n".join(failures[:8]))
            self.update_workflow_status()
            return

        if new_paths and self.svn_manager.check_svn_command():
            self.svn_manager.add_files(new_paths)

        detail = f"已复制 {copied_count} 个文件到 SVN 目录。"
        if failures:
            detail += f"\n\n有 {len(failures)} 个文件复制失败，请检查后重试。"

        QMessageBox.information(
            self,
            "传输完成",
            f"{detail}\n\n即将打开 SVN 提交窗口，请确认提交。"
        )

        self.svn_manager.commit(self.svn_panel.current_path, self.pending_commit_msg)
        self.start_refresh(update_svn=False)

    def on_favorites(self):
        """收藏夹按钮点击 - 已废弃，改为独立按钮"""
        pass

    def show_path_pairs_menu(self):
        """显示路径对选择菜单"""
        menu = QMenu(self)

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

        if not history:
            no_history = menu.addAction("(暂无历史记录)")
            no_history.setEnabled(False)

        menu.addSeparator()
        clear_action = menu.addAction("清空历史路径")
        clear_action.triggered.connect(self.clear_history)

        menu.exec(self.btn_path_pairs.mapToGlobal(self.btn_path_pairs.rect().bottomLeft()))

    def show_svn_dirs_menu(self):
        """显示 SVN 目录管理菜单"""
        menu = QMenu(self)

        svn_header = menu.addAction("── SVN 父级目录 ──")
        svn_header.setEnabled(False)

        # 添加已保存的 SVN 父级目录列表
        saved_svn_dirs = self.history_manager.get_svn_parent_dirs()
        for svn_dir in saved_svn_dirs:
            is_current = self.svn_parent_path == svn_dir
            marker = "● " if is_current else "   "
            action = menu.addAction(f"{marker}{svn_dir.name}")
            action.setToolTip(str(svn_dir))
            if is_current:
                action.setEnabled(False)  # 当前选中的不可点击
            else:
                action.triggered.connect(lambda checked, d=svn_dir: self.select_svn_parent_dir(d))

        menu.addSeparator()

        # 添加新目录选项
        add_svn_action = menu.addAction("➕ 添加 SVN 父级目录...")
        add_svn_action.triggered.connect(self.set_svn_parent_path)

        # 清空 SVN 目录列表
        if saved_svn_dirs:
            clear_svn_action = menu.addAction("清空 SVN 目录列表")
            clear_svn_action.triggered.connect(self.clear_svn_parent_dirs)

        menu.exec(self.btn_svn_dirs.mapToGlobal(self.btn_svn_dirs.rect().bottomLeft()))

    def show_favorites_menu(self):
        """显示收藏夹菜单 - 已废弃"""
        pass

    def select_svn_parent_dir(self, svn_dir):
        """选择已有的 SVN 父级目录"""
        self.svn_parent_path = svn_dir
        self.history_manager.set_current_svn_parent_dir(svn_dir)
        print(f"[SVN] 切换父级目录: {svn_dir}")

        # 如果左侧已有加载的文件夹，右侧自动切换到对应SVN子目录
        if self.svn_mode and self.local_panel.current_path:
            current_path_str = self.local_panel.current_path
            # 从字符串直接提取文件夹名
            path_normalized = current_path_str.replace("\\", "/").rstrip("/")
            folder_name = path_normalized.split("/")[-1] if path_normalized else ""
            svn_target = svn_dir / folder_name

            try:
                svn_exists = svn_target.exists() and svn_target.is_dir()
            except RecursionError:
                svn_exists = False

            if svn_exists:
                try:
                    self.svn_panel.load_folder(str(svn_target))
                except RecursionError:
                    print(f"[SVN] 加载目标路径递归错误")
                    return
                print(f"[SVN] 自动切换右侧到: {svn_target}")
                self.update_diff_list()
            else:
                # 如果不存在同名文件夹，清空右侧
                self.svn_panel.clear_files()
                self.diff_panel.clear_diff()
                self.last_comparison_result = {}
                print(f"[SVN] 目标目录不存在: {svn_target}")
        else:
            # 左侧没有文件夹，只设置路径不扫描
            self.svn_panel.set_path_only(svn_dir)
        self.update_workflow_status()

    def clear_svn_parent_dirs(self):
        """清空 SVN 父级目录列表"""
        self.history_manager.clear_svn_parent_dirs()
        self.svn_parent_path = None
        print("[SVN] 已清空父级目录列表")
        self.update_workflow_status()
        QMessageBox.information(self, "已清空", "SVN 父级目录列表已清空")

    def load_folder_pair(self, local_path, svn_path):
        """加载文件夹对（同时设置本地和SVN路径）"""
        try:
            local_exists = local_path.exists()
        except RecursionError:
            local_exists = False

        try:
            svn_exists = svn_path.exists()
        except RecursionError:
            svn_exists = False

        if local_exists:
            self.local_panel.load_folder(str(local_path))
        if svn_exists:
            self.svn_panel.load_folder(str(svn_path))
        if local_exists and svn_exists:
            self.update_diff_list()
            self.save_history()
        else:
            self.update_workflow_status()

    def clear_history(self):
        """清空历史记录"""
        self.history_manager.clear()
        self.local_panel.clear_files()
        self.svn_panel.clear_files()
        self.diff_panel.clear_diff()
        self.last_comparison_result = {}
        print("[历史] 已清空")
        self.update_workflow_status()

    def closeEvent(self, event):
        """窗口关闭时保存尺寸"""
        size = self.size()
        self.history_manager.set_main_window_size(size.width(), size.height())
        print(f"[窗口] 保存尺寸: {size.width()}x{size.height()}")
        event.accept()
