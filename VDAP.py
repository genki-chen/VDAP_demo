from PyQt6.QtWidgets import QFileDialog, QMainWindow, QApplication, QPushButton, QMessageBox
from PyQt6.QtCore import Qt, QRectF, QThread, pyqtSignal
from PyQt6 import uic

import os
import sys
import pyaudio
import numpy as np
from pathlib import Path
from scipy.io import wavfile

p = pyaudio.PyAudio()
play_format = pyaudio.paFloat32
gain_idx = 30

class VDAP(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = uic.loadUi((Path(__file__).parent / "VDAP.ui"),self)
        self.init_UI()
        self.cal_para()
        self.ui.show()
    
    def init_UI(self):
        self.Slider_Angle.valueChanged.connect(self.change_Slider)
        self.Slider_Angle.setProperty("name", "Box_Angle")
        self.Box_Angle.valueChanged.connect(self.change_Slider)
        self.Box_Angle.setProperty("name", "Slider_Angle")
        self.PB_open: QPushButton
        self.PB_open.clicked.connect(self.set_file_path)

    def cal_para(self):
        theta_1 = -30
        theta_2 = 30
        self.theta_obj = np.arange(theta_1,theta_2+1,1)
        gain_ori = np.zeros((self.theta_obj.__len__() , 2),dtype=np.float32)
        self.gain_norm = np.zeros((self.theta_obj.__len__() , 2),dtype=np.float32)
        gain_ori[:30,0] = 1
        gain_ori[30:,1] = 1
        gain_ori[30:,0] = (self.theta_obj[30:]-gain_ori[30:,1]*theta_2)/theta_1
        gain_ori[:30,1] = (self.theta_obj[:30]-gain_ori[:30,0]*theta_1)/theta_2
        self.gain_norm[:,0] = gain_ori[:,0]/np.sqrt(np.square(gain_ori[:,0])+np.square(gain_ori[:,1]))
        self.gain_norm[:,1] = gain_ori[:,1]/np.sqrt(np.square(gain_ori[:,0])+np.square(gain_ori[:,1]))
        
    def change_Slider(self):
        global gain_idx
        val = self.sender().value()
        gain_idx = np.where(self.theta_obj == val)[0][0]
        #print(self.gain_norm[gain_idx,:])
        eval('self.'+self.sender().property("name")).setValue(val)
    
    def set_file_path(self):
        self.wave_path = QFileDialog.getOpenFileName(self,"Choose a wave file",filter='*.wav')[0]
        if len(self.wave_path) == 0:
            QMessageBox.warning(self,'Warning','Plase select a wave file first.')
            return
        self.PB_open.setEnabled(False)
        self.TB_file_path.setText(self.wave_path)
        rate, audio_data = wavfile.read(self.wave_path)
        if np.issubdtype(audio_data.dtype, np.integer):
            max_val = np.iinfo(audio_data.dtype).max
            audio_data = audio_data.astype(np.float32) / max_val
        self.play_thread = Runthread(rate,self.gain_norm,audio_data)
        self.play_thread.start()

class Runthread(QThread):
    def __init__(self, rate, gain_norm, audio_data):
        super().__init__()
        self.block_size = 2205
        self.rate = rate
        self.gain_norm = gain_norm
        self.audio_data = audio_data

    def run(self):
        global gain_idx
        stream = p.open(format=play_format, channels=2, rate=self.rate, output=True, frames_per_buffer=self.block_size)
        current_pos = 0
        while current_pos < len(self.audio_data):
            # 检查播放控制状态
            #playback_control.wait()  # 如果未设置，将阻塞在这里
            block_end = min(current_pos + self.block_size, len(self.audio_data))
            l_s = self.gain_norm[gain_idx,0]*self.audio_data[current_pos:block_end]
            r_s = self.gain_norm[gain_idx,1]*self.audio_data[current_pos:block_end]
            stereo = np.vstack((l_s, r_s)).T.flatten()
            stream.write(stereo.astype(np.float32).tobytes())
            current_pos = block_end

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = VDAP()
    w.show()
    sys.exit(app.exec())