"""
数据模型定义
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path


class FileStatus(Enum):
    """文件状态枚举"""
    MODIFIED = "modified"      # 本地已修改（红色）
    SAME = "same"              # 无需更新（绿色）
    SVN_NEWER = "svn_newer"    # SVN 较新（橙色）
    NEW_FILE = "new_file"      # 新文件（仅存在于本地）
    DELETED = "deleted"        # 已删除（仅存在于SVN历史）


@dataclass
class FileInfo:
    """文件信息数据类"""
    path: Path                 # 文件完整路径
    name: str                  # 文件名
    size: int                  # 文件大小（字节）
    modify_time: datetime      # 修改时间
    width: int = 0             # 图片宽度（像素）
    height: int = 0            # 图片高度（像素）
    is_image: bool = False     # 是否为图片文件

    @property
    def size_display(self) -> str:
        """显示用文件大小"""
        if self.size < 1024:
            return f"{self.size} B"
        elif self.size < 1024 * 1024:
            return f"{self.size / 1024:.1f} KB"
        else:
            return f"{self.size / (1024 * 1024):.1f} MB"

    @property
    def dimensions_display(self) -> str:
        """显示用图片尺寸"""
        if self.is_image and self.width > 0:
            return f"{self.width} x {self.height}"
        return ""


@dataclass
class FolderPair:
    """文件夹对数据类"""
    local_path: Path           # 本地路径
    svn_path: Path             # SVN路径
    last_used: datetime        # 最后使用时间

    @property
    def local_name(self) -> str:
        """本地文件夹名"""
        return self.local_path.name

    @property
    def svn_name(self) -> str:
        """SVN文件夹名"""
        return self.svn_path.name


@dataclass
class FavoriteItem:
    """收藏项数据类"""
    path: Path                 # 路径
    name: str                  # 显示名称
    is_default: bool = False   # 是否为预设默认项