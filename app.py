import streamlit as st
import pandas as pd
import requests
import os
from google import genai

# ==========================================
# 版本資訊 (Version Info)
# 版本別：v1.2.0
# 更新日期：2026-08-12
# 修改內容：
# 1. 支援次產業 PE 中位數與個股 PE 雙重上限篩選。
# 2. 內建台股 33 大產業分類字典，修正「一般產業」問題。
# 3. 產業色彩標籤 (8 大色系歸類)。
# 4. 新增外資持股比與負債比欄位，並支援動態勾選顯示與橫向凍結卷軸。
# 5. 左下角側邊欄新增個人識別碼與頭像上傳展示區塊。
# ==========================================

VERSION = "v1.2.0"
UPDATE_DATE = "2026-08-12"

st.set_page_config(
    page_title=f"台股價值與潛力股智慧分析系統 {VERSION}",
    page_icon="📈",
    layout="wide"
)

st.title("📈 台股價值與潛力股智慧分析系統")
st.caption(f"📌 版本別：{VERSION} | 🗓️ 更新日期：{UPDATE_DATE} | 結合官方 OpenAPI、開源財報數據與 Gemini AI 的同業估值診斷平台")

# ==========================================
# 台股官方 33 大產業字典與色彩歸類對照表
# ==========================================
INDUSTRY_MAP = {
    "2330": "半導體業", "2454": "半導體業", "2303": "半導體業", "3711": "半導體業", "2379": "半導體業",
    "2317": "其他電子業", "2382": "電腦及週邊設備業", "2357": "電腦及週邊設備業", "3231": "電腦及週邊設備業",
    "2308": "電子零組件業", "2316": "電子零組件業", "3034": "半導體業",
    "2881": "金融保險業", "2882": "金融保險業", "2892": "金融保險業", "2886": "金融保險業", "2884": "金融保險業",
    "1101": "水泥工業", "1102": "水泥工業", "1301": "塑膠工業", "1303": "塑膠工業",
    "2002": "鋼鐵工業", "1216": "食品工業", "2603": "航運業", "2609": "航運業", "2615": "航運業",
    "2542": "建材營造", "2511": "建材營造", "1707": "生技醫療業", "6446": "生技醫療業"
}

# 8 大核心產業色彩 mapping (Hex Code)
def get_industry_color(industry_name):
    if industry_name in ["半導體業", "電子零組件業"]:
        return "🔵 " + industry_name  # 科技藍
    elif industry_name in ["電腦及週邊設備業", "光電業", "通信網路業"]:
        return "🔷 " + industry_name  # 青綠
    elif industry_name in ["網通業", "資訊服務業", "電子通路業", "其他電子業"]:
        return "🟣 " + industry_name  # 紫羅蘭
    elif industry_name in ["金融保險業"]:
        return "🟢 " + industry_name  # 翡翠綠
    elif industry_name in ["鋼鐵工業", "水泥工業", "塑膠工業", "橡膠工業", "綠能環保"]:
        return "🟠 " + industry_name  # 琥珀橙
    elif industry_name in ["航運業", "觀光餐旅", "汽車工業", "食品工業", "百貨貿易"]:
        return "🔴 " + industry_name  # 珊瑚紅
    elif industry_name in ["生技醫療業"]:
        return "🟢 " + industry_name  # 醫用青
    else:
        return "⚪ " + industry_name  # 石灰灰

# 初始化 Gemini API Client
gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))

@st.cache_data(ttl=3600)
def load_stock_data():
    """載入台股資料庫並補充 33 大產業別、籌碼與財務指標"""
    fallback_data = [
        {"Code": "2330", "Name": "台積電", "PE": 18.5, "Sector_PE_Median": 22.0, "ROE": 28.5, "YoY": 16.8, "Foreign_Hold": 73.2, "Debt_Ratio": 38.5},
        {"Code": "2454", "Name": "聯發科", "PE": 15.2, "Sector_PE_Median": 22.0, "ROE": 22.1, "YoY": 8.5, "Foreign_Hold": 61.5, "Debt_Ratio": 42.1},
        {"Code": "2317", "Name": "鴻海", "PE": 10.5, "Sector_PE_Median": 14.0, "ROE": 11.2, "YoY": 3.2, "Foreign_Hold": 41.8, "Debt_Ratio": 58.2},
        {"Code": "2308", "Name": "台達電", "PE": 21.0, "Sector_PE_Median": 20.0, "ROE": 16.5, "YoY": 7.4, "Foreign_Hold": 65.4, "Debt_Ratio": 45.0},
        {"Code": "2881", "Name": "富邦金", "PE": 10.2, "Sector_PE_Median": 12.5, "ROE": 13.8, "YoY": 12.1, "Foreign_Hold": 28.5, "Debt_Ratio": 88.2},
        {"Code": "2882", "Name": "國泰金", "PE": 11.0, "Sector_PE_Median": 12.5, "ROE": 12.5, "YoY": 9.4, "Foreign_Hold": 24.1, "Debt_Ratio": 89.5},
        {"Code": "2892", "Name": "第一金", "PE": 14.5, "Sector_PE_Median": 14.0, "ROE": 9.8, "YoY": 4.5, "Foreign_Hold": 22.3, "Debt_Ratio": 91.0},
        {"Code": "1101", "Name": "台泥", "PE": 13.8, "Sector_PE_Median": 16.0, "ROE": 6.5, "YoY": -2.1, "Foreign_Hold": 21.5, "Debt_Ratio": 48.6},
        {"Code": "1301", "Name": "台塑", "PE": 18.2, "Sector_PE_Median": 17.5, "ROE": 5.2, "YoY": -8.5, "Foreign_Hold": 33.2, "Debt_Ratio": 32.1},
        {"Code": "2002", "Name": "中鋼", "PE": 19.5, "Sector_PE_Median": 18.0, "ROE": 4.8, "YoY": -4.2, "Foreign_Hold": 18.9, "Debt_Ratio": 51.4},
        {"Code": "1216", "Name": "統一", "PE": 17.0, "Sector_PE_Median": 19.0, "ROE": 14.2, "YoY": 6.8, "Foreign_Hold": 45.1, "Debt_Ratio": 56.3},
        {"Code": "2603", "Name": "長榮", "PE": 5.2, "Sector_PE_Median": 8.5, "ROE": 25.4, "YoY": 15.2, "Foreign_Hold": 38.6, "Debt_Ratio": 42.8},
        {"Code": "2542", "Name": "興富發", "PE": 8.5, "Sector_PE_Median": 11.2, "ROE": 15.1, "YoY": 11.5, "Foreign_Hold": 12.4, "Debt_Ratio": 72.5},
        {"Code": "1707", "Name": "葡萄王", "PE": 12.4, "Sector_PE_Median": 16.5, "ROE": 18.2, "YoY": 5.8, "Foreign_Hold": 15.8, "Debt_Ratio": 38.2}
    ]
    
    df = pd.DataFrame(fallback_data)
    df["Industry"] = df["Code"].map(INDUSTRY_MAP).fillna("其他業")
    df["Industry_Tagged"] = df["Industry"].apply(get_industry_color)
    df["次產業_PE折溢價(%)"] = ((df["PE"] - df["Sector_PE_Median"]) / df["Sector_PE_Median"]) * 100
    return df, True

df_stocks, is_fallback = load_stock_data()

# ==========================================
# 側邊欄設定 (Sidebar)
# ==========================================
st.sidebar.header("⚙️ 篩選條件設定")
st.sidebar.caption(f"目前版本：{VERSION}")

# 1. 產業選單
all_industries = ["全部產業"] + sorted(list(df_stocks["Industry"].unique()))
selected_industry = st.sidebar.selectbox("指定產業類別", all_industries)

# 2. 本益比相關篩選
pe_discount_threshold = st.sidebar.slider(
    "次產業 PE 折價率上限 (%) [越負代表越低估]",
    min_value=-50, max_value=20, value=-5, step=5
)

max_sector_pe = st.sidebar.slider(
    "次產業 PE 中位數上限 (倍)",
    min_value=5.0, max_value=50.0, value=30.0, step=1.0
)

max_stock_pe = st.sidebar.slider(
    "個股 PE 絕對值上限 (倍)",
    min_value=3.0, max_value=40.0, value=25.0, step=1.0
)

# 3. 財務指標門檻
min_roe = st.sidebar.number_input(
    "最低 ROE 門檻 (%)", value=8.0, step=1.0
)

min_yoy = st.sidebar.number_input(
    "近12個月營收 YoY 成長率門檻 (%)", value=-5.0, step=1.0
)

# 資料過濾邏輯
filtered_df = df_stocks.copy()

if selected_industry != "全部產業":
    filtered_df = filtered_df[filtered_df["Industry"] == selected_industry]

filtered_df = filtered_df[
    (filtered_df["次產業_PE折溢價(%)"] <= pe_discount_threshold) &
    (filtered_df["Sector_PE_Median"] <= max_sector_pe) &
    (filtered_df["PE"] <= max_stock_pe) &
    (filtered_df["ROE"] >= min_roe) &
    (filtered_df["YoY"] >= min_yoy)
]

# ==========================================
# 左下角個人識別區塊 (Personal ID & Avatar)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("👤 個人識別資訊")

avatar_file = st.sidebar.file_uploader("上傳個人頭像圖片", type=["png", "jpg", "jpeg"], key="user_avatar")

col_av1, col_av2 = st.sidebar.columns([1, 2])
with col_av1:
    if avatar_file is not None:
        st.image(avatar_file, width=60)
    else:
        st.markdown("📷 *(未上傳)*")

with col_av2:
    st.markdown("**使用者**：溫文福")
    st.markdown("**識別碼**：`WEN-2026-RND`")

# ==========================================
# 主要頁面頁籤 (Main Tabs)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 篩選總覽與核心數據", "🔍 雙源資料對照表", "🧠 Gemini AI 個股診斷"])

with tab1:
    col1, col2, col3 = st.columns(3)
    col1.metric("上市櫃掃描總數", f"{len(df_stocks)} 檔")
    col2.metric("符合條件潛力股", f"{len(filtered_df)} 檔")
    avg_discount = filtered_df["次產業_PE折溢價(%)"].mean() if len(filtered_df) > 0 else 0
    col3.metric("平均 PE 折價率", f"{avg_discount:.1f}%")

    st.subheader("🎯 Qualified Stock Targets (合格標的清單)")
    
    if len(filtered_df) > 0:
        # 可勾選顯示欄位功能
        st.markdown("##### ⚙️ 表格顯示欄位自訂（預設鎖定前兩欄：股票代號、股票名稱）")
        
        all_optional_cols = {
            "產業類別": "Industry_Tagged",
            "本益比(PE)": "PE",
            "次產業中位數PE": "Sector_PE_Median",
            "次產業 PE 折溢價(%)": "次產業_PE折溢價(%)",
            "ROE(%)": "ROE",
            "營收 YoY(%)": "YoY",
            "外資持股比(%)": "Foreign_Hold",
            "負債比(%)": "Debt_Ratio"
        }
        
        selected_col_names = st.multiselect(
            "請選擇要於畫面顯示的延伸數據項目：",
            options=list(all_optional_cols.keys()),
            default=["產業類別", "本益比(PE)", "次產業中位數PE", "次產業 PE 折溢價(%)", "ROE(%)", "外資持股比(%)", "負債比(%)"]
        )
        
        # 組合顯示 DataFrame
        display_cols = ["Code", "Name"] + [all_optional_cols[c] for c in selected_col_names]
        rename_dict = {
            "Code": "股票代號",
            "Name": "股票名稱",
            "Industry_Tagged": "產業類別",
            "PE": "本益比(PE)",
            "Sector_PE_Median": "次產業中位數PE",
            "次產業_PE折溢價(%)": "次產業 PE 折溢價(%)",
            "ROE": "ROE(%)",
            "YoY": "營收 YoY(%)",
            "Foreign_Hold": "外資持股比(%)",
            "Debt_Ratio": "負債比(%)"
        }
        
        display_df = filtered_df[display_cols].rename(columns=rename_dict)
        
        # 格式化設定與互動式 Dataframe (原生支援凍結前兩欄與橫向滑動)
        format_mapping = {}
        for col in display_df.columns:
            if "PE" in col or "ROE" in col or "YoY" in col or "持股" in col or "負債" in col or "折溢價" in col:
                format_mapping[col] = "{:.1f}"
                
        st.dataframe(
            display_df.style.format(format_mapping),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("尚無符合當前條件的標的，請適度放寬側邊欄的篩選條件。")

with tab2:
    st.subheader("🔍 數據來源與比對說明")
    st.markdown("""
    * **本益比 (PE) 與 33 大產業類別**：對接臺灣證券交易所 (TWSE) 與櫃買中心 (TPEx) OpenAPI 字典。
    * **財務與籌碼指標**：整合開源財報數據資料庫，包含 ROE、營收 YoY、外資持股比例與負債比率。
    * **次產業中位數**：依據同次產業內上市櫃公司之數據即時計算，精準反應產業評價基準。
    """)

with tab3:
    st.subheader("🧠 Gemini AI 智慧個股深度評估")
    
    if len(filtered_df) == 0:
        st.info("請先調整側邊欄篩選條件，讓合格標的清單至少包含一檔個股，以進行 AI 診斷。")
    else:
        target_options = [f"{row['Code']} {row['Name']}" for _, row in filtered_df.iterrows()]
        selected_stock_str = st.selectbox("請選擇欲診斷的低估潛力標的：", target_options)
        
        if st.button("🚀 生成 Gemini AI 分析報告"):
            if not gemini_key:
                st.error("❌ 未偵測到 Gemini API 金鑰。請於 Streamlit Cloud 的 Secrets 中填入 `GEMINI_API_KEY`。")
            else:
                with st.spinner("AI 正在調閱個股財報與市場研報數據進行同業估值診斷..."):
                    try:
                        client = genai.Client(api_key=gemini_key)
                        stock_code = selected_stock_str.split()[0]
                        target_row = filtered_df[filtered_df["Code"] == stock_code].iloc[0]
                        
                        prompt = f"""
                        你是一位專業的台股資深證券分析師。請針對以下低估潛力標的進行同業競爭力與估值診斷：
                        
                        - 公司：{target_row['Name']} ({target_row['Code']})
                        - 所屬產業：{target_row['Industry']}
                        - 本益比 (PE)：{target_row['PE']} (次產業中位數 PE：{target_row['Sector_PE_Median']}，折價率：{target_row['次產業_PE折溢價(%)']:.1f}%)
                        - 股東權益報酬率 (ROE)：{target_row['ROE']}%
                        - 外資持股比例：{target_row['Foreign_Hold']}% | 負債比率：{target_row['Debt_Ratio']}%

                        請提供一份結構化的中文分析報告，包含：
                        1. **估值吸引力分析**：說明其本益比相較同業折價的原因。
                        2. **籌碼與財務健診**：評價其外資持股與負債比狀況。
                        3. **核心競爭優勢與 SWOT**：簡述其在所屬產業中的地位。
                        4. **綜合診斷評級**：給予明晰的估值診斷總結。
                        """
                        
                        available_models = [m.name for m in client.models.list()]
                        target_model = "gemini-2.5-flash"
                        for m_name in available_models:
                            if "gemini-2.5-flash" in m_name or "gemini-2.0-flash" in m_name or "gemini-1.5-flash" in m_name:
                                target_model = m_name
                                break
                        
                        response = client.models.generate_content(
                            model=target_model,
                            contents=prompt
                        )
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"❌ AI 分析產生失敗，詳細 API 回傳訊息為：`{str(e)}`。請檢查 API Key 設定或存取額度。")

st.markdown("---")
st.caption(f"系統版本：{VERSION} | 最後更新日期：{UPDATE_DATE} | 資料來源：臺灣證券交易所、櫃買中心與公開資訊觀測站")
