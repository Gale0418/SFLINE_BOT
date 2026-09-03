# 永恆北極星｜任務樹

| ID | Title | Type | Parent | Priority | Status | Owner | Depends on | Next action | Verification | Estimate | Labels | Comments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LB-E1 | 安全的專案基礎與金鑰遷移 | Epic | - | P0 | In Progress | Codex | - | 建立可測試的 Python 專案與安全設定流程 | 設定與遷移測試通過 | L | execution | 第一里程碑 |
| LB-001 | 建立 Python 3.11 專案骨架 | Task | LB-E1 | P0 | Review | Codex | - | 建立套件、依賴、設定與啟動入口 | `py -3.11 -m pytest` 可收集測試 | M | execution | - |
| LB-002 | 建立一次性金鑰遷移工具 | Task | LB-E1 | P0 | Review | Codex | LB-001 | 實作拒絕覆寫與不洩漏值的遷移 | 遷移單元測試通過 | M | execution,verification | `.env` 已建立；原始來源檔未刪除 |
| LB-E2 | LINE 真實端到端流程 | Epic | - | P0 | In Progress | Codex | LB-E1 | 完成 webhook 與真實 LINE 回覆 | 手機 LINE 收到回覆 | L | execution | 第一里程碑 |
| LB-003 | 實作健康檢查與 LINE webhook | Task | LB-E2 | P0 | Review | Codex | LB-001 | 完成 `/health`、簽章驗證與事件處理 | Flask webhook 測試通過 | L | execution,verification | - |
| LB-004 | 接通 OpenAI 結構化回答 | Task | LB-E2 | P0 | Review | Codex | LB-003 | 串接 Responses API 與安全降級 | Mock 與選配線上煙霧測試通過 | L | execution,verification | - |
| LB-005 | 完成 ngrok 與手機 LINE 垂直切片 | Task | LB-E2 | P0 | In Progress | User | LB-002, LB-003, LB-004 | 手機傳送問題並保存回覆截圖 | 手機實際問答截圖 | M | verification | Flask/ngrok 運行中；LINE 官方 Webhook 測試成功；待 API 額度 |
| LB-E3 | 天文與科幻知識庫與回答格式 | Epic | - | P1 | Review | Codex | LB-E2 | 建立 24 張知識卡與四類輸出 | 知識卡驗證與渲染測試通過 | L | execution | 24 張卡與來源連結已驗證 |
| LB-E4 | 三輪記憶、錯誤處理與可靠性 | Epic | - | P1 | Review | Codex | LB-E3 | 完成記憶、去重、逾時與隱私日誌 | 可靠性測試通過 | L | execution,verification | 可靠性測試已通過 |
| LB-E5 | 30 題測試集與評估報表 | Epic | - | P1 | In Progress | Codex | LB-E4 | 補足 OpenAI API 額度後重跑線上評估 | 產生可重跑有效評估報表 | L | verification | 離線驗證完成；真實 API 回報 insufficient_quota |
| LB-E6 | 報告、簡報、Demo 與成果封裝 | Epic | - | P2 | Backlog | User | LB-E5 | 依實測結果完成報告素材 | 交付物清單人工驗收 | L | closeout | 正式頁數與期限待公告 |
