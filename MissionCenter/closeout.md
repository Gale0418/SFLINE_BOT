# Closeout

## Summary

2026-10-02 目前檢查點：10 個 Task 中 9 個 Done（90%）；LB-008／LB-009／LB-010 已 Done，LB-E6 為 In Progress。百分比只計算 Task，並非專題完成率。候選版 131 個 runtime 檔與 44 項鎖定依賴 parity 通過，6 項 NAS POSIX checks 通過；source `a3078f1cf7139b1a0b01d6c9359af468ae5f3e4d` 完整驗證為 1259 passed、10 skipped、1 warning、83.23% branch coverage，pip check、compileall 與離線評估通過。main 已發布，Main CI與Release certification成功，正式 NAS 新映像已部署並驗證 healthy；內外 health/ready 及媒體端點均回 200。

## Completed evidence

- 六輪 CodeRabbit 審查涵蓋 137／103／103／116／112／113 檔；6 項有效問題已修正（舊 GPT cert、遮罩截斷、模型缺欄位、per-key admission、卡片語法、人工 requeue），1 項表格空行 finding 以原始內容反證結案。
- 玩家／安全／效能三領域 Luna 多輪唯讀審查及獨立唯讀仲裁的確認問題均已修正並複核。目前沒有已知未處置 P0／P1 或已確認的低級問題；這不保證未來不會出現 bug，也不等於 strict plugin completion passport 通過。
- 候選 131 個 runtime 檔與 44 項鎖定依賴逐項 parity 通過，6 項 NAS POSIX checks 通過。21ec0b9 候選的 25 組混合本地與真實 GPT-6 Luna 問答通過；另 6 種語法以拒絕模型 fallback 的 stub 驗證，不呼叫 API。之後只修改 dispatcher／requeue／tests／MissionCenter，answer source、data、config、assets 內容 byte 相同。因此不宣稱已對最新 source SHA 重跑 25 組含 API 問答。
- 六題舊 out-of-scope label 已修正為符合「自由提問」產品契約。Google `gemma-4-31b-it` 的歷史 30/30 有效報告、24/24 人工事實核對及分類指標見 ST-021；不把它當成 GPT-6 Luna 新版成績。
- 1234 張固定笑話已定稿，卡片 facts/source/label 保留；a3078f1 完整 pytest 通過。

## Unfinished

- LB-E2／LB-005：既有手機實機證據待正式評審複核；GPT-6 Luna 手機 E2E 尚未重跑。
- LB-E5：六題 label 已修；GPT-6 Luna 新版完整 30 題線上評估尚未執行，既有評估仍待正式評審。
- LB-E6：正式報告、簡報及 15 分鐘演練尚未完成；這些排除於本輪 deliverables。
- Mission Center 插件 freshness 尚未通過；摘要依 canonical `tasks.md` 重建，不能把摘要正確等同插件 freshness 成功。

## Historical evidence

過往完整測試、coverage、手機 E2E、Google 31B 評估與 GPT-6 Luna NAS 切換的歷史結果，分別依 ST-014 至 ST-024 保留。此前「6/7（約 86%）」是較早檢查點；現行 Task 計數為 9/10（90%）。此前重新建立既有 image 的記錄也是歷史事件，不代表當時已發布新版；本輪正式發布另見 ST-028／ST-029。PPT v11 及擴充稿的歷史驗收不代表本輪正式報告／簡報交付已完成。

## Risks and interpretation

程式測試、coverage 或題庫結構驗證不代表學習成效。Google 31B 的 accuracy=0.875 只描述該份 30 題分類集；24/24 人工事實核對只涵蓋當時 24 題範圍內生成回答。不得把歷史模型分數套到 GPT-6 Luna，也不可用舊 out-of-scope label 要求 Bot 為了評分而拒答。正式部署、CI 與尚未執行的線上／手機驗收須各自保留證據。

## Smoke tests

ST-014 至 ST-024 保留各自歷史執行證據。候選 131/44 parity 與 6 項 POSIX checks 的本輪證據記錄在 `output/code-review-20261002/final-candidate-parity.ndjson` 與 `output/code-review-20261002/final-release-nas-posix.log`。a3078f1 完整驗證為 1259 passed、10 skipped、1 warning、83.23% branch coverage，pip check、compileall 與離線評估通過；正式部署結果見 ST-028。

## Retro

發布紀錄要區分候選驗收與正式切換，也要分開標示每個 SHA 上實際執行過的離線、付費 API、手機與 NAS 檢查。對話審查的 finding 應以可重現證據判定；超出已觀察範圍的結論不要寫成永久保證。任務核對後更新 canonical 狀態與摘要，但不讓衍生摘要凌駕 tasks.md。


- 2026-10-02 最終發布對帳：main `fa11654e8c52f425ce18cb74910e2d59d24c1772` 的 Main CI與Release certification成功（Linux1269 passed、83.99%coverage）；LB-008經Review結案、Task9/10 Done（90%）。code a3078f1與其後文件提交的執行內容相同，正式NAS已healthy。現行狀態以tasks.md及ST-029為準。
