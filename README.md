# MMY SvnGo

MMY SvnGo 是一个面向 SVN 项目文件管理的桌面同步工具，主要用于本地资源目录与 SVN 工作目录之间的对比、预览、备份和传输。

## 主要功能

- 左侧拖入本地目录，右侧拖入 SVN 目录，自动扫描并对比文件。
- SVN 模式支持设置 SVN 父级目录，拖入本地目录后自动匹配或创建右侧同名目录。
- 差异列表支持“待处理 / 风险 / 全部”筛选。
- 支持图片预览、透明边缘裁剪、棋盘格背景和统一裁剪范围。
- 传输前提示 SVN 较新风险项，避免误覆盖。
- 支持后台刷新、后台传输、后台统一裁剪计算。
- 新文件传输后使用 `svn add --parents` 加入版本控制。
- 支持 SVN 目录备份和发布打包。

## 环境要求

- Python 3.10+
- Windows 推荐安装 TortoiseSVN
- 如需命令行 SVN 操作，需要 `svn` 命令可用

Python 依赖见 [requirements.txt](requirements.txt)。

## 安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

如果系统里 `python` 命令不可用，可以尝试：

```powershell
py -3 -m pip install -r requirements.txt
```

## 运行应用

在项目根目录执行：

```powershell
python -m src.main
```

也可以直接运行入口文件：

```powershell
python src\main.py
```

## 运行测试

核心逻辑测试不依赖 PyQt6，可以在项目根目录执行：

```powershell
python -m unittest discover -s tests
```

语法检查：

```powershell
python -m compileall -q src tests build.py
```

GUI 烟测（需要 PyQt6）：

```powershell
python tests\gui_smoke.py
```

当前测试覆盖：

- SVN 较新文件优先标记为风险项。
- 图片尺寸缓存逻辑。
- `svn add --parents` 参数。
- SVN 工具可用状态查询。
- 主窗口基础初始化和首次使用入口 smoke 检查。

## 打包发布

Windows 下执行：

```powershell
python build.py
```

也可以使用一键脚本：

```powershell
.\build.bat
```

仅打包、不复制到发布目录：

```powershell
python build.py --no-release
```

指定版本号：

```powershell
python build.py --version 0.1.1
```

发布产物会输出到：

```text
release/v{版本号}/
```

最新发布包也会同步到：

```text
release/latest/
release/LATEST.txt
```

Windows 发布文件命名格式：

```text
MMY_SvnGo_v{版本号}_{时间戳}.exe
```

macOS 可使用：

```bash
./build.sh
```

## 基本使用流程

1. 启动应用。
2. 首次使用时，可在顶部状态区点击“检查 SVN 工具”确认环境。
3. 在 SVN 模式下，点击“设置 SVN 父级目录”选择 SVN 项目父目录。
4. 点击“选择本地目录”或将本地资源目录拖入左侧。
5. 工具会自动匹配或创建右侧 SVN 同名目录。
6. 查看差异列表和左右图片预览。
7. 填写更新说明。
8. 点击“传输”，确认文件清单和 SVN 风险提示。
9. 传输完成后确认 SVN 提交窗口。

## 开发文档

- [开发计划](开发文档/开发计划.md)
- [工作流安全与心流优化方案](开发文档/工作流安全与心流优化方案.md)

## 注意事项

- 当前 GUI 运行依赖 PyQt6；只运行核心测试时不需要启动界面。
- SVN 较新文件会作为风险项提示，默认不会被传输覆盖。
- 大目录首次扫描仍可能耗时，后续重复扫描会利用图片元数据缓存降低成本。
