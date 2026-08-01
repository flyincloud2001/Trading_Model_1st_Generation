# fetcher.py
# 負責從 yfinance 下載歷史股價資料並儲存為 CSV
# 設計原則：介面統一，未來可替換為 IBKR 或其他資料來源

import yfinance as yf
import os
import pandas as pd
from datetime import datetime
# ============================================================
# 可調整參數區（未來新增策略時在此修改預設值）
# ============================================================
# DEFAULT_START_DATE   預設起始日期
# DEFAULT_END_DATE     預設結束日期（今天）
# DEFAULT_DATA_DIR     CSV 儲存資料夾
DEFAULT_START_DATE = '2010-01-01'
DEFAULT_END_DATE = datetime.today().strftime("%Y-%m-%d")
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "csv")

def fetch_single(symbol: str, 
                 start_date: str = DEFAULT_START_DATE, 
                 end_date: str = DEFAULT_END_DATE, 
                 data_dir: str = DEFAULT_DATA_DIR) -> pd.DataFrame:

    os.makedirs(data_dir, exist_ok=True)

    raw = yf.download(symbol, start=start_date, end=end_date, auto_adjust=True, progress=False)

    df = [['Close', '']]
    print(raw)
fetch_single("GLD")
    
# fetch_single(symbol, start_date, end_date, data_dir)
# 下載單一股票的日線 OHLCV 資料並儲存為 CSV。
#
# 參數：
#     symbol     : 股票代號，例如 "GLD" 或 "EWA"
#     start_date : 起始日期，格式 "YYYY-MM-DD"
#     end_date   : 結束日期，格式 "YYYY-MM-DD"
#     data_dir   : CSV 儲存資料夾路徑
#
# 回傳：
#     df : 包含 Open, High, Low, Close, Volume 的 DataFrame
#
# 內部步驟：
#     1. 建立 CSV 儲存資料夾（若不存在則自動建立）
#     2. 下載資料
#     3. 檢查是否成功下載
#     4. 只保留需要的欄位
#     5. 儲存為 CSV，檔名格式：GLD_2010-01-01_2024-01-01.csv


# fetch_multiple(symbols, start_date, end_date, data_dir)
# 批次下載多個股票的日線資料並各自儲存為 CSV。
#
# 參數：
#     symbols    : 股票代號清單，例如 ["GLD", "GDX", "EWA", "EWC"]
#     start_date : 起始日期
#     end_date   : 結束日期
#     data_dir   : CSV 儲存資料夾路徑
#
# 回傳：
#     data : 以股票代號為 key 的字典，每個 value 是對應的 DataFrame
#
# 內部步驟：
#     1. 對每個 symbol 呼叫 fetch_single
#     2. 若下載失敗則印出警告並跳過


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
# 測試下載配對交易常用的股票：GLD, GDX, EWA, EWC, USO, BNO
# 呼叫 fetch_multiple 執行批次下載