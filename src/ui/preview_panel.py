"""
预览图面板
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage, QColor, QBrush, QPainter, QPen


class PreviewPanel(QWidget):
    """预览图面板"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self.current_image_path: Path | None = None
        self.show_checkerboard = False  # 是否显示棋盘格背景
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
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        title_layout.addWidget(title_label)

        # 棋盘格切换按钮
        self.btn_checkerboard = QPushButton("棋盘格")
        self.btn_checkerboard.setToolTip("切换棋盘格背景显示透明区域")
        self.btn_checkerboard.setMaximumWidth(70)
        self.btn_checkerboard.setCheckable(True)
        title_layout.addWidget(self.btn_checkerboard)

        title_layout.addStretch()

        layout.addWidget(title_bar)

        # 图片显示区域
        self.image_frame = QFrame()
        self.image_frame.setStyleSheet("QFrame { background-color: #2a2a2a; }")
        self.image_frame.setMinimumHeight(200)

        image_layout = QVBoxLayout(self.image_frame)
        image_layout.setContentsMargins(0, 0, 0, 0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("选择文件查看预览")
        self.image_label.setStyleSheet("color: #888;")
        image_layout.addWidget(self.image_label)

        layout.addWidget(self.image_frame)

        # 连接信号
        self.btn_checkerboard.clicked.connect(self.toggle_checkerboard)

    def toggle_checkerboard(self):
        """切换棋盘格背景"""
        self.show_checkerboard = self.btn_checkerboard.isChecked()
        if self.current_image_path:
            self.load_image(self.current_image_path)

    def load_image(self, path: Path):
        """加载图片"""
        self.current_image_path = path

        # 检查文件大小
        if path.stat().st_size > self.MAX_FILE_SIZE:
            self.image_label.setText(f"文件过大（>{self.MAX_FILE_SIZE // (1024*1024)}MB），不加载预览")
            self.image_label.setPixmap(QPixmap())
            return

        # 检查文件格式
        ext = path.suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif"):
            self.image_label.setText("不支持的格式")
            self.image_label.setPixmap(QPixmap())
            return

        try:
            pixmap = QPixmap(str(path))

            if pixmap.isNull():
                self.image_label.setText("无法加载图片")
                return

            # 如果是透明图片且启用棋盘格，合成棋盘格背景
            if self.show_checkerboard and ext == ".png":
                pixmap = self.add_checkerboard(pixmap)

            # 缩放到适合显示区域（不变形）
            scaled = self.scale_pixmap(pixmap)
            self.image_label.setPixmap(scaled)
            self.image_label.setText("")
        except Exception as e:
            self.image_label.setText(f"加载失败: {e}")

    def add_checkerboard(self, pixmap: QPixmap) -> QPixmap:
        """添加棋盘格背景"""
        size = pixmap.size()
        checkerboard = self.create_checkerboard(size)

        # 合成图片
        result = QPixmap(size)
        result.fill(Qt.GlobalColor.transparent)

        painter = QPainter(result)
        painter.drawPixmap(0, 0, checkerboard)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        return result

    def create_checkerboard(self, size: QSize) -> QPixmap:
        """创建棋盘格背景"""
        pixmap = QPixmap(size)
        painter = QPainter(pixmap)

        # 棋盘格大小
        checker_size = 10

        # 两种颜色
        color1 = QColor(200, 200, 200)
        color2 = QColor(150, 150, 150)

        for x in range(0, size.width(), checker_size):
            for y in range(0, size.height(), checker_size):
                color = color1 if ((x // checker_size) + (y // checker_size)) % 2 == 0 else color2
                painter.fillRect(x, y, checker_size, checker_size, color)

        painter.end()
        return pixmap

    def scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """缩放图片（保持比例，不变形）"""
        label_size = self.image_label.size()
        if label_size.width() < 10 or label_size.height() < 10:
            return pixmap

        # 计算缩放比例
        scale_w = label_size.width() / pixmap.width()
        scale_h = label_size.height() / pixmap.height()
        scale = min(scale_w, scale_h, 1.0)  # 不放大

        if scale < 1.0:
            new_size = QSize(
                int(pixmap.width() * scale),
                int(pixmap.height() * scale)
            )
            return pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        return pixmap

    def clear_preview(self):
        """清空预览"""
        self.current_image_path = None
        self.image_label.setText("选择文件查看预览")
        self.image_label.setPixmap(QPixmap())