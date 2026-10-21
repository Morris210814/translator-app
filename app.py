import streamlit as st
import google.generativeai as genai
import streamlit.components.v1 as components
import json
import os

st.set_page_config(page_title="中印即時雙向翻譯", page_icon="🌐", layout="centered")

# 讀取金鑰
API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

if not API_KEY:
    API_KEY = st.sidebar.text_input("輸入 Gemini API Key:", type="password")

if not API_KEY:
    st.info("💡 請在側邊欄輸入 Gemini API Key 或於雲端後台設定 Secrets 以啟動翻譯。")
    st.stop()

# 初始化模型
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

st.title("🌐 中 ⇄ 印 雙向即時翻譯")

direction = st.radio(
    "選擇翻譯方向：",
    ("繁體中文 ➔ 印尼文 (Bahasa Indonesia)", "印尼文 ➔ 繁體中文"),
    horizontal=True
)

is_zh_to_id = direction.startswith("繁體中文")
src_lang = "繁體中文" if is_zh_to_id else "Bahasa Indonesia"
target_lang = "Bahasa Indonesia" if is_zh_to_id else "繁體中文"
tts_lang_code = "id-ID" if is_zh_to_id else "zh-TW"

# 使用瀏覽器原生 Web Speech API 朗讀（免安裝任何後端套件）
def speak_text(text, lang_code):
    js_text = json.dumps(text)
    js_code = f"""
    <script>
    if ('speechSynthesis' in window) {{
        window.speechSynthesis.cancel();
        var msg = new SpeechSynthesisUtterance({js_text});
        msg.lang = '{lang_code}';
        msg.rate = 1.0;
        window.speechSynthesis.speak(msg);
    }}
    </script>
    """
    components.html(js_code, height=0)

def translate_content(text=None, image=None):
    prompt = (
        f"你是一名專業的雙向口譯助手。請將以下內容從 {src_lang} 精準翻譯為 {target_lang}。\n"
        "要求：\n"
        "1. 口吻自然、清晰，貼合現場日常溝通。\n"
        "2. 只輸出翻譯後的結果，嚴禁添加任何多餘寒暄、解釋、標籤或拼音標註。\n"
        "3. 若為圖片，請直接辨識文字並翻譯成目標語言。"
    )
    
    contents = [prompt]
    if image is not None:
        contents.append(image)
    if text:
        contents.append(text)
        
    response = model.generate_content(contents)
    return response.text.strip()

tab_voice, tab_text, tab_camera = st.tabs(["🎙️ 語音對話", "⌨️ 打字輸入", "📷 拍照/圖檔辨識"])

with tab_voice:
    st.write(f"請點擊錄音按鈕，說出 **{src_lang}**：")
    audio_val = st.audio_input("錄製語音")
    
    if audio_val is not None:
        if st.button("開始語音辨識與翻譯", key="btn_voice"):
            with st.spinner("翻譯中..."):
                audio_bytes = audio_val.read()
                audio_part = {
                    "mime_type": "audio/wav",
                    "data": audio_bytes
                }
                response = model.generate_content([
                    f"請辨識音訊中的語音，並直接翻譯成 {target_lang}。只回傳翻譯結果。",
                    audio_part
                ])
                result_text = response.text.strip()
                st.success("翻譯結果：")
                st.subheader(result_text)
                speak_text(result_text, tts_lang_code)

with tab_text:
    user_input = st.text_area(f"請輸入 {src_lang} 內容：", height=100)
    if st.button("翻譯文字", key="btn_text"):
        if user_input.strip():
            with st.spinner("翻譯中..."):
                translated = translate_content(text=user_input)
                st.success("翻譯結果：")
                st.subheader(translated)
                speak_text(translated, tts_lang_code)
        else:
            st.warning("請先輸入文字。")

with tab_camera:
    img_file = st.camera_input("拍照現場文字/文件")
    uploaded_file = st.file_uploader("或上傳相片", type=["jpg", "jpeg", "png"])
    
    target_img = img_file or uploaded_file
    if target_img is not None:
        from PIL import Image
        image = Image.open(target_img)
        st.image(image, caption="待翻譯圖片", use_container_width=True)
        if st.button("開始圖片文字翻譯", key="btn_image"):
            with st.spinner("正在辨識與翻譯..."):
                translated_img = translate_content(image=image)
                st.success("翻譯結果：")
                st.subheader(translated_img)
                speak_text(translated_img, tts_lang_code)
