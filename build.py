"""
MMY SvnGo 跨平台打包脚本
=========================
支持 Windows (.exe) 和 macOS (.app)
用法: python build.py [--no-release] [--version X.X.X]

注意事项:
  - PyInstaller 不支持交叉编译，需在目标平台上运行
  - Windows 打包 → 在 Windows 上运行此脚本
  - macOS 打包   → 在 Mac 上运行此脚本
"""

import subprocess
import shutil
import sys
import os
import platform
import argparse
from pathlib import Path
from datetime import datetime
import re


# ============================================================
# 路径配置
# ============================================================
project_root = Path(__file__).parent.resolve()
dist_dir = project_root / "dist"
release_dir = project_root / "release"
build_dir = project_root / "build"
assets_dir = project_root / "assets"

# App 名称（不含空格，PyInstaller 用）
APP_NAME = "MMY_SvnGo"
APP_DISPLAY = "MMY SvnGo"

# ============================================================
# 平台检测
# ============================================================
IS_WINDOWS = platform.system() == "Windows"
IS_MAC = platform.system() == "Darwin"


def get_version():
    """从 main.py 获取版本号"""
    main_file = project_root / "src" / "main.py"
    content = main_file.read_text(encoding="utf-8")
    match = re.search(r'setApplicationVersion\("([\d.]+)"\)', content)
    return match.group(1) if match else "0.1.0"


def check_pyinstaller():
    """检查 PyInstaller 是否已安装"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  PyInstaller {result.stdout.strip()}")
            return True
    except Exception:
        pass

    print("[错误] 未检测到 PyInstaller")
    print("  请运行: pip install pyinstaller")
    return False


def clean_build():
    """清理旧的构建文件"""
    for d in [dist_dir, build_dir]:
        if d.exists():
            print(f"[清理] 删除 {d.name}/")
            shutil.rmtree(d)

    # 清理临时文件（排除 .gitkeep 等）
    for f in project_root.glob("*.spec.bak"):
        f.unlink()


def find_icon():
    """查找图标文件"""
    if IS_WINDOWS:
        # Windows 优先用 .ico
        ico = assets_dir / "icon.ico"
        if ico.exists():
            return ico
    elif IS_MAC:
        # macOS 优先用 .icns
        icns = assets_dir / "icon.icns"
        if icns.exists():
            return icns
        # 也支持 .png 自动转 .icns
        png = assets_dir / "icon.png"
        if png.exists():
            return png

    return None


def get_pyinstaller_cmd():
    """
    构建 PyInstaller 命令行参数
    使用 --onefile 模式，单文件输出
    """
    main_script = project_root / "src" / "main.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(main_script),
        "--name", APP_NAME,
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--workpath", str(build_dir),
        "--distpath", str(dist_dir),
        "--specpath", str(build_dir),
    ]

    # ---- 隐藏导入 ----
    hidden_imports = [
        "PyQt6", "PyQt6.QtCore", "PyQt6.QtGui", "PyQt6.QtWidgets",
        "PIL", "PIL.Image",
    ]
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])

    # ---- 排除大模块（减小体积）----
    excludes = ["tkinter", "matplotlib", "numpy", "scipy", "pandas", "jedi", "IPython"]
    for exc in excludes:
        cmd.extend(["--exclude-module", exc])

    # ---- 收集源码目录（确保模块能被找到）----
    cmd.extend(["--paths", str(project_root)])
    cmd.extend(["--paths", str(project_root / "src")])

    # ---- 平台特定参数 ----
    if IS_WINDOWS:
        icon = find_icon()
        if icon:
            cmd.extend(["--icon", str(icon)])
        # UPX 压缩（如果可用）
        # cmd.append("--upx-dir")
        # cmd.append("path/to/upx")

    elif IS_MAC:
        icon = find_icon()
        if icon:
            cmd.extend(["--icon", str(icon)])
        cmd.extend(["--osx-bundle-identifier", "com.mmy.svngo"])

    return cmd


def find_output():
    """查找打包输出文件"""
    if not dist_dir.exists():
        return None

    if IS_WINDOWS:
        exe = dist_dir / f"{APP_NAME}.exe"
        if exe.exists():
            return exe
    elif IS_MAC:
        # onefile 模式输出单个可执行文件
        exe = dist_dir / APP_NAME
        if exe.exists():
            return exe

    # 兜底搜索
    for ext in [".exe", ".app", ""]:
        for f in dist_dir.iterdir():
            name = f.name.lower()
            if name.startswith(APP_NAME.lower()) and (not ext or f.suffix.lower() == ext.lower()):
                return f

    return None


def build():
    """执行打包，返回输出文件路径"""
    print("=" * 60)
    print(f"  {APP_DISPLAY} 打包脚本")
    print(f"  平台: {platform.system()} {platform.machine()}")
    print(f"  Python: {platform.python_version()}")
    print("=" * 60)
    print()

    # 前置检查
    if not check_pyinstaller():
        return None

    # 显示打包路径
    print(f"  源代码: {project_root / 'src'}")
    print(f"  输出目录: {dist_dir}")
    print()

    # 清理
    clean_build()

    # 执行 PyInstaller
    cmd = get_pyinstaller_cmd()
    print(f"[打包] 执行 PyInstaller ...")
    print(f"  (这可能需要几分钟，请耐心等待)")
    print()

    result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)

    if result.returncode != 0:
        print("\n[错误] 打包失败!")
        # 显示关键错误信息
        stderr_lines = result.stderr.strip().split("\n")
        for line in stderr_lines[-20:]:
            if line.strip():
                print(f"  {line}")
        return None

    # 查找输出
    output_file = find_output()
    if output_file is None:
        print("[错误] 打包完成但未找到输出文件。")
        print(f"  请检查 {dist_dir} 目录")
        return None

    size_mb = output_file.stat().st_size / (1024 * 1024)
    print(f"\n[成功] 打包完成!")
    print(f"  文件: {output_file.name}")
    print(f"  大小: {size_mb:.2f} MB")
    print(f"  路径: {output_file}")
    print()

    return output_file


def create_release(output_file, version=None):
    """
    创建发布包
    将打包产物复制到 release/v{version}/ 并生成 README
    """
    if version is None:
        version = get_version()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 平台标识
    if IS_WINDOWS:
        platform_tag = "win"
        platform_name = "Windows"
    elif IS_MAC:
        platform_tag = "mac"
        platform_name = "macOS"
    else:
        platform_tag = platform.system().lower()
        platform_name = platform.system()

    # 发布目录
    version_dir = release_dir / f"v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    # 目标文件名：Windows 遵循项目发布规范，macOS 保留平台标识
    ext = output_file.suffix
    if IS_WINDOWS:
        target_name = f"{APP_NAME}_v{version}_{timestamp}{ext}"
    else:
        target_name = f"{APP_NAME}_v{version}_{platform_tag}_{timestamp}{ext}"
    target_file = version_dir / target_name

    # 复制文件
    print(f"[发布] 复制到发布目录...")
    print(f"  {output_file.name} -> {target_name}")

    if output_file.is_dir():
        if target_file.exists():
            shutil.rmtree(target_file)
        shutil.copytree(output_file, target_file)
    else:
        shutil.copy2(output_file, target_file)

    # 生成 README.txt
    readme_name = f"README_v{version}.txt"
    readme_file = version_dir / readme_name
    if IS_WINDOWS:
        usage_text = f"  Windows: 双击 {target_name}"
    elif IS_MAC:
        usage_text = f"  macOS: 双击 {target_name} 或在终端运行 ./{target_name}"
    else:
        usage_text = f"  运行: ./{target_name}"

    readme_content = f"""MMY SvnGo 发布说明
==================

版本: {version}
平台: {platform_name}
时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

文件:
  {target_name}

系统要求:
  - {platform_name}
  - 需要 TortoiseSVN（Windows）/ svn 命令行工具（macOS）

使用方法:
{usage_text}

功能说明:
  - 文件同步工具，用于 SVN 项目文件管理
  - 支持本地文件与 SVN 仓库之间的智能对比和同步
  - 支持图片预览、键盘导航、历史记录、收藏夹等

项目地址:
  {project_root.name}
"""
    readme_file.write_text(readme_content, encoding="utf-8")
    print(f"  {readme_name}")

    latest_dir = update_latest_release(version, target_file, readme_file, target_name)

    print(f"\n[发布] 完成!")
    print(f"  目录: {version_dir}")
    print(f"  最新: {latest_dir}")
    print()

    return version_dir


def update_latest_release(version, target_file, readme_file, target_name):
    """更新 release/latest 和 LATEST.txt，方便快速找到最新发布包。"""
    latest_dir = release_dir / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)

    for old_file in latest_dir.iterdir():
        if old_file.is_file():
            old_file.unlink()
        elif old_file.is_dir():
            shutil.rmtree(old_file)

    latest_target = latest_dir / target_name
    if target_file.is_dir():
        shutil.copytree(target_file, latest_target)
    else:
        shutil.copy2(target_file, latest_target)

    latest_readme = latest_dir / readme_file.name
    shutil.copy2(readme_file, latest_readme)

    latest_note = release_dir / "LATEST.txt"
    latest_note.write_text(
        "\n".join([
            "MMY SvnGo 最新发布",
            "==================",
            f"版本: {version}",
            f"文件: latest/{target_name}",
            f"说明: latest/{readme_file.name}",
            f"源目录: v{version}/",
        ]) + "\n",
        encoding="utf-8",
    )

    return latest_dir


def main():
    parser = argparse.ArgumentParser(
        description=f"{APP_DISPLAY} 跨平台打包脚本"
    )
    parser.add_argument(
        "--no-release", action="store_true",
        help="仅打包，不复制到发布目录"
    )
    parser.add_argument(
        "--version", type=str, default=None,
        help="覆盖版本号（默认从 main.py 读取）"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="测试模式：打包后尝试运行检测"
    )
    args = parser.parse_args()

    version = args.version or get_version()
    print(f"\n  [版本] {version}\n")

    # Step 1: 打包
    output_file = build()
    if output_file is None:
        print("\n  打包失败，请检查上方错误信息。")
        sys.exit(1)

    # Step 2: 发布
    if not args.no_release:
        create_release(output_file, version)

    # Step 3: 可选测试
    if args.test and output_file:
        print(f"[测试] 尝试运行 {output_file.name} ...")
        try:
            subprocess.run([str(output_file)], timeout=5)
        except subprocess.TimeoutExpired:
            print("  (程序已启动，5秒后自动结束)")
        except Exception as e:
            print(f"  [警告] 运行测试失败: {e}")

    print("=" * 60)
    print("  全部完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
