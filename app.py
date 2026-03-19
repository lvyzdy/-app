# -*- coding: utf-8 -*-
"""
智能读书 APP v3.1 - 莫兰迪主题 + 左右翻页 + 自动续读 + 目录导航
运行：streamlit run app.py
"""

import streamlit as st
import os
import asyncio
import edge_tts
import ebooklib
from ebooklib import epub
import PyPDF2
import re
import time
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="智能读书 APP",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===== 主题配置（默认莫兰迪灰）=====
THEMES = {
    "🎨 莫兰迪灰": {
        "bg_color": "#E8E4E1", "text_color": "#5A5A5A", "read_bg": "#F2EFE9",
        "highlight_bg": "#FFD700", "note_bg": "#D7CCC8", "accent": "#B8A99A",
        "border_radius": "16px", "shadow": "0 4px 16px rgba(90,90,90,0.15)"
    },
    "🌙 深夜阅读": {
        "bg_color": "#0B0F19", "text_color": "#F0F2F6", "read_bg": "#161B22",
        "highlight_bg": "#FFD700", "note_bg": "#4EC9B0", "accent": "#58A6FF",
        "border_radius": "12px", "shadow": "0 4px 16px rgba(0,0,0,0.4)"
    },
    "🍃 护眼模式": {
        "bg_color": "#C7EDCC", "text_color": "#2F4F2F", "read_bg": "#D4EDD4",
        "highlight_bg": "#FFF4E6", "note_bg": "#E8F5E9", "accent": "#66BB6A",
        "border_radius": "12px", "shadow": "0 2px 8px rgba(47,79,47,0.15)"
    },
}

DEFAULT_THEME_INDEX = 0

# 主题选择
st.sidebar.markdown("---")
selected_theme = st.sidebar.selectbox(
    "🎨 选择主题",
    list(THEMES.keys()),
    index=st.session_state.get('theme_index', DEFAULT_THEME_INDEX)
)

if 'theme_index' not in st.session_state:
    st.session_state.theme_index = DEFAULT_THEME_INDEX
elif selected_theme != list(THEMES.keys())[st.session_state.theme_index]:
    st.session_state.theme_index = list(THEMES.keys()).index(selected_theme)

theme = THEMES[selected_theme]
bg_color = theme["bg_color"]
text_color = theme["text_color"]
read_bg = theme["read_bg"]
highlight_bg = theme["highlight_bg"]
note_bg = theme["note_bg"]
accent_color = theme["accent"]
border_radius = theme["border_radius"]
shadow = theme["shadow"]

# ===== CSS 样式 =====
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&display=swap');
    
    * {{
        font-family: 'Noto Serif SC', serif;
    }}
    
    .stApp {{
        background: linear-gradient(180deg, {bg_color} 0%, {read_bg} 100%);
        min-height: 100vh;
    }}
    
    h1 {{
        font-size: 2em;
        font-weight: 700;
        text-align: center;
        color: {text_color};
        margin-bottom: 20px;
    }}
    
    .reading-container {{
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
    }}
    
    .page-content {{
        background: linear-gradient(145deg, {read_bg}, {bg_color});
        border-radius: {border_radius};
        padding: 40px;
        margin: 20px 0;
        box-shadow: {shadow};
        border: 1px solid rgba(0,0,0,0.05);
        min-height: 500px;
    }}
    
    .sentence {{
        font-size: 22px;
        line-height: 2.2;
        color: {text_color};
        padding: 8px 12px;
        margin: 4px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
    }}
    
    .sentence:hover {{
        background: rgba(0,0,0,0.05);
    }}
    
    .sentence.current {{
        background: linear-gradient(135deg, {highlight_bg}, #FFA500);
        color: #000;
        font-weight: 700;
        box-shadow: 0 2px 12px rgba(255, 215, 0, 0.4);
        transform: scale(1.02);
    }}
    
    .page-controls {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 30px;
        padding: 20px;
    }}
    
    .nav-btn {{
        background: linear-gradient(135deg, {accent_color}, {highlight_bg});
        color: #000;
        border: none;
        padding: 15px 30px;
        border-radius: {border_radius};
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    }}
    
    .nav-btn:hover {{
        transform: translateY(-3px);
        box-shadow: 0 6px 24px rgba(0,0,0,0.2);
    }}
    
    .nav-btn:disabled {{
        opacity: 0.3;
        cursor: not-allowed;
        transform: none;
    }}
    
    .page-info {{
        text-align: center;
        color: {text_color};
        font-size: 14px;
    }}
    
    /* 目录样式 */
    .toc-container {{
        max-height: 400px;
        overflow-y: auto;
        background: {read_bg};
        border-radius: {border_radius};
        padding: 20px;
        margin: 20px 0;
        box-shadow: {shadow};
    }}
    
    .toc-item {{
        padding: 10px 15px;
        margin: 5px 0;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.2s ease;
        color: {text_color};
        font-size: 15px;
    }}
    
    .toc-item:hover {{
        background: rgba(0,0,0,0.05);
        transform: translateX(5px);
    }}
    
    .toc-item.active {{
        background: linear-gradient(135deg, {highlight_bg}, #FFA500);
        color: #000;
        font-weight: 600;
    }}
    
    .toc-level-1 {{ padding-left: 0px; font-weight: 600; font-size: 16px; }}
    .toc-level-2 {{ padding-left: 20px; }}
    .toc-level-3 {{ padding-left: 40px; font-size: 14px; }}
    
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)

# ===== 状态管理 =====
if 'current_book' not in st.session_state:
    st.session_state.current_book = None
if 'sentences' not in st.session_state:
    st.session_state.sentences = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'current_sentence' not in st.session_state:
    st.session_state.current_sentence = 0
if 'is_playing' not in st.session_state:
    st.session_state.is_playing = False
if 'sentences_per_page' not in st.session_state:
    st.session_state.sentences_per_page = 15
if 'toc' not in st.session_state:
    st.session_state.toc = []
if 'chapter_pages' not in st.session_state:
    st.session_state.chapter_pages = {}

SENTENCES_PER_PAGE = st.session_state.sentences_per_page

# ===== 工具函数 =====
def extract_text_from_pdf(file_path):
    text = ""
    chapters = {}
    current_chapter = "正文"
    
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            
            # 先尝试提取目录（从第 1-2 页）
            toc_text = ""
            for i in range(min(2, len(reader.pages))):
                toc_text += reader.pages[i].extract_text()
            
            # 从目录页提取章节（匹配"第 X 章"或"第 X 节"格式）
            toc_matches = re.findall(r'(第 [一二三四五六七八九十百\d]+[章节篇部].*?)(?:\n|$)', toc_text)
            if toc_matches:
                for idx, chapter in enumerate(toc_matches[:30]):  # 最多 30 章
                    chapters[chapter.strip()] = idx * 50  # 估算位置
            
            # 提取正文
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    # 检测章节标题
                    lines = page_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if 5 < len(line) < 40 and re.search(r'第 [一二三四五六七八九十百\d]+[章节篇部]', line):
                            if line not in chapters:
                                chapters[line] = len(text)
                    
                    text += page_text
    except Exception as e:
        st.error(f"PDF 读取失败：{e}")
    
    return text, chapters

def extract_text_from_epub(file_path):
    text = ""
    chapters = {}
    
    try:
        book = epub.read_epub(file_path)
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                content = item.get_content().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(content, 'html.parser')
                
                # 提取标题
                title_elem = soup.find(['h1', 'h2', 'h3'])
                if title_elem:
                    chapter_name = title_elem.get_text().strip()
                    if chapter_name:
                        chapters[chapter_name] = len(text)
                
                # 提取正文
                text += soup.get_text(separator='\n')
    except Exception as e:
        st.error(f"EPUB 读取失败：{e}")
    
    return text, chapters

def split_sentences(text):
    sentences = re.split(r'(?<=[。！？！？.!?])\s*', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]

def get_current_page_sentences():
    start = st.session_state.current_page * SENTENCES_PER_PAGE
    end = start + SENTENCES_PER_PAGE
    return st.session_state.sentences[start:end]

def jump_to_chapter(chapter_name):
    if chapter_name in st.session_state.chapter_pages:
        char_pos = st.session_state.chapter_pages[chapter_name]
        # 估算句子位置
        sentence_idx = int((char_pos / len(''.join(st.session_state.sentences))) * len(st.session_state.sentences))
        st.session_state.current_sentence = sentence_idx
        st.session_state.current_page = sentence_idx // SENTENCES_PER_PAGE
        st.rerun()

# ===== 侧边栏 =====
with st.sidebar:
    st.header("📖 我的书架")
    
    uploaded_file = st.file_uploader("上传书籍", type=['pdf', 'epub', 'txt'])
    
    if uploaded_file:
        file_path = os.path.join("my_books", uploaded_file.name)
        os.makedirs("my_books", exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"✅ {uploaded_file.name}")
    
    book_list = os.listdir("my_books") if os.path.exists("my_books") else []
    if book_list:
        selected_book = st.selectbox("选择书籍", book_list)
        if st.button("📖 打开"):
            file_path = os.path.join("my_books", selected_book)
            st.session_state.current_book = selected_book
            
            if selected_book.endswith('.pdf'):
                text, chapters = extract_text_from_pdf(file_path)
            elif selected_book.endswith('.epub'):
                text, chapters = extract_text_from_epub(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                chapters = {}
            
            st.session_state.sentences = split_sentences(text)
            st.session_state.toc = list(chapters.keys()) if chapters else ["正文"]
            st.session_state.chapter_pages = chapters
            st.session_state.current_page = 0
            st.session_state.current_sentence = 0
            st.session_state.is_playing = False
            st.rerun()
    
    st.divider()
    
    # 目录导航
    if st.session_state.toc:
        st.subheader("📑 目录")
        for chapter in st.session_state.toc[:20]:  # 最多显示 20 章
            if st.button(f"📖 {chapter}", key=f"toc_{chapter}"):
                jump_to_chapter(chapter)
    
    st.divider()
    st.subheader("⚙️ 设置")
    voice = st.selectbox("声音", ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunjianNeural"], index=0)
    speed = st.slider("语速", 0.5, 2.0, 1.0, 0.1)
    SENTENCES_PER_PAGE = st.slider("每页句数", 5, 30, 15)
    st.session_state.sentences_per_page = SENTENCES_PER_PAGE

# ===== 主界面 =====
if not st.session_state.sentences:
    st.markdown("""
    <div style="text-align: center; padding: 100px 20px;">
        <h1 style="font-size: 3em; margin-bottom: 20px;">📚 智能读书 APP</h1>
        <p style="font-size: 1.2em; color: #888;">请在左侧上传书籍开始阅读</p>
        <p style="font-size: 1em; color: #aaa;">支持 PDF / EPUB / TXT 格式</p>
        <p style="font-size: 1em; color: #aaa;">✨ 新增功能：目录导航，随时跳转章节</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# 当前页句子
page_sentences = get_current_page_sentences()
total_pages = (len(st.session_state.sentences) + SENTENCES_PER_PAGE - 1) // SENTENCES_PER_PAGE

# 标题
st.markdown(f"<h1>📖 {st.session_state.current_book}</h1>", unsafe_allow_html=True)

# 阅读区域
st.markdown("<div class='reading-container'>", unsafe_allow_html=True)
st.markdown("<div class='page-content'>", unsafe_allow_html=True)

for i, sentence in enumerate(page_sentences):
    global_idx = st.session_state.current_page * SENTENCES_PER_PAGE + i
    is_current = global_idx == st.session_state.current_sentence
    css_class = "sentence current" if is_current else "sentence"
    st.markdown(f"<div class='{css_class}' data-idx='{global_idx}'>{sentence}</div>", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# 翻页控制
st.markdown("<div class='page-controls'>", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])

with col1:
    prev_page = st.button("⬅️ 上一页", disabled=st.session_state.current_page == 0, key="prev")
    if prev_page:
        st.session_state.current_page -= 1
        st.session_state.current_sentence = st.session_state.current_page * SENTENCES_PER_PAGE
        st.rerun()

with col2:
    st.markdown(f"<div class='page-info'>第 {st.session_state.current_page + 1} / {total_pages} 页 | 进度：{st.session_state.current_sentence}/{len(st.session_state.sentences)} 句</div>", unsafe_allow_html=True)

with col3:
    next_page = st.button("下一页 ➡️", disabled=st.session_state.current_page >= total_pages - 1, key="next")
    if next_page:
        st.session_state.current_page += 1
        st.session_state.current_sentence = st.session_state.current_page * SENTENCES_PER_PAGE
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# 播放控制
st.divider()
col_play, col_stop, col_jump = st.columns(3)

with col_play:
    if st.button("▶️ 开始朗读", disabled=st.session_state.is_playing, use_container_width=True):
        st.session_state.is_playing = True
        st.rerun()

with col_stop:
    if st.button("⏹️ 停止", disabled=not st.session_state.is_playing, use_container_width=True):
        st.session_state.is_playing = False
        st.rerun()

with col_jump:
    jump_to = st.number_input("跳转到句", min_value=0, max_value=len(st.session_state.sentences)-1, value=st.session_state.current_sentence)
    if st.button("🎯 跳转", use_container_width=True):
        st.session_state.current_sentence = jump_to
        st.session_state.current_page = jump_to // SENTENCES_PER_PAGE
        st.rerun()

# 朗读逻辑
if st.session_state.is_playing and st.session_state.sentences:
    current_text = st.session_state.sentences[st.session_state.current_sentence]
    
    placeholder = st.empty()
    with placeholder.container():
        st.info(f"🔊 正在朗读：{current_text[:50]}...")
    
    try:
        asyncio.run(edge_tts.Communicate(
            current_text,
            voice=voice,
            rate=f"{int((speed - 1) * 100)}%"
        ).save("temp_audio.mp3"))
        
        st.audio("temp_audio.mp3", autoplay=True)
        
        # 等待播放完成（估算）
        time.sleep(len(current_text) / (speed * 15))
        
        # 下一句
        st.session_state.current_sentence += 1
        
        # 检查是否需要翻页
        if st.session_state.current_sentence >= (st.session_state.current_page + 1) * SENTENCES_PER_PAGE:
            if st.session_state.current_page < total_pages - 1:
                st.session_state.current_page += 1
                st.session_state.current_sentence = st.session_state.current_page * SENTENCES_PER_PAGE
                st.rerun()
        
        # 检查是否读完
        if st.session_state.current_sentence >= len(st.session_state.sentences):
            st.success("🎉 恭喜！已读完本书！")
            st.session_state.is_playing = False
        
        st.rerun()
        
    except Exception as e:
        st.error(f"朗读失败：{e}")
        st.session_state.is_playing = False
