"""
文件扫描器
"""

import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from PIL import Image

from src.models.file_info import FileInfo


class FileScanner:
    """文件扫描器"""

    # 图片文件扩展名
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".tif", ".tiff"}

    # 默认过滤规则
    DEFAULT_FILTERS = {
        ".svn",
        ".git",
        "__pycache__",
        ".idea",
        ".vscode",
        "node_modules",
    }

    # 默认过滤文件扩展名
    DEFAULT_FILE_FILTERS = {
        ".pyc",
        ".pyo",
        ".DS_Store",
        "Thumbs.db",
    }

    def __init__(self, custom_filters: Optional[set] = None, custom_file_filters: Optional[set] = None):
        """
        Args:
            custom_filters: 自定义文件夹过滤规则
            custom_file_filters: 自定义文件扩展名过滤规则
        """
        self.folder_filters = self.DEFAULT_FILTERS | (custom_filters or set())
        self.file_filters = self.DEFAULT_FILE_FILTERS | (custom_file_filters or set())

    def scan_folder(self, folder_path: Path) -> List[FileInfo]:
        """扫描文件夹，返回文件信息列表"""
        if not folder_path.exists() or not folder_path.is_dir():
            return []

        files = []

        for root, dirs, filenames in os.walk(folder_path):
            # 过滤文件夹
            dirs[:] = [d for d in dirs if d not in self.folder_filters and not d.startswith(".")]

            for filename in filenames:
                # 过滤文件
                if filename in self.file_filters or any(filename.endswith(ext) for ext in self.file_filters):
                    continue

                file_path = Path(root) / filename
                try:
                    file_info = self.get_file_info(file_path, folder_path)
                    files.append(file_info)
                except Exception as e:
                    # 跳过无法访问的文件
                    print(f"无法访问文件 {file_path}: {e}")
                    continue

        return files

    def get_file_info(self, file_path: Path, root_path: Path = None) -> FileInfo:
        """获取单个文件的信息

        Args:
            file_path: 文件路径
            root_path: 扫描根目录（用于计算相对路径）
        """
        stat = file_path.stat()

        # 计算相对路径
        relative_path = ""
        if root_path:
            try:
                rel = file_path.relative_to(root_path)
                relative_path = str(rel)
            except ValueError:
                relative_path = file_path.name

        # 基本信息
        file_info = FileInfo(
            path=file_path,
            name=file_path.name,
            size=stat.st_size,
            modify_time=datetime.fromtimestamp(stat.st_mtime),
            relative_path=relative_path,
        )

        # 判断是否为图片
        ext = file_path.suffix.lower()
        if ext in self.IMAGE_EXTENSIONS:
            file_info.is_image = True
            try:
                # 获取图片尺寸（不加载完整图片）
                with Image.open(file_path) as img:
                    file_info.width, file_info.height = img.size
            except Exception:
                # 无法读取图片尺寸
                pass

        return file_info

    def get_image_dimensions(self, file_path: Path) -> tuple[int, int]:
        """获取图片尺寸"""
        try:
            with Image.open(file_path) as img:
                return img.size
        except Exception:
            return (0, 0)

    def add_filter(self, folder_name: str):
        """添加文件夹过滤规则"""
        self.folder_filters.add(folder_name)

    def add_file_filter(self, extension: str):
        """添加文件扩展名过滤规则"""
        self.file_filters.add(extension)

    def remove_filter(self, folder_name: str):
        """移除文件夹过滤规则"""
        self.folder_filters.discard(folder_name)

    def remove_file_filter(self, extension: str):
        """移除文件扩展名过滤规则"""
        self.file_filters.discard(extension)