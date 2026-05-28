"""
备份对话框 - 选择备份路径、显示备份进度
"""

from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFileDialog, QProgressBar,
    QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from src.core.backup_manager import BackupManager
from src.core.history_manager import HistoryManager


class BackupWorker(QThread):
    """备份工作线程"""
    progress = pyqtSignal(int)  # 进度信号
    finished = pyqtSignal(Path)  # 完成信号
    error = pyqtSignal(str)  # 错误信号

    def __init__(self, source_path: Path, backup_dir: Path, backup_name: str):
        super().__init__()
        self.source_path = source_path
        self.backup_dir = backup_dir
        self.backup_name = backup_name
        self.backup_manager = BackupManager(backup_dir)

    def run(self):
        """执行备份"""
        try:
            self.progress.emit(10)
            zip_path = self.backup_manager.backup_to_zip(
                self.source_path,
                self.backup_name
            )
            self.progress.emit(100)
            self.finished.emit(zip_path)
        except Exception as e:
            self.error.emit(str(e))


class BackupDialog(QDialog):
    """备份对话框"""

    def __init__(self, source_path: Path, history_manager: HistoryManager = None, parent=None):
        super().__init__(parent)
        self.source_path = source_path
        self.history_manager = history_manager or HistoryManager()
        self.result_path: Path | None = None
        self.init_ui()

    def init_ui(self):
        """初始化 UI"""
        self.setWindowTitle("备份 SVN 目录")
        self.setMinimumWidth(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 源目录显示
        source_bar = QWidget()
        source_layout = QHBoxLayout(source_bar)
        source_layout.setContentsMargins(0, 0, 0, 0)

        source_label = QLabel("备份目录：")
        source_layout.addWidget(source_label)

        source_path_label = QLabel(self.source_path.name)
        source_path_label.setStyleSheet("font-weight: bold;")
        source_layout.addWidget(source_path_label)

        source_layout.addStretch()
        layout.addWidget(source_bar)

        # 备份路径选择
        backup_bar = QWidget()
        backup_layout = QHBoxLayout(backup_bar)
        backup_layout.setContentsMargins(0, 0, 0, 0)

        backup_label = QLabel("保存位置：")
        backup_layout.addWidget(backup_label)

        self.backup_edit = QLineEdit()
        self.backup_edit.setPlaceholderText("选择备份保存目录...")
        self.backup_edit.setReadOnly(True)
        backup_layout.addWidget(self.backup_edit)

        self.select_btn = QPushButton("选择")
        self.select_btn.setMaximumWidth(60)
        self.select_btn.clicked.connect(self.select_backup_dir)
        backup_layout.addWidget(self.select_btn)

        layout.addWidget(backup_bar)

        # 备份路径：优先使用记忆的路径，否则使用默认路径
        remembered_dir = self.history_manager.get_backup_dir()
        if remembered_dir and remembered_dir.exists():
            self.backup_dir = remembered_dir
        else:
            default_backup_dir = Path.home() / "Documents" / "MMY_SvnGo_Backups"
            default_backup_dir.mkdir(parents=True, exist_ok=True)
            self.backup_dir = default_backup_dir
        self.backup_edit.setText(str(self.backup_dir))

        # 备份文件名预览
        name_bar = QWidget()
        name_layout = QHBoxLayout(name_bar)
        name_layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel("文件名：")
        name_layout.addWidget(name_label)

        # 检查文件夹名是否已包含时间戳格式（YYYYMMDD_HHMMSS）
        import re
        folder_name = self.source_path.name
        if re.search(r'\d{8}_\d{6}', folder_name):
            # 如果已包含时间戳，添加 SVN 前缀
            default_name = f"SVN_{folder_name}"
        else:
            # 否则添加时间戳和 SVN 前缀
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"SVN_{folder_name}_{timestamp}"
        self.name_edit = QLineEdit(default_name)
        name_layout.addWidget(self.name_edit)

        layout.addWidget(name_bar)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # 按钮
        btn_bar = QWidget()
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(0, 0, 0, 0)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.backup_btn = QPushButton("开始备份")
        self.backup_btn.setStyleSheet("QPushButton { background: #4a90d9; color: white; }")
        self.backup_btn.clicked.connect(self.start_backup)
        btn_layout.addWidget(self.backup_btn)

        layout.addWidget(btn_bar)

    def select_backup_dir(self):
        """选择备份保存目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择备份保存目录",
            str(self.backup_dir)
        )
        if dir_path:
            self.backup_dir = Path(dir_path)
            self.backup_edit.setText(dir_path)
            # 记忆备份路径
            self.history_manager.set_backup_dir(self.backup_dir)

    def start_backup(self):
        """开始备份"""
        backup_name = self.name_edit.text()
        if not backup_name:
            QMessageBox.warning(self, "提示", "请输入备份文件名")
            return

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.backup_btn.setEnabled(False)
        self.select_btn.setEnabled(False)
        self.name_edit.setEnabled(False)

        # 创建备份工作线程
        self.worker = BackupWorker(
            self.source_path,
            self.backup_dir,
            backup_name
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, value: int):
        """更新进度"""
        self.progress_bar.setValue(value)

    def on_finished(self, zip_path: Path):
        """备份完成"""
        self.result_path = zip_path
        QMessageBox.information(
            self,
            "备份完成",
            f"备份已保存到：\n{zip_path}\n\n文件大小：{zip_path.stat().st_size / (1024*1024):.2f} MB"
        )
        self.accept()

    def on_error(self, error_msg: str):
        """备份失败"""
        QMessageBox.warning(self, "备份失败", f"备份过程中发生错误：\n{error_msg}")
        self.progress_bar.setVisible(False)
        self.backup_btn.setEnabled(True)
        self.select_btn.setEnabled(True)
        self.name_edit.setEnabled(True)