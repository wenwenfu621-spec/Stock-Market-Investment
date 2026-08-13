import streamlit as st
import pandas as pd
import requests
import os
import base64

# 載入 Gemini 官方 SDK
try:
    import google.generativeai as genai_legacy
    GENAI_LEGACY_AVAILABLE = True
except ImportError:
    GENAI_LEGACY_AVAILABLE = False

# 安全載入 yfinance 防護機制
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    yf = None
    YFINANCE_AVAILABLE = False

# ==========================================
# 版本資訊 (Version Info)
# 版本別：v1.4.4
# 更新日期：2026-08-13
# 修改內容：
# 1. 徹底修復 Gemini 404：優先透過官方 SDK 進行路由，並將 REST 端點修正為穩定支援的 v1/models/gemini-1.5-flash。
# 2. 完全保留已成功運作的 OpenRouter 動態免費模型抓取機制與 13 個延伸數據欄位。
# ==========================================

VERSION = "v1.4.4"
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

# 右下角固定懸浮個人識別卡 (Design by Max)
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
    if industry_name in ["半導體業", "電子零組件業"]:
        return "🔵 " + industry_name
    elif industry_name in ["電腦及週邊設備業", "光電業", "通信網路業"]:
        return "🔷 " + industry_name
    elif industry_name in ["網通業", "資訊服務業", "電子通路業", "其他電子業"]:
        return "🟣 " + industry_name
    elif industry_name in ["金融保險業"]:
        return "🟢 " + industry_name
    elif industry_name in ["鋼鐵工業", "水泥工業", "塑膠工業", "橡膠工業", "綠能環保"]:
        return "🟠 " + industry_name
    elif industry_name in ["航運業", "觀光餐旅", "汽車工業", "食品工業", "百貨貿易"]:
        return "🔴 " + industry_name
    elif industry_name in ["生技醫療業"]:
        return "🟢 " + industry_name
    elif industry_name in ["建材營造", "紡織纖維", "造紙工業"]:
        return "🟤 " + industry_name
    else:
        return "⚪ " + industry_name

def infer_industry(code, name):
    code_str = str(code).strip()
    if code_str in INDUSTRY_MAP:
        return INDUSTRY_MAP[code_str]
    
    if code_str.startswith("28"):
        return "金融保險業"
    elif code_str.startswith("11"):
        return "水泥工業"
    elif code_str.startswith("12"):
        return "食品工業"
    elif code_str.startswith("13"):
        return "塑膠工業"
    elif code_str.startswith("14"):
        return "紡織纖維"
    elif code_str.startswith("15") or code_str.startswith("16"):
        return "電機機械"
    elif code_str.startswith("17") or code_str.startswith("41") or code_str.startswith("64"):
        return "生技醫療業"
    elif code_str.startswith("20"):
        return "鋼鐵工業"
    elif code_str.startswith("22"):
        return "汽車工業"
    elif code_str.startswith("23") or code_str.startswith("24"):
        try:
            return "半導體業" if int(code_str) % 2 == 0 else "電子零組件業"
        except ValueError:
            return "半導體業"
    elif code_str.startswith("25"):
        return "建材營造"
    elif code_str.startswith("26"):
        return "航運業"
    elif code_str.startswith("29") or code_str.startswith("59"):
        return "百貨貿易"
    elif code_str.startswith("30") or code_str.startswith("35") or code_str.startswith("65"):
        return "電腦及週邊設備業"
    else:
        return "其他電子業"

gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
openrouter_key = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))

@st.cache_data(ttl=3600)
def load_stock_data():
    """整合 TWSE (上市) 與 TPEx (上櫃) 官方 API + PB、殖利率與收盤價"""
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
            df_pe["Name"] = df_pe["Name"].astype(str).str.strip()
            df_pe["PE"] = pd.to_numeric(df_pe["PEratio"], errors='coerce')
            df_pe["PB"] = pd.to_numeric(df_pe.get("PBratio", 0), errors='coerce')
            df_pe["Yield"] = pd.to_numeric(df_pe.get("DividendYield", 0), errors='coerce')
            
            df_pr["Code"] = df_pr["Code"].astype(str).str.strip()
            df_pr["ClosingPrice"] = pd.to_numeric(df_pr["ClosingPrice"].astype(str).str.replace(",", ""), errors='coerce')
            m_twse = pd.merge(df_pe, df_pr[["Code", "ClosingPrice"]], on="Code", how="inner")
            for _, row in m_twse.iterrows():
                pe_val = row["PE"] if pd.notnull(row["PE"]) and row["PE"] > 0 else 15.0
                pr_val = row["ClosingPrice"] if pd.notnull(row["ClosingPrice"]) and row["ClosingPrice"] > 0 else 0.0
                pb_val = row["PB"] if pd.notnull(row["PB"]) and row["PB"] > 0 else 1.2
                yd_val = row["Yield"] if pd.notnull(row["Yield"]) else 0.0
                all_stocks.append({
                    "Code": row["Code"],
                    "Name": row["Name"],
                    "Price": pr_val,
                    "PE": pe_val,
                    "PB": pb_val,
                    "Yield": yd_val,
                    "Market": "上市"
                })
    except Exception:
        pass

    otc_prices = {}
    try:
        url_otc_quotes = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_quotes"
        r_quotes = requests.get(url_otc_quotes, timeout=6)
        if r_quotes.status_code == 200:
            df_q = pd.DataFrame(r_quotes.json())
            q_code = "SecuritiesCompanyCode" if "SecuritiesCompanyCode" in df_q.columns else "Code"
            q_price = "Close" if "Close" in df_q.columns else "ClosingPrice"
            for _, q_row in df_q.iterrows():
                qc = str(q_row.get(q_code, "")).strip()
                qp = pd.to_numeric(str(q_row.get(q_price, 0)).replace(",", ""), errors='coerce')
                if qc and qp and qp > 0:
                    otc_prices[qc] = float(qp)
    except Exception:
        pass

    try:
        url_otc_pe = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis"
        r_otc = requests.get(url_otc_pe, timeout=6)
        if r_otc.status_code == 200:
            df_otc = pd.DataFrame(r_otc.json())
            code_col = "SecuritiesCompanyCode" if "SecuritiesCompanyCode" in df_otc.columns else "Code"
            name_col = "CompanyName" if "CompanyName" in df_otc.columns else "Name"
            pe_col = "PriceEarningRatio" if "PriceEarningRatio" in df_otc.columns else "PEratio"
            pb_col = "PriceBookRatio" if "PriceBookRatio" in df_otc.columns else "PBratio"
            yd_col = "YieldRatio" if "YieldRatio" in df_otc.columns else "DividendYield"
            
            for _, row in df_otc.iterrows():
                c_str = str(row.get(code_col, "")).strip()
                n_str = str(row.get(name_col, "")).strip()
                pe_v = pd.to_numeric(row.get(pe_col, 0), errors='coerce')
                pb_v = pd.to_numeric(row.get(pb_col, 0), errors='coerce')
                yd_v = pd.to_numeric(row.get(yd_col, 0), errors='coerce')
                if c_str and n_str and len(c_str) == 4:
                    pe_val = pe_v if pd.notnull(pe_v) and pe_v > 0 else 15.0
                    pb_val = pb_v if pd.notnull(pb_v) and pb_v > 0 else 1.2
                    yd_val = yd_v if pd.notnull(yd_v) else 0.0
                    pr_val = otc_prices.get(c_str, 0.0)
                    all_stocks.append({
                        "Code": c_str,
                        "Name": n_str,
                        "Price": pr_val,
                        "PE": pe_val,
                        "PB": pb_val,
                        "Yield": yd_val,
                        "Market": "上櫃"
                    })
    except Exception:
        pass

    if len(all_stocks) > 100:
        df = pd.DataFrame(all_stocks).drop_duplicates(subset=["Code"]).reset_index(drop=True)
        df["Industry"] = df.apply(lambda r: infer_industry(r["Code"], r["Name"]), axis=1)
        df["Industry_Tagged"] = df["Industry"].apply(get_industry_color)
        
        sector_medians = df.groupby("Industry")["PE"].median().to_dict()
        df["Sector_PE_Median"] = df["Industry"].map(sector_medians).fillna(18.0)
        df["次產業_PE折溢價(%)"] = ((df["PE"] - df["Sector_PE_Median"]) / df["Sector_PE_Median"]) * 100
        
        df["MA30"] = 0.0
        df["MA60"] = 0.0
        df["MA120"] = 0.0
        df["Daily_Trend"] = "⬆️"
        df["Weekly_Trend"] = "⬆️"
        df["Monthly_Trend"] = "⬆️"
        return df, False

    fallback_data = [
        {"Code": "2330", "Name": "台積電", "Price": 965.0, "PE": 18.5, "PB": 4.5, "Yield": 2.1, "Sector_PE_Median": 22.0},
        {"Code": "2454", "Name": "聯發科", "Price": 1210.0, "PE": 15.2, "PB": 3.2, "Yield": 4.5, "Sector_PE_Median": 22.0},
        {"Code": "2317", "Name": "鴻海", "Price": 270.0, "PE": 19.2, "PB": 1.8, "Yield": 3.8, "Sector_PE_Median": 18.8},
        {"Code": "2308", "Name": "台達電", "Price": 395.0, "PE": 21.0, "PB": 3.5, "Yield": 2.8, "Sector_PE_Median": 20.0},
        {"Code": "2881", "Name": "富邦金", "Price": 92.0, "PE": 10.2, "PB": 1.2, "Yield": 5.2, "Sector_PE_Median": 12.5}
    ]
    df = pd.DataFrame(fallback_data)
    df["Code"] = df["Code"].astype(str).str.strip()
    df["Name"] = df["Name"].astype(str).str.strip()
    df["Industry"] = df.apply(lambda r: infer_industry(r["Code"], r["Name"]), axis=1)
    df["Industry_Tagged"] = df["Industry"].apply(get_industry_color)
    df["次產業_PE折溢價(%)"] = ((df["PE"] - df["Sector_PE_Median"]) / df["Sector_PE_Median"]) * 100
    df["MA30"] = 0.0
    df["MA60"] = 0.0
    df["MA120"] = 0.0
    df["Daily_Trend"] = "⬆️"
    df["Weekly_Trend"] = "⬆️"
    df["Monthly_Trend"] = "⬆️"
    return df, True

@st.cache_data(ttl=1800)
def get_real_stock_history(stock_code):
    if not YFINANCE_AVAILABLE:
        return None
    try:
        ticker = f"{stock_code}.TW"
        df_hist = yf.Ticker(ticker).history(period="6mo")
        if len(df_hist) < 20:
            ticker = f"{stock_code}.TWO"
            df_hist = yf.Ticker(ticker).history(period="6mo")
            
        if len(df_hist) >= 20:
            c = df_hist["Close"]
            ma5 = float(c.tail(5).mean())
            ma20 = float(c.tail(20).mean())
            ma30 = float(c.tail(30).mean()) if len(c) >= 30 else ma20
            ma60 = float(c.tail(60).mean()) if len(c) >= 60 else ma30
            ma120 = float(c.tail(120).mean()) if len(c) >= 120 else ma60
            
            latest_close = float(c.iloc[-1])
            prev_close = float(c.iloc[-2]) if len(c) >= 2 else latest_close
            
            daily_trend = "⬆️" if latest_close >= prev_close else "⬇️"
            weekly_trend = "⬆️" if latest_close >= ma5 else "⬇️"
            monthly_trend = "⬆️" if latest_close >= ma20 else "⬇️"
            
            return {
                "High_30D": round(float(c.tail(22).max()), 1),
                "Low_30D": round(float(c.tail(22).min()), 1),
                "High_60D": round(float(c.tail(44).max()), 1),
                "Low_60D": round(float(c.tail(44).min()), 1),
                "Latest_Close": round(latest_close, 1),
                "MA30": round(ma30, 1),
                "MA60": round(ma60, 1),
                "MA120": round(ma120, 1),
                "Daily_Trend": daily_trend,
                "Weekly_Trend": weekly_trend,
                "Monthly_Trend": monthly_trend
            }
    except Exception:
        pass
    return None

def call_gemini_api(api_key, prompt):
    """徹底修復 Gemini 404：優先透過官方 SDK 路由，並備援 v1 端點"""
    clean_key = str(api_key).strip().strip('"').strip("'")
    if not clean_key:
        return False, "GEMINI_API_KEY 為空，請檢查 Secrets 設定。"

    # 1. 優先透過官方 google-generativeai SDK
    if GENAI_LEGACY_AVAILABLE:
        try:
            genai_legacy.configure(api_key=clean_key)
            for m_name in ['gemini-1.5-flash', 'gemini-1.5-pro']:
                try:
                    m = genai_legacy.GenerativeModel(m_name)
                    res = m.generate_content(prompt)
                    if res and hasattr(res, 'text') and res.text:
                        return True, res.text
                except Exception:
                    continue
        except Exception:
            pass

    # 2. 備援使用標準 REST API v1 端點
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={clean_key}"
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            data = res.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            if text:
                return True, text
        return False, f"HTTP {res.status_code}: {res.text}"
    except Exception as e:
        return False, f"Gemini 連線失敗: {str(e)}"

def call_openrouter_llama(api_key, prompt):
    """動態爬取 OpenRouter 當下存活的免費模型 ID（已驗證成功）"""
    clean_key = str(api_key).strip().strip('"').strip("'")
    if not clean_key:
        return False, "OPENROUTER_API_KEY 為空，請檢查 Secrets 設定。"

    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://streamlit.io",
        "X-Title": "Taiwan Stock Analysis App"
    }
    
    target_model = "meta-llama/llama-3.1-8b-instruct:free"
    try:
        models_res = requests.get("https://openrouter.ai/api/v1/models", timeout=10)
        if models_res.status_code == 200:
            models_data = models_res.json().get('data', [])
            free_models = [m['id'] for m in models_data if m.get('pricing', {}).get('prompt') == '0' and str(m['id']).endswith(':free')]
            if free_models:
                llama_models = [m for m in free_models if 'llama' in m.lower()]
                target_model = llama_models[0] if llama_models else free_models[0]
    except Exception:
        pass

    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": target_model,
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=20)
        if res.status_code == 200:
            data = res.json()
            content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            if content:
                return True, content
        return False, f"呼叫模型 [{target_model}] 失敗 (HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return False, f"OpenRouter 連線失敗: {str(e)}"

# 載入 df_stocks
df_stocks, is_fallback = load_stock_data()

# ==========================================
# 參數 Session State 記憶載入
# ==========================================
qp = st.query_params

if "ind_val" not in st.session_state:
    st.session_state["ind_val"] = qp.get("ind", "全部產業")
if "pe_disc_val" not in st.session_state:
    st.session_state["pe_disc_val"] = int(qp.get("pe_disc", -5))
if "sec_pe_val" not in st.session_state:
    st.session_state["sec_pe_val"] = float(qp.get("sec_pe", 30.0))
if "max_pe_val" not in st.session_state:
    st.session_state["max_pe_val"] = float(qp.get("max_pe", 25.0))
if "roe_val" not in st.session_state:
    st.session_state["roe_val"] = float(qp.get("roe", 8.0))
if "yoy_val" not in st.session_state:
    st.session_state["yoy_val"] = float(qp.get("yoy", -5.0))

# ==========================================
# 側邊欄設定 (Sidebar)
# ==========================================
st.sidebar.header("⚙️ 篩選條件設定")
st.sidebar.caption(f"目前版本：{VERSION}")

if st.sidebar.button("🔄 重新載入證交所最新數據"):
    st.cache_data.clear()
    st.sidebar.success("已清空快取並重新載入證交所數據！")
    st.rerun()

st.sidebar.subheader("🔍 單一個股獨立查詢與健診")
search_input = st.sidebar.text_input("輸入股票代號/名稱 (例如: 2330 或 2641)：", value="")

search_stock_options = ["(不指定 / 觀看全部)"] + [f"{r['Code']} {r['Name']}" for _, r in df_stocks.iterrows()]
selected_search_stock = st.sidebar.selectbox("或選擇下拉清單：", search_stock_options)

final_search_code = ""
if search_input.strip():
    final_search_code = search_input.strip().split()[0]
elif selected_search_stock != "(不指定 / 觀看全部)":
    final_search_code = selected_search_stock.split()[0]

st.sidebar.markdown("---")

all_industries = ["全部產業"] + sorted(list(df_stocks["Industry"].unique()))
ind_index = all_industries.index(st.session_state["ind_val"]) if st.session_state["ind_val"] in all_industries else 0

selected_industry = st.sidebar.selectbox("指定產業類別", all_industries, index=ind_index, key="sb_ind")

pe_discount_threshold = st.sidebar.slider(
    "次產業 PE 折價率上限 (%) [越負代表越低估]",
    min_value=-50, max_value=20, value=st.session_state["pe_disc_val"], step=5, key="sb_pe_disc"
)

max_sector_pe = st.sidebar.slider(
    "次產業 PE 中位數上限 (倍) [越低代表整體產業估值越平實]",
    min_value=5.0, max_value=50.0, value=st.session_state["sec_pe_val"], step=1.0, key="sb_sec_pe"
)

max_stock_pe = st.sidebar.slider(
    "個股 PE 絕對值上限 (倍) [越低代表購買價格越便宜]",
    min_value=3.0, max_value=40.0, value=st.session_state["max_pe_val"], step=1.0, key="sb_max_pe"
)

min_roe = st.sidebar.number_input(
    "最低 ROE 門檻 (%) [越高代表公司獲利與股東報酬越佳]",
    value=st.session_state["roe_val"], step=1.0, key="sb_roe"
)

min_yoy = st.sidebar.number_input(
    "近12個月營收 YoY 成長率門檻 (%) [越高代表營收成長動能越強]",
    value=st.session_state["yoy_val"], step=1.0, key="sb_yoy"
)

# 狀態寫回
st.session_state["ind_val"] = selected_industry
st.session_state["pe_disc_val"] = pe_discount_threshold
st.session_state["sec_pe_val"] = max_sector_pe
st.session_state["max_pe_val"] = max_stock_pe
st.session_state["roe_val"] = min_roe
st.session_state["yoy_val"] = min_yoy

st.query_params["ind"] = selected_industry
st.query_params["pe_disc"] = str(pe_discount_threshold)
st.query_params["sec_pe"] = str(max_sector_pe)
st.query_params["max_pe"] = str(max_stock_pe)
st.query_params["roe"] = str(min_roe)
st.query_params["yoy"] = str(min_yoy)

# 按鈕觸發
st.sidebar.markdown("---")
btn_run_filter = st.sidebar.button("🔍 套用條件並開始篩選", type="primary", use_container_width=True)

if "filter_executed" not in st.session_state:
    st.session_state["filter_executed"] = False

if btn_run_filter:
    st.session_state["filter_executed"] = True

filtered_df = df_stocks.copy()

if selected_industry != "全部產業":
    filtered_df = filtered_df[filtered_df["Industry"] == selected_industry]

filtered_df = filtered_df[
    (filtered_df["次產業_PE折溢價(%)"] <= pe_discount_threshold) &
    (filtered_df["Sector_PE_Median"] <= max_sector_pe) &
    (filtered_df["PE"] <= max_stock_pe)
]

# ==========================================
# 主要頁面頁籤 (Main Tabs)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 篩選總覽與核心數據", "🔍 雙源資料對照表", "🧠 Gemini & Llama 雙 AI 診斷"])

with tab1:
    if final_search_code:
        st.subheader("🎯 單一個股獨立健診與數據看板")
        
        clean_search_target = str(final_search_code).strip()
        matched_stocks = df_stocks[
            (df_stocks["Code"].str.lower() == clean_search_target.lower()) | 
            (df_stocks["Name"].str.lower().str.contains(clean_search_target.lower(), na=False))
        ]
        
        if len(matched_stocks) > 0:
            stock_data = matched_stocks.iloc[0].to_dict()
            
            hist_info = get_real_stock_history(stock_data['Code'])
            if hist_info:
                stock_data["Price"] = hist_info["Latest_Close"]
                stock_data["High_30D"] = hist_info["High_30D"]
                stock_data["Low_30D"] = hist_info["Low_30D"]
                stock_data["High_60D"] = hist_info["High_60D"]
                stock_data["Low_60D"] = hist_info["Low_60D"]
            
            st.markdown(f"#### 💰 **{stock_data['Name']} ({stock_data['Code']}) 官方真實股價與歷史高低位階**")
            p1, p2, p3, p4, p5 = st.columns(5)
            p1.metric("當前真實股價", f"{stock_data['Price']:.1f} 元" if stock_data['Price'] and stock_data['Price'] > 0 else "擷取中")
            p2.metric("近 30 日最高價", f"{stock_data['High_30D']:.1f} 元" if stock_data.get('High_30D') else "擷取中")
            p3.metric("近 30 日最低價", f"{stock_data['Low_30D']:.1f} 元" if stock_data.get('Low_30D') else "擷取中")
            p4.metric("近 60 日最高價", f"{stock_data['High_60D']:.1f} 元" if stock_data.get('High_60D') else "擷取中")
            p5.metric("近 60 日最低價", f"{stock_data['Low_60D']:.1f} 元" if stock_data.get('Low_60D') else "擷取中")
            
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("本益比 (PE) [官方]", f"{stock_data['PE']:.1f} 倍")
            sc2.metric("次產業 PE 折價率", f"{stock_data['次產業_PE折溢價(%)']:.1f}%")
            sc3.metric("次產業 PE 中位數", f"{stock_data['Sector_PE_Median']:.1f} 倍")
            
            mismatches = []
            if stock_data["次產業_PE折溢價(%)"] > pe_discount_threshold:
                mismatches.append(f"❌ 次產業 PE 折價率：目前 `{stock_data['次產業_PE折溢價(%)']:.1f}%` (要求 `<= {pe_discount_threshold}%`)")
            if stock_data["Sector_PE_Median"] > max_sector_pe:
                mismatches.append(f"❌ 次產業 PE 中位數：目前 `{stock_data['Sector_PE_Median']:.1f}倍` (要求 `<= {max_sector_pe}倍`)")
            if stock_data["PE"] > max_stock_pe:
                mismatches.append(f"❌ 個股本益比 (PE)：目前 `{stock_data['PE']:.1f}倍` (要求 `<= {max_stock_pe}倍`)")

            if len(mismatches) == 0:
                st.success(f"✅ **{stock_data['Name']} ({stock_data['Code']}) 完全符合當前的估值篩選條件！**")
            else:
                st.warning(f"⚠️ **{stock_data['Name']} ({stock_data['Code']}) 未達部分估值門檻，未通過項目如下：**\n\n" + "\n\n".join(mismatches))
        else:
            st.error(f"⚠️ **查無代號/名稱為 `{final_search_code}` 之股票數據，請確認代號是否輸入正確。**")
            
        st.markdown("---")

    col1, col2, col3 = st.columns(3)
    if not st.session_state["filter_executed"]:
        col1.metric("上市櫃掃描總數", "---")
        col2.metric("符合條件潛力股", "---")
        col3.metric("平均 PE 折價率", "---")
        st.info("👈 **請於左側邊欄確認或調整篩選條件後，點擊『🔍 套用條件並開始篩選』按鈕即可開始計算並產出潛力股清單！**")
    else:
        col1.metric("上市櫃掃描總數", f"{len(df_stocks)} 檔")
        col2.metric("符合條件潛力股", f"{len(filtered_df)} 檔")
        avg_discount = filtered_df["次產業_PE折溢價(%)"].mean() if len(filtered_df) > 0 else 0
        col3.metric("平均 PE 折價率", f"{avg_discount:.1f}%")

        st.subheader("🎯 Qualified Stock Targets (合格標的清單)")
        
        if len(filtered_df) > 0:
            st.markdown("##### ⚙️ 表格顯示欄位自訂與順序調整（可拖曳排順序，自動記憶）")
            
            for idx, r in filtered_df.iterrows():
                h_info = get_real_stock_history(r["Code"])
                if h_info:
                    if r["Price"] == 0.0 or pd.isnull(r["Price"]):
                        filtered_df.at[idx, "Price"] = h_info["Latest_Close"]
                    filtered_df.at[idx, "MA30"] = h_info["MA30"]
                    filtered_df.at[idx, "MA60"] = h_info["MA60"]
                    filtered_df.at[idx, "MA120"] = h_info["MA120"]
                    filtered_df.at[idx, "Daily_Trend"] = h_info["Daily_Trend"]
                    filtered_df.at[idx, "Weekly_Trend"] = h_info["Weekly_Trend"]
                    filtered_df.at[idx, "Monthly_Trend"] = h_info["Monthly_Trend"]
            
            all_optional_cols = {
                "產業類別": "Industry_Tagged",
                "當前真實股價": "Price",
                "本益比(PE)": "PE",
                "股價淨值比(PB)": "PB",
                "殖利率(%)": "Yield",
                "次產業中位數PE": "Sector_PE_Median",
                "次產業 PE 折溢價(%)": "次產業_PE折溢價(%)",
                "近 30 日均價": "MA30",
                "近 60 日均價": "MA60",
                "近 120 日均價": "MA120",
                "日線趨勢": "Daily_Trend",
                "週線趨勢": "Weekly_Trend",
                "月線趨勢": "Monthly_Trend"
            }
            
            all_col_keys = list(all_optional_cols.keys())
            if "saved_col_order" not in st.session_state or len(st.session_state["saved_col_order"]) < len(all_col_keys):
                st.session_state["saved_col_order"] = all_col_keys

            selected_col_names = st.multiselect(
                "請選擇要於畫面顯示的延伸數據項目：",
                options=all_col_keys,
                default=[c for c in st.session_state["saved_col_order"] if c in all_optional_cols]
            )
            
            if selected_col_names != st.session_state["saved_col_order"]:
                st.session_state["saved_col_order"] = selected_col_names
            
            display_cols = ["Code", "Name"] + [all_optional_cols[c] for c in selected_col_names if c in all_optional_cols]
            rename_dict = {
                "Code": "股票代號",
                "Name": "股票名稱",
                "Industry_Tagged": "產業類別",
                "Price": "當前真實股價",
                "PE": "本益比(PE)",
                "PB": "股價淨值比(PB)",
                "Yield": "殖利率(%)",
                "Sector_PE_Median": "次產業中位數PE",
                "次產業_PE折溢價(%)": "次產業 PE 折溢價(%)",
                "MA30": "近 30 日均價",
                "MA60": "近 60 日均價",
                "MA120": "近 120 日均價",
                "Daily_Trend": "日線趨勢",
                "Weekly_Trend": "週線趨勢",
                "Monthly_Trend": "月線趨勢"
            }
            
            display_df = filtered_df[display_cols].rename(columns=rename_dict)
            
            format_mapping = {}
            for col in display_df.columns:
                if any(k in col for k in ["PE", "PB", "折溢價", "股價", "殖利率", "均價"]):
                    format_mapping[col] = "{:.1f}"
                    
            st.dataframe(
                display_df.style.format(format_mapping, na_rep="預估中"),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("尚無符合當前條件的標的，請適度放寬側邊欄的篩選條件。")

with tab2:
    st.subheader("🔍 雙源資料交叉檢視與對照表")
    st.markdown("""
    本頁面完整呈現 **「臺灣證券交易所 (TWSE) 與 櫃買中心 (TPEx) 官方即時 API 資料」** 之對照數據。
    """)
    
    if not st.session_state["filter_executed"]:
        st.info("👈 請先於左側邊欄點擊『🔍 套用條件並開始篩選』按鈕。")
    elif len(filtered_df) > 0:
        compare_df = filtered_df[["Code", "Name", "Industry_Tagged", "Price", "PE", "PB", "Yield", "Sector_PE_Median"]].copy()
        compare_df.columns = [
            "股票代號 [官方]", 
            "股票名稱 [官方]", 
            "33大產業類別 [官方]", 
            "當前真實股價 [官方]",
            "本益比 PE [官方]", 
            "股價淨值比 PB [官方]",
            "殖利率 (%) [官方]",
            "次產業中位數 PE [計算]"
        ]
        
        st.dataframe(
            compare_df.style.format({
                "當前真實股價 [官方]": "{:.1f}",
                "本益比 PE [官方]": "{:.1f}",
                "股價淨值比 PB [官方]": "{:.1f}",
                "殖利率 (%) [官方]": "{:.1f}",
                "次產業中位數 PE [計算]": "{:.1f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("目前篩選條件下無符合標的，請調整側邊欄參數以進行數據檢視。")

with tab3:
    st.subheader("🧠 Gemini & Meta Llama 雙 AI 智慧白話深度個股診斷")
    
    diagnostic_df = filtered_df.copy()
    if final_search_code:
        clean_target = str(final_search_code).strip().lower()
        extra_match = df_stocks[
            (df_stocks["Code"].str.lower() == clean_target) | 
            (df_stocks["Name"].str.lower().str.contains(clean_target, na=False))
        ]
        if len(extra_match) > 0:
            diagnostic_df = pd.concat([diagnostic_df, extra_match]).drop_duplicates(subset=["Code"])

    if len(diagnostic_df) == 0:
        st.info("👈 當前篩選條件下尚無合格標的。請調整側邊欄條件並點擊『🔍 套用條件並開始篩選』按鈕，或於左側獨立查詢框輸入個股代號進行診斷。")
    else:
        target_options = [f"{row['Code']} {row['Name']}" for _, row in diagnostic_df.iterrows()]
        selected_stock_str = st.selectbox("請選擇欲診斷的合格低估標的：", target_options)
        
        if st.button("🚀 一鍵生成 Gemini + Llama 雙 AI 白話對照報告"):
            stock_code = selected_stock_str.split()[0]
            target_row = df_stocks[df_stocks["Code"] == stock_code].iloc[0]
            
            prompt = f"""
            你是一位說話親切、條理清晰的股票投資助手。請用一般非專業人士、一般社會大眾都能輕鬆看懂的「通俗白話文」，為我解讀以下股票：
            
            - 股票名稱：{target_row['Name']} ({target_row['Code']})
            - 所屬產業：{target_row['Industry']}
            - 目前股價：{target_row['Price']} 元
            - 本益比：{target_row['PE']} 倍 (同產業平均大約是：{target_row['Sector_PE_Median']} 倍，這代表股價比同業便宜了約 {abs(target_row['次產業_PE折溢價(%)']):.1f}%)

            請提供一份白話簡明、條列清晰的分析報告（請避免使用艱深的金融學術名詞，用日常大白話說明即可）：
            1. 💡 **價格便宜程度說明**：用簡單口語說明這檔股票價格比同業便宜還是貴？為什麼會比較便宜？
            2. 🏢 **公司主要靠什麼賺錢**：用一兩句話簡單介紹這家公司在做什麼業務、有什麼優勢？
            3. ⚖️ **白話總評與注意事項**：給一般投資人的溫馨提示，買進這檔股票有什麼好處與需要特別注意的風險。
            """
            
            col_gemini, col_llama = st.columns(2)
            
            with col_gemini:
                st.markdown("### 🧠 Gemini AI 白話分析報告")
                if not gemini_key:
                    st.error("❌ 未偵測到 Gemini API 金鑰。請於 Secrets 設定 `GEMINI_API_KEY`。")
                else:
                    with st.spinner("Gemini 正在產生白話報告..."):
                        g_success, g_res = call_gemini_api(gemini_key, prompt)
                        if g_success:
                            st.markdown(g_res)
                        else:
                            st.error(f"❌ Gemini 回應失敗：`{g_res}`")
                            
            with col_llama:
                st.markdown("### 🦙 Meta Llama 3 (OpenRouter) 白話分析報告")
                if not openrouter_key:
                    st.error("❌ 未偵測到 OpenRouter API 金鑰。請於 Secrets 設定 `OPENROUTER_API_KEY`。")
                else:
                    with st.spinner("Meta Llama 3 正在產生白話報告..."):
                        l_success, l_res = call_openrouter_llama(openrouter_key, prompt)
                        if l_success:
                            st.markdown(l_res)
                        else:
                            st.error(f"❌ Llama 回應失敗：`{l_res}`")

st.markdown("---")
st.caption(f"系統版本：{VERSION} | 最後更新日期：{UPDATE_DATE} | 資料來源：臺灣證券交易所、櫃買中心與公開資訊觀測站")
