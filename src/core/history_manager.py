"""
历史记录管理器
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from src.models.file_info import FolderPair


class HistoryManager:
    """历史记录管理器"""

    MAX_HISTORY = 30  # 最大历史记录数
    CONFIG_FILE = Path("config/history.json")

    def __init__(self):
        self.history: List[FolderPair] = []
        self.backup_dir: Optional[Path] = None  # 记忆的备份路径
        self.load()

    def load(self):
        """从配置文件加载历史记录"""
        if not self.CONFIG_FILE.exists():
            return

        try:
            with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.history = []
            for item in data.get("history", []):
                folder_pair = FolderPair(
                    local_path=Path(item["local_path"]),
                    svn_path=Path(item["svn_path"]),
                    last_used=datetime.fromisoformat(item["last_used"]),
                )
                self.history.append(folder_pair)

            # 加载备份路径
            backup_dir_str = data.get("backup_dir")
            if backup_dir_str:
                self.backup_dir = Path(backup_dir_str)

            # 按最后使用时间排序（最近的在前）
            self.history.sort(key=lambda x: x.last_used, reverse=True)

        except Exception as e:
            print(f"加载历史记录失败: {e}")
            self.history = []
            self.backup_dir = None

    def save(self):
        """保存历史记录到配置文件"""
        # 确保配置目录存在
        self.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "history": [
                {
                    "local_path": str(fp.local_path),
                    "svn_path": str(fp.svn_path),
                    "last_used": fp.last_used.isoformat(),
                }
                for fp in self.history
            ],
            "backup_dir": str(self.backup_dir) if self.backup_dir else None
        }

        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, local_path: Path, svn_path: Path):
        """添加或更新历史记录"""
        # 检查是否已存在相同的文件夹对
        for fp in self.history:
            if fp.local_path == local_path and fp.svn_path == svn_path:
                # 更新使用时间
                fp.last_used = datetime.now()
                self.history.sort(key=lambda x: x.last_used, reverse=True)
                self.save()
                return

        # 添加新记录
        new_pair = FolderPair(
            local_path=local_path,
            svn_path=svn_path,
            last_used=datetime.now(),
        )
        self.history.insert(0, new_pair)

        # 限制数量
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[:self.MAX_HISTORY]

        self.save()

    def get_last_used(self) -> Optional[FolderPair]:
        """获取最后使用的文件夹对"""
        return self.history[0] if self.history else None

    def get_all(self) -> List[FolderPair]:
        """获取所有历史记录"""
        return self.history.copy()

    def clear(self):
        """清空历史记录"""
        self.history = []
        self.save()

    def remove(self, local_path: Path, svn_path: Path):
        """移除指定历史记录"""
        self.history = [
            fp for fp in self.history
            if fp.local_path != local_path or fp.svn_path != svn_path
        ]
        self.save()

    def set_backup_dir(self, backup_dir: Path):
        """设置备份路径"""
        self.backup_dir = backup_dir
        self.save()

    def get_backup_dir(self) -> Optional[Path]:
        """获取备份路径"""
        return self.backup_dir