"""
备份管理器
"""

import zipfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


class BackupManager:
    """备份管理器"""

    def __init__(self, backup_dir: Optional[Path] = None):
        """
        Args:
            backup_dir: 备份目录（默认为 config/backups）
        """
        self.backup_dir = backup_dir or Path("config/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def backup_to_zip(self, source_path: Path, custom_name: Optional[str] = None) -> Path:
        """备份目录到压缩包

        Args:
            source_path: 要备份的目录
            custom_name: 自定义名称（可选，不含 .zip 扩展名）

        Returns:
            压缩包路径
        """
        if not source_path.exists() or not source_path.is_dir():
            raise ValueError(f"源路径不存在或不是目录: {source_path}")

        # 生成备份文件名（custom_name 已包含时间戳，直接使用）
        if custom_name:
            zip_name = f"{custom_name}.zip"
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_name = f"{source_path.name}_{timestamp}.zip"

        zip_path = self.backup_dir / zip_name

        # 创建压缩包
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 提取 ID 作为压缩包内的父级文件夹名
            # 例如：source_path.name = "502032_20260528_183410" -> ID = "502032"
            import re
            id_match = re.match(r'^(\d+)', source_path.name)
            parent_folder = id_match.group(1) if id_match else source_path.name

            for root, dirs, files in source_path.walk():
                # 过滤 .svn 目录
                dirs[:] = [d for d in dirs if d != ".svn"]

                for file in files:
                    file_path = root / file
                    # 计算相对路径，并添加父级 ID 文件夹
                    rel_path = file_path.relative_to(source_path)
                    zip_path_inside = Path(parent_folder) / rel_path
                    zf.write(file_path, zip_path_inside)

        return zip_path

    def backup_files(self, files: list[Path], output_path: Path) -> Path:
        """备份指定文件列表

        Args:
            files: 要备份的文件列表
            output_path: 输出压缩包路径

        Returns:
            压缩包路径
        """
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files:
                if file.exists():
                    zf.write(file, file.name)

        return output_path

    def get_backups(self) -> list[Path]:
        """获取所有备份文件"""
        return sorted(self.backup_dir.glob("*.zip"), reverse=True)

    def delete_backup(self, zip_path: Path) -> bool:
        """删除备份文件"""
        if zip_path.exists() and zip_path.parent == self.backup_dir:
            zip_path.unlink()
            return True
        return False

    def restore_backup(self, zip_path: Path, target_path: Path) -> bool:
        """恢复备份

        Args:
            zip_path: 压缩包路径
            target_path: 目标路径

        Returns:
            是否成功
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(target_path)
            return True
        except Exception as e:
            print(f"恢复备份失败: {e}")
            return False