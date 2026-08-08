# engine.py
# 負責執行配對交易的回測邏輯
# 根據 signals.py 生成的信號，計算每日損益與持倉
import pandas as pd



def run_backtest(series_y: pd.Series,
                 series_x: pd.Series,
                 hedge_ratio: float,
                 signals: pd.DataFrame,
                 transaction_cost: float = 0.001) -> pd.DataFrame:
    """
    根據進出場信號執行回測，計算每日損益。

    倉位邏輯：
        signal = +1 → 做多 Y，做空 hedge_ratio 單位的 X
        signal = -1 → 做空 Y，做多 hedge_ratio 單位的 X
        signal =  0 → 平倉

    交易成本邏輯：
        每次倉位改變時，對 Y 和 X 各收取單邊交易成本
        交易成本 = transaction_cost * |倉位變化| * 股價

    參數：
        series_y         : 因變數價格序列（例如 GLD 收盤價）
        series_x         : 自變數價格序列（例如 GDX 收盤價）
        hedge_ratio      : 固定 hedge ratio（純量）
        signals          : 包含 signal 欄位的 DataFrame（來自 signals.py）
        transaction_cost : 單邊交易成本比例，預設 0.001（10 bps）
                           例如 0.001 代表買入 $10,000 的 GLD 需付 $10 手續費

    回傳：
        results : 包含每日損益與累積報酬的 DataFrame
                  例如：
                              signal  daily_pnl  cumulative_return  cost
                  Date
                  2010-02-05     1.0      0.0023             0.0023  0.0010
                  2010-02-08     1.0      0.0015             0.0038  0.0000
                  2010-02-09     0.0     -0.0008             0.0030  0.0010
    """
    # 對齊所有序列的日期
    df = pd.DataFrame({'price_y': series_y,
                        'price_x': series_x,
                        'signal': signals['signal']})

    # 計算每日報酬率
    df['return_y'] = df['price_y'].pct_change()
    df['return_x'] = df['price_x'].pct_change()
    df.drop(inplace=True)

    # 計算倉位變化（用來判斷是否有交易發生）
    df['signal_prev'] = df['signal'].shift(1).fillna(0.0)
    df['position_changes'] = (df['signal'] != df['signal_prev']).astype(float)

    # 計算每日策略損益（用前一天的信號乘以今天的報酬）
    # signal = +1：做多 Y，做空 X
    # signal = -1：做空 Y，做多 X
    df['pnl_y'] = df['signal']* df['return_y']
    df['pnl_x'] = -df['signal']* hedge_ratio* df['return_x']
    df['pnl_gross'] = (df['pnl_y'] + df['pnl_x']) / 2
    
    # 計算交易成本（每次倉位改變時收取）
    df['cost'] = df['position_changes']* transaction_cost* 2

    # 每日淨損益
    df['pnl_daily'] = df['pnl_gross'] - df['cost']

    # 累積報酬
    df['pnl_cumulative'] = (1 + df['pnl_daily']).cumprod() - 1

    result = df[['signal', 'pnl_daily', 'pnl_cumulative', 'cost']]