# Snapshot

## 2026-10-02 目前檢查點

- Source of truth：tasks.md；此摘要不擁有任務生命週期。
- Task 狀態：8/10 Done（80%）；LB-008 為 Review，LB-009／LB-010 已 Done；LB-E6 為 In Progress。百分比只計算 Task，不代表專題完成度。
- 最新 source SHA：`a3078f1cf7139b1a0b01d6c9359af468ae5f3e4d`；完整 pytest 1259 passed、10 skipped、1 warning，branch coverage 83.23%；pip check、compileall、離線評估通過。
- 候選驗證：131 個 runtime 檔與 44 項鎖定依賴 parity 通過；6 項 NAS POSIX checks 通過。正式部署另有 ST-028 的運行映像與健康證據。
- 行為探測：21ec0b9 候選的 25 組混合本地與真實 GPT-6 Luna 問答通過；另 6 種語法以拒絕模型 fallback 的 stub 驗證，不呼叫 API。其後只改 dispatcher／requeue／tests／MissionCenter；answer source、data、config、assets 內容相同。未對 a3078f1 重跑含 API 問答。
- 審查：CodeRabbit 六輪涵蓋 137／103／103／116／112／113 檔；6 項有效問題已修，一項表格空行 finding 以反證結案。玩家／安全／效能三席 Luna 多輪審查及獨立唯讀仲裁的確認問題均已處理；不保證未來零 bug，也不宣稱 strict plugin completion passport 通過。
- 發布：main 尚未 push，GitHub CI 未知；正式 NAS 新映像已部署並驗證 healthy；內外 health/ready 及媒體端點均回 200。
- 尚待：正式評審、GitHub CI 發布對帳；GPT-6 Luna 手機 E2E、新版完整 30 題線上評估、正式成果報告／簡報和 15 分鐘演練。後三項排除於本輪 deliverables。

## 歷史檢查點（保留，不作目前狀態）

- 日期：2026-09-01
- 階段：M1 本機實作完成，等待真實金鑰與 LINE 驗收
- 已核准：六個 Epic、第一里程碑、技術與安全邊界
- 目前工作：LB-001、LB-002、LB-003、LB-004 均在 Review；LB-005 等待外部驗收
- 驗證：22 tests passed、79% coverage、Bandit 0 issue、pip-audit 0 vulnerability、`/health` 200
- 下一個可重開點：依 README 標記四項來源金鑰，執行遷移後進行 OpenAI 與手機 LINE 驗收

## 歷史快照說明

過往 2026-10-02 的 LB-007 GPT-6 Luna 切換及 NAS bot 容器重啟證據見 `smoke-tests.md` 的 ST-024；之後候選映像另有 runtime parity 與 POSIX 驗收。正式發布狀態以本節、tasks.md 及最新證據為準。Plugin snapshot 子命令曾不接受環境參數，故保留人工可重開摘要；不宣稱 plugin freshness 檢查通過。

- 2026-10-02 正式發布檢查點：a3078f1 新映像已部署，1259 tests／83.23% coverage及NAS健康、131檔／44依賴、private0700／DB0600通過；ngrok原ID保留。LB-009／LB-010由Review結案，LB-008待main推送與精確SHA CI對帳；Task 8/10 Done（80%）。詳見ST-028。
