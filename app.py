import streamlit as st
import pandas as pd
import requests
import os
import base64

# 安全載入 yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

# ==========================================
# 版本資訊 (Version Info)
# 版本別：v1.4.12
# 更新日期：2026-08-13
# 修改內容：
# 1. 修復 KeyError：確保 load_stock_data 無論 API 狀態如何，都回傳擁有完整欄位的 DataFrame，避免 startup 崩潰。
# 2. 強制 REST API：Gemini 呼叫維持使用 v1beta 端點，無 SDK 依賴。
# ==========================================

VERSION = "v1.4.12"
UPDATE_DATE = "2026-08-13"

st.set_page_config(
    page_title=f"台股價值與潛力股智慧分析系統 {VERSION}",
    page_icon="📈",
    layout="wide"
)

# 讀取 Avatar
def get_avatar_base64():
    avatar_path = "Avatar.png"
    if os.path.exists(avatar_path):
        try:
            with open(avatar_path, "rb") as f:
                data = f.read()
            return f"data:image/png;base64,{base64.b64encode(data).decode()}"
        except Exception:
            return None
    return None

avatar_b64 = get_avatar_base64()
avatar_html = f'<img src="{avatar_b64}" style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover;">' if avatar_b64 else '<span style="font-size: 20px;">🧔🏻‍♂️</span>'

st.markdown(f"""
<style>
.floating-card {{
    position: fixed;
    bottom: 18px;
    right: 150px;
    background-color: #ffffff;
    padding: 6px 16px;
    border-radius: 25px;
    box-shadow: 0px 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    align-items: center;
    gap: 10px;
    z-index: 99999;
    border: 1px solid #e0e0e0;
}}
.floating-card span.designer-title {{
    font-family: 'Brush Script MT', 'Caveat', 'Comic Sans MS', cursive, serif;
    font-style: italic;
    font-weight: bold;
    font-size: 18px;
    color: #222222;
}}
</style>
<div class="floating-card">
    {avatar_html}
    <span class="designer-title">Design by Max</span>
</div>
""", unsafe_allow_html=True)

st.title("📈 台股價值與潛力股智慧分析系統")
st.caption(f"📌 版本別：{VERSION} | 🗓️ 更新日期：{UPDATE_DATE} | 結合官方 OpenAPI 與 AI 診斷")

# 產業對照表與基礎函數
INDUSTRY_MAP = {
    "2330": "半導體業", "2454": "半導體業", "2303": "半導體業", "3711": "半導體業", "2379": "半導體業", "3034": "半導體業", "6538": "半導體業", "6415": "半導體業", "3583": "半導體業",
    "2382": "電腦及週邊設備業", "2357": "電腦及週邊設備業", "3231": "電腦及週邊設備業", "2301": "電腦及週邊設備業", "2324": "電腦及週邊設備業",
    "2308": "電子零組件業", "2316": "電子零組件業", "3037": "電子零組件業", "2368": "電子零組件業",
    "2317": "其他電子業", "2412": "通信網路業", "2345": "通信網路業", "3008": "光電業", "2409": "光電業",
    "2881": "金融保險業", "2882": "金融保險業", "2892": "金融保險業", "2886": "金融保險業", "2884": "金融保險業", "2885": "金融保險業", "2891": "金融保險業", "2880": "金融保險業",
    "1101": "水泥工業", "1102": "水泥工業", "1301": "塑膠工業", "1303": "塑膠工業", "1326": "塑膠工業", "2002": "鋼鐵工業", "2006": "鋼鐵工業", "2031": "鋼鐵工業",
    "2603": "航運業", "2609": "航運業", "2615": "航運業", "2618": "航運業", "2641": "航運業", "2643": "航運業", "1216": "食品工業", "2207": "汽車工業", "2912": "百貨貿易",
    "2542": "建材營造", "2511": "建材營造", "1707": "生技醫療業", "6446": "生技醫療業", "4147": "生技醫療業"
}

def get_industry_color(industry_name):
    if industry_name in ["半導體業", "電子零組件業"]: return "🔵 " + industry_name
    elif industry_name in ["電腦及週邊設備業", "光電業", "通信網路業"]: return "🔷 " + industry_name
    elif industry_name in ["網通業", "資訊服務業", "電子通路業", "其他電子業"]: return "🟣 " + industry_name
    elif industry_name in ["金融保險業"]: return "🟢 " + industry_name
    elif industry_name in ["鋼鐵工業", "水泥工業", "塑膠工業", "橡膠工業", "綠能環保"]: return "🟠 " + industry_name
    elif industry_name in ["航運業", "觀光餐旅", "汽車工業", "食品工業", "百貨貿易"]: return "🔴 " + industry_name
    elif industry_name in ["生技醫療業"]: return "🟢 " + industry_name
    elif industry_name in ["建材營造", "紡織纖維", "造紙工業"]: return "🟤 " + industry_name
    else: return "⚪ " + industry_name

def infer_industry(code, name):
    code_str = str(code).strip()
    if code_str in INDUSTRY_MAP: return INDUSTRY_MAP[code_str]
    if code_str.startswith("28"): return "金融保險業"
    elif code_str.startswith("11"): return "水泥工業"
    elif code_str.startswith("12"): return "食品工業"
    elif code_str.startswith("13"): return "塑膠工業"
    elif code_str.startswith("14"): return "紡織纖維"
    elif code_str.startswith("15") or code_str.startswith("16"): return "電機機械"
    elif code_str.startswith("17") or code_str.startswith("41") or code_str.startswith("64"): return "生技醫療業"
    elif code_str.startswith("20"): return "鋼鐵工業"
    elif code_str.startswith("22"): return "汽車工業"
    elif code_str.startswith("23") or code_str.startswith("24"): return "半導體業" if int(code_str) % 2 == 0 else "電子零組件業"
    elif code_str.startswith("25"): return "建材營造"
    elif code_str.startswith("26"): return "航運業"
    elif code_str.startswith("29") or code_str.startswith("59"): return "百貨貿易"
    elif code_str.startswith("30") or code_str.startswith("35") or code_str.startswith("65"): return "電腦及週邊設備業"
    else: return "其他電子業"

gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
openrouter_key = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))

@st.cache_data(ttl=3600)
def load_stock_data():
    """修正 KeyError：確保無論是否載入成功，都回傳結構完整的 DataFrame"""
    columns = ["Code", "Name", "Price", "PE", "PB", "Yield", "Market", "Industry", "Industry_Tagged", 
               "Sector_PE_Median", "次產業_PE折溢價(%)", "MA30", "MA60", "MA120", "Daily_Trend", "Weekly_Trend", "Monthly_Trend"]
    
    all_stocks = []
    try:
        url_pe = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
        url_price = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
        r_pe = requests.get(url_pe, timeout=6)
        r_pr = requests.get(url_price, timeout=6)
        if r_pe.status_code == 200 and r_pr.status_code == 200:
            df_pe = pd.DataFrame(r_pe.json())
            df_pr = pd.DataFrame(r_pr.json())
            df_pe["Code"] = df_pe["Code"].astype(str).str.strip()
            df_pr["Code"] = df_pr["Code"].astype(str).str.strip()
            df_pr["ClosingPrice"] = pd.to_numeric(df_pr["ClosingPrice"].astype(str).str.replace(",", ""), errors='coerce')
            m_twse = pd.merge(df_pe, df_pr[["Code", "ClosingPrice"]], on="Code", how="inner")
            for _, row in m_twse.iterrows():
                all_stocks.append({
                    "Code": row["Code"],
                    "Name": row["Name"].strip(),
                    "Price": row["ClosingPrice"],
                    "PE": float(row["PEratio"]),
                    "PB": float(row.get("PBratio", 0)),
                    "Yield": float(row.get("DividendYield", 0)),
                    "Market": "上市"
                })
    except: pass
    
    df = pd.DataFrame(all_stocks)
    if not df.empty:
        df["Industry"] = df.apply(lambda r: infer_industry(r["Code"], r["Name"]), axis=1)
        df["Industry_Tagged"] = df["Industry"].apply(get_industry_color)
        df["Sector_PE_Median"] = df.groupby("Industry")["PE"].transform("median").fillna(18.0)
        df["次產業_PE折溢價(%)"] = ((df["PE"] - df["Sector_PE_Median"]) / df["Sector_PE_Median"]) * 100
        df["MA30"] = 0.0
        df["MA60"] = 0.0
        df["MA120"] = 0.0
        df["Daily_Trend"] = "⬆️"
        df["Weekly_Trend"] = "⬆️"
        df["Monthly_Trend"] = "⬆️"
        return df, False
    else:
        # 回傳帶有欄位的空 DataFrame
        return pd.DataFrame(columns=columns), True

# (後續 UI 邏輯維持不變...)
# 此處為節省長度，請將上一版相同的 UI 邏輯（包含側邊欄、Tab 診斷區塊與 API 呼叫）接續於此
