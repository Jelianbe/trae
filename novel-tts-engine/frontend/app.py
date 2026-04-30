import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.chapter_splitter import split_with_volumes, get_structure_info
from pipeline.nlp_basics import tokenize, pos_tag, get_persons

st.set_page_config(
    page_title="Novel-TTS-Engine",
    page_icon="📚",
    layout="wide"
)

st.title("📚 小说转有声书 - 智能解析引擎")
st.markdown("---")

if 'novel_text' not in st.session_state:
    st.session_state['novel_text'] = ""
if 'chapters' not in st.session_state:
    st.session_state['chapters'] = []

st.sidebar.header("功能导航")
page = st.sidebar.radio(
    "选择功能",
    ["上传小说", "章节管理", "NLP分析", "角色管理", "导出结果"]
)

if page == "上传小说":
    st.header("上传小说文件")
    uploaded_file = st.file_uploader("选择TXT文件", type=['txt'])
    
    if uploaded_file:
        text = uploaded_file.read().decode('utf-8')
        st.session_state['novel_text'] = text
        st.success(f"已上传: {uploaded_file.name}")
        
        st.info("正在分析章节结构...")
        structure = split_with_volumes(text)
        st.session_state['chapters'] = structure.chapters
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总卷数", structure.total_volumes)
        with col2:
            st.metric("总章节数", structure.total_chapters)
        with col3:
            st.metric("总字符数", len(text))
        
        if structure.total_volumes > 1:
            st.subheader("卷结构")
            for vol in structure.volumes:
                with st.expander(f"📖 {vol.title} ({len(vol.chapters)}章)"):
                    for ch in vol.chapters:
                        st.write(f"  - {ch.title}")

elif page == "章节管理":
    st.header("章节管理")
    
    if not st.session_state['chapters']:
        st.warning("请先上传小说文件")
    else:
        chapters = st.session_state['chapters']
        
        st.subheader(f"共 {len(chapters)} 章")
        
        selected_chapters = st.multiselect(
            "选择要分析的章节",
            range(len(chapters)),
            format_func=lambda x: chapters[x].title
        )
        
        if selected_chapters:
            st.write(f"已选择 {len(selected_chapters)} 章")
            
            for idx in selected_chapters[:3]:
                chapter = chapters[idx]
                with st.expander(f"第{idx+1}章: {chapter.title}"):
                    content_preview = chapter.content[:500] + "..." if len(chapter.content) > 500 else chapter.content
                    st.text(content_preview)

elif page == "NLP分析":
    st.header("NLP分析")
    
    test_text = st.text_area(
        "输入测试文本",
        value="张三在北京大学学习自然语言处理。",
        height=100
    )
    
    if st.button("分析"):
        if test_text:
            with st.spinner("正在分析..."):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("分词结果")
                    tokens = tokenize(test_text)
                    st.write(" / ".join(tokens))
                
                with col2:
                    st.subheader("词性标注")
                    pos_tags = pos_tag(test_text)
                    for word, pos in pos_tags:
                        st.write(f"**{word}**: `{pos}`")
                
                st.subheader("命名实体识别")
                persons = get_persons(test_text)
                if persons:
                    st.write(f"👤 人物: {', '.join(persons)}")
                else:
                    st.write("未识别到人物实体")

elif page == "角色管理":
    st.header("角色管理")
    st.info("请先分析小说")

elif page == "导出结果":
    st.header("导出结果")
    st.info("请先完成分析")
