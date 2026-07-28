# execution

將訊號送到 IBKR 實際下單。

- 接收經過 risk 模組調整後的交易訊號（含倉位大小、停損等資訊）。
- 透過 IBKR（Interactive Brokers）API 將訊號轉換為實際的下單指令。
- 處理下單後的回報，包括成交、部分成交、取消等狀態。
