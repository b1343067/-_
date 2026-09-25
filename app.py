import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- 常數設定 ---
SHOPEE_FEE = 0.12
PACKAGING = 10

st.set_page_config(page_title="拾序｜營運與利潤儀表板", page_icon="📦", layout="wide")
st.title("拾序")

# --- 建立與 Google 試算表的連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

# 讀取試算表資料 (ttl=0 確保每次重整網頁都抓取最新資料，強制清除舊記憶)
try:
    df = conn.read(worksheet="工作表1", usecols=[0, 1, 2, 3, 4, 5, 6], ttl=0)
    df = df.dropna(subset=['品名款式'])
except Exception as e:
    st.error("連線到試算表失敗，請檢查金鑰設定。")
    st.stop()

# --- 頂部儀表板的「佔位符」 ---
# 這樣設計可以讓大字報顯示在最上面，但數字是根據你下面輸入的即時更新！
metrics_container = st.container()
st.divider()

# --- 互動式資料表 ---
st.markdown("### 📝 庫存與銷售紀錄")
st.caption("💡 提示：修改數量時，上方的數字會「即時試算」。確認無誤後，請務必點擊最下方的「儲存按鈕」寫入雲端！")

edited_df = st.data_editor(
    df,
    column_config={
        "品名款式": st.column_config.TextColumn("品名款式", disabled=True),
        "總庫存": st.column_config.NumberColumn("總庫存", disabled=True),
        "進貨成本": st.column_config.NumberColumn("成本 ($)", disabled=True),
        "早鳥價": st.column_config.NumberColumn("早鳥價 ($)", disabled=True),
        "原價": st.column_config.NumberColumn("原價 ($)", disabled=True),
        "賣出早鳥": st.column_config.NumberColumn("✨ 賣出早鳥", min_value=0, step=1),
        "賣出原價": st.column_config.NumberColumn("🛒 賣出原價", min_value=0, step=1),
    },
    hide_index=True,
    use_container_width=True
)

# --- 核心數據即時計算 (直接使用你正在編輯的 edited_df) ---
edited_df['剩餘庫存'] = edited_df['總庫存'] - edited_df['賣出早鳥'] - edited_df['賣出原價']
edited_df['總營業額'] = (edited_df['賣出早鳥'] * edited_df['早鳥價']) + (edited_df['賣出原價'] * edited_df['原價'])

total_sold = edited_df['賣出早鳥'] + edited_df['賣出原價']
shopee_cut = edited_df['總營業額'] * SHOPEE_FEE
edited_df['實賺淨利'] = edited_df['總營業額'] - shopee_cut - (total_sold * edited_df['進貨成本']) - (total_sold * PACKAGING)
edited_df['實賺淨利'] = edited_df['實賺淨利'].round().astype(int)

# --- 將算好的數字填回頂部的儀表板 ---
with metrics_container:
    col1, col2, col3 = st.columns(3)
    col1.metric("賣出件數", f"{int(total_sold.sum())} 件")
    col2.metric("營業額", f"$ {int(edited_df['總營業額'].sum()):,}")
    col3.metric("淨利", f"$ {int(edited_df['實賺淨利'].sum()):,}")

# --- 手動儲存按鈕 ---
if st.button("確認無誤，儲存最新數量到雲端", type="primary", use_container_width=True):
    columns_to_save = ['品名款式', '總庫存', '進貨成本', '早鳥價', '原價', '賣出早鳥', '賣出原價']
    save_df = edited_df[columns_to_save].copy()
    
    save_df.iloc[:, 1:] = save_df.iloc[:, 1:].fillna(0).astype(int)
    
    with st.spinner('儲存至 Google 雲端中...'):
        conn.update(worksheet="工作表1", data=save_df)
        st.cache_data.clear() # 存檔後強制把系統的舊記憶刪除
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
            updated_df = pd.concat([df[['品名款式', '總庫存', '進貨成本', '早鳥價', '原價', '賣出早鳥', '賣出原價']], new_row], ignore_index=True)
            with st.spinner('寫入資料庫中...'):
                conn.update(worksheet="工作表1", data=updated_df)
                st.cache_data.clear()
            st.success("新增成功！")
            st.rerun()
