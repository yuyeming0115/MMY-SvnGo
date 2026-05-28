"""
MMY SvnGo 打包脚本
"""

import subprocess
import shutil
from pathlib import Path
from datetime import datetime
import re

project_root = Path(__file__).parent
dist_dir = project_root / "dist"
release_dir = project_root / "release"

def get_version():
    """从 main.py 获取版本号"""
    main_file = project_root / "src" / "main.py"
    content = main_file.read_text(encoding="utf-8")
    match = re.search(r'setApplicationVersion\("([\d.]+)"\)', content)
    return match.group(1) if match else "0.1.0"

def build():
    """执行打包"""
    print("=" * 50)
    print("MMY SvnGo 打包脚本")
    print("=" * 50)

    # 清理旧的打包文件
    if dist_dir.exists():
        print(f"[清理] 删除 {dist_dir}")
        shutil.rmtree(dist_dir)

    # 执行 PyInstaller
    print("[打包] 执行 PyInstaller...")
    spec_file = project_root / "MMY_SvnGo.spec"
    result = subprocess.run(
        ["pyinstaller", str(spec_file), "--clean", "--noconfirm"],
        cwd=project_root,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("[错误] 打包失败:")
        print(result.stderr)
        return False

    print("[完成] 打包成功")

    # 检查输出文件
    exe_file = dist_dir / "MMY SvnGo.exe"
    if not exe_file.exists():
        print("[错误] 未找到输出文件")
        return False

    print(f"[输出] {exe_file}")
    print(f"[大小] {exe_file.stat().st_size / (1024*1024):.2f} MB")

    return True

def create_release():
    """创建发布包"""
    version = get_version()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 创建发布目录
    if not release_dir.exists():
        release_dir.mkdir()

    # 创建版本目录
    version_dir = release_dir / f"v{version}"
    if not version_dir.exists():
        version_dir.mkdir()

    # 复制文件
    exe_file = dist_dir / "MMY SvnGo.exe"
    target_file = version_dir / f"MMY_SvnGo_v{version}_{timestamp}.exe"

    print(f"[复制] {exe_file} -> {target_file}")
    shutil.copy2(exe_file, target_file)

    # 创建 README.txt
    readme_file = version_dir / f"README_v{version}_{timestamp}.txt"
    readme_content = f"""
MMY SvnGo 发布说明
==================

版本: {version}
时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

文件列表:
- MMY_SvnGo_v{version}_{timestamp}.exe

功能说明:
- 文件同步工具，用于 SVN 项目文件管理
- 支持本地文件与 SVN 仓库之间的智能对比和同步
- 支持图片预览、键盘导航、历史记录等

使用方法:
1. 双击运行 MMY_SvnGo.exe
2. 左侧拖入本地文件夹，右侧拖入 SVN 文件夹
3. 点击"传输"按钮执行同步

依赖说明:
- 需要 TortoiseSVN（用于 SVN 操作）
"""
    readme_file.write_text(readme_content, encoding="utf-8")

    print(f"[发布] 发布目录: {version_dir}")
    print(f"[文件] {target_file.name}")
    print(f"[文件] {readme_file.name}")

    return True

def main():
    """主函数"""
    print(f"[版本] {get_version()}")

    if build():
        create_release()
    print("=" * 50)
    print("打包完成!")

if __name__ == "__main__":
    main()