"""
主窗口 UI - 连接各模块信号
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from src.ui.file_list_panel import FileListPanel
from src.ui.diff_list_panel import DiffListPanel
from src.ui.preview_panel import PreviewPanel
from src.core.file_comparator import FileComparator
from src.core.history_manager import HistoryManager
from src.core.favorite_manager import FavoriteManager


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.comparator = FileComparator()
        self.history_manager = HistoryManager()
        self.favorite_manager = FavoriteManager()
        self.init_ui()
        self.load_last_used()

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

        # 传输预览按钮
        self.btn_preview_transfer = QPushButton("传输预览")
        self.btn_preview_transfer.setToolTip("预览即将传输的文件清单")
        self.btn_preview_transfer.setMinimumWidth(100)
        top_layout.addWidget(self.btn_preview_transfer)

        # 传输按钮
        self.btn_transfer = QPushButton("传输")
        self.btn_transfer.setToolTip("执行文件复制并提交 SVN")
        self.btn_transfer.setMinimumWidth(80)
        top_layout.addWidget(self.btn_transfer)

        # 分隔
        top_layout.addSpacing(20)

        # 收藏夹按钮
        self.btn_favorites = QPushButton("收藏夹")
        self.btn_favorites.setToolTip("预设和历史目录")
        self.btn_favorites.setMinimumWidth(80)
        top_layout.addWidget(self.btn_favorites)

        top_layout.addStretch()

        parent_layout.addWidget(top_bar)

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

        # 文件选中信号（三列同步）
        self.local_panel.file_selected.connect(self.on_local_file_selected)
        self.svn_panel.file_selected.connect(self.on_svn_file_selected)
        self.diff_panel.file_selected.connect(self.on_diff_file_selected)

        # 按钮点击信号
        self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_backup.clicked.connect(self.on_backup)
        self.btn_preview_transfer.clicked.connect(self.on_preview_transfer)
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
        """本地文件选中时，同步三列并更新预览"""
        filename = path.name
        self.local_preview.load_image(path)
        self.svn_panel.select_file_by_name(filename)
        self.diff_panel.select_by_filename(filename)
        # 让本地列也滚动到居中
        self.local_panel.scrollToSelectedRow()
        svn_path = self.svn_panel.get_file_path_by_name(filename)
        if svn_path:
            self.svn_preview.load_image(svn_path)

    def on_svn_file_selected(self, path: Path):
        """SVN 文件选中时，同步三列并更新预览"""
        filename = path.name
        self.svn_preview.load_image(path)
        self.local_panel.select_file_by_name(filename)
        self.diff_panel.select_by_filename(filename)
        # 让SVN列也滚动到居中
        self.svn_panel.scrollToSelectedRow()
        local_path = self.local_panel.get_file_path_by_name(filename)
        if local_path:
            self.local_preview.load_image(local_path)

    def on_diff_file_selected(self, filename: str):
        """中间列选中时，同步左右两列并更新预览"""
        self.local_panel.select_file_by_name(filename)
        self.svn_panel.select_file_by_name(filename)
        # 让中间列也滚动到居中
        self.diff_panel.scrollToSelectedRow()
        local_path = self.local_panel.get_file_path_by_name(filename)
        svn_path = self.svn_panel.get_file_path_by_name(filename)
        if local_path:
            self.local_preview.load_image(local_path)
        if svn_path:
            self.svn_preview.load_image(svn_path)

    # === 文件夹拖入处理 ===

    def on_local_folder_dropped(self, path: Path):
        """本地文件夹拖入"""
        print(f"[本地] 拖入: {path}")
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
        QMessageBox.information(self, "提示", f"备份功能开发中...\n目标: {self.svn_panel.current_path}")

    def on_preview_transfer(self):
        """传输预览按钮点击"""
        print("[按钮] 传输预览")
        local_files = self.local_panel.get_file_list()
        svn_files = self.svn_panel.get_file_list()
        if not local_files or not svn_files:
            QMessageBox.warning(self, "提示", "请先拖入本地和 SVN 目录")
            return
        QMessageBox.information(self, "提示", "传输预览功能开发中...")

    def on_transfer(self):
        """传输按钮点击"""
        print("[按钮] 传输")
        if not self.local_panel.current_path or not self.svn_panel.current_path:
            QMessageBox.warning(self, "提示", "请先拖入本地和 SVN 目录")
            return
        QMessageBox.information(self, "提示", "传输功能开发中...")

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