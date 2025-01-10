import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

class VideoExporter(QObject):
    progress_updated = pyqtSignal(int)  # 导出进度信号
    
    def __init__(self):
        super().__init__()
        
    def export_video(self, segments, output_path):
        # 创建视频写入器
        first_segment = segments[0]
        cap = cv2.VideoCapture(first_segment['file'])
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        # 处理每个片段
        for segment in segments:
            cap = cv2.VideoCapture(segment['file'])
            start_frame = int(segment['start_time'] * fps)
            end_frame = int(segment['end_time'] * fps)
            
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            current_frame = start_frame
            
            while current_frame < end_frame:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                out.write(frame)
                current_frame += 1
                
                # 更新进度
                progress = int((current_frame - start_frame) / 
                             (end_frame - start_frame) * 100)
                self.progress_updated.emit(progress)
                
            cap.release()
            
        out.release() 