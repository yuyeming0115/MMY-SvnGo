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

    _dimension_cache: dict = {}
    _bbox_cache: dict = {}
    MAX_CACHE_ITEMS = 20000

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

    def _cache_key(self, file_path, stat_result=None):
        """生成文件缓存键，文件变化后自动失效。"""
        path_str = str(file_path)
        try:
            stat_result = stat_result or os.stat(path_str)
            modified = getattr(stat_result, "st_mtime_ns", int(stat_result.st_mtime * 1_000_000_000))
            return (os.path.normcase(os.path.abspath(path_str)), stat_result.st_size, modified)
        except Exception:
            return None

    def _remember_cache(self, cache: dict, key, value):
        """写入缓存，达到上限时清空旧缓存。"""
        if len(cache) >= self.MAX_CACHE_ITEMS:
            cache.clear()
        cache[key] = value

    def get_cached_image_dimensions(self, file_path, stat_result=None) -> tuple[int, int]:
        """获取带缓存的图片尺寸。"""
        key = self._cache_key(file_path, stat_result)
        if key and key in self._dimension_cache:
            return self._dimension_cache[key]

        try:
            with Image.open(file_path) as img:
                dimensions = img.size
        except Exception:
            dimensions = (0, 0)

        if key:
            self._remember_cache(self._dimension_cache, key, dimensions)
        return dimensions

    def get_cached_image_bbox(self, file_path) -> tuple[int, int, int, int] | None:
        """获取带缓存的透明像素边界框。"""
        key = self._cache_key(file_path)
        if key and key in self._bbox_cache:
            return self._bbox_cache[key]

        try:
            with Image.open(file_path) as img:
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                alpha = img.split()[-1]
                bbox = alpha.getbbox()
                result = bbox if bbox else None
        except Exception as e:
            print(f"[边界框] 无法处理图片 {file_path}: {e}")
            result = None

        if key:
            self._remember_cache(self._bbox_cache, key, result)
        return result

    def scan_folder(self, folder_path) -> List[FileInfo]:
        """扫描文件夹，返回文件信息列表

        Args:
            folder_path: 文件夹路径（可以是 Path 或字符串）
        """
        # 直接使用字符串，避免任何 Path 操作
        if isinstance(folder_path, str):
            path_str = folder_path
        else:
            try:
                path_str = str(folder_path)
            except RecursionError:
                print(f"[扫描] Path转字符串递归错误")
                return []

        # 跳过特殊路径（检查是否包含重复的文件夹名，可能是符号链接循环）
        path_normalized = path_str.replace("\\", "/").rstrip("/")
        parts = path_normalized.split("/")
        # 检查最后两个部分是否相同（表示可能的循环）
        if len(parts) >= 2 and parts[-1] == parts[-2]:
            print(f"[扫描] 检测到可能的循环路径，跳过: {path_str}")
            return []

        try:
            if not os.path.exists(path_str) or not os.path.isdir(path_str):
                return []
        except RecursionError:
            print(f"[扫描] os.path 检查递归错误: {path_str}")
            return []

        files = []
        max_depth = 15  # 最大递归深度限制

        try:
            walk_iter = os.walk(path_str)
            for root, dirs, filenames in walk_iter:
                try:
                    # 检查深度限制（使用字符串操作）
                    rel_path = root[len(path_str):] if root.startswith(path_str) else ""
                    depth = rel_path.count("\\") + rel_path.count("/") if rel_path else 0
                    if depth > max_depth:
                        print(f"[扫描] 跳过深度过大的目录: {root}")
                        dirs[:] = []  # 不再深入
                        continue

                    # 过滤文件夹（排除符号链接防止循环）
                    filtered_dirs = []
                    for d in dirs:
                        try:
                            full_path = root + "\\" + d if root else d
                            if d not in self.folder_filters and not d.startswith("."):
                                try:
                                    if not os.path.islink(full_path):
                                        filtered_dirs.append(d)
                                except:
                                    pass
                        except:
                            pass
                    dirs[:] = filtered_dirs

                    for filename in filenames:
                        # 过滤文件
                        if filename in self.file_filters or any(filename.endswith(ext) for ext in self.file_filters):
                            continue

                        file_full_path = root + "\\" + filename if root else filename
                        try:
                            file_info = self.get_file_info_from_str(file_full_path, path_str)
                            if file_info:
                                files.append(file_info)
                        except Exception as e:
                            print(f"[扫描] 跳过文件: {filename} - {e}")
                            continue
                except RecursionError:
                    print(f"[扫描] 处理目录递归错误: {root}")
                    dirs[:] = []
                    continue

        except RecursionError as e:
            print(f"[扫描] os.walk 递归错误: {path_str}")
        except Exception as e:
            print(f"[扫描] 扫描出错: {e}")

        return files

    def get_file_info_from_str(self, file_path_str: str, root_path_str: str = "") -> FileInfo | None:
        """从字符串路径获取文件信息（避免 Path 递归问题）"""
        try:
            stat = os.stat(file_path_str)
            # 从字符串直接提取文件名
            path_normalized = file_path_str.replace("\\", "/").rstrip("/")
            filename = path_normalized.split("/")[-1] if path_normalized else ""

            # 计算相对路径
            if root_path_str and file_path_str.startswith(root_path_str):
                relative_path = file_path_str[len(root_path_str):].lstrip("\\").lstrip("/")
            else:
                relative_path = filename

            # 基本信息（使用字符串路径）
            file_info = FileInfo(
                path=file_path_str,  # 存储字符串而非 Path
                name=filename,
                size=stat.st_size,
                modify_time=datetime.fromtimestamp(stat.st_mtime),
                relative_path=relative_path,
            )

            # 判断是否为图片
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext in self.IMAGE_EXTENSIONS:
                file_info.is_image = True
                file_info.width, file_info.height = self.get_cached_image_dimensions(file_path_str, stat)

            return file_info
        except Exception as e:
            print(f"[文件信息] 获取失败: {file_path_str} - {e}")
            return None

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
            file_info.width, file_info.height = self.get_cached_image_dimensions(file_path, stat)

        return file_info

    def get_image_dimensions(self, file_path: Path) -> tuple[int, int]:
        """获取图片尺寸"""
        return self.get_cached_image_dimensions(file_path)

    def get_image_bbox(self, file_path: Path) -> tuple[int, int, int, int] | None:
        """获取单张图片的有效像素边界框（裁剪透明边缘后的边界）"""
        return self.get_cached_image_bbox(file_path)

    def compute_global_bbox(self, folder_path: Path) -> tuple[int, int, int, int] | None:
        """计算文件夹内所有PNG图片的有效像素边界框交集

        Args:
            folder_path: 文件夹路径

        Returns:
            全局边界框 (left, top, right, bottom)，如果无有效图片则返回 None
        """
        # 使用 os.path 避免 Path 对象的递归问题
        path_str = str(folder_path)
        if not os.path.exists(path_str) or not os.path.isdir(path_str):
            return None

        global_bbox = None
        processed_count = 0
        max_depth = 20

        try:
            for root, dirs, filenames in os.walk(path_str):
                # 检查深度限制
                depth = root[len(path_str):].count(os.sep)
                if depth > max_depth:
                    dirs[:] = []
                    continue

                # 过滤文件夹（排除符号链接防止循环）
                dirs[:] = [
                    d for d in dirs
                    if d not in self.folder_filters
                    and not d.startswith(".")
                    and not os.path.islink(os.path.join(root, d))
                ]

                for filename in filenames:
                    ext = Path(filename).suffix.lower()
                    if ext != ".png":  # 只处理PNG图片
                        continue

                    file_path = Path(root) / filename
                    try:
                        bbox = self.get_image_bbox(file_path)
                        processed_count += 1

                        if bbox:
                            if global_bbox is None:
                                global_bbox = bbox
                            else:
                                # 取交集（取最小的边界）
                                global_bbox = (
                                    max(global_bbox[0], bbox[0]),  # left 取最大
                                    max(global_bbox[1], bbox[1]),  # top 取最大
                                    min(global_bbox[2], bbox[2]),  # right 取最小
                                    min(global_bbox[3], bbox[3]),  # bottom 取最小
                                )
                    except Exception as e:
                        print(f"[边界框] 处理文件出错 {file_path}: {e}")
                        continue

            print(f"[边界框] 处理了 {processed_count} 张PNG图片，全局边界框: {global_bbox}")
            return global_bbox
        except Exception as e:
            print(f"[边界框] 计算全局边界框出错: {e}")
            return None

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
