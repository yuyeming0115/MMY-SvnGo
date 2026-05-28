"""
MMY SvnGo - 程序入口
"""

import sys
from pathlib import Path

# 添加项目根目录到 sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    """程序入口函数"""
    app = QApplication(sys.argv)
    app.setApplicationName("MMY SvnGo")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()