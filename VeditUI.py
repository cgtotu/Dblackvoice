from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QPushButton, QScrollArea, QLabel, QSlider, QCheckBox,
                           QLineEdit, QFrame, QGridLayout, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from sourceinfo import SourceInfo
from AVreader import AudioReader
from AVtimeCut import TimeCutter, TimeSegmentItem
from AVplayer import VideoPlayer
from AVoutput import VideoExporter
from PyQt5.QtWidgets import QFileDialog, QMessageBox
import cv2
from timeline import Timeline
import subprocess

class VideoEditUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_playing = None  # 当前播放的片段
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("视频剪辑程序")
        self.setGeometry(100, 100, 1600, 900)
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建上下两个主要区域
        upper_widget = QWidget()
        lower_widget = QWidget()
        upper_layout = QHBoxLayout(upper_widget)
        lower_layout = QVBoxLayout(lower_widget)
        
        # === 上半部分 ===
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)  # 添加边距
        left_layout.setSpacing(10)  # 添加间距
        
        # 1. 素材栏
        source_group = QFrame()
        source_group.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)  # 修改边框样式
        source_layout = QVBoxLayout(source_group)
        source_layout.setContentsMargins(5, 5, 5, 5)
        source_layout.setSpacing(5)
        
        # 素材栏标题和导入按钮
        source_header = QHBoxLayout()
        source_header.addWidget(QLabel("<b>素材栏</b>"))
        source_header.addStretch()
        self.import_btn = QPushButton("导入文件")
        self.import_btn.clicked.connect(self.import_files)  # 连接导入按钮信号
        source_header.addWidget(self.import_btn)
        source_layout.addLayout(source_header)
        
        # 创建SourceInfo实例
        self.source_info = SourceInfo()
        source_layout.addWidget(self.source_info)
        
        # 将素材栏添加到左侧面板
        left_layout.addWidget(source_group)
        
        # 2. 音频信息读取栏
        audio_group = QFrame()
        audio_group.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        audio_layout = QVBoxLayout(audio_group)
        audio_layout.setContentsMargins(5, 5, 5, 5)
        audio_layout.setSpacing(5)  # 添加间距
        
        # 音频栏标题和读取按钮
        audio_header = QHBoxLayout()
        audio_header.addWidget(QLabel("<b>音频信息读取栏</b>"))
        audio_header.addStretch()
        self.read_audio_btn = QPushButton("读取音频")
        self.read_audio_btn.setFixedWidth(100)  # 设置按钮宽度
        self.read_audio_btn.clicked.connect(self.analyze_selected_audio)
        audio_header.addWidget(self.read_audio_btn)
        audio_layout.addLayout(audio_header)
        
        # 创建AudioReader实例
        self.audio_reader = AudioReader()
        audio_layout.addWidget(self.audio_reader)
        
        # 将音频栏添加到左侧面板
        left_layout.addWidget(audio_group)
        
        # 调整左侧面板中各部分的比例（如果之前没有设置）
        left_layout.addWidget(source_group, 3)  # 素材栏占3份
        left_layout.addWidget(audio_group, 2)   # 音频栏占2份
        
        # 3. 自动剪辑信息栏
        cut_group = QFrame()
        cut_group.setFrameStyle(QFrame.Box)
        cut_layout = QVBoxLayout(cut_group)
        
        cut_header = QHBoxLayout()
        cut_header.addWidget(QLabel("<b>自动剪辑信息栏</b>"))
        cut_header.addStretch()
        self.select_all = QCheckBox("全选")
        self.select_all.stateChanged.connect(self.toggle_all_segments)
        self.auto_cut_btn = QPushButton("自动剪辑")
        self.auto_cut_btn.clicked.connect(self.perform_auto_cut)
        cut_header.addWidget(self.select_all)
        cut_header.addWidget(self.auto_cut_btn)
        cut_layout.addLayout(cut_header)
        
        # 创建TimeCutter实例
        self.time_cutter = TimeCutter()
        cut_layout.addWidget(self.time_cutter)
        
        # 将左侧面板和剪辑栏平分空间
        upper_layout.addWidget(left_panel, 1)
        upper_layout.addWidget(cut_group, 1)
        
        # === 下半部分 ===
        # 5. 时间线栏
        timeline_group = QFrame()
        timeline_group.setFrameStyle(QFrame.Box)
        timeline_layout = QVBoxLayout(timeline_group)
        
        # 时间线标题
        timeline_layout.addWidget(QLabel("<b>时间线栏</b>"))
        
        # 创建Timeline实例
        self.timeline = Timeline()
        timeline_layout.addWidget(self.timeline)
        
        # 连接信号
        self.time_cutter.segments_created.connect(self.timeline.add_segments)
        self.timeline.exportVideo.connect(self.export_video)
        self.timeline.exportAudio.connect(self.export_audio)
        self.timeline.exportScript.connect(self.export_script)
        
        # 将时间线添加到下半部分
        lower_layout.addWidget(timeline_group)
        
        # 设置上下部分的比例
        main_layout.addWidget(upper_widget, 2)
        main_layout.addWidget(lower_widget, 1)

        # 创建VideoExporter实例
        self.video_exporter = VideoExporter()
        self.video_exporter.progress_updated.connect(self.update_export_progress)
        
        # 连接静音检测信号
        self.audio_reader.silence_detected.connect(self.update_silence_threshold)

    def import_files(self):
        """处理文件导入"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter(self.source_info.get_media_filters())
        
        if file_dialog.exec_():
            file_paths = file_dialog.selectedFiles()
            for file_path in file_paths:
                self.source_info.add_source(file_path)
    
    def get_selected_sources(self):
        """获取选中的素材列表"""
        return self.source_info.get_selected_sources()

    def analyze_selected_audio(self):
        """分析选中素材的音频"""
        selected_sources = self.get_selected_sources()
        if not selected_sources:
            QMessageBox.warning(self, "警告", "请先选择要分析的素材")
            return
        
        # 清除之前的显示
        self.audio_reader.clear_display()
        
        # 分析所有选中的素材
        min_db = float('inf')
        max_db = float('-inf')
        valid_results = []
        
        for source in selected_sources:
            result = self.audio_reader.analyze_audio(source)
            if result:
                # 更新全局最大最小值
                min_db = min(min_db, result['min_db'])
                max_db = max(max_db, result['max_db'])
                valid_results.append(result)
        
        if not valid_results:
            QMessageBox.warning(self, "警告", "没有可用的音频分析结果")
            return
        
        # 保存分析结果供后续使用
        self.audio_analysis_result = {
            'min_db': min_db,
            'max_db': max_db,
            'sources': selected_sources,
            'waveform': valid_results[0]['waveform'],  # 使用第一个有效结果的波形
            'sr': valid_results[0]['sr'],  # 使用第一个有效结果的采样率
            'selected_range': (
                float(self.audio_reader.min_input.text()),
                float(self.audio_reader.max_input.text())
            )
        }
        
        # 更新音频读取栏显示
        self.audio_reader.min_db = min_db
        self.audio_reader.max_db = max_db
        self.audio_reader.update_display()
    
    def perform_auto_cut(self):
        """执行自动剪辑"""
        if not hasattr(self, 'audio_analysis_result'):
            QMessageBox.warning(self, "警告", "请先进行音频分析")
            return
            
        # 获取当前的选择范围
        selected_range = (
            float(self.audio_reader.min_input.text()),
            float(self.audio_reader.max_input.text())
        )
        
        # 更新分析结果中的选择范围
        self.audio_analysis_result['selected_range'] = selected_range
        
        # 执行自动剪辑
        self.time_cutter.auto_cut(self.audio_analysis_result)
    
    def toggle_all_segments(self, state):
        """切换所有片段的选中状态"""
        if hasattr(self, 'time_cutter'):
            for segment in self.time_cutter.segments:
                segment.checkbox.setChecked(state == Qt.Checked)

    def export_video(self, segment_info):
        """导出视频"""
        output_path, _ = QFileDialog.getSaveFileName(
            self, "导出视频", "", "MP4文件 (*.mp4)")
        if output_path and segment_info:
            try:
                commands = []
                temp_files = []
                
                # 处理每个片段
                for i, info in enumerate(segment_info):
                    temp_file = f"temp_{i}.mp4"
                    temp_files.append(temp_file)
                    
                    command = (
                        f'ffmpeg -i "{info["file_path"]}" -ss {info["start_time"]} '
                        f'-t {info["end_time"] - info["start_time"]} '
                        f'-c copy "{temp_file}"'
                    )
                    commands.append(command)
                
                # 创建文件列表
                with open("mylist.txt", "w") as f:
                    for temp in temp_files:
                        f.write(f"file '{temp}'\n")
                
                # 使用 concat demuxer 合并
                merge_command = f'ffmpeg -f concat -safe 0 -i mylist.txt -c copy "{output_path}"'
                commands.append(merge_command)
                
                # 清理命令
                commands.append('del mylist.txt')
                for temp_file in temp_files:
                    commands.append(f'del "{temp_file}"')
                
                # 执行命令
                for command in commands:
                    subprocess.run(command, shell=True, check=True)
                
                QMessageBox.information(self, "成功", "视频导出完成")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def export_audio(self, segment_info):
        """导出音频"""
        output_path, _ = QFileDialog.getSaveFileName(
            self, "导出音频", "", "WAV文件 (*.wav);;MP3文件 (*.mp3)")
        if output_path and segment_info:
            try:
                commands = []
                temp_files = []
                
                # 处理每个片段
                for i, info in enumerate(segment_info):
                    temp_file = f"temp_{i}.wav"
                    temp_files.append(temp_file)
                    
                    command = (
                        f'ffmpeg -i "{info["file_path"]}" -ss {info["start_time"]} '
                        f'-t {info["end_time"] - info["start_time"]} '
                        f'-vn -acodec pcm_s16le "{temp_file}"'
                    )
                    commands.append(command)
                
                # 创建文件列表
                with open("mylist.txt", "w") as f:
                    for temp in temp_files:
                        f.write(f"file '{temp}'\n")
                
                # 使用 concat demuxer 合并
                if output_path.endswith('.mp3'):
                    merge_command = (
                        f'ffmpeg -f concat -safe 0 -i mylist.txt '
                        f'-acodec libmp3lame "{output_path}"'
                    )
                else:
                    merge_command = (
                        f'ffmpeg -f concat -safe 0 -i mylist.txt '
                        f'-acodec pcm_s16le "{output_path}"'
                    )
                commands.append(merge_command)
                
                # 清理命令
                commands.append('del mylist.txt')
                for temp_file in temp_files:
                    commands.append(f'del "{temp_file}"')
                
                # 执行命令
                for command in commands:
                    subprocess.run(command, shell=True, check=True)
                
                QMessageBox.information(self, "成功", "音频导出完成")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def export_script(self, segment_info):
        """导出ffmpeg脚本"""
        output_path, _ = QFileDialog.getSaveFileName(
            self, "保存脚本", "", "批处理文件 (*.bat)")
        if output_path and segment_info:
            try:
                commands = []
                temp_files = []
                
                # 添加注释
                commands.append("@echo off")
                commands.append("rem 自动生成的ffmpeg剪辑脚本")
                commands.append("")
                
                # 处理每个片段
                for i, info in enumerate(segment_info):
                    temp_file = f"temp_{i}.mp4"
                    temp_files.append(temp_file)
                    
                    commands.append(f'rem 处理片段 {i+1}')
                    command = (
                        f'ffmpeg -i "{info["file_path"]}" -ss {info["start_time"]} '
                        f'-t {info["end_time"] - info["start_time"]} '
                        f'-c copy "{temp_file}"'
                    )
                    commands.append(command)
                    commands.append("")
                
                # 创建文件列表
                commands.append("rem 创建文件列表")
                commands.append('echo file temp_0.mp4 > mylist.txt')
                for i in range(1, len(temp_files)):
                    commands.append(f'echo file temp_{i}.mp4 >> mylist.txt')
                commands.append("")
                
                # 合并命令
                commands.append("rem 合并所有片段")
                commands.append(
                    'ffmpeg -f concat -safe 0 -i mylist.txt -c copy "output.mp4"'
                )
                commands.append("")
                
                # 清理命令
                commands.append("rem 清理临时文件")
                commands.append("del mylist.txt")
                for temp_file in temp_files:
                    commands.append(f'del "{temp_file}"')
                
                # 保存脚本
                with open(output_path, "w", encoding='utf-8') as f:
                    f.write("\n".join(commands))
                
                QMessageBox.information(self, "成功", "脚本导出完成")
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def update_export_progress(self, progress):
        """更新导出进度"""
        # 可以添加进度条显示
        pass

    def update_silence_threshold(self, min_val, max_val):
        """更新静音阈值"""
        self.time_cutter.set_silence_threshold(min_val, max_val)

    def add_to_timeline(self):
        """将选中片段添加到时间线"""
        selected = self.get_selected_segments()
        if selected:
            # 按编号排序
            selected.sort(key=lambda x: x.index)
            self.segments_created.emit(selected)

if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = VideoEditUI()
    window.show()
    sys.exit(app.exec_())