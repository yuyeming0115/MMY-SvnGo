"""
文件对比器
"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

from src.models.file_info import FileInfo, FileStatus
from src.core.file_scanner import FileScanner


class FileComparator:
    """文件对比器"""

    def __init__(self, scanner: FileScanner = None):
        self.scanner = scanner or FileScanner()

    def compare(self, local_files: List[FileInfo], svn_files: List[FileInfo]) -> Dict[str, Tuple[FileInfo, FileStatus]]:
        """对比本地文件和 SVN 文件

        Args:
            local_files: 本地文件列表
            svn_files: SVN 文件列表

        Returns:
            {filename: (file_info, status)}
        """
        result = {}

        # 建立文件名映射（使用相对路径名）
        local_map = {f.name: f for f in local_files}
        svn_map = {f.name: f for f in svn_files}

        # 检查本地文件
        for filename, local_info in local_map.items():
            if filename not in svn_map:
                # 仅存在于本地：新文件
                result[filename] = (local_info, FileStatus.NEW_FILE)
            else:
                svn_info = svn_map[filename]
                status = self.compare_file(local_info, svn_info)
                result[filename] = (local_info, status)

        # 检查 SVN 中独有的文件（可能被本地删除）
        for filename, svn_info in svn_map.items():
            if filename not in local_map:
                # 仅存在于 SVN：SVN 较新或本地已删除
                result[filename] = (svn_info, FileStatus.SVN_NEWER)

        return result

    def compare_file(self, local_info: FileInfo, svn_info: FileInfo) -> FileStatus:
        """对比单个文件

        Args:
            local_info: 本地文件信息
            svn_info: SVN 文件信息

        Returns:
            FileStatus
        """
        # 1. 文件大小不同 → 已修改
        if local_info.size != svn_info.size:
            return FileStatus.MODIFIED

        # 2. 修改时间不同（本地较新） → 已修改
        if local_info.modify_time > svn_info.modify_time:
            return FileStatus.MODIFIED

        # 3. SVN 修改时间较新 → SVN 较新
        if svn_info.modify_time > local_info.modify_time:
            return FileStatus.SVN_NEWER

        # 4. 图片文件：像素尺寸不同 → 已修改
        if local_info.is_image and svn_info.is_image:
            if local_info.width != svn_info.width or local_info.height != svn_info.height:
                return FileStatus.MODIFIED

        # 5. 相同
        return FileStatus.SAME

    def get_transfer_list(self, comparison_result: Dict[str, Tuple[FileInfo, FileStatus]]) -> List[Tuple[FileInfo, FileStatus]]:
        """获取需要传输的文件列表（排除相同和 SVN 较新）"""
        return [
            (file_info, status)
            for filename, (file_info, status) in comparison_result.items()
            if status in (FileStatus.MODIFIED, FileStatus.NEW_FILE)
        ]

    def get_status_summary(self, comparison_result: Dict[str, Tuple[FileInfo, FileStatus]]) -> Dict[FileStatus, int]:
        """获取状态统计"""
        summary = {status: 0 for status in FileStatus}
        for filename, (file_info, status) in comparison_result.items():
            summary[status] += 1
        return summary