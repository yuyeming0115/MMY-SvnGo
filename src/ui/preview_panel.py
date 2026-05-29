"""
预览图面板 - 支持自动裁剪透明像素最大化显示
"""

from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter

from PIL import Image


class PreviewPanel(QWidget):
    """预览图面板"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self.current_image_path: Path | None = None
        self.show_checkerboard = False
        self.auto_crop = True  # 默认启用自动裁剪透明像素
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(3)

        # 标题栏（紧凑）
        title_bar = QWidget()
        title_bar.setMaximumHeight(24)
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        title_label = QLabel(self.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        title_layout.addWidget(title_label)

        # 棋盘格切换按钮（紧凑）
        self.btn_checkerboard = QPushButton("棋盘")
        self.btn_checkerboard.setToolTip("切换棋盘格背景")
        self.btn_checkerboard.setFixedSize(45, 20)
        self.btn_checkerboard.setCheckable(True)
        title_layout.addWidget(self.btn_checkerboard)

        # 自动裁剪按钮（紧凑）
        self.btn_auto_crop = QPushButton("裁剪")
        self.btn_auto_crop.setToolTip("裁剪透明边缘")
        self.btn_auto_crop.setFixedSize(40, 20)
        self.btn_auto_crop.setCheckable(True)
        self.btn_auto_crop.setChecked(True)
        title_layout.addWidget(self.btn_auto_crop)

        title_layout.addStretch()

        layout.addWidget(title_bar)

        # 图片显示区域
        self.image_frame = QFrame()
        self.image_frame.setStyleSheet("QFrame { background-color: #2a2a2a; }")
        self.image_frame.setMinimumHeight(200)
        self.image_frame.setMinimumWidth(200)  # 设置最小宽度，使其接近方形

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
        self.btn_auto_crop.clicked.connect(self.toggle_auto_crop)

    def toggle_checkerboard(self):
        """切换棋盘格背景"""
        self.show_checkerboard = self.btn_checkerboard.isChecked()
        if self.current_image_path:
            self.load_image(self.current_image_path)

    def toggle_auto_crop(self):
        """切换自动裁剪"""
        self.auto_crop = self.btn_auto_crop.isChecked()
        if self.current_image_path:
            self.load_image(self.current_image_path)

    def load_image(self, path: Path):
        """加载图片"""
        self.current_image_path = path

        # 检查文件大小
        if path.stat().st_size > self.MAX_FILE_SIZE:
            self.image_label.setText(f"文件过大（>{self.MAX_FILE_SIZE // (1024*1024)}MB）")
            self.image_label.setPixmap(QPixmap())
            return

        # 检查文件格式
        ext = path.suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga"):
            self.image_label.setText("不支持的格式")
            self.image_label.setPixmap(QPixmap())
            return

        try:
            # 使用 Pillow 加载图片
            with Image.open(path) as img:
                # 转换为 RGBA 模式（确保透明通道存在）
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                # 如果启用自动裁剪，裁剪透明边缘
                if self.auto_crop and ext == ".png":
                    img = self.crop_transparent(img)

                # 如果启用棋盘格，合成棋盘格背景
                if self.show_checkerboard:
                    img = self.add_checkerboard_pil(img)

                # 转换为 QPixmap
                data = img.tobytes("raw", "RGBA")
                qimage = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
                pixmap = QPixmap.fromImage(qimage)

                # 缩放到适合显示区域（不变形，最大化显示）
                scaled = self.scale_pixmap(pixmap)
                self.image_label.setPixmap(scaled)
                self.image_label.setText("")
        except Exception as e:
            self.image_label.setText(f"加载失败: {e}")

    def crop_transparent(self, img: Image.Image) -> Image.Image:
        """裁剪透明边缘，只保留有效像素区域"""
        # 获取图片边界框（非透明区域）
        # alpha 通道中，0 表示完全透明
        alpha = img.split()[-1]  # 获取 alpha 通道
        bbox = alpha.getbbox()  # 获取非透明区域的边界框

        if bbox:
            # 裁剪到边界框
            return img.crop(bbox)
        else:
            # 整张图片都是透明的，返回原图
            return img

    def add_checkerboard_pil(self, img: Image.Image) -> Image.Image:
        """使用 Pillow 添加棋盘格背景"""
        width, height = img.size
        checker_size = 10

        # 创建棋盘格背景
        background = Image.new("RGBA", (width, height), (200, 200, 200, 255))

        for x in range(0, width, checker_size):
            for y in range(0, height, checker_size):
                color = (200, 200, 200, 255) if ((x // checker_size) + (y // checker_size)) % 2 == 0 else (150, 150, 150, 255)
                for dx in range(min(checker_size, width - x)):
                    for dy in range(min(checker_size, height - y)):
                        background.putpixel((x + dx, y + dy), color)

        # 合成图片（棋盘格作为背景，原图叠加在上面）
        composite = Image.alpha_composite(background, img)
        return composite

    def scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """缩放图片（保持比例，最大化显示）"""
        label_size = self.image_label.size()
        if label_size.width() < 10 or label_size.height() < 10:
            return pixmap

        # 计算缩放比例（最大化填充，不超出边界）
        scale_w = label_size.width() / pixmap.width()
        scale_h = label_size.height() / pixmap.height()
        scale = min(scale_w, scale_h)  # 选择较小的比例，确保完全显示

        new_size = QSize(
            int(pixmap.width() * scale),
            int(pixmap.height() * scale)
        )
        return pixmap.scaled(new_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def clear_preview(self):
        """清空预览"""
        self.current_image_path = None
        self.image_label.setText("选择文件查看预览")
        self.image_label.setPixmap(QPixmap())