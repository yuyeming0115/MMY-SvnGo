"""
SVN 管理器
"""

import subprocess
import shutil
from pathlib import Path
from typing import List, Tuple, Optional


class SVNManager:
    """SVN 操作管理器"""

    # TortoiseSVN 路径（通常安装位置）
    TORTOISESVN_PATH = Path("C:/Program Files/TortoiseSVN/bin/TortoiseProc.exe")

    def __init__(self):
        self.tortoise_available = self.check_tortoise()

    def check_tortoise(self) -> bool:
        """检查 TortoiseSVN 是否可用"""
        return self.TORTOISESVN_PATH.exists()

    def check_svn_command(self) -> bool:
        """检查 svn 命令行是否可用"""
        try:
            result = subprocess.run(["svn", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    def update(self, path: Path, silent: bool = False) -> bool:
        """执行 SVN 更新

        Args:
            path: SVN 目录路径
            silent: 是否静默执行（后台执行，不弹窗）

        Returns:
            是否成功
        """
        if silent:
            # 静默模式：使用命令行后台执行
            return self.command_update(path)
        elif self.tortoise_available:
            # 使用 TortoiseSVN（弹出 GUI）
            return self.tortoise_update(path)
        else:
            # 使用命令行
            return self.command_update(path)

    def tortoise_update(self, path: Path) -> bool:
        """使用 TortoiseSVN 更新"""
        try:
            subprocess.run([
                str(self.TORTOISESVN_PATH),
                "/command:update",
                f"/path:{path}",
            ], check=True)
            return True
        except Exception as e:
            print(f"TortoiseSVN 更新失败: {e}")
            return False

    def command_update(self, path: Path) -> bool:
        """使用 svn 命令行更新"""
        try:
            result = subprocess.run(
                ["svn", "update", str(path)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except Exception as e:
            print(f"svn update 失败: {e}")
            return False

    def get_status(self, path: Path) -> List[Tuple[str, str]]:
        """获取 SVN 状态

        Args:
            path: SVN 目录路径

        Returns:
            [(filename, status_code), ...]
            status_code: M=修改, A=新增, D=删除, ?=未跟踪
        """
        try:
            result = subprocess.run(
                ["svn", "status", str(path)],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return []

            status_list = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                # SVN status 输出格式：状态码 文件路径
                status_code = line[0]
                filepath = line[8:].strip()  # 跳过前8个字符
                status_list.append((filepath, status_code))

            return status_list

        except Exception as e:
            print(f"svn status 失败: {e}")
            return []

    def add_files(self, files: List[Path]) -> bool:
        """添加文件到 SVN

        Args:
            files: 要添加的文件列表

        Returns:
            是否成功
        """
        if not files:
            return True

        try:
            for file in files:
                result = subprocess.run(
                    ["svn", "add", "--parents", str(file)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0 and "already under version control" not in result.stderr:
                    print(f"svn add 失败: {file} - {result.stderr.strip()}")
                    return False
            return True
        except Exception as e:
            print(f"svn add 失败: {e}")
            return False

    def commit(self, path: Path, message: str, files: Optional[List[Path]] = None) -> bool:
        """提交 SVN

        Args:
            path: SVN 目录路径
            message: 提交信息
            files: 要提交的文件列表（可选，不指定则提交所有变更）

        Returns:
            是否成功
        """
        if self.tortoise_available:
            return self.tortoise_commit(path, message)
        else:
            return self.command_commit(path, message, files)

    def tortoise_commit(self, path: Path, message: str) -> bool:
        """使用 TortoiseSVN 提交（弹出 GUI）"""
        try:
            # TortoiseSVN 的 /logmsg 参数不支持多行文本
            # 使用临时文件传递提交信息
            import tempfile

            # 创建临时文件保存提交信息
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
                f.write(message)
                logmsg_file = Path(f.name)

            subprocess.run([
                str(self.TORTOISESVN_PATH),
                "/command:commit",
                f"/path:{path}",
                f"/logmsgfile:{logmsg_file}",
            ], check=True)

            # 提交窗口打开后删除临时文件（保留一段时间让TortoiseSVN读取）
            # 使用定时器延迟删除
            import threading
            def cleanup():
                try:
                    logmsg_file.unlink()
                except:
                    pass
            threading.Timer(5.0, cleanup).start()

            return True
        except Exception as e:
            print(f"TortoiseSVN 提交失败: {e}")
            return False

    def command_commit(self, path: Path, message: str, files: Optional[List[Path]] = None) -> bool:
        """使用 svn 命令行提交"""
        try:
            cmd = ["svn", "commit"]

            if files:
                for f in files:
                    cmd.append(str(f))
            else:
                cmd.append(str(path))

            cmd.extend(["-m", message])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return result.returncode == 0
        except Exception as e:
            print(f"svn commit 失败: {e}")
            return False

    def generate_commit_message(self, status_list: List[Tuple[str, str]]) -> str:
        """根据状态列表生成提交信息

        Args:
            status_list: SVN 状态列表 [(filename, status_code), ...]

        Returns:
            生成的提交信息
        """
        added = [f for f, s in status_list if s == "A"]
        modified = [f for f, s in status_list if s == "M"]
        deleted = [f for f, s in status_list if s == "D"]
        untracked = [f for f, s in status_list if s == "?"]

        lines = []

        total = len(added) + len(modified) + len(deleted)
        if total == 0 and not untracked:
            return "无变更"

        lines.append(f"更新 {total} 个文件")

        if added:
            lines.append("\n新增：")
            for f in added[:10]:  # 最多显示10个
                lines.append(f"  - {Path(f).name}")
            if len(added) > 10:
                lines.append(f"  - ... 共 {len(added)} 个")

        if modified:
            lines.append("\n修改：")
            for f in modified[:10]:
                lines.append(f"  - {Path(f).name}")
            if len(modified) > 10:
                lines.append(f"  - ... 共 {len(modified)} 个")

        if deleted:
            lines.append("\n删除：")
            for f in deleted[:10]:
                lines.append(f"  - {Path(f).name}")
            if len(deleted) > 10:
                lines.append(f"  - ... 共 {len(deleted)} 个")

        lines.append("\n[请补充详细说明]")

        return "\n".join(lines)
