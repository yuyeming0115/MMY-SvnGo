import os
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from PyQt6.QtWidgets import QApplication
    from src.core.history_manager import HistoryManager

    with tempfile.TemporaryDirectory() as tmp:
        HistoryManager.CONFIG_FILE = Path(tmp) / "history.json"

        from src.ui.main_window import MainWindow

        app = QApplication.instance() or QApplication(sys.argv)
        window = MainWindow()

        assert window.windowTitle()
        assert window.local_panel is not None
        assert window.svn_panel is not None
        assert window.diff_panel is not None
        assert window.local_preview is not None
        assert window.svn_preview is not None

        with redirect_stdout(StringIO()):
            window.close()
        app.quit()

    print("GUI smoke OK")


if __name__ == "__main__":
    main()
