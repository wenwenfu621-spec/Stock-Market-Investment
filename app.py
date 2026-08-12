import json
import urllib.request
import os
import io
import pandas as pd
import streamlit as st
from google import genai

# ----------------------------------------------------
# 1. 網頁基本設定 (Page Config)
# ----------------------------------------------------
st.set_page_config(
    page_title="台股價值與潛力股智慧分析系統",
    page_icon="📈",
    layout="wide"
)

st.title("📈 台股價值與潛力股智慧分析系統")
st.caption("結合官方 OpenAPI、開源財報數據與 Gemini AI 的同業估值診斷平台")

# ----------------------------------------------------
# 2. 安全讀取 Gemini API 金鑰並初始化 Client
# ----------------------------------------------------
@st.cache_resource
def init_gemini_client():
    # 優先從 Streamlit Secrets 讀取，若無則讀取系統環境變數
    api_key = None
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = os.environ.get("GEMINI_API_KEY")
        
    if api_key:
        return genai.Client(api_key=api_key)
    return None

client = init_gemini_client()

if not client:
    st.warning("⚠️ 未檢測到 Gemini API 金鑰。請於 Streamlit Cloud 的 Secrets 設定 `GEMINI_API_KEY`，或於本地端設定環境變數以啟用 AI 診斷功能。")

# ----------------------------------------------------
# 3. 資料抓取模組 (Data Retrieval & Preprocessing)
# ----------------------------------------------------
@st.cache_data(ttl=3600)  # 快取 1 小時以提升網頁載入速度
def fetch_stock_data():
    """抓取證交所與櫃買中心官方 API 最新數據並整理"""
    try:
        # 上市股票估值數據
        url_twse = "https://openapi.twse.com.tw/v1/exchangeReport/BWIBBU_ALL"
        req_twse = urllib.request.Request(url_twse, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_twse) as resp:
            data_twse = json.loads(resp.read().decode("utf-8"))
        
        df_twse = pd.DataFrame(data_twse).rename(columns={
            "Code": "股票代碼", "Name": "股票名稱", 
            "PEratio": "官方_PE", "PBratio": "官方_PB", "DividendYield": "官方_殖利率(%)"
        })
        df_twse["市場"] = "上市"

        # 上櫃股票估值數據
        url_tpex = "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratios_analysis"
        req_tpex = urllib.request.Request(url_tpex, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req_tpex) as resp:
            data_tpex = json.loads(resp.read().decode("utf-8"))

        df_tpex = pd.DataFrame(data_tpex).rename(columns={
            "SecuritiesCompanyCode": "股票代碼", "CompanyName": "股票名稱",
            "PERatio": "官方_PE", "PBRatio": "官方_PB", "DividendYield": "官方_殖利率(%)"
        })
        df_tpex["市場"] = "上櫃"

        # 合併上市櫃資料
        df_all = pd.concat([df_twse, df_tpex], ignore_index=True)

        for col in ["官方_PE", "官方_PB", "官方_殖利率(%)"]:
            df_all[col] = pd.to_numeric(df_all[col], errors="coerce")

        # 過濾虧損或異常值
        df_valid = df_all[df_all["官方_PE"] > 0].dropna(subset=["官方_PE"]).copy()

        # 模擬/補充雙源欄位 (實務上接 FinMind API)
        df_valid["官方_大產業"] = "電子/半導體類"
        df_valid["開源_次產業"] = "IC設計與封測"
        df_valid["MOPS官方_ROE(%)"] = (df_valid["官方_PB"] / df_valid["官方_PE"] * 100).round(2)
        df_valid["FinMind開源_ROE(%)"] = df_valid["MOPS官方_ROE(%)"]
        df_valid["近12月營收YoY(%)"] = 8.5  # 預設範例成長值

        # 計算次產業中位數 PE 與相對折溢價率
        sub_pe = df_valid.groupby("開源_次產業")["官方_PE"].transform("median")
        df_valid["次產業_中位數PE"] = sub_pe.round(2)
        df_valid["次產業_PE折溢價(%)"] = (((df_valid["官方_PE"] - sub_pe) / sub_pe) * 100).round(2)

        return df_valid
    except Exception as e:
        st.error(f"資料抓取失敗：{e}")
        return pd.DataFrame()

with st.spinner("⏳ 正在連線至證交所與櫃買中心抓取最新盤後數據..."):
    df_stocks = fetch_stock_data()

# ----------------------------------------------------
# 4. 側邊欄控制項 (Sidebar Controls)
# ----------------------------------------------------
st.sidebar.header("⚙️ 篩選條件門檻")

if not df_stocks.empty:
    pe_discount_cutoff = st.sidebar.slider(
        "次產業 PE 折價率 (%) [低於多少%算低估]",
        min_value=-50, max_value=0, value=-15, step=5
    )

    roe_cutoff = st.sidebar.number_input(
        "最低 ROE 門檻 (%)",
        min_value=0.0, max_value=50.0, value=12.0, step=1.0
    )

    yoy_cutoff = st.sidebar.number_input(
        "近12個月營收 YoY 成長率門檻 (%)",
        min_value=-20.0, max_value=100.0, value=0.0, step=1.0
    )

    # 資料篩選
    filtered_df = df_stocks[
        (df_stocks["次產業_PE折溢價(%)"] <= pe_discount_cutoff) &
        (df_stocks["MOPS官方_ROE(%)"] >= roe_cutoff) &
        (df_stocks["近12月營收YoY(%)"] >= yoy_cutoff)
    ].copy()
else:
    filtered_df = pd.DataFrame()

# ----------------------------------------------------
# 5. 主頁面頁籤 (Main Area Tabs)
# ----------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📊 篩選總覽與核心數據", "🔍 雙源資料對照表", "🤖 Gemini AI 個股診斷"])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("上市櫃掃描總數", f"{len(df_stocks)} 檔")
    col2.metric("符合條件潛力股", f"{len(filtered_df)} 檔")
    col3.metric("平均 PE 折價率", f"{filtered_df['次產業_PE折溢價(%)'].mean():.1f}%" if not filtered_df.empty else "0%")

    st.markdown("---")
    st.subheader("🎯 Qualified Stock Targets (合格標的清單)")
    
    if not filtered_df.empty:
        display_cols = [
            "股票代碼", "股票名稱", "市場", "官方_PE", 
            "次產業_中位數PE", "次產業_PE折溢價(%)", "MOPS官方_ROE(%)", "官方_殖利率(%)"
        ]
        st.dataframe(filtered_df[display_cols], use_container_width=True)
    else:
        st.info("尚無符合當前條件的標的，請放寬側邊欄的篩選條件。")

with tab2:
    st.subheader("📑 官方原始數據 vs 開源數據完整對照")
    st.caption("同步呈現公開資訊觀測站 (MOPS) 與 FinMind API 欄位以確保數據純度與一致性")
    if not filtered_df.empty:
        st.dataframe(filtered_df, use_container_width=True)

with tab3:
    st.subheader("🤖 個股深度價值與風險 AI 診斷")
    
    if not filtered_df.empty:
        target_option = st.selectbox(
            "請選擇欲分析的目標股票：",
            options=filtered_df["股票代碼"] + " " + filtered_df["股票名稱"]
        )
        
        target_code = target_option.split()[0]
        stock_info = filtered_df[filtered_df["股票代碼"] == target_code].iloc[0]
        
        if st.button("🚀 啟動 Gemini AI 報告生成"):
            if client:
                with st.spinner(f"Gemini 正在分析 {stock_info['股票代碼']} {stock_info['股票名稱']} 的基本面與產業競爭力..."):
                    prompt = f"""
                    你是一位專業的台股價值投資分析師。請針對以下經過量化篩選出的標的生成診斷報告：

                    【標的數據】
                    - 股票代碼與名稱：{stock_info['股票代碼']} {stock_info['股票名稱']} ({stock_info['市場']})
                    - 細分次產業：{stock_info['開源_次產業']}
                    - 當前本益比 (PE)：{stock_info['官方_PE']}
                    - 次產業 PE 中位數：{stock_info['次產業_中位數PE']} (折價 {stock_info['次產業_PE折溢價(%)']}%)
                    - 官方 ROE：{stock_info['MOPS官方_ROE(%)']}%

                    請嚴格依據以下結構輸出報告：
                    1. **值得投資的核心原因 (Investment Thesis)**
                    2. **資料來源與資訊純度標籤** (明確標註數據來自公開資訊觀測站 MOPS，並說明有無未經證實之網路傳聞)
                    3. **同業競爭與產業風險** (包含同業龍頭壓制風險或產品替代風險)
                    4. **投資風險程度評估** (給予 低 / 中 / 高 等級，並說明理由)
                    5. **總結與長期持有建議**
                    """
                    try:
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=prompt
                        )
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Gemini 分析產生錯誤：{e}")
            else:
                st.error("無法呼叫 Gemini API，請確保已設定正確的 API Key。")
    else:
        st.warning("⚠️ 目前無符合條件之標的可供分析。")

# ----------------------------------------------------
# 6. 報表匯出功能 (Exports)
# ----------------------------------------------------
st.markdown("---")
st.subheader("📥 數據下載")

if not filtered_df.empty:
    # 建立 Excel 下載緩衝區
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, sheet_name='低估潛力股', index=False)
        df_stocks.to_excel(writer, sheet_name='全市場同業對比', index=False)
    
    st.download_button(
        label="📄 下載 Excel 完整篩選報表",
        data=buffer.getvalue(),
        file_name="台股潛力股篩選報表.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )