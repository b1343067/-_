import streamlit as st
import pandas as pd

# --- 常數設定 ---
SHOPEE_FEE = 0.12  # 蝦皮手續費 12%
PACKAGING = 10     # 包材費 10 元

# --- 頁面設定 ---
st.set_page_config(page_title="拾序｜營運與利潤儀表板", page_icon="📦", layout="wide")
st.title("拾序")

# --- 初始化 Session State ---
# 確保每次重整網頁時，數據不會跑掉，且預載你目前的 7 樣商品
if 'df' not in st.session_state:
    initial_data = {
        "品名款式": ["簡約桌面理線盒", "無痕浴室防水掛袋", "床頭掛燈（無時鐘）", "床頭掛燈（有時鐘）", "質感洞洞板收納盒", "床邊收納掛袋（低配）", "床邊收納掛袋（高配）"],
        "總庫存": [5, 5, 3, 3, 5, 4, 4],
        "進貨成本": [43, 47, 58, 58, 86, 102, 102],
        "早鳥價": [69, 75, 99, 129, 159, 135, 219],
        "原價": [99, 119, 149, 179, 229, 179, 279],
        "賣出早鳥": [0, 0, 0, 0, 0, 0, 0],
        "賣出原價": [0, 0, 0, 0, 0, 0, 0]
    }
    st.session_state.df = pd.DataFrame(initial_data)

# --- 核心數據計算 ---
df = st.session_state.df.copy()

# 1. 計算剩餘庫存
df['剩餘庫存'] = df['總庫存'] - df['賣出早鳥'] - df['賣出原價']

# 2. 計算總營業額 (早鳥營收 + 原價營收)
df['總營業額'] = (df['賣出早鳥'] * df['早鳥價']) + (df['賣出原價'] * df['原價'])

# 3. 計算實賺淨利 
# 公式 = 營業額 - (營業額 * 12% 手續費) - (總賣出件數 * 成本) - (總賣出件數 * 10元包材)
total_sold_per_item = df['賣出早鳥'] + df['賣出原價']
shopee_cut = df['總營業額'] * SHOPEE_FEE
df['實賺淨利'] = df['總營業額'] - shopee_cut - (total_sold_per_item * df['進貨成本']) - (total_sold_per_item * PACKAGING)
df['實賺淨利'] = df['實賺淨利'].round().astype(int) # 四捨五入取整數

# --- 頂部儀表板 (Metrics) ---
st.markdown("### 📊 總體營運狀況")
col1, col2, col3 = st.columns(3)
col1.metric(" 總賣出件數", f"{int(total_sold_per_item.sum())} 件")
col2.metric(" 累積營業額", f"$ {int(df['總營業額'].sum()):,}")
col3.metric(" 實賺", f"$ {int(df['實賺淨利'].sum()):,}")

st.divider()

# --- 互動式資料表 (Data Editor) ---
st.markdown("### 庫存與銷售紀錄")
st.caption("提示：請直接在下表的 **「賣出早鳥」** 與 **「賣出原價」** 欄位點擊兩下修改數字，系統會自動重算利潤。")

# 設定欄位顯示格式與鎖定狀態 (只允許編輯銷售數量)
edited_df = st.data_editor(
    df,
    column_config={
        "品名款式": st.column_config.TextColumn("品名款式", disabled=True),
        "總庫存": st.column_config.NumberColumn("總庫存", disabled=True),
        "進貨成本": st.column_config.NumberColumn("成本 ($)", disabled=True),
        "早鳥價": st.column_config.NumberColumn("早鳥價 ($)", disabled=True),
        "原價": st.column_config.NumberColumn("原價 ($)", disabled=True),
        "賣出早鳥": st.column_config.NumberColumn("賣出早鳥", min_value=0, step=1, help="請填寫早鳥方案賣出數量"),
        "賣出原價": st.column_config.NumberColumn("賣出原價", min_value=0, step=1, help="請填寫原價方案賣出數量"),
        "剩餘庫存": st.column_config.NumberColumn("剩餘庫存", disabled=True),
        "總營業額": st.column_config.NumberColumn("總營業額 ($)", disabled=True),
        "實賺淨利": st.column_config.NumberColumn("實賺淨利 ($)", disabled=True),
    },
    hide_index=True,
    use_container_width=True
)

# 當使用者在表格上修改數字後，更新回 Session State，讓網頁刷新時維持最新數據
if not edited_df.equals(df):
    st.session_state.df['賣出早鳥'] = edited_df['賣出早鳥']
    st.session_state.df['賣出原價'] = edited_df['賣出原價']
    st.rerun()

st.divider()

# --- 新增商品區塊 ---
st.markdown("### ➕ 新增商品至資料庫")
with st.form("add_product_form", clear_on_submit=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    new_name = c1.text_input("品名款式", placeholder="例如：桌上收納盒")
    new_stock = c2.number_input("總庫存", min_value=1, step=1)
    new_cost = c3.number_input("進貨成本 ($)", min_value=0, step=1)
    new_eb = c4.number_input("早鳥價 ($)", min_value=0, step=1)
    new_org = c5.number_input("原價 ($)", min_value=0, step=1)
    
    submitted = st.form_submit_button("新增商品", type="primary")
    
    if submitted:
        if new_name.strip() == "":
            st.warning("⚠️ 請輸入商品名稱！")
        else:
            new_row = pd.DataFrame({
                "品名款式": [new_name],
                "總庫存": [new_stock],
                "進貨成本": [new_cost],
                "早鳥價": [new_eb],
                "原價": [new_org],
                "賣出早鳥": [0],
                "賣出原價": [0]
            })
            # 將新商品加入 Session State
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            st.success(f"✅ 已成功新增：{new_name}！")
            st.rerun()
