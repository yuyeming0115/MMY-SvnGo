"""
预览图面板 - 支持自动裁剪透明像素最大化显示
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter

from PIL import Image


class PreviewPanel(QWidget):
    """预览图面板"""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    _checkerboard_tiles = {}

    # 信号：请求计算全局边界框
    request_global_bbox = pyqtSignal()

    def __init__(self, title: str):
        super().__init__()
        self.title = title
        self.current_image_path: str | None = None  # 改用字符串避免 Path 递归
        self.show_checkerboard = False
        self.auto_crop = True  # 默认启用自动裁剪透明像素
        self.global_bbox: tuple | None = None  # 全局裁剪边界框
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

        # 统一裁剪按钮
        self.btn_unify = QPushButton("统一")
        self.btn_unify.setToolTip("计算当前文件夹所有PNG的统一裁剪范围")
        self.btn_unify.setFixedSize(40, 20)
        title_layout.addWidget(self.btn_unify)

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
        self.btn_unify.clicked.connect(self.on_unify_clicked)

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

    def on_unify_clicked(self):
        """点击统一按钮，请求计算全局边界框"""
        self.request_global_bbox.emit()

    def set_global_bbox(self, bbox: tuple | None):
        """设置全局裁剪边界框"""
        self.global_bbox = bbox
        # 如果当前有图片，重新加载以应用新的边界框
        if self.current_image_path:
            self.load_image(self.current_image_path)

    def load_image(self, path):
        """加载图片

        Args:
            path: 图片路径（可以是 Path 或字符串）
        """
        # 转换为字符串避免 Path 递归问题
        path_str = str(path) if isinstance(path, Path) else path
        self.current_image_path = path_str

        # 检查文件大小
        try:
            file_size = os.path.getsize(path_str)
        except Exception as e:
            self.image_label.setText(f"无法访问文件: {e}")
            self.image_label.setPixmap(QPixmap())
            return

        if file_size > self.MAX_FILE_SIZE:
            self.image_label.setText(f"文件过大（>{self.MAX_FILE_SIZE // (1024*1024)}MB）")
            self.image_label.setPixmap(QPixmap())
            return

        # 检查文件格式
        ext = os.path.splitext(path_str)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga"):
            self.image_label.setText("不支持的格式")
            self.image_label.setPixmap(QPixmap())
            return

        try:
            # 使用 Pillow 加载图片
            with Image.open(path_str) as img:
                # 转换为 RGBA 模式（确保透明通道存在）
                if img.mode != "RGBA":
                    img = img.convert("RGBA")

                # 如果启用自动裁剪，裁剪透明边缘
                if self.auto_crop and ext == ".png":
                    # 优先使用全局边界框
                    if self.global_bbox:
                        # 检查全局边界框是否在图片范围内
                        left, top, right, bottom = self.global_bbox
                        if left < right and top < bottom and right <= img.width and bottom <= img.height:
                            img = img.crop((left, top, right, bottom))
                        else:
                            # 全局边界框无效或超出范围，回退到单独裁剪
                            img = self.crop_transparent(img)
                    else:
                        # 没有全局边界框，单独裁剪
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
        tile = self.get_checkerboard_tile(checker_size)

        background = Image.new("RGBA", (width, height), (200, 200, 200, 255))
        for x in range(0, width, tile.width):
            for y in range(0, height, tile.height):
                background.paste(tile, (x, y))

        # 合成图片（棋盘格作为背景，原图叠加在上面）
        composite = Image.alpha_composite(background, img)
        return composite

    def get_checkerboard_tile(self, checker_size: int) -> Image.Image:
        """获取缓存的棋盘格小纹理。"""
        if checker_size in self._checkerboard_tiles:
            return self._checkerboard_tiles[checker_size]

        light = Image.new("RGBA", (checker_size, checker_size), (200, 200, 200, 255))
        dark = Image.new("RGBA", (checker_size, checker_size), (150, 150, 150, 255))
        tile = Image.new("RGBA", (checker_size * 2, checker_size * 2), (200, 200, 200, 255))
        tile.paste(light, (0, 0))
        tile.paste(dark, (checker_size, 0))
        tile.paste(dark, (0, checker_size))
        tile.paste(light, (checker_size, checker_size))
        self._checkerboard_tiles[checker_size] = tile
        return tile

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
