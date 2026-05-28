"""
收藏夹管理器
"""

import json
from pathlib import Path
from typing import List

from src.models.file_info import FavoriteItem


class FavoriteManager:
    """收藏夹管理器"""

    CONFIG_FILE = Path("config/favorites.json")

    # 默认预设目录
    DEFAULT_FAVORITES = [
        FavoriteItem(
            path=Path("E:/XYJProject/美术资源/动画序列帧/角色输出图"),
            name="角色输出图（美术资源）",
            is_default=True,
        ),
        FavoriteItem(
            path=Path("D:/Work/预传输前序列帧"),
            name="预传输前序列帧",
            is_default=True,
        ),
    ]

    def __init__(self):
        self.favorites: List[FavoriteItem] = []
        self.load()

    def load(self):
        """从配置文件加载收藏夹"""
        if not self.CONFIG_FILE.exists():
            # 使用默认预设
            self.favorites = self.DEFAULT_FAVORITES.copy()
            return

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.favorites = []
            for item in data.get("favorites", []):
                favorite = FavoriteItem(
                    path=Path(item["path"]),
                    name=item["name"],
                    is_default=item.get("is_default", False),
                )
                self.favorites.append(favorite)

        except Exception as e:
            print(f"加载收藏夹失败: {e}")
            self.favorites = self.DEFAULT_FAVORITES.copy()

    def save(self):
        """保存收藏夹到配置文件"""
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "favorites": [
                {
                    "path": str(fav.path),
                    "name": fav.name,
                    "is_default": fav.is_default,
                }
                for fav in self.favorites
            ]
        }

        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, path: Path, name: str):
        """添加收藏项"""
        # 检查是否已存在
        for fav in self.favorites:
            if fav.path == path:
                return

        favorite = FavoriteItem(
            path=path,
            name=name,
            is_default=False,
        )
        self.favorites.append(favorite)
        self.save()

    def remove(self, path: Path):
        """移除收藏项"""
        # 不允许删除默认预设
        self.favorites = [
            fav for fav in self.favorites
            if fav.path != path or fav.is_default
        ]
        self.save()

    def update_name(self, path: Path, new_name: str):
        """更新收藏项名称"""
        for fav in self.favorites:
            if fav.path == path:
                fav.name = new_name
                self.save()
                return

    def get_all(self) -> List[FavoriteItem]:
        """获取所有收藏项"""
        return self.favorites.copy()

    def get_defaults(self) -> List[FavoriteItem]:
        """获取默认预设"""
        return [fav for fav in self.favorites if fav.is_default]