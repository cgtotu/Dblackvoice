from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QLineEdit, QCheckBox, QScrollArea,
                           QFrame, QSizePolicy, QSpacerItem, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QImage, QPixmap, QDoubleValidator
import cv2
import numpy as np
import librosa

class TimeSegmentItem(QWidget):
    """时间区间项目"""
    deleted = pyqtSignal(int)  # 发送删除信号
    timeChanged = pyqtSignal(int, float, float)  # 发送时间改变信号
    playClicked = pyqtSignal(str, float, float, 'PyQt_PyObject')  # 修改信号
    
    def __init__(self, index, file_path, start_time, end_time, thumbnail, parent=None):
        super().__init__(parent)
        self.index = index
        self.file_path = file_path
        self.start_time = start_time
        self.end_time = end_time
        self.thumbnail = thumbnail
        self.is_playing = False
        self.initUI()
        
    def initUI(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # 行编号
        index_label = QLabel(f"#{self.index:02d}")
        index_label.setFixedWidth(30)
        index_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(index_label)
        
        # 缩略图
        thumbnail_label = QLabel()
        if isinstance(self.thumbnail, np.ndarray):
            h, w, ch = self.thumbnail.shape
            img = QImage(self.thumbnail.data, w, h, w * 3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            thumbnail_label.setPixmap(pixmap)
            thumbnail_label.setFixedSize(pixmap.size())
        thumbnail_label.setStyleSheet("border: 1px solid #ccc;")
        layout.addWidget(thumbnail_label)
        
        # 时间输入区域
        time_group = QWidget()
        time_layout = QHBoxLayout(time_group)
        time_layout.setContentsMargins(0, 0, 0, 0)
        
        # 开始时间
        time_layout.addWidget(QLabel("开始:"))
        self.start_edit = QLineEdit(f"{self.start_time:.2f}")
        self.start_edit.setValidator(QDoubleValidator(0, 999999, 2))
        self.start_edit.setFixedWidth(70)
        self.start_edit.textChanged.connect(self.time_changed)
        time_layout.addWidget(self.start_edit)
        
        # 结束时间
        time_layout.addWidget(QLabel("结束:"))
        self.end_edit = QLineEdit(f"{self.end_time:.2f}")
        self.end_edit.setValidator(QDoubleValidator(0, 999999, 2))
        self.end_edit.setFixedWidth(70)
        self.end_edit.textChanged.connect(self.time_changed)
        time_layout.addWidget(self.end_edit)
        
        layout.addWidget(time_group)
        
        # 播放/暂停按钮
        self.play_btn = QPushButton("播放")
        self.play_btn.setFixedWidth(60)
        self.play_btn.clicked.connect(self.toggle_play)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(self.play_btn)
        
        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setFixedWidth(60)
        delete_btn.clicked.connect(lambda: self.deleted.emit(self.index))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        layout.addWidget(delete_btn)
        
        # 勾选框
        self.checkbox = QCheckBox()
        layout.addWidget(self.checkbox)
        
        # 设置整体样式
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            QLineEdit {
                padding: 3px;
                border: 1px solid #ccc;
                border-radius: 2px;
            }
            QLabel {
                border: none;
            }
        """)
        self.setMinimumHeight(90)
    
    def toggle_play(self):
        """切换播放状态"""
        self.is_playing = not self.is_playing
        self.play_btn.setText("暂停" if self.is_playing else "播放")
        if self.is_playing:
            self.playClicked.emit(
                self.file_path,
                float(self.start_edit.text()),
                float(self.end_edit.text()),
                self
            )
    
    def time_changed(self):
        """时间输入改变处理"""
        try:
            start = float(self.start_edit.text())
            end = float(self.end_edit.text())
            if start < end:
                self.timeChanged.emit(self.index, start, end)
        except ValueError:
            pass
    
    def update_play_state(self, is_playing):
        """更新播放状态"""
        self.is_playing = is_playing
        self.play_btn.setText("暂停" if is_playing else "播放")

class TimeCutter(QWidget):
    segments_created = pyqtSignal(list)  # 发送创建的时间段列表信号
    play_segment = pyqtSignal(str, float, float)  # 发送播放片段信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.segments = []
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
            }
            QScrollBar:vertical {
                width: 10px;
            }
        """)
        
        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setAlignment(Qt.AlignTop)
        self.content_layout.setSpacing(5)
        
        self.scroll.setWidget(self.content_widget)
        layout.addWidget(self.scroll)
        
        # 添加放入时间线按钮
        self.add_to_timeline_btn = QPushButton("放入时间线")
        self.add_to_timeline_btn.clicked.connect(self.add_to_timeline)
        self.add_to_timeline_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 5px;
                border: none;
                border-radius: 3px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(self.add_to_timeline_btn)
    
    def auto_cut(self, audio_data):
        """执行自动剪辑"""
        if not audio_data or 'waveform' not in audio_data:
            return
        
        try:
            # 获取音频数据
            y = audio_data['waveform']
            sr = audio_data['sr']
            selected_range = audio_data['selected_range']
            min_db = selected_range[0]
            max_db = selected_range[1]
            
            # 优化参数设置
            frame_length = 256  # 减小帧长度以提高精度
            hop_length = 64     # 减小步长以提高时间精度
            
            # 计算RMS能量
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            db_values = librosa.amplitude_to_db(rms, ref=np.max)
            
            # 查找符合条件的时间段
            segments = []
            current_start = None
            MAX_SILENCE_LENGTH = 0.05  # 最大空白时长（秒）
            MIN_SEGMENT_LENGTH = 0.1   # 最小有效片段时长（秒）
            SAMPLES_PER_SECOND = sr / hop_length
            MAX_SILENCE_SAMPLES = int(MAX_SILENCE_LENGTH * SAMPLES_PER_SECOND)
            MIN_SEGMENT_SAMPLES = int(MIN_SEGMENT_LENGTH * SAMPLES_PER_SECOND)
            
            silence_count = 0
            
            for i, db_val in enumerate(db_values):
                is_valid = min_db <= db_val <= max_db
                
                if current_start is None:
                    if is_valid:
                        current_start = i
                        silence_count = 0
                else:
                    if not is_valid:
                        silence_count += 1
                        if silence_count >= MAX_SILENCE_SAMPLES:
                            # 如果静音时长超过阈值，结束当前片段
                            segment_length = i - current_start - silence_count
                            if segment_length >= MIN_SEGMENT_SAMPLES:
                                segments.append((current_start, i - silence_count))
                            current_start = None
                            silence_count = 0
                    else:
                        silence_count = 0
            
            # 处理最后一个片段
            if current_start is not None:
                segment_length = len(db_values) - current_start
                if segment_length >= MIN_SEGMENT_SAMPLES:
                    segments.append((current_start, len(db_values)))
            
            # 转换为实际时间
            time_segments = []
            for start, end in segments:
                start_time = start / SAMPLES_PER_SECOND
                end_time = end / SAMPLES_PER_SECOND
                time_segments.append((start_time, end_time))
            
            # 创建时间段项目
            self.clear_segments()
            for i, (start, end) in enumerate(time_segments):
                self.add_segment(i + 1, start, end, audio_data.get('sources', [None])[0])
                
        except Exception as e:
            print(f"自动剪辑错误: {str(e)}")
    
    def _merge_close_segments(self, segments, min_gap):
        """合并间隔太小的片段"""
        if not segments:
            return []
        
        merged = []
        current_start, current_end = segments[0]
        
        for start, end in segments[1:]:
            if start - current_end <= min_gap:
                # 如果两个片段间隔小于最小间隔，则合并
                current_end = end
            else:
                # 否则保存当前片段，开始新片段
                merged.append((current_start, current_end))
                current_start, current_end = start, end
        
        # 添加最后一个片段
        merged.append((current_start, current_end))
        
        return merged
    
    def add_segment(self, index, start_time, end_time, file_path=None):
        """添加时间段"""
        # 获取缩略图
        thumbnail = self.get_thumbnail(file_path, start_time) if file_path else None
        
        # 创建时间段项目
        segment = TimeSegmentItem(index, file_path, start_time, end_time, thumbnail)
        segment.deleted.connect(self.remove_segment)
        segment.timeChanged.connect(self.update_segment_time)
        segment.playClicked.connect(self.play_segment.emit)
        
        self.segments.append(segment)
        self.content_layout.addWidget(segment)
    
    def get_thumbnail(self, file_path, time):
        """获取指定时间的缩略图"""
        try:
            cap = cv2.VideoCapture(file_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, time * 1000)
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w = frame.shape[:2]
                if w > h:
                    thumbnail = cv2.resize(frame, (128, 72))
                else:
                    thumbnail = cv2.resize(frame, (72, 128))
                return thumbnail
        except Exception as e:
            print(f"获取缩略图错误: {str(e)}")
        finally:
            cap.release()
        return None
    
    def clear_segments(self):
        """清除所有片段"""
        for segment in self.segments:
            self.content_layout.removeWidget(segment)
            segment.deleteLater()
        self.segments.clear()
    
    def remove_segment(self, index):
        """删除指定片段"""
        for segment in self.segments:
            if segment.index == index:
                self.content_layout.removeWidget(segment)
                self.segments.remove(segment)
                segment.deleteLater()
                break
    
    def update_segment_time(self, index, start_time, end_time):
        """更新片段时间"""
        for segment in self.segments:
            if segment.index == index:
                segment.start_time = start_time
                segment.end_time = end_time
                break
    
    def get_selected_segments(self):
        """获取选中的片段"""
        return [segment for segment in self.segments if segment.checkbox.isChecked()]
    
    def add_to_timeline(self):
        """将选中片段添加到时间线"""
        selected = self.get_selected_segments()
        if selected:
            self.segments_created.emit(selected) 
    
    def set_silence_threshold(self, min_val, max_val):
        """设置静音阈值"""
        self.silence_min = min_val
        self.silence_max = max_val
        # 可以在这里添加自动更新剪辑的逻辑 