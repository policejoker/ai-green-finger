import streamlit as st
from google import genai
from PIL import Image
import pandas as pd
import os
from datetime import datetime
import requests
import time

# ==========================================
# 1. 設定區 & 讀取密碼
# ==========================================
st.set_page_config(page_title="AI 綠手指 - 最終進化版", page_icon="🌿")
st.title("🌿 AI 綠手指 (LINE 官方帳號連動版)")

# 從 Secrets 讀取密碼
# 注意：這裡的變數名稱必須跟你在 secrets.toml 裡設定的一模一樣
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    LINE_ACCESS_TOKEN = st.secrets.get("LINE_CHANNEL_ACCESS_TOKEN", None) 
except:
    st.error("找不到 API Key！請確認 secrets.toml 設定正確。")
    st.stop()

# 資料庫檔案名稱
DB_FILE = "plant_history.csv"

if "history" not in st.session_state:
    st.session_state.history = []

# 初始化「上次警告時間」，避免洗頻 (預設為 0)
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = 0

# ==========================================
# 2. 函式區 (Messaging API + 資料庫)
# ==========================================
def send_line_broadcast(msg, sticker=False):
    """
    使用 Messaging API 的 Broadcast 功能 (廣播給所有好友)
    """
    if LINE_ACCESS_TOKEN is None:
        st.warning("⚠️ 未設定 LINE Access Token，無法發送通知。")
        return

    # 這是 Messaging API 的廣播網址
    url = "https://api.line.me/v2/bot/message/broadcast"
    
    headers = {
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # 準備訊息內容 (JSON 格式)
    messages = [{"type": "text", "text": msg}]
    
    # 如果需要貼圖 (例如缺水時傳哭臉)
    if sticker:
        messages.append({
            "type": "sticker",
            "packageId": "11537",  # LINE 官方預設貼圖包 (黃色圓臉)
            "stickerId": "52002758" # 哭哭表情
        })

    payload = {"messages": messages}
    
    try:
        r = requests.post(url, headers=headers, json=payload)
        if r.status_code == 200:
            st.toast("已透過官方帳號廣播警示！📢", icon="✅")
        else:
            # 如果失敗，顯示錯誤代碼 (例如 401 代表 Token 錯了)
            st.error(f"LINE 傳送失敗: {r.status_code} - {r.text}")
    except Exception as e:
        st.error(f"連線錯誤: {e}")

def save_to_csv(humidity, temperature, ai_response):
    """將資料寫入 CSV 檔案"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{
        "日期時間": now,
        "濕度(%)": humidity,
        "溫度(°C)": temperature,
        "AI 診斷與建議": ai_response
    }])
    
    if not os.path.exists(DB_FILE):
        new_data.to_csv(DB_FILE, index=False, encoding="utf-8-sig")
    else:
        new_data.to_csv(DB_FILE, mode='a', header=False, index=False, encoding="utf-8-sig")

def load_history():
    """讀取歷史紀錄"""
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return None

# ==========================================
# 3. 側邊欄
# ==========================================
with st.sidebar:
    # --- 新增：QR Code 顯示區 ---
    st.header("📱 加入好友接收警報")
    # 這裡的檔名 "line_qr.png" 要跟你真正的檔名一樣喔！
    # 如果你的圖片是 jpg，記得改成 line_qr.jpg
    st.image("line_qr.png", caption="掃描加入植物管家", use_container_width=True)
    st.divider() # 加一條分隔線
    # ---------------------------

    st.header("⚙️ 環境與視覺")
    humidity = st.slider("土壤濕度 (%)", 0, 100, 15)
    temperature = st.slider("環境溫度 (°C)", 10, 40, 28)
    
    uploaded_file = st.file_uploader("📸 拍張照幫我找回記憶", type=["jpg", "jpeg", "png"])
    
    ask_ai_btn = st.button("🔍 啟動 AI 分析")
# ==========================================
# 4. 主畫面
# ==========================================
col1, col2 = st.columns(2)
col1.metric("濕度", f"{humidity}%", "-5%" if humidity < 20 else "0%")
col2.metric("溫度", f"{temperature}°C")

# 顯示照片預覽
image = None
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="AI 正在觀察...", use_container_width=True)

# ==========================================
# 5. AI 邏輯核心
# ==========================================
if ask_ai_btn:
    with st.spinner('AI 正在分析數據、寫入日記並檢查警報...'):
        try:
            client = genai.Client(api_key=API_KEY)
            
            # --- 警報邏輯 (含冷卻機制) ---
            current_time = time.time()
            
            # 規則：濕度 < 20% 且 距離上次警告超過 60 秒
            if humidity < 20:
                if (current_time - st.session_state.last_alert_time) > 60:
                    warning_msg = f"⚠️ 救命啊！我快乾死了！\n目前濕度：{humidity}%\n快點來澆水！"
                    # 傳送文字 + 哭哭貼圖
                    send_line_broadcast(warning_msg, sticker=True)
                    # 更新上次警告時間
                    st.session_state.last_alert_time = current_time
                else:
                    st.warning("⚠️ 濕度過低！(訊息冷卻中，避免洗頻扣額度)")

            # --- AI 生成回應 ---
            if image:
                prompt_text = f"""
                目前的感測器數據：濕度 {humidity}%，溫度 {temperature}度。
                請執行：
                1. **視覺辨識**：判斷我是什麼植物？
                2. **性格切換**：依照品種切換個性(傲嬌/溫柔/高貴)。
                3. **回應**：結合數據跟我對話。如果濕度低於20%，請崩潰求救。
                (請用繁體中文，簡短有力)
                """
                contents = [prompt_text, image]
            else:
                prompt_text = f"""
                目前數據：濕度 {humidity}%，溫度 {temperature}度。
                你處於黑暗中(沒照片)，請用疑惑語氣並要求照片。
                但如果濕度低於20%，請優先喊救命。
                """
                contents = [prompt_text]

            response = client.models.generate_content(
                model='gemini-flash-latest', 
                contents=contents
            )
            
            # 顯示回應
            st.session_state.history.append({"role": "ai", "msg": response.text})
            
            # 存檔
            save_to_csv(humidity, temperature, response.text)
            st.success("✅ 診斷完成！資料已紀錄。")
            
        except Exception as e:
            st.error(f"發生錯誤: {e}")

# 顯示對話紀錄
st.divider()
for chat in reversed(st.session_state.history):
    st.info(f"🌿 植物說：{chat['msg']}")

# 歷史回顧區
st.divider()
st.subheader("📊 植物健康履歷表")
df = load_history()
if df is not None:
    st.dataframe(df.sort_index(ascending=False).head(5), use_container_width=True)