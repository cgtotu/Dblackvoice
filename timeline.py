from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, 
                           QPushButton, QLabel, QSlider, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap

class TimelineSegment(QWidget):
    """时间线片段组件"""
    def __init__(self, segment, scale_factor=1.0, parent=None):
        super().__init__(parent)
        self.segment = segment
        self.scale_factor = scale_factor
        self.initUI()
    
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # 编号标签
        index_label = QLabel(f"#{self.segment.index:02d}")
        index_label.setFixedWidth(30)
        index_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(index_label)
        
        # 缩略图
        self.thumbnail_label = QLabel()
        self.update_thumbnail()
        layout.addWidget(self.thumbnail_label)
        
        self.setFixedHeight(40)
        self.update_width()
    
    def update_thumbnail(self):
        if self.segment.thumbnail is not None:
            duration = self.segment.end_time - self.segment.start_time
            scaled_width = int(duration * 50 * self.scale_factor)  # 50像素/秒
            scaled_height = 36  # 保持16:9比例
            
            h, w = self.segment.thumbnail.shape[:2]
            img = QImage(self.segment.thumbnail.data, w, h, w * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            scaled_pixmap = pixmap.scaled(scaled_width, scaled_height, 
                                        Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled_pixmap)
            self.thumbnail_label.setFixedSize(scaled_width, scaled_height)
    
    def update_width(self):
        duration = self.segment.end_time - self.segment.start_time
        width = int(duration * 50 * self.scale_factor) + 90  # 基础宽度 + 缩略图宽度
        self.setFixedWidth(width)

class Timeline(QWidget):
    exportVideo = pyqtSignal(list)
    exportAudio = pyqtSignal(list)
    exportScript = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scale_factor = 1.0
        self.segments = []
        self.initUI()
    
    def initUI(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 时间线区域
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(True)
        self.timeline_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.timeline_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.timeline_scroll.setMinimumHeight(150)
        
        # 时间线容器
        self.timeline_widget = QWidget()
        self.timeline_layout = QHBoxLayout(self.timeline_widget)
        self.timeline_layout.setAlignment(Qt.AlignLeft)
        self.timeline_layout.setContentsMargins(5, 5, 5, 5)
        self.timeline_layout.setSpacing(5)
        
        self.timeline_scroll.setWidget(self.timeline_widget)
        layout.addWidget(self.timeline_scroll)
        
        # 底部控制区域
        bottom_layout = QHBoxLayout()
        
        # 缩放控制
        zoom_layout = QHBoxLayout()
        zoom_out_btn = QPushButton("缩小")
        zoom_out_btn.clicked.connect(lambda: self.zoom_changed(self.zoom_slider.value() - 10))
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(10, 200)  # 10% 到 200%
        self.zoom_slider.setValue(100)
        self.zoom_slider.valueChanged.connect(self.zoom_changed)
        
        zoom_in_btn = QPushButton("放大")
        zoom_in_btn.clicked.connect(lambda: self.zoom_slider.setValue(self.zoom_slider.value() + 10))
        
        zoom_layout.addWidget(zoom_out_btn)
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(zoom_in_btn)
        
        bottom_layout.addLayout(zoom_layout)
        bottom_layout.addStretch()
        
        # 导出按钮
        export_layout = QHBoxLayout()
        self.export_video_btn = QPushButton("输出视频")
        self.export_audio_btn = QPushButton("输出音频")
        self.export_script_btn = QPushButton("输出脚本")
        
        self.export_video_btn.clicked.connect(self.export_video)
        self.export_audio_btn.clicked.connect(self.export_audio)
        self.export_script_btn.clicked.connect(self.export_script)
        
        for btn in [self.export_video_btn, self.export_audio_btn, self.export_script_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    padding: 5px 15px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            export_layout.addWidget(btn)
        
        bottom_layout.addLayout(export_layout)
        layout.addLayout(bottom_layout)
    
    def clear_segments(self):
        """清除所有片段"""
        for segment in self.segments:
            self.timeline_layout.removeWidget(segment)
            segment.deleteLater()
        self.segments.clear()
    
    def zoom_changed(self, value):
        """处理缩放变化"""
        self.scale_factor = value / 100.0
        for segment in self.segments:
            segment.scale_factor = self.scale_factor
            segment.update_thumbnail()
            segment.update_width()
    
    def export_video(self):
        """导出视频"""
        if self.segments:
            segment_info = []
            for segment in self.segments:
                info = {
                    'file_path': segment.segment.file_path,
                    'start_time': segment.segment.start_time,
                    'end_time': segment.segment.end_time
                }
                segment_info.append(info)
            self.exportVideo.emit(segment_info)
    
    def export_audio(self):
        """导出音频"""
        if self.segments:
            segment_info = []
            for segment in self.segments:
                info = {
                    'file_path': segment.segment.file_path,
                    'start_time': segment.segment.start_time,
                    'end_time': segment.segment.end_time
                }
                segment_info.append(info)
            self.exportAudio.emit(segment_info)
    
    def export_script(self):
        """导出脚本"""
        if self.segments:
            segment_info = []
            for segment in self.segments:
                info = {
                    'file_path': segment.segment.file_path,
                    'start_time': segment.segment.start_time,
                    'end_time': segment.segment.end_time
                }
                segment_info.append(info)
            self.exportScript.emit(segment_info)
    
    def add_segments(self, segments):
        """添加时间段到时间线"""
        # 清除现有片段
        self.clear_segments()
        
        # 添加新片段
        for segment in segments:
            timeline_segment = TimelineSegment(segment, self.scale_factor)
            self.segments.append(timeline_segment)
            self.timeline_layout.addWidget(timeline_segment) 