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
    MAX_SVN_DIRS = 10  # 最大 SVN 父级目录数
    CONFIG_FILE = Path("config/history.json")

    def __init__(self):
        self.history: List[FolderPair] = []
        self.backup_dir: Optional[Path] = None  # 记忆的备份路径
        self.svn_parent_dirs: List[Path] = []  # SVN 模式父级目录列表
        self.current_svn_parent_dir: Optional[Path] = None  # 当前选中的 SVN 父级目录
        self.main_window_size: tuple = (700, 700)  # 主窗口尺寸
        self.transfer_dialog_size: tuple = (500, 650)  # 传输预览对话框尺寸
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

            # 加载 SVN 父级目录列表
            self.svn_parent_dirs = []
            for dir_str in data.get("svn_parent_dirs", []):
                svn_dir = Path(dir_str)
                if svn_dir.exists():
                    self.svn_parent_dirs.append(svn_dir)

            # 加载当前 SVN 父级目录
            current_svn_str = data.get("current_svn_parent_dir")
            if current_svn_str:
                self.current_svn_parent_dir = Path(current_svn_str)

            # 加载窗口尺寸
            main_size = data.get("main_window_size")
            if main_size and isinstance(main_size, list) and len(main_size) == 2:
                self.main_window_size = (main_size[0], main_size[1])

            transfer_size = data.get("transfer_dialog_size")
            if transfer_size and isinstance(transfer_size, list) and len(transfer_size) == 2:
                self.transfer_dialog_size = (transfer_size[0], transfer_size[1])

            # 兼容旧版本：如果有旧的 svn_parent_dir，迁移到新列表
            old_svn_str = data.get("svn_parent_dir")
            if old_svn_str:
                old_svn = Path(old_svn_str)
                if old_svn.exists() and old_svn not in self.svn_parent_dirs:
                    self.svn_parent_dirs.append(old_svn)
                if not self.current_svn_parent_dir:
                    self.current_svn_parent_dir = old_svn

            # 按最后使用时间排序（最近的在前）
            self.history.sort(key=lambda x: x.last_used, reverse=True)

        except Exception as e:
            print(f"加载历史记录失败: {e}")
            self.history = []
            self.backup_dir = None
            self.svn_parent_dirs = []
            self.current_svn_parent_dir = None

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
            "backup_dir": str(self.backup_dir) if self.backup_dir else None,
            "svn_parent_dirs": [str(d) for d in self.svn_parent_dirs],
            "current_svn_parent_dir": str(self.current_svn_parent_dir) if self.current_svn_parent_dir else None,
            "main_window_size": list(self.main_window_size),
            "transfer_dialog_size": list(self.transfer_dialog_size)
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

    def add_svn_parent_dir(self, svn_parent_dir: Path):
        """添加 SVN 父级目录到列表"""
        if svn_parent_dir not in self.svn_parent_dirs:
            self.svn_parent_dirs.insert(0, svn_parent_dir)
            # 限制数量
            if len(self.svn_parent_dirs) > self.MAX_SVN_DIRS:
                self.svn_parent_dirs = self.svn_parent_dirs[:self.MAX_SVN_DIRS]
        self.current_svn_parent_dir = svn_parent_dir
        self.save()

    def get_svn_parent_dirs(self) -> List[Path]:
        """获取所有 SVN 父级目录"""
        return [d for d in self.svn_parent_dirs if d.exists()]

    def set_current_svn_parent_dir(self, svn_parent_dir: Path):
        """设置当前 SVN 父级目录"""
        self.current_svn_parent_dir = svn_parent_dir
        # 如果不在列表中，添加进去
        if svn_parent_dir not in self.svn_parent_dirs:
            self.svn_parent_dirs.insert(0, svn_parent_dir)
        self.save()

    def get_current_svn_parent_dir(self) -> Optional[Path]:
        """获取当前 SVN 父级目录"""
        if self.current_svn_parent_dir and self.current_svn_parent_dir.exists():
            return self.current_svn_parent_dir
        # 如果当前目录不存在，返回列表中的第一个有效目录
        valid_dirs = self.get_svn_parent_dirs()
        if valid_dirs:
            self.current_svn_parent_dir = valid_dirs[0]
            return self.current_svn_parent_dir
        return None

    def clear_svn_parent_dirs(self):
        """清空 SVN 父级目录列表"""
        self.svn_parent_dirs = []
        self.current_svn_parent_dir = None
        self.save()

    # 兼容旧版本的方法
    def set_svn_parent_dir(self, svn_parent_dir: Path):
        """设置 SVN 父级目录（兼容旧版本）"""
        self.add_svn_parent_dir(svn_parent_dir)

    def get_svn_parent_dir(self) -> Optional[Path]:
        """获取 SVN 父级目录（兼容旧版本）"""
        return self.get_current_svn_parent_dir()

    def set_main_window_size(self, width: int, height: int):
        """保存主窗口尺寸"""
        self.main_window_size = (width, height)
        self.save()

    def get_main_window_size(self) -> tuple:
        """获取主窗口尺寸"""
        return self.main_window_size

    def set_transfer_dialog_size(self, width: int, height: int):
        """保存传输预览对话框尺寸"""
        self.transfer_dialog_size = (width, height)
        self.save()

    def get_transfer_dialog_size(self) -> tuple:
        """获取传输预览对话框尺寸"""
        return self.transfer_dialog_size