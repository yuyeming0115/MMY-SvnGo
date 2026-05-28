"""
主窗口 UI
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSplitter, QFrame, QFileDialog
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from src.ui.file_list_panel import FileListPanel
from src.ui.diff_list_panel import DiffListPanel
from src.ui.preview_panel import PreviewPanel


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("MMY SvnGo - 文件同步工具")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

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

        # 连接信号
        self.btn_refresh.clicked.connect(self.on_refresh)
        self.btn_backup.clicked.connect(self.on_backup)
        self.btn_preview_transfer.clicked.connect(self.on_preview_transfer)
        self.btn_transfer.clicked.connect(self.on_transfer)
        self.btn_favorites.clicked.connect(self.on_favorites)

    def create_list_area(self, parent_layout: QVBoxLayout):
        """创建列表对比区域"""
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：本地文件列表
        self.local_panel = FileListPanel("本地文件", "local")
        splitter.addWidget(self.local_panel)

        # 中间：差异列表
        self.diff_panel = DiffListPanel()
        splitter.addWidget(self.diff_panel)

        # 右侧：SVN 文件列表
        self.svn_panel = FileListPanel("SVN 文件", "svn")
        splitter.addWidget(self.svn_panel)

        # 设置分割比例
        splitter.setSizes([400, 300, 400])

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
        preview_splitter.setSizes([700, 700])

        # 预览区域高度固定
        preview_splitter.setMaximumHeight(300)

        parent_layout.addWidget(preview_splitter)

    # === 按钮事件处理 ===

    def on_refresh(self):
        """手动更新按钮点击"""
        # TODO: 实现刷新逻辑
        print("手动更新")

    def on_backup(self):
        """备份按钮点击"""
        # TODO: 实现备份逻辑
        print("备份")

    def on_preview_transfer(self):
        """传输预览按钮点击"""
        # TODO: 实现传输预览逻辑
        print("传输预览")

    def on_transfer(self):
        """传输按钮点击"""
        # TODO: 实现传输逻辑
        print("传输")

    def on_favorites(self):
        """收藏夹按钮点击"""
        # TODO: 实现收藏夹逻辑
        print("收藏夹")