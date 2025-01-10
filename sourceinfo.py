from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QCheckBox, QPushButton, QFileDialog, QScrollArea, QSizePolicy, QListWidget, QListWidgetItem)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QFileInfo
from PyQt5.QtGui import QImage, QPixmap
import cv2
import os
import wave
import mutagen
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

class MediaInfo:
    def __init__(self, file_path):
        self.file_path = file_path
        self.file_info = QFileInfo(file_path)
        self.file_size = self.file_info.size()
        self.format = self.file_info.suffix().lower()
        self.duration = 0
        self.width = 0
        self.height = 0
        self.fps = 0
        self.is_video = False
        self.thumbnail = None
        
        self._read_media_info()
    
    def _read_media_info(self):
        """读取媒体文件信息"""
        if self.format in ['mp4', 'avi', 'mkv', 'mpeg', 'mov']:
            self._read_video_info()
        elif self.format in ['wav', 'mp3', 'wma']:
            self._read_audio_info()
    
    def _read_video_info(self):
        """读取视频信息"""
        try:
            cap = cv2.VideoCapture(self.file_path)
            if cap.isOpened():
                self.is_video = True
                self.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                self.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                self.fps = cap.get(cv2.CAP_PROP_FPS)
                total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                self.duration = total_frames / self.fps if self.fps > 0 else 0
                
                # 读取缩略图
                ret, frame = cap.read()
                if ret:
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    if self.width > self.height:
                        self.thumbnail = cv2.resize(frame, (128, 72))
                    else:
                        self.thumbnail = cv2.resize(frame, (72, 128))
            cap.release()
        except Exception as e:
            print(f"读取视频信息错误: {str(e)}")
    
    def _read_audio_info(self):
        """读取音频信息"""
        try:
            if self.format == 'wav':
                with wave.open(self.file_path, 'rb') as wav:
                    frames = wav.getnframes()
                    rate = wav.getframerate()
                    self.duration = frames / float(rate)
            elif self.format == 'mp3':
                audio = MP3(self.file_path)
                self.duration = audio.info.length
            elif self.format == 'wma':
                audio = mutagen.File(self.file_path)
                if audio is not None:
                    self.duration = audio.info.length
        except Exception as e:
            print(f"读取音频信息错误: {str(e)}")
    
    def get_formatted_size(self):
        """返回格式化的文件大小"""
        size_bytes = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.2f} TB"
    
    def get_formatted_duration(self):
        """返回格式化的时长"""
        hours = int(self.duration // 3600)
        minutes = int((self.duration % 3600) // 60)
        seconds = int(self.duration % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

class SourceItem(QWidget):
    """素材项组件"""
    deleted = pyqtSignal(str)  # 发送删除信号，参数为文件路径
    
    def __init__(self, media_info, parent=None):
        super().__init__(parent)
        self.media_info = media_info
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # 缩略图
        thumbnail_label = QLabel()
        if self.media_info.is_video and self.media_info.thumbnail is not None:
            h, w, ch = self.media_info.thumbnail.shape
            img = QImage(self.media_info.thumbnail.data, w, h, w * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
        else:
            # 为音频文件显示默认图标
            pixmap = QPixmap("icons/audio.png")
            if not QFileInfo("icons/audio.png").exists():
                pixmap = QPixmap(72, 72)
                pixmap.fill(Qt.lightGray)
            pixmap = pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
        thumbnail_label.setPixmap(pixmap)
        thumbnail_label.setFixedSize(pixmap.size())
        thumbnail_label.setStyleSheet("QLabel { background-color: #f0f0f0; border: 1px solid #cccccc; }")
        layout.addWidget(thumbnail_label)
        
        # 文件信息
        info_layout = QVBoxLayout()
        
        # 文件名和删除按钮在同一行
        name_layout = QHBoxLayout()
        name_label = QLabel(os.path.basename(self.media_info.file_path))
        name_label.setStyleSheet("QLabel { font-weight: bold; }")
        name_layout.addWidget(name_label)
        name_layout.addStretch()
        
        # 添加删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setFixedWidth(60)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff4444;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #ff6666;
            }
            QPushButton:pressed {
                background-color: #cc0000;
            }
        """)
        delete_btn.clicked.connect(lambda: self.deleted.emit(self.media_info.file_path))
        name_layout.addWidget(delete_btn)
        
        info_layout.addLayout(name_layout)
        
        # 其他信息
        info_text = (
            f"格式: {self.media_info.format.upper()}\n"
            f"大小: {self.media_info.get_formatted_size()}\n"
            f"时长: {self.media_info.get_formatted_duration()}"
        )
        if self.media_info.is_video:
            info_text += f"\n分辨率: {self.media_info.width}x{self.media_info.height}"
            info_text += f"\n帧率: {self.media_info.fps:.2f}fps"
            
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #666666; }")
        info_layout.addWidget(info_label)
        
        layout.addLayout(info_layout, 1)
        
        # 勾选框
        self.checkbox = QCheckBox()
        self.checkbox.setStyleSheet("QCheckBox { margin: 5px; }")
        layout.addWidget(self.checkbox)
        
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        self.setMinimumHeight(90)

class SourceInfo(QWidget):
    source_selected = pyqtSignal(list)  # 发送选中的素材列表信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.sources = []
        self.initUI()
        
    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setStyleSheet("""
            QScrollArea { 
                background-color: white;
                border: none;
            }
            QScrollBar:vertical {
                width: 10px;
            }
            QScrollBar:horizontal {
                height: 10px;
            }
        """)
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(5)
        
        scroll.setWidget(self.content_widget)
        main_layout.addWidget(scroll)
    
    @staticmethod
    def get_media_filters():
        """返回媒体文件过滤器"""
        return "媒体文件 (*.mp4 *.avi *.mkv *.mpeg *.mov *.wav *.mp3 *.wma)"
    
    def add_source(self, file_path):
        """添加新的素材"""
        # 检查文件是否已经存在
        if any(source.media_info.file_path == file_path for source in self.sources):
            return False
        
        # 创建媒体信息对象
        media_info = MediaInfo(file_path)
        source_item = SourceItem(media_info)
        self.sources.append(source_item)
        self.content_layout.addWidget(source_item)
        
        # 连接信号
        source_item.checkbox.stateChanged.connect(self.selection_changed)
        source_item.deleted.connect(self.remove_source)  # 连接删除信号
        return True
    
    def get_selected_sources(self):
        """获取选中的素材列表"""
        return [source.media_info.file_path for source in self.sources 
                if source.checkbox.isChecked()]
    
    def get_selected_source_info(self):
        """获取选中素材的详细信息"""
        return [source.media_info for source in self.sources 
                if source.checkbox.isChecked()]
    
    def selection_changed(self):
        """当选择改变时发出信号"""
        self.source_selected.emit(self.get_selected_sources())
    
    def clear_selection(self):
        """清除所有选择"""
        for source in self.sources:
            source.checkbox.setChecked(False)
    
    def select_all(self):
        """选择所有素材"""
        for source in self.sources:
            source.checkbox.setChecked(True)
    
    def remove_source(self, file_path):
        """删除指定素材"""
        for source in self.sources:
            if source.media_info.file_path == file_path:
                self.content_layout.removeWidget(source)
                self.sources.remove(source)
                source.deleteLater()
                # 发出选择改变信号
                self.selection_changed()
                break 