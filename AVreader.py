from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QSlider, QSizePolicy, QFrame, QLineEdit, QMessageBox, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QRect, QMargins
from PyQt5.QtGui import (QDoubleValidator, QPainter, QPen, QColor, QPainterPath,
                        QLinearGradient)
from PyQt5.QtChart import QChart, QChartView, QLineSeries, QValueAxis
import numpy as np
import librosa
import os
import warnings

# 过滤警告
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

# 设置librosa的缓存
os.environ['LIBROSA_CACHE_DIR'] = 'tmp_cache'
os.makedirs('tmp_cache', exist_ok=True)

class WaveformWidget(QWidget):
    """音频波形图表组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(150)
        self.audio_data = None
        self.min_db = -60
        self.max_db = 0
        self.threshold = -40  # 添加阈值属性
        self.selected_min = -60
        self.selected_max = 0
        
        # 添加图表
        self.chart = QChart()
        self.chart.setMargins(QMargins(0, 0, 0, 0))
        self.chart.setBackgroundVisible(False)
        
        # 创建图表视图
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.Antialiasing)
        
        # 创建布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chart_view)
    
    def set_selected_range(self, min_val, max_val):
        """设置选择范围"""
        self.selected_min = float(min_val)
        self.selected_max = float(max_val)
        self.update_chart()
    
    def set_data(self, data, min_db, max_db):
        """设置音频数据并更新显示"""
        self.audio_data = data
        self.min_db = float(min_db)
        self.max_db = float(max_db)
        self.update_chart()
    
    def set_threshold(self, value):
        """设置阈值"""
        self.threshold = value
        self.update_chart()
    
    def _setup_axes(self, data_length, y, sr):
        """设置坐标轴"""
        # 创建X轴
        axis_x = QValueAxis()
        axis_x.setRange(0, data_length)
        duration = len(y) / sr
        axis_x.setLabelFormat("%.1f")
        axis_x.setTitleText(f"时间 (总长: {duration:.1f}s)")
        
        # 创建Y轴
        axis_y = QValueAxis()
        axis_y.setRange(0, 100)
        axis_y.setLabelFormat("%d")
        axis_y.setTitleText("电平 (dB)")
        
        # 设置轴
        for series in self.chart.series():
            self.chart.setAxisX(axis_x, series)
            self.chart.setAxisY(axis_y, series)
        
        # 添加选择范围
        self._add_range_lines(data_length, axis_x, axis_y)

    def update_chart(self):
        """更新图表显示"""
        self.chart.removeAllSeries()
        
        if self.audio_data is None or 'waveform' not in self.audio_data:
            return
            
        # 创建波形系列
        series = QLineSeries()
        series.setName("音频电平")
        
        # 使用原始波形计算RMS能量
        y = self.audio_data['waveform']
        frame_length = 2048
        hop_length = 512
        
        # 计算RMS能量
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        db_values = librosa.amplitude_to_db(rms, ref=np.max)
        
        # 重采样以适应显示
        target_points = 1000
        if len(db_values) > target_points:
            indices = np.linspace(0, len(db_values)-1, target_points, dtype=int)
            db_values = db_values[indices]
        
        # 添加数据点
        for i, value in enumerate(db_values):
            normalized_value = (value - self.min_db) / (self.max_db - self.min_db)
            normalized_value = max(0, min(1, normalized_value))
            series.append(i, normalized_value * 100)
        
        self.chart.addSeries(series)
        
        # 添加阈值线
        threshold_series = QLineSeries()
        normalized_threshold = (self.threshold - self.min_db) / (self.max_db - self.min_db)
        normalized_threshold = max(0, min(1, normalized_threshold)) * 100
        threshold_series.append(0, normalized_threshold)
        threshold_series.append(len(db_values), normalized_threshold)
        threshold_series.setPen(QPen(QColor(255, 0, 0, 128), 2, Qt.DashLine))
        self.chart.addSeries(threshold_series)
        
        # 设置坐标轴
        self._setup_axes(len(db_values), y, self.audio_data['sr'])

    def _add_range_lines(self, data_length, axis_x, axis_y):
        """添加选择范围线"""
        # 下边界线
        lower_series = QLineSeries()
        normalized_min = (self.selected_min - self.min_db) / (self.max_db - self.min_db)
        normalized_min = max(0, min(1, normalized_min)) * 100
        lower_series.append(0, normalized_min)
        lower_series.append(data_length, normalized_min)
        lower_series.setPen(QPen(QColor(0, 255, 0, 128), 2, Qt.DashLine))
        self.chart.addSeries(lower_series)
        lower_series.attachAxis(axis_x)
        lower_series.attachAxis(axis_y)
        
        # 上边界线
        upper_series = QLineSeries()
        normalized_max = (self.selected_max - self.min_db) / (self.max_db - self.min_db)
        normalized_max = max(0, min(1, normalized_max)) * 100
        upper_series.append(0, normalized_max)
        upper_series.append(data_length, normalized_max)
        upper_series.setPen(QPen(QColor(0, 255, 0, 128), 2, Qt.DashLine))
        self.chart.addSeries(upper_series)
        upper_series.attachAxis(axis_x)
        upper_series.attachAxis(axis_y)

class AudioReader(QWidget):
    audio_analyzed = pyqtSignal(dict)
    silence_detected = pyqtSignal(float, float)  # 添加静音检测信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.audio_data = None
        self.current_file = None
        self.silence_threshold = -40  # 默认静音阈值
        self.min_db = -60  # 添加默认最小分贝值
        self.max_db = 0    # 添加默认最大分贝值
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 添加阈值输入框
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("静音阈值:"))
        self.threshold_input = QLineEdit("-40")
        self.threshold_input.setValidator(QDoubleValidator(-100, 0, 1))
        self.threshold_input.textChanged.connect(self.threshold_changed)
        threshold_layout.addWidget(self.threshold_input)
        layout.addLayout(threshold_layout)
        
        # 1. 文件信息区
        file_info = QFrame()
        file_info.setFrameStyle(QFrame.StyledPanel)
        file_info_layout = QVBoxLayout(file_info)
        
        self.file_label = QLabel("当前文件：未选择")
        self.duration_label = QLabel("时长：--:--")
        file_info_layout.addWidget(self.file_label)
        file_info_layout.addWidget(self.duration_label)
        
        layout.addWidget(file_info)
        
        # 2. 音频统计信息
        stats_info = QFrame()
        stats_info.setFrameStyle(QFrame.StyledPanel)
        stats_layout = QVBoxLayout(stats_info)
        
        self.level_label = QLabel("音频电平范围：等待分析...")
        self.silence_stats_label = QLabel("静音统计：等待分析...")
        stats_layout.addWidget(self.level_label)
        stats_layout.addWidget(self.silence_stats_label)
        
        layout.addWidget(stats_info)
        
        # 3. 波形图
        self.waveform = WaveformWidget()
        layout.addWidget(self.waveform)
        
        # 4. 控制区域
        controls = QFrame()
        controls.setFrameStyle(QFrame.StyledPanel)
        controls_layout = QHBoxLayout(controls)
        
        # 电平控制
        level_group = QWidget()
        level_layout = QHBoxLayout(level_group)
        
        # 最小电平
        min_layout = QHBoxLayout()
        min_layout.addWidget(QLabel("最小电平:"))
        self.min_input = QLineEdit("-60")
        self.min_input.setValidator(QDoubleValidator(-100, 0, 1))
        self.min_input.setFixedWidth(60)
        min_layout.addWidget(self.min_input)
        min_layout.addWidget(QLabel("dB"))
        level_layout.addLayout(min_layout)
        
        level_layout.addSpacing(20)
        
        # 最大电平
        max_layout = QHBoxLayout()
        max_layout.addWidget(QLabel("最大电平:"))
        self.max_input = QLineEdit("0")
        self.max_input.setValidator(QDoubleValidator(-100, 0, 1))
        self.max_input.setFixedWidth(60)
        max_layout.addWidget(self.max_input)
        max_layout.addWidget(QLabel("dB"))
        level_layout.addLayout(max_layout)
        
        controls_layout.addWidget(level_group)
        
        # 添加自动检测按钮
        detect_btn = QPushButton("检测静音")
        detect_btn.clicked.connect(self.detect_silence)
        controls_layout.addWidget(detect_btn)
        
        layout.addWidget(controls)
        
        # 设置样式
        self.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QLabel {
                padding: 2px;
            }
            QLineEdit {
                padding: 3px;
                border: 1px solid #ccc;
                border-radius: 2px;
            }
            QPushButton {
                padding: 5px 15px;
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        # 连接信号
        self.min_input.textChanged.connect(self.range_value_changed)
        self.max_input.textChanged.connect(self.range_value_changed)

    def detect_silence(self):
        """检测静音段落"""
        if not self.audio_data or 'waveform' not in self.audio_data:
            return
            
        try:
            y = self.audio_data['waveform']
            sr = self.audio_data['sr']
            
            # 使用更小的分析窗口
            frame_length = 1024
            hop_length = 256
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            db_values = librosa.amplitude_to_db(rms, ref=np.max)
            
            # 计算更精确的静音统计
            silence_threshold = float(self.threshold_input.text() or "-40")
            silence_mask = db_values < silence_threshold
            
            # 计算连续静音段
            silence_runs = []
            run_start = None
            
            for i, is_silence in enumerate(silence_mask):
                if is_silence:
                    if run_start is None:
                        run_start = i
                elif run_start is not None:
                    silence_runs.append((run_start, i))
                    run_start = None
            
            # 计算静音统计
            total_frames = len(db_values)
            silence_ratio = np.mean(silence_mask)
            total_duration = len(y) / sr
            silence_duration = silence_ratio * total_duration
            
            # 更新显示
            stats_text = (
                f"静音统计：\n"
                f"静音比例: {silence_ratio:.1%}\n"
                f"静音总时长: {silence_duration:.3f}秒\n"
                f"最长静音: {max([end-start for start, end in silence_runs], default=0) / (sr/hop_length):.3f}秒\n"
                f"建议阈值: {np.percentile(db_values, 10):.1f} dB"
            )
            self.silence_stats_label.setText(stats_text)
            
            # 发送检测结果
            suggested_min = np.percentile(db_values, 10)
            suggested_max = np.percentile(db_values, 90)
            self.silence_detected.emit(suggested_min, suggested_max)
            
        except Exception as e:
            print(f"静音检测错误: {str(e)}")

    def analyze_audio(self, file_path):
        """分析音频文件"""
        try:
            self.current_file = file_path
            y, sr = librosa.load(file_path, sr=44100)
            
            # 计算音频特征
            duration = len(y) / sr
            rms = librosa.feature.rms(y=y)[0]
            db_values = librosa.amplitude_to_db(rms, ref=np.max)
            
            # 计算统计值
            min_db = float(np.percentile(db_values, 1))
            max_db = float(np.percentile(db_values, 99))
            mean_db = float(np.mean(db_values))
            
            # 保存分析结果
            self.audio_data = {
                'waveform': y,
                'sr': sr,
                'duration': duration,
                'min_db': min_db,
                'max_db': max_db,
                'mean_db': mean_db,
                'db_values': db_values
            }
            
            # 更新类属性
            self.min_db = min_db
            self.max_db = max_db
            
            # 更新显示
            self.update_display()
            
            # 返回分析结果
            return self.audio_data
            
        except Exception as e:
            print(f"音频分析错误: {str(e)}")
            return None
    
    def update_display(self):
        """更新显示的音频值"""
        if hasattr(self, 'audio_data') and self.audio_data:
            try:
                # 更新文件名
                if self.current_file:
                    self.file_label.setText(f"当前文件：{os.path.basename(self.current_file)}")
                else:
                    self.file_label.setText("当前文件：未选择")
                
                # 更新电平范围
                level_text = (
                    f"音频电平范围：{self.audio_data['min_db']:.1f} dB 至 "
                    f"{self.audio_data['max_db']:.1f} dB"
                )
                self.level_label.setText(level_text)
                
                # 更新波形图
                self.waveform.set_data(self.audio_data, self.min_db, self.max_db)
                
            except KeyError as e:
                self.level_label.setText(f"音频电平范围：数据不完整 (缺少 {str(e)})")
        else:
            self.file_label.setText("当前文件：未选择")
            self.level_label.setText("音频电平范围：等待分析...")
    
    def clear_display(self):
        """清除显示"""
        self.file_label.setText("当前文件：未选择")
        self.level_label.setText("音频电平范围：等待分析...")
        self.current_file = None
        self.audio_data = None
        self.waveform.set_data(None, -60, 0)
    
    def range_value_changed(self):
        """输入框值变化处理"""
        try:
            min_val = float(self.min_input.text() or "-60")
            max_val = float(self.max_input.text() or "0")
            
            # 确保最小值不大于最大值
            if min_val > max_val:
                if self.sender() == self.min_input:
                    min_val = max_val
                    self.min_input.setText(f"{min_val}")
                else:
                    max_val = min_val
                    self.max_input.setText(f"{max_val}")
            
            # 更新波形图的选中范围
            self.waveform.set_selected_range(min_val, max_val)
            
            # 保存当前值作为实例变量
            self.min_db = min_val
            self.max_db = max_val
            
        except ValueError:
            pass
    
    def threshold_changed(self):
        """阈值改变时更新显示"""
        try:
            threshold = float(self.threshold_input.text() or "-40")
            self.silence_threshold = threshold  # 更新类属性
            if hasattr(self, 'waveform') and self.audio_data:
                self.waveform.set_threshold(threshold)
                self.detect_silence()  # 重新检测静音
        except ValueError:
            pass

    def auto_cut(self, audio_data):
        """执行自动剪辑"""
        # 获取音频数据
        y = audio_data['waveform']  # 原始波形
        sr = audio_data['sr']       # 采样率
        selected_range = audio_data['selected_range']  # 用户选择的阈值范围
        min_db = selected_range[0]  # 最小分贝值
        max_db = selected_range[1]  # 最大分贝值
        
        # 计算RMS能量
        frame_length = 2048   # 帧长度，影响精度
        hop_length = 512      # 帧移动步长，影响精度
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        db_values = librosa.amplitude_to_db(rms, ref=np.max)  # 转换为分贝值