<!-- Generated materialized view. Do not edit directly; rebuild from canonical MissionCenter files. -->
<!-- Deprecated compatibility view: focus.md is generated from tasks.md only and must never be edited or treated as a second lifecycle source. -->
<!-- mission-center-derived schema=1.0 fingerprint-format=sha256-v2-lf source-fingerprint=d45ed4e134c9689a9195958322e20a7e612bec7d561db08c5677a6a006e162e9 -->
# P0 Focus

- Source of truth: `tasks.md`
- Unfinished P0: 7

| ID | Title | Status | Next action | Depends on | Verification |
| --- | --- | --- | --- | --- | --- |
| LB-E1 | 安全的專案基礎與金鑰遷移 | In Progress | 建立可測試的 Python 專案與安全設定流程 | - | 設定與遷移測試通過 |
| LB-001 | 建立 Python 3.11 專案骨架 | Review | 建立套件、依賴、設定與啟動入口 | - | `py -3.11 -m pytest` 可收集測試 |
| LB-002 | 建立一次性金鑰遷移工具 | Review | 實作拒絕覆寫與不洩漏值的遷移 | LB-001 | 遷移單元測試通過 |
| LB-E2 | LINE 真實端到端流程 | In Progress | 完成 webhook 與真實 LINE 回覆 | LB-E1 | 手機 LINE 收到回覆 |
| LB-003 | 實作健康檢查與 LINE webhook | Review | 完成 `/health`、簽章驗證與事件處理 | LB-001 | Flask webhook 測試通過 |
| LB-004 | 接通 OpenAI 結構化回答 | Review | 串接 Responses API 與安全降級 | LB-003 | Mock 與選配線上煙霧測試通過 |
| LB-005 | 完成 ngrok 與手機 LINE 垂直切片 | In Progress | 手機傳送問題並保存回覆截圖 | LB-002, LB-003, LB-004 | 手機實際問答截圖 |
