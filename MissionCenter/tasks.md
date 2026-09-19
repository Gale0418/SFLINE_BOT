# 永恆北極星｜任務樹

| ID | Title | Type | Parent | Priority | Status | Owner | Depends on | Next action | Verification | Estimate | Labels | Comments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LB-E1 | 安全的專案基礎與金鑰遷移 | Epic | - | P0 | In Progress | Codex | - | 建立可測試的 Python 專案與安全設定流程 | 設定與遷移測試通過 | L | execution | 第一里程碑 |
| LB-001 | 建立 Python 3.11 專案骨架 | Task | LB-E1 | P0 | Review | Codex | - | 建立套件、依賴、設定與啟動入口 | `py -3.11 -m pytest` 可收集測試 | M | execution | - |
| LB-002 | 建立一次性金鑰遷移工具 | Task | LB-E1 | P0 | Review | Codex | LB-001 | 實作拒絕覆寫與不洩漏值的遷移 | 遷移單元測試通過 | M | execution,verification | `.env` 已建立；原始來源檔未刪除 |
| LB-E2 | LINE 真實端到端流程 | Epic | - | P0 | In Progress | Codex | LB-E1 | 完成 webhook 與真實 LINE 回覆 | 手機 LINE 收到回覆 | L | execution | 第一里程碑 |
| LB-003 | 實作健康檢查與 LINE webhook | Task | LB-E2 | P0 | Review | Codex | LB-001 | 完成 `/health`、簽章驗證與事件處理 | Flask webhook 測試通過 | L | execution,verification | - |
| LB-004 | 接通 OpenAI 結構化回答 | Task | LB-E2 | P0 | Review | Codex | LB-003 | 串接 Responses API 與安全降級 | Mock 與選配線上煙霧測試通過 | L | execution,verification | - |
| LB-005 | 完成 ngrok 與手機 LINE 垂直切片 | Task | LB-E2 | P0 | In Progress | Codex | LB-002, LB-003, LB-004 | 手機驗收新版自然閒聊、三輪追問與科學回答；後續重跑正式評估 | 手機實際問答與試煉截圖，Google 路徑成功 | M | verification | 2026-09-08 改用 gemma-4-26b-a4b-it：同 KEY 真實聊天三輪及科學問題共4次成功；91項測試通過，服務重啟健康正常；新版手機驗收待確認，見 chat-verification-20260908.md |
| LB-E3 | 天文與科幻知識庫與回答格式 | Epic | - | P1 | Review | Codex | LB-E2 | 維護 1234 張知識卡與受限回答格式 | 1234 張知識卡、來源連結與渲染測試通過 | L | execution | 2026-09-19 移除兩張偏現實政治制度且低耦合的卡片；待與正式交付 SHA 對齊 |
| LB-E4 | 三輪記憶、錯誤處理與可靠性 | Epic | - | P1 | Review | Codex | LB-E3 | 完成記憶、去重、逾時與隱私日誌 | 可靠性測試通過 | L | execution,verification | 可靠性測試已通過 |
| LB-E5 | 30 題測試集與評估報表 | Epic | - | P1 | In Progress | Codex | LB-E4 | 使用 Google 路徑完成 30 題評估，保存失敗與指標 | 產生可重跑有效評估報表 | L | verification | 不再以 OpenAI 額度作為 Google 路徑的阻塞 |
| LB-E6 | 報告、簡報、Demo 與成果封裝 | Epic | - | P2 | In Progress | Codex | LB-E5, LB-005 | 依現況證據完成報告骨架、Demo 矩陣與交付封裝 | 書面與 PPT 對照配分，15 分鐘演練及人工驗收 | L | closeout | 2026-09-13 已重整報告骨架；手機 E2E、有效30題評估與正式截圖仍是 blocker |
| LB-006 | 全面品質優化與對抗審查 | Task | LB-E4 | P1 | Done | Codex | LB-E3 | 維持可靠性保護並在 NAS 上線前完成手機實機驗收 | 1176 項測試、82.91% coverage、Ruff、Bandit 與鎖定依賴稽核通過；最終無未處置 P0/P1 | L | execution,verification | 兩輪三席盲審與證據仲裁完成；CodeRabbit 六項皆修正或以程式證據駁回。Antigravity 串流中斷，未列入有效審查證據 |
