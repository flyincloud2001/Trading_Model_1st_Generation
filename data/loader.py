# loader.py
# 負責從 CSV 讀取已下載的歷史股價資料
# 設計原則：其他模組（strategy、backtest 等）統一透過此檔案讀取資料

import pandas as pd
import os
from glob import glob

# CSV 預設儲存資料夾（與 fetcher.py 一致）
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(__file__), "csv")


def load_single(symbol: str,
                data_dir: str = DEFAULT_DATA_DIR) -> pd.DataFrame:
    """
    從 CSV 讀取單一股票的歷史資料。
    自動尋找該股票代號最新的 CSV 檔案。

    參數：
        symbol   : 股票代號，例如 "GLD"
        data_dir : CSV 所在資料夾

    回傳：
        df : 包含 Open, High, Low, Close, Volume 的 DataFrame
             index 為日期（datetime 格式）
             例如：
                         Open    High     Low   Close    Volume
             Date
             2010-01-04  107.35  107.49  106.55  107.16  13561200
             2010-01-05  107.16  107.69  106.75  107.45  10925200
    """
    # 尋找所有符合該股票代號的 CSV 檔案
    pattern = os.path.join(data_dir, f"{symbol}_*.csv")
    files = sorted(glob(pattern))

    if not files:
        raise FileNotFoundError(
            f"[loader] 找不到 {symbol} 的 CSV 檔案，請先執行 fetcher.py 下載資料。"
        )

    # 取最新的檔案（依檔名排序，最後一個即最新）
    filepath = files[-1]
    print(f"[loader] 讀取 {filepath}")

    # 讀取 CSV，將 Date 欄位設為 index 並轉為 datetime 格式
    df = pd.read_csv(filepath, index_col="Date", parse_dates=True)

    return df
    

def load_multiple(symbols: list,
                  data_dir: str = DEFAULT_DATA_DIR) -> dict:
    """
    批次讀取多個股票的歷史資料。

    參數：
        symbols  : 股票代號清單，例如 ["GLD", "GDX"]
        data_dir : CSV 所在資料夾

    回傳：
        data : 以股票代號為 key 的字典
               例如：
               {
                   "GLD": DataFrame(...),
                   "GDX": DataFrame(...)
               }
    """
    data = {}
    for symbol in symbols:
        try:
            df = load_single(symbol, data_dir)
            data[symbol] = df
        except FileNotFoundError as e:
            print(f"[loader] 警告：{e}，跳過 {symbol}。")
    return data


# ============================================================
# 直接執行此檔案時的測試用範例
# ============================================================
if __name__ == "__main__":
    data = load_multiple(["GLD", "GDX"])
    for symbol, df in data.items():
        print(f"\n{symbol}：")
        print(df.head())