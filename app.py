import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
from gTTS import gTTS
import io
import os

st.set_page_config(page_title="中印即時雙向翻譯", page_icon="🌐", layout="centered")

# 優先讀取 Streamlit Secrets 或環境變數中的 GEMINI_API_KEY
API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

if not API_KEY:
    API_KEY = st.sidebar.text_input("輸入 Gemini API Key:", type="password")

if not API_KEY:
    st.info("💡 請在側邊欄輸入 Gemini API Key 或於雲端後台設定 Secrets 以啟動翻譯。")
    st.stop()

client = genai.Client(api_key=API_KEY)

st.title("🌐 中 ⇄ 印 雙向即時翻譯")

direction = st.radio(
    "選擇翻譯方向：",
    ("繁體中文 ➔ 印尼文 (Bahasa Indonesia)", "印尼文 ➔ 繁體中文"),
    horizontal=True
)

is_zh_to_id = direction.startswith("繁體中文")
src_lang = "繁體中文" if is_zh_to_id else "Bahasa Indonesia"
target_lang = "Bahasa Indonesia" if is_zh_to_id else "繁體中文"
tts_lang_code = "id" if is_zh_to_id else "zh-TW"

def translate_content(text=None, image=None):
    system_instruction = (
        f"你是一名專業的雙向口譯與文件翻譯助手。目標是將輸入的內容從 {src_lang} 精準翻譯為 {target_lang}。"
        "要求：\n"
        "1. 口吻自然、清晰，貼合日常工作與現場口語交流情境。\n"
        "2. 只輸出翻譯後的結果，嚴禁添加任何多餘的寒暄、解釋、標籤或拼音標註。\n"
        "3. 若輸入為圖片，請先辨識圖片中的文字並直接翻譯成目標語言。"
    )
    
    contents = []
    if image is not None:
        contents.append(image)
    if text:
        contents.append(text)
        
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3
        )
    )
    return response.text.strip()

def play_audio(text, lang_code):
    tts = gTTS(text=text, lang=lang_code)
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    st.audio(fp, format="audio/mp3", autoplay=True)

tab_voice, tab_text, tab_camera = st.tabs(["🎙️ 語音對話", "⌨️ 打字輸入", "📷 拍照/圖檔辨識"])

with tab_voice:
    st.write(f"請點擊錄音按鈕，說出 **{src_lang}**：")
    audio_val = st.audio_input("錄製語音")
    
    if audio_val is not None:
        if st.button("開始語音辨識與翻譯", key="btn_voice"):
            with st.spinner("翻譯中..."):
                audio_bytes = audio_val.read()
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                        f"請辨識音訊中的語音，並直接翻譯成 {target_lang}。只回傳翻譯結果。"
                    ]
                )
                result_text = response.text.strip()
                st.success("翻譯結果：")
                st.subheader(result_text)
                play_audio(result_text, tts_lang_code)

with tab_text:
    user_input = st.text_area(f"請輸入 {src_lang} 內容：", height=100)
    if st.button("翻譯文字", key="btn_text"):
        if user_input.strip():
            with st.spinner("翻譯中..."):
                translated = translate_content(text=user_input)
                st.success("翻譯結果：")
                st.subheader(translated)
                play_audio(translated, tts_lang_code)
        else:
            st.warning("請先輸入文字。")

with tab_camera:
    img_file = st.camera_input("拍照現場文字/文件")
    uploaded_file = st.file_uploader("或上傳相片", type=["jpg", "jpeg", "png"])
    
    target_img = img_file or uploaded_file
    if target_img is not None:
        image = Image.open(target_img)
        st.image(image, caption="待翻譯圖片", use_container_width=True)
        if st.button("開始圖片文字翻譯", key="btn_image"):
            with st.spinner("正在辨識與翻譯..."):
                translated_img = translate_content(image=image)
                st.success("翻譯結果：")
                st.subheader(translated_img)
                play_audio(translated_img, tts_lang_code)
