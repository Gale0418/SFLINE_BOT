# Mission Brief

- Project: 永恆北極星——LINE 天文與科幻物理問答機器人
- Cycle: 正式交付收尾：評審複核、評估契約、報告簡報與發布版本對齊
- Source of truth: tasks.md
- Last organized: 2026-10-02
- Source fingerprint: 6606de5daa1b5a14a69da6a1917bffb856660622ba17f350948418b5a480b487

## 2026-10-02

- Timestamp: 2026-10-02T10:03:36+08:00
  - Change: LB-007 將本機與 NAS 的 `.env` 設為 `OPENAI_MODEL=gpt-6-luna`、`AI_PROVIDER=openai`，以既有映像重新建立 `eternal-polaris-bot`。
  - Reason: 使用者明確要求切換 GPT-6 Luna 並重啟 NAS Docker 機器人；容器 restart 不會重新載入 env_file，故使用 Compose force-recreate。
  - Impact: NAS 真實模型探針、healthy、內外 `/health` 與 `/ready` 通過；映像 SHA、資料卷及 ngrok 容器 ID 保留。NAS 環境設定備份權限 600；未修改原始碼、重建 image 或重跑歷史評估。詳見 ST-024。此條原誤置於 9 月區段，本次移入正確日期，內容保留。

- Date: 2026-10-02
  - Change: 依 ST-001～ST-024 的具體驗證與 Luna 唯讀交叉核對，LB-001～LB-004 由 Review 結案；LB-E1 經 Review 後結案，LB-E4 依既有可靠性審查結案，LB-E2 改為 Review。更新專案階段、剩餘工作與收尾摘要。
  - Reason: 使用者指出 Mission Center 落後；早期 Review 未收斂，摘要仍描述 M1／待遷移金鑰。Rust sync 更新 progress/focus 後，status 仍回 stale 且 brief/working-set 保持舊內容；以 canonical files 重新產生衍生摘要，保留 tasks.md 的唯一狀態來源。
  - Impact: Task 完成數 6/7（約 86%），不是整份專題完成率。評審複核、正式交付 SHA／CI 對齊、六題評估契約與報告簡報／15 分鐘演練仍未完成；GPT-6 Luna 尚未重跑手機 E2E 或 30 題評估。本次只對帳文件，未改機器人或重跑應用測試。

## 2026-10-02 現況

目前 10 個 Task 中 8 個 Done（80%）；LB-008、LB-009、LB-010 均由 In Progress 轉為 Review，尚未結案。LB-E5 六題舊 out-of-scope label 已修正；仍待正式評審及 GPT-6 Luna 新版 30 題線上評估，不能以 Google 31B 歷史結果代替。

候選驗收已確認 131 個 runtime 檔與 44 項鎖定依賴逐項 parity，並通過 6 項 NAS POSIX 檢查。21ec0b9 候選的 25 組混合本地與真實 GPT-6 Luna 問答通過；另 6 種語法以拒絕模型 fallback 的 stub 驗證，不呼叫 API。後續只改 dispatcher／requeue／tests／MissionCenter，Git diff 證實 answer source、data、config、assets 內容相同，不宣稱對最新 SHA 重跑過 25 組含 API 問答。最新 source SHA 為 `a3078f1cf7139b1a0b01d6c9359af468ae5f3e4d`；完整 pytest 1259 passed、10 skipped、1 warning，branch coverage 83.23%，pip check／compileall／離線評估通過。

CodeRabbit 六輪分別涵蓋 137／103／103／116／112／113 檔，6 項有效問題已修正，1 項表格空行 finding 以反證結案。三領域 Luna 多輪審查與獨立唯讀仲裁確認的問題均已處置；目前沒有已知未處置 P0／P1 或已確認的低級問題，但不代表未來不會發現 bug，也不代表 strict plugin completion passport 已通過。

main 尚未 push，GitHub CI 狀態未知；正式 NAS 部署結果待 root 回報，不能先宣稱切換完成。GPT-6 Luna 手機 E2E、完整 30 題線上評估、正式成果報告／簡報及 15 分鐘演練尚未完成；它們不列入本輪 deliverables。完整 canonical 狀態以 tasks.md 為準。

- 2026-10-02 正式發布檢查點：a3078f1 新映像已部署，1259 tests／83.23% coverage及NAS健康、131檔／44依賴、private0700／DB0600通過；ngrok原ID保留。LB-009／LB-010由Review結案，LB-008待main推送與精確SHA CI對帳；Task 8/10 Done（80%）。詳見ST-028。
