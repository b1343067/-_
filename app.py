import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 常數設定 ---
SHOPEE_FEE = 0.12
PACKAGING = 10

st.set_page_config(page_title="拾序｜營運與利潤儀表板", page_icon="📦", layout="wide")
st.title("拾序")

# --- 建立與 Google 試算表的連線 ---
# 這行會自動讀取我們等一下在後台設定的金鑰
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取試算表資料 (包含標題列與前 7 欄)
try:
    df = conn.read(worksheet="工作表1", usecols=[0, 1, 2, 3, 4, 5, 6])
    # 清理掉空白列
    df = df.dropna(subset=['品名款式'])
except Exception as e:
    st.error("連線到試算表失敗，請檢查金鑰設定。")
    st.stop()

# --- 核心數據計算 ---
# 將讀取到的資料加上計算欄位
df['剩餘庫存'] = df['總庫存'] - df['賣出早鳥'] - df['賣出原價']
df['總營業額'] = (df['賣出早鳥'] * df['早鳥價']) + (df['賣出原價'] * df['原價'])

total_sold = df['賣出早鳥'] + df['賣出原價']
shopee_cut = df['總營業額'] * SHOPEE_FEE
df['實賺淨利'] = df['總營業額'] - shopee_cut - (total_sold * df['進貨成本']) - (total_sold * PACKAGING)
df['實賺淨利'] = df['實賺淨利'].round().astype(int)

# --- 頂部儀表板 ---
col1, col2, col3 = st.columns(3)
col1.metric("賣出件數", f"{int(total_sold.sum())} 件")
col2.metric("營業額", f"$ {int(df['總營業額'].sum()):,}")
col3.metric("實賺淨利", f"$ {int(df['實賺淨利'].sum()):,}")

st.divider()

# --- 互動式資料表 ---
st.markdown("### 庫存與銷售紀錄")
st.caption("修改完「賣出早鳥」與「賣出原價」後，請點擊下方的「儲存」按鈕同步至雲端。")

edited_df = st.data_editor(
    df,
    column_config={
        "品名款式": st.column_config.TextColumn("品名款式", disabled=True),
        "總庫存": st.column_config.NumberColumn("總庫存", disabled=True),
        "進貨成本": st.column_config.NumberColumn("成本 ($)", disabled=True),
        "早鳥價": st.column_config.NumberColumn("早鳥價 ($)", disabled=True),
        "原價": st.column_config.NumberColumn("原價 ($)", disabled=True),
        "賣出早鳥": st.column_config.NumberColumn("賣出早鳥", min_value=0, step=1),
        "賣出原價": st.column_config.NumberColumn("賣出原價", min_value=0, step=1),
        "剩餘庫存": st.column_config.NumberColumn("庫存", disabled=True),
        "總營業額": st.column_config.NumberColumn("營業額 ($)", disabled=True),
        "實賺淨利": st.column_config.NumberColumn("淨利 ($)", disabled=True),
    },
    hide_index=True,
    use_container_width=True
)

# --- 手動儲存按鈕 (取代原本的自動存檔，避免 Google API 限制) ---
if st.button("確認無誤，儲存最新數量到雲端", type="primary", use_container_width=True):
    columns_to_save = ['品名款式', '總庫存', '進貨成本', '早鳥價', '原價', '賣出早鳥', '賣出原價']
    save_df = edited_df[columns_to_save].copy()
    
    # 防呆機制：確保空白欄位補 0 並轉為整數，防止 Google 試算表格式錯誤
    save_df.iloc[:, 1:] = save_df.iloc[:, 1:].fillna(0).astype(int)
    
    with st.spinner('儲存至 Google 雲端中...'):
        conn.update(worksheet="工作表1", data=save_df)
    st.success("已成功存回 Google 試算表！")
    st.rerun()

st.divider()

# --- 新增商品 ---
st.markdown("### ➕ 新增商品")
with st.form("add_product_form", clear_on_submit=True):
    c1, c2, c3, c4, c5 = st.columns(5)
    new_name = c1.text_input("品名款式")
    new_stock = c2.number_input("總庫存", min_value=1, step=1)
    new_cost = c3.number_input("進貨成本", min_value=0, step=1)
    new_eb = c4.number_input("早鳥價", min_value=0, step=1)
    new_org = c5.number_input("原價", min_value=0, step=1)
    
    if st.form_submit_button("新增", type="primary"):
        if new_name.strip() == "":
            st.warning("請輸入名稱！")
        else:
            new_row = pd.DataFrame([[new_name, new_stock, new_cost, new_eb, new_org, 0, 0]], 
                                   columns=['品名款式', '總庫存', '進貨成本', '早鳥價', '原價', '賣出早鳥', '賣出原價'])
            # 將新資料加到底部
            updated_df = pd.concat([df[['品名款式', '總庫存', '進貨成本', '早鳥價', '原價', '賣出早鳥', '賣出原價']], new_row], ignore_index=True)
            with st.spinner('寫入資料庫中...'):
                conn.update(worksheet="工作表1", data=updated_df)
            st.success("新增成功！")
            st.rerun()
