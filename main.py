# -*- coding: utf-8 -*-
"""
智能读书 APP - 电子书朗读器
支持 PDF/EPUB/AZW3 格式，中文 TTS 朗读
功能：语速调节、暂停/播放、定时关闭
"""

import os
import time
import threading
from datetime import datetime, timedelta

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.core.window import Window

# 电子书解析库
import ebooklib
from ebooklib import epub
import PyPDF2
import mobi

# TTS - Edge TTS (微软免费)
import asyncio
import edge_tts
import pygame


class BookReader(FloatLayout):
    """主界面"""
    
    current_text = StringProperty("")
    progress = NumericProperty(0)
    is_playing = BooleanProperty(False)
    current_book = StringProperty("")
    current_voice = StringProperty("zh-CN-XiaoxiaoNeural")
    speed_rate = NumericProperty(1.0)
    timer_minutes = NumericProperty(0)
    status_text = StringProperty("准备就绪")
    
    # 可用中文声音
    VOICES = [
        ("晓晓 (女声)", "zh-CN-XiaoxiaoNeural"),
        ("云希 (男声)", "zh-CN-YunxiNeural"),
        ("云扬 (男声)", "zh-CN-YunyangNeural"),
        ("晓伊 (女声)", "zh-CN-XiaoyiNeural"),
    ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.book_content = ""
        self.chapters = []
        self.current_chapter_idx = 0
        self.audio_queue = []
        self.is_paused = False
        self.timer_active = False
        self.stop_event = threading.Event()
        
        # 初始化 pygame 混音器
        pygame.mixer.init()
        
        self.build_ui()
    
    def build_ui(self):
        """构建界面"""
        Window.clearcolor = (0.1, 0.1, 0.15, 1)
        
        # 标题
        title = Label(
            text="📚 智能读书 APP",
            font_size="24sp",
            size_hint=(1, 0.1),
            pos_hint={"center_x": 0.5, "top": 1},
            color=(1, 1, 1, 1),
            bold=True
        )
        self.add_widget(title)
        
        # 当前书籍信息
        self.book_label = Label(
            text="未选择书籍",
            font_size="16sp",
            size_hint=(0.8, 0.08),
            pos_hint={"center_x": 0.5, "top": 0.88},
            color=(0.8, 0.8, 0.8, 1),
            halign="center"
        )
        self.add_widget(self.book_label)
        
        # 状态显示
        self.status_label = Label(
            text="准备就绪",
            font_size="14sp",
            size_hint=(0.8, 0.06),
            pos_hint={"center_x": 0.5, "top": 0.80},
            color=(0.6, 0.8, 1, 1),
            halign="center"
        )
        self.add_widget(self.status_label)
        
        # 选择书籍按钮
        select_btn = Button(
            text="📁 选择书籍",
            font_size="18sp",
            size_hint=(0.4, 0.08),
            pos_hint={"center_x": 0.5, "top": 0.72},
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1)
        )
        select_btn.bind(on_press=self.select_book)
        self.add_widget(select_btn)
        
        # 声音选择
        voice_layout = BoxLayout(
            orientation="horizontal",
            size_hint=(0.8, 0.08),
            pos_hint={"center_x": 0.5, "top": 0.62}
        )
        
        voice_label = Label(
            text="声音:",
            font_size="16sp",
            size_hint=(0.3, 1),
            color=(1, 1, 1, 1),
            halign="right"
        )
        
        self.voice_spinner = Spinner(
            text="晓晓 (女声)",
            values=[v[0] for v in self.VOICES],
            size_hint=(0.7, 1),
            font_size="14sp",
            background_color=(0.3, 0.3, 0.4, 1),
            color=(1, 1, 1, 1)
        )
        self.voice_spinner.bind(text=self.on_voice_change)
        
        voice_layout.add_widget(voice_label)
        voice_layout.add_widget(self.voice_spinner)
        self.add_widget(voice_layout)
        
        # 语速调节
        speed_layout = BoxLayout(
            orientation="horizontal",
            size_hint=(0.8, 0.1),
            pos_hint={"center_x": 0.5, "top": 0.52}
        )
        
        speed_label = Label(
            text="语速:",
            font_size="16sp",
            size_hint=(0.3, 1),
            color=(1, 1, 1, 1),
            halign="right"
        )
        
        self.speed_slider = Slider(
            min=0.5,
            max=2.0,
            value=1.0,
            size_hint=(0.5, 1),
            step=0.1
        )
        self.speed_slider.bind(value=self.on_speed_change)
        
        self.speed_value = Label(
            text="1.0x",
            font_size="16sp",
            size_hint=(0.2, 1),
            color=(1, 1, 1, 1)
        )
        
        speed_layout.add_widget(speed_label)
        speed_layout.add_widget(self.speed_slider)
        speed_layout.add_widget(self.speed_value)
        self.add_widget(speed_layout)
        
        # 定时关闭
        timer_layout = BoxLayout(
            orientation="horizontal",
            size_hint=(0.8, 0.08),
            pos_hint={"center_x": 0.5, "top": 0.40}
        )
        
        timer_label = Label(
            text="定时:",
            font_size="16sp",
            size_hint=(0.3, 1),
            color=(1, 1, 1, 1),
            halign="right"
        )
        
        self.timer_spinner = Spinner(
            text="关闭",
            values=["关闭", "15 分钟", "30 分钟", "45 分钟", "60 分钟", "90 分钟"],
            size_hint=(0.7, 1),
            font_size="14sp",
            background_color=(0.3, 0.3, 0.4, 1),
            color=(1, 1, 1, 1)
        )
        self.timer_spinner.bind(text=self.on_timer_change)
        
        timer_layout.add_widget(timer_label)
        timer_layout.add_widget(self.timer_spinner)
        self.add_widget(timer_layout)
        
        # 播放控制按钮
        control_layout = BoxLayout(
            orientation="horizontal",
            size_hint=(0.9, 0.12),
            pos_hint={"center_x": 0.5, "top": 0.28},
            spacing=10
        )
        
        # 播放/暂停按钮
        self.play_btn = Button(
            text="▶ 播放",
            font_size="20sp",
            background_color=(0.2, 0.8, 0.4, 1),
            color=(1, 1, 1, 1)
        )
        self.play_btn.bind(on_press=self.toggle_play)
        
        # 停止按钮
        stop_btn = Button(
            text="⏹ 停止",
            font_size="20sp",
            background_color=(0.9, 0.3, 0.3, 1),
            color=(1, 1, 1, 1)
        )
        stop_btn.bind(on_press=self.stop_playback)
        
        # 上一章
        prev_btn = Button(
            text="◀ 上一章",
            font_size="14sp",
            background_color=(0.4, 0.4, 0.6, 1),
            color=(1, 1, 1, 1)
        )
        prev_btn.bind(on_press=self.prev_chapter)
        
        # 下一章
        next_btn = Button(
            text="下一章 ▶",
            font_size="14sp",
            background_color=(0.4, 0.4, 0.6, 1),
            color=(1, 1, 1, 1)
        )
        next_btn.bind(on_press=self.next_chapter)
        
        control_layout.add_widget(prev_btn)
        control_layout.add_widget(self.play_btn)
        control_layout.add_widget(stop_btn)
        control_layout.add_widget(next_btn)
        self.add_widget(control_layout)
        
        # 进度条
        progress_layout = BoxLayout(
            orientation="horizontal",
            size_hint=(0.8, 0.08),
            pos_hint={"center_x": 0.5, "top": 0.15}
        )
        
        self.progress_label = Label(
            text="0%",
            font_size="14sp",
            size_hint=(0.2, 1),
            color=(1, 1, 1, 1)
        )
        
        self.progress_slider = Slider(
            min=0,
            max=100,
            value=0,
            size_hint=(0.8, 1),
            step=1
        )
        
        progress_layout.add_widget(self.progress_label)
        progress_layout.add_widget(self.progress_slider)
        self.add_widget(progress_layout)
    
    def select_book(self, instance):
        """选择书籍文件"""
        self.show_file_picker()
    
    def show_file_picker(self):
        """显示文件选择器"""
        content = FileChooserListView(
            size_hint=(1, 1),
            path=os.path.expanduser("~"),
            filters=["*.pdf", "*.epub", "*.azw3", "*.mobi"]
        )
        
        popup = Popup(
            title="选择电子书",
            content=content,
            size_hint=(0.9, 0.9),
            background_color=(0.2, 0.2, 0.3, 1)
        )
        
        content.bind(on_submit=lambda x: self.load_book(x[0], popup))
        popup.open()
    
    def load_book(self, filepath, popup):
        """加载书籍"""
        popup.dismiss()
        
        try:
            self.status_text = "正在加载..."
            Clock.schedule_once(lambda dt: self._load_book_async(filepath), 0)
        except Exception as e:
            self.status_label.text = f"加载失败：{str(e)}"
    
    def _load_book_async(self, filepath):
        """异步加载书籍"""
        def load_thread():
            try:
                ext = os.path.splitext(filepath)[1].lower()
                
                if ext == ".epub":
                    self.load_epub(filepath)
                elif ext == ".pdf":
                    self.load_pdf(filepath)
                elif ext in [".azw3", ".mobi"]:
                    self.load_mobi(filepath)
                else:
                    Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', "不支持的格式"))
                    return
                
                Clock.schedule_once(lambda dt: self.on_book_loaded(filepath))
                
            except Exception as e:
                Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"加载失败：{str(e)}"))
        
        thread = threading.Thread(target=load_thread)
        thread.daemon = True
        thread.start()
    
    def load_epub(self, filepath):
        """加载 EPUB"""
        book = epub.read_epub(filepath)
        self.chapters = []
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8', errors='ignore')
                # 简单清理 HTML 标签
                content = self.clean_html(content)
                if content.strip():
                    self.chapters.append(content)
        
        self.book_content = "\n\n".join(self.chapters)
    
    def load_pdf(self, filepath):
        """加载 PDF"""
        self.chapters = []
        
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    self.chapters.append(text)
        
        self.book_content = "\n\n".join(self.chapters)
    
    def load_mobi(self, filepath):
        """加载 MOBI/AZW3"""
        self.chapters = []
        
        text, metadata = mobi.extract(filepath)
        self.chapters = [text]
        self.book_content = text
    
    def clean_html(self, html):
        """清理 HTML 标签"""
        import re
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', html)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def on_book_loaded(self, filepath):
        """书籍加载完成"""
        self.current_book = os.path.basename(filepath)
        self.book_label.text = f"📖 {self.current_book}"
        self.status_label.text = f"加载完成 | {len(self.chapters)} 章"
        self.progress = 0
        self.current_chapter_idx = 0
    
    def on_voice_change(self, instance, value):
        """切换声音"""
        for name, voice_id in self.VOICES:
            if name == value:
                self.current_voice = voice_id
                break
    
    def on_speed_change(self, instance, value):
        """语速变化"""
        self.speed_rate = value
        self.speed_value.text = f"{value:.1f}x"
    
    def on_timer_change(self, instance, value):
        """定时关闭设置"""
        if value == "关闭":
            self.timer_minutes = 0
            self.timer_active = False
        else:
            self.timer_minutes = int(value.replace(" 分钟", ""))
            self.timer_active = True
    
    def toggle_play(self, instance):
        """播放/暂停切换"""
        if self.is_playing:
            self.pause_playback()
        else:
            self.start_playback()
    
    def start_playback(self):
        """开始播放"""
        if not self.book_content:
            self.status_label.text = "请先选择书籍"
            return
        
        self.is_playing = True
        self.is_paused = False
        self.play_btn.text = "⏸ 暂停"
        self.status_label.text = "正在播放..."
        
        # 启动播放线程
        thread = threading.Thread(target=self.playback_thread)
        thread.daemon = True
        thread.start()
        
        # 启动定时器
        if self.timer_active and self.timer_minutes > 0:
            self.start_timer()
    
    def pause_playback(self):
        """暂停播放"""
        self.is_paused = True
        self.play_btn.text = "▶ 继续"
        self.status_label.text = "已暂停"
        self.stop_event.set()
    
    def stop_playback(self, instance=None):
        """停止播放"""
        self.is_playing = False
        self.is_paused = False
        self.play_btn.text = "▶ 播放"
        self.status_label.text = "已停止"
        self.stop_event.set()
        
        if self.timer_active:
            self.timer_active = False
    
    def prev_chapter(self, instance):
        """上一章"""
        if self.current_chapter_idx > 0:
            self.current_chapter_idx -= 1
            self.status_label.text = f"第 {self.current_chapter_idx + 1} 章"
            if self.is_playing:
                self.stop_playback()
                self.start_playback()
    
    def next_chapter(self, instance):
        """下一章"""
        if self.current_chapter_idx < len(self.chapters) - 1:
            self.current_chapter_idx += 1
            self.status_label.text = f"第 {self.current_chapter_idx + 1} 章"
            if self.is_playing:
                self.stop_playback()
                self.start_playback()
    
    def playback_thread(self):
        """播放线程"""
        self.stop_event.clear()
        
        try:
            # 获取当前章节文本
            if self.chapters and self.current_chapter_idx < len(self.chapters):
                text = self.chapters[self.current_chapter_idx]
                
                # 分段朗读（每段约 300 字）
                segments = self.split_text(text, 300)
                
                for i, segment in enumerate(segments):
                    if self.stop_event.is_set():
                        break
                    
                    if self.is_paused:
                        while self.is_paused and not self.stop_event.is_set():
                            time.sleep(0.5)
                        if self.stop_event.is_set():
                            break
                    
                    # 生成语音
                    self.speak_segment(segment)
                    
                    # 更新进度
                    progress = ((self.current_chapter_idx + (i + 1) / len(segments)) / len(self.chapters)) * 100
                    Clock.schedule_once(lambda dt, p=progress: self.update_progress(p))
                    
        except Exception as e:
            Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', f"播放错误：{str(e)}"))
            self.is_playing = False
    
    def split_text(self, text, max_length):
        """分割文本"""
        segments = []
        current = ""
        
        for char in text:
            current += char
            if len(current) >= max_length and char in '。.！？!?':
                segments.append(current.strip())
                current = ""
        
        if current.strip():
            segments.append(current.strip())
        
        return segments if segments else [text]
    
    def speak_segment(self, text):
        """朗读文本片段"""
        try:
            # 使用 Edge TTS
            communicate = edge_tts.Communicate(
                text,
                self.current_voice,
                rate=f"{int((self.speed_rate - 1) * 100)}%"
            )
            
            # 保存临时音频文件
            temp_file = os.path.join(os.path.dirname(__file__), "temp_audio.mp3")
            asyncio.run(communicate.save(temp_file))
            
            # 播放音频
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy() and not self.stop_event.is_set():
                time.sleep(0.1)
            
            # 清理临时文件
            try:
                os.remove(temp_file)
            except:
                pass
                
        except Exception as e:
            print(f"TTS 错误：{e}")
    
    def update_progress(self, progress):
        """更新进度"""
        self.progress = progress
        self.progress_slider.value = progress
        self.progress_label.text = f"{progress:.0f}%"
    
    def start_timer(self):
        """启动定时关闭"""
        def timer_callback(dt):
            if self.timer_active and self.is_playing:
                self.timer_minutes -= 1
                if self.timer_minutes <= 0:
                    self.stop_playback()
                    self.status_label.text = "定时关闭"
                    self.timer_active = False
                    return False
            return True
        
        Clock.schedule_interval(timer_callback, 60)  # 每分钟检查


class ReaderApp(App):
    def build(self):
        self.title = "智能读书 APP"
        return BookReader()


if __name__ == "__main__":
    ReaderApp().run()
