# Trading_Model_1st_Generation
5 conditions need to be satisfied.
 - Non-high-frequency (holding period above second-level)
 - Small spread (below institutional profit threshold)
 - Markets with less institutional attention (emerging markets, niche ETFs)
 - Transaction costs covered by the spread
 - Python-executable (no millisecond-level speed required)

## 專案架構

這是一個個人量化交易系統，包含以下八個模組：

- **data**：負責下載、清理、儲存歷史與即時價格資料。
- **strategy**：存放各個獨立交易策略，每個策略產生買賣訊號。
- **backtest**：用歷史資料驗證策略，計算 Sharpe Ratio、最大回撤等績效指標。
- **risk**：控制倉位大小、設定停損、控制最大總曝險。
- **execution**：將訊號送到 IBKR 實際下單。
- **monitor**：即時追蹤持倉、P&L、策略是否失效。
- **portfolio**：管理多個同時運行策略之間的資金分配，根據績效與風險決定每個策略的資金比例。
- **feedback**：監控 monitor 模組偵測到的策略失效並觸發重新校正，將回測後分析結果反饋至策略與風險模組，使系統持續自我改進。

每個模組的詳細說明請參考各自資料夾內的 README.md。

## Files Dependency
data/loader.py  
    ↓  
strategy/cointegration.py  →  半衰期、CADF 檢定  
    ↓  
strategy/hedge_ratio.py    →  動態 hedge ratio、spread  
    ↓
strategy/signals.py        →  Z-score、進出場信號
    ↓
backtest/engine.py         →  每日損益、累積報酬
    ↓
backtest/metrics.py        →  Sharpe、APR、最大回撤
    ↓
risk/kelly.py              →  單策略 Kelly 槓桿
portfolio/allocator.py     →  多策略 Kelly 資本配置
    ↓
monitor/account.py         →  IBKR 持倉與帳戶淨值
monitor/tracker.py         →  即時 P&L、Z-score 警示、log
    ↓
execution/order.py         →  送出兩條腿訂單、取消訂單
    ↓
feedback/evaluator.py      →  P&L 比較、共整合重新檢定、週報告
