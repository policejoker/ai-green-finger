import streamlit as st
from google import genai
from PIL import Image
import pandas as pd
import os
from datetime import datetime

# ==========================================
# 1. 設定區
# ==========================================
# ==========================================
# 1. 設定區
# ==========================================
# 強制從 Secrets 讀取密碼
# 如果在雲端沒設定，或者在本機沒設定 secrets.toml，程式就會直接報錯停止 (保護安全)
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("找不到 API Key！請確認你有在 Streamlit Cloud 設定 Secrets，或在本機設定 .streamlit/secrets.toml")
    st.stop()
# 資料庫檔案名稱
DB_FILE = "plant_history.csv"

st.set_page_config(page_title="AI 綠手指 - 智慧紀錄版", page_icon="🌿")
st.title("🌿 AI 綠手指 (附帶健康履歷)")

if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================
# 2. 函式區 (處理資料庫)
# ==========================================
def save_to_csv(humidity, temperature, ai_response):
    """將資料寫入 CSV 檔案"""
    # 取得現在時間
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 準備一筆新資料
    new_data = pd.DataFrame([{
        "日期時間": now,
        "濕度(%)": humidity,
        "溫度(°C)": temperature,
        "AI 診斷與建議": ai_response
    }])
    
    # 如果檔案不存在，就在此建立；如果存在，就附加在後面 (mode='a')
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
    st.header("⚙️ 環境與視覺")
    humidity = st.slider("土壤濕度 (%)", 0, 100, 15)
    temperature = st.slider("環境溫度 (°C)", 10, 40, 28)
    
    uploaded_file = st.file_uploader("📸 拍張照幫我找回記憶", type=["jpg", "jpeg", "png"])
    
    ask_ai_btn = st.button("🔍 啟動 AI 分析並紀錄")

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
    st.image(image, caption="AI 正在觀察這株植物...", use_container_width=True)

# ==========================================
# 5. AI 邏輯核心
# ==========================================
if ask_ai_btn:
    with st.spinner('AI 正在運算並寫入日記...'):
        try:
            client = genai.Client(api_key=API_KEY)
            
            # 依照「有沒有照片」決定劇本
            if image:
                prompt_text = f"""
                目前的感測器數據：濕度 {humidity}%，溫度 {temperature}度。
                請執行：
                1. **視覺辨識**：判斷我是什麼植物？
                2. **性格切換**：依照品種切換個性(傲嬌/溫柔/高貴)。
                3. **回應**：結合數據跟我對話。如果照片有病徵請警告我。
                (請用繁體中文，簡短有力一點)
                """
                contents = [prompt_text, image]
            else:
                prompt_text = f"""
                你現在處於一片漆黑中 (使用者沒傳照片)。
                數據：濕度 {humidity}%，溫度 {temperature}度。
                請用「疑惑、失憶」的語氣，並強烈要求主人上傳照片。
                (請用繁體中文，簡短一點)
                """
                contents = [prompt_text]

            # 呼叫模型
            response = client.models.generate_content(
                model='gemini-flash-latest', 
                contents=contents
            )
            
            # 顯示回應
            st.session_state.history.append({"role": "ai", "msg": response.text})
            
            # ★★★ 關鍵動作：存檔 ★★★
            save_to_csv(humidity, temperature, response.text)
            st.success("✅ 診斷結果已寫入健康履歷！")
            
        except Exception as e:
            st.error(f"連線錯誤: {e}")

# 顯示當次對話紀錄
st.divider()
for chat in reversed(st.session_state.history):
    st.info(f"🌿 植物說：{chat['msg']}")

# ==========================================
# 6. 歷史回顧區 (新增功能)
# ==========================================
st.divider()
st.subheader("📊 過去 7 天的健康紀錄表")

df = load_history()
if df is not None:
    # 這裡可以只顯示最新的 5 筆，避免太長
    st.dataframe(df.sort_index(ascending=False).head(7), use_container_width=True)
    
    # 讓你下載 CSV 的按鈕 (方便做報告)
    with open(DB_FILE, "rb") as file:
        st.download_button(
            label="📥 下載完整紀錄 (CSV)",
            data=file,
            file_name="plant_history.csv",
            mime="text/csv"
        )
else:
    st.write("目前還沒有紀錄，快按下「啟動 AI 分析」來產生第一筆資料吧！")