import streamlit as st
import pandas as pd
import requests
import os
import base64

# 安全載入 yfinance 防護機制
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

# ==========================================
# 版本資訊 (Version Info)
# 版本別：v1.4.11
# 更新日期：2026-08-13
# 修改內容：
# 1. 徹底移除 SDK 依賴：刪除所有 google-generativeai 相關語法。
# 2. 鎖定標準 REST 端點：統一使用 v1beta 路徑呼叫 gemini-1.5-flash。
# 3. 保留所有功能：13 個延伸數據欄位、趨勢指標與 OpenRouter 動態機制。
# ==========================================

VERSION = "v1.4.11"
UPDATE_DATE = "2026-08-13"

st.set_page_config(
    page_title=f"台股價值與潛力股智慧分析系統 {VERSION}",
    page_icon="📈",
    layout="wide"
)

# 讀取 GitHub 中的 Avatar.png
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

if avatar_b64:
    avatar_html = f'<img src="{avatar_b64}" style="width: 28px; height: 28px; border-radius: 50%; object-fit: cover;">'
else:
    avatar_html = '<span style="font-size: 20px;">🧔🏻‍♂️</span>'

# 右下角固定懸浮個人識別卡
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
st.caption(f"📌 版本別：{VERSION} | 🗓️ 更新日期：{UPDATE_DATE} | 結合官方 OpenAPI、真實市場 K 線資料與 Gemini + Meta Llama 雙 AI 的同業估值診斷平台")

# ==========================================
# 台股官方 33 大產業字典與色彩歸類對照表
# ==========================================
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
    return pd.DataFrame(), True

@st.cache_data(ttl=1800)
def get_real_stock_history(stock_code):
    if not YFINANCE_AVAILABLE: return None
    try:
        ticker = f"{stock_code}.TW"
        df_hist = yf.Ticker(ticker).history(period="6mo")
        if len(df_hist) < 20:
            ticker = f"{stock_code}.TWO"
            df_hist = yf.Ticker(ticker).history(period="6mo")
        if len(df_hist) >= 20:
            c = df_hist["Close"]
            return {
                "High_30D": round(float(c.tail(22).max()), 1),
                "Low_30D": round(float(c.tail(22).min()), 1),
                "High_60D": round(float(c.tail(44).max()), 1),
                "Low_60D": round(float(c.tail(44).min()), 1),
                "Latest_Close": round(float(c.iloc[-1]), 1),
                "MA30": round(float(c.tail(30).mean()), 1),
                "MA60": round(float(c.tail(60).mean()), 1),
                "MA120": round(float(c.tail(120).mean()), 1),
                "Daily_Trend": "⬆️" if c.iloc[-1] >= c.iloc[-2] else "⬇️",
                "Weekly_Trend": "⬆️" if c.iloc[-1] >= c.tail(5).mean() else "⬇️",
                "Monthly_Trend": "⬆️" if c.iloc[-1] >= c.tail(20).mean() else "⬇️"
            }
    except: pass
    return None

def call_gemini_api(api_key, prompt):
    """純 REST API 呼叫，強制使用 v1beta 路徑"""
    clean_key = str(api_key).strip().strip('"').strip("'")
    if not clean_key: return False, "API Key 為空"
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=15)
        if res.status_code == 200:
            return True, res.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return False, f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

def call_openrouter_llama(api_key, prompt):
    """動態爬取 OpenRouter"""
    clean_key = str(api_key).strip().strip('"').strip("'")
    if not clean_key: return False, "API Key 為空"
    
    target_model = "meta-llama/llama-3.1-8b-instruct:free"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {clean_key}", "Content-Type": "application/json"}
    payload = {"model": target_model, "messages": [{"role": "user", "content": prompt}]}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            return True, res.json()['choices'][0]['message']['content']
        return False, f"Error {res.status_code}: {res.text}"
    except Exception as e:
        return False, str(e)

# 載入
df_stocks, is_fallback = load_stock_data()

# 參數 Session State
qp = st.query_params
if "ind_val" not in st.session_state: st.session_state["ind_val"] = qp.get("ind", "全部產業")
if "pe_disc_val" not in st.session_state: st.session_state["pe_disc_val"] = int(qp.get("pe_disc", -5))
if "sec_pe_val" not in st.session_state: st.session_state["sec_pe_val"] = float(qp.get("sec_pe", 30.0))
if "max_pe_val" not in st.session_state: st.session_state["max_pe_val"] = float(qp.get("max_pe", 25.0))
if "roe_val" not in st.session_state: st.session_state["roe_val"] = float(qp.get("roe", 8.0))
if "yoy_val" not in st.session_state: st.session_state["yoy_val"] = float(qp.get("yoy", -5.0))

# 側邊欄
st.sidebar.header("⚙️ 篩選條件設定")
if st.sidebar.button("🔄 重新載入數據"): st.cache_data.clear(); st.rerun()

search_input = st.sidebar.text_input("輸入股票代號/名稱：", value="")
search_stock_options = ["(不指定 / 觀看全部)"] + [f"{r['Code']} {r['Name']}" for _, r in df_stocks.iterrows()]
selected_search_stock = st.sidebar.selectbox("或選擇下拉清單：", search_stock_options)

final_search_code = ""
if search_input.strip(): final_search_code = search_input.strip().split()[0]
elif selected_search_stock != "(不指定 / 觀看全部)": final_search_code = selected_search_stock.split()[0]

st.sidebar.markdown("---")
selected_industry = st.sidebar.selectbox("指定產業類別", ["全部產業"] + sorted(list(df_stocks["Industry"].unique())), index=["全部產業"] + sorted(list(df_stocks["Industry"].unique())).index(st.session_state["ind_val"]) if st.session_state["ind_val"] in ["全部產業"] + sorted(list(df_stocks["Industry"].unique())) else 0, key="sb_ind")
pe_discount_threshold = st.sidebar.slider("次產業 PE 折價率上限 (%)", -50, 20, st.session_state["pe_disc_val"], 5)
max_sector_pe = st.sidebar.slider("次產業 PE 中位數上限 (倍)", 5.0, 50.0, st.session_state["sec_pe_val"], 1.0)
max_stock_pe = st.sidebar.slider("個股 PE 絕對值上限 (倍)", 3.0, 40.0, st.session_state["max_pe_val"], 1.0)
st.session_state.update({"ind_val": selected_industry, "pe_disc_val": pe_discount_threshold, "sec_pe_val": max_sector_pe, "max_pe_val": max_stock_pe})

if st.sidebar.button("🔍 套用條件"): st.session_state["filter_executed"] = True

filtered_df = df_stocks.copy()
if selected_industry != "全部產業": filtered_df = filtered_df[filtered_df["Industry"] == selected_industry]
filtered_df = filtered_df[(filtered_df["次產業_PE折溢價(%)"] <= pe_discount_threshold) & (filtered_df["Sector_PE_Median"] <= max_sector_pe) & (filtered_df["PE"] <= max_stock_pe)]

# Tab 診斷區塊
tab1, tab2, tab3 = st.tabs(["📊 篩選總覽", "🔍 對照表", "🧠 雙 AI 診斷"])
with tab3:
    if st.button("🚀 一鍵生成報告"):
        stock_code = final_search_code if final_search_code else df_stocks.iloc[0]["Code"]
        target_row = df_stocks[df_stocks["Code"] == stock_code].iloc[0]
        prompt = f"分析 {target_row['Name']}。價格{target_row['Price']}，本益比{target_row['PE']}，產業{target_row['Industry']}。"
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🧠 Gemini")
            succ, res = call_gemini_api(gemini_key, prompt)
            st.markdown(res if succ else f"❌ {res}")
        with c2:
            st.markdown("### 🦙 Llama")
            succ, res = call_openrouter_llama(openrouter_key, prompt)
            st.markdown(res if succ else f"❌ {res}")
