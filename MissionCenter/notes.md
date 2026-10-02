# Notes

## Research log

| Pre-search idea | Source | Adopted insight | License status |
| --- | --- | --- | --- |
| 使用 Responses API 結構化輸出 | OpenAI 官方 API 文件 | 使用 `text.format` JSON Schema、`store=false` 與 `output_text` | 文件引用 |
| 使用低成本模型 | OpenAI GPT-5.6 Luna 模型文件 | 預設 `gpt-5.6-luna` 並使用 `reasoning.effort=none`，保留環境變數覆寫 | 文件引用 |
| LINE 簽章驗證 | LINE Developers 文件 | 在 JSON 解析前以原始 request body 驗證 | 文件引用 |

## Open questions

- 老師尚未公告正式期限、頁數與報告時間。
- 憑證遷移的早期阻礙已由 ST-007 解除；手機 E2E 與四格實點已有 ST-017／ST-019，NAS GPT-6 Luna 運行有 ST-024。候選 parity／POSIX 驗收已通過，但候選尚未切換；正式評審、交付與評估契約項目以 tasks.md 為準。
- 2026-10-02 既有本機 `.venv` 缺少 linebot.api／dotenv；乾淨環境歷史驗證見 ST-023，NAS 真實運行驗證見 ST-024。此本機環境維護尚未處理。

## 2026-10-02 目前狀態

- Task 共 10 項、6 項 Done（60%）；LB-008／009／010 為 Review，LB-E6 為 In Progress。這不是專題完成率；canonical 狀態以 tasks.md 為準。
- 候選 131 runtime 檔與 44 項鎖定依賴 parity、6 項 NAS POSIX checks 通過。source SHA `a3078f1cf7139b1a0b01d6c9359af468ae5f3e4d` 完整 pytest 1259 passed、10 skipped、1 warning、83.23% branch coverage；pip check、compileall、離線評估通過。main 未 push、GitHub CI 未知；正式 NAS deployment 結果待 root 回報。
- CodeRabbit 六輪涵蓋 137／103／103／116／112／113 檔，6 項有效問題已修，1 項表格空行 finding 有原文反證。玩家／安全／效能多輪 Luna 唯讀審查及獨立仲裁確認的問題均已處置；不保證未來零 bug，也不宣稱 strict plugin completion passport 通過。
- 21ec0b9 候選的 25 組混合本地與真實 GPT-6 Luna 問答通過；另 6 種語法以拒絕模型 fallback 的 stub 驗證，不呼叫 API。其後僅 dispatcher／requeue／tests／MissionCenter 有變更；answer source、data、config、assets 內容相同，因此不宣稱 a3078f1 重跑過含 API 問答。
- 六題舊 out-of-scope label 已修正；GPT-6 Luna 新版完整 30 題線上評估與手機 E2E 尚未執行。正式成果報告、簡報及 15 分鐘演練不屬本輪 deliverables。
- Mission Center 衍生摘要已依 canonical tasks.md 更新；plugin freshness 狀態仍未獲驗證，不因內容已更新而宣稱通過。

## 2026-09-01 多角度審查摘要

- 安全：限制 Webhook 64 KB、問題 1000 字；日誌只記錄錯誤型別；秘密值不插值、不輸出且不覆寫。
- 分散式可靠性：LINE reply 每次事件只嘗試一次；真正傳送失敗會解除去重，允許 LINE redelivery。
- ML／評估：矩陣外預測納入 FN；分類指標與人工事實正確率分離；輸出保留回答文字供人工評分。
- 操作：改用 Waitress；啟動腳本固定 `.venv` 並以 PATH／`NGROK_EXE` 尋找 ngrok。
- 對話語氣：保留冷靜親切的星空導覽員聲音，但避免浮誇角色扮演與把不確定性說成定論。
- GitHub 官方比對：LINE SDK v3 官方範例同樣使用原始 body、`X-Line-Signature`、`WebhookHandler/Parser` 與 `reply_message_with_http_info`；本專案額外移除官方範例會記錄 body 的做法以保護隱私。
- Chrome：本機 URL 請求有抵達服務，但擴充功能以 `ERR_BLOCKED_BY_CLIENT` 阻止頁面呈現；改以可重跑的本機 HTTP 煙霧測試作為證據。
- Antigravity：本機 session 健康，但同一冪等 request ID 兩次皆在 dispatch 前 RPC deadline exceeded，未取得可用審查內容，沒有聲稱 Gemini 已完成審查。
- CodeRabbit：工作區不是 Git repository，且既定計畫禁止擅自 `git init`，因此未執行；不得把人工審查冒稱為 CodeRabbit 結果。
- Completion Critic：未取得總額／席次／工具／時間預算，依 Mission Center 規範未派送，任務維持 Review 而非 Done。
- 知識來源：逐一稽核 24 個來源並修正網站改版造成的舊路徑；20 個回傳 200，4 個官方站因反爬回傳 403 但已由搜尋索引複核，沒有 404。
- 憑證辨識：OpenAI、LINE access token 與 ngrok 候選均經唯讀或暫時連線實測；兩串同長 Channel Secret 以檔案區塊上下文確認 Messaging API 所屬值。`.env` 已安全建立，原始 TXT 未修改。
- 真實整合：LINE Webhook 已更新至目前 ngrok `/callback`，官方測試 `success=true`。
- OpenAI 線上評估：先發現 Structured Outputs 不接受 `uniqueItems`，已改由程式端檢查並新增測試；修正後因 API 餘額為 0 而無法取得有效回答。失敗報表不得作為 0 分結果使用。
- 成本控制：可委派工作與 LINE 機器人執行模型均使用 Luna；API 端固定為 `gpt-5.6-luna`、`reasoning.effort=none`。


## 2026-10-02 卡片與發布補充

- 既有 `.venv` 未被改動；本次另建鎖定依賴的 Python 3.11 暫時環境，避免舊環境缺少 linebot.api/dotenv 影響驗證。
- CodeRabbit 六輪每輪均不超過 150 檔，覆蓋 137／103／103／116／112／113 檔；每個 fixture 總量不超過 150，排除大型 data/assets/secrets/reports。審查節流遵守每時窗最多三輪。
- 7 項 finding 判定：舊 GPT cert、遮罩截斷邊界、模型缺欄位契約、per-key admission、卡片 grammar、人工 requeue 六項有效並修正；表格空行 finding 由原內容證明為 false positive。
- 使用者追加隨機問答後，確實重現指代追問誤取弱年份卡、完整索卡題目被刪內文、GENERAL固定卡驗證與顯示缺口；均以回歸修正。Luna獨立唯讀再指出跨過未知新主題復活舊卡，改為相鄰最近主題並加測。此複核不冒稱CodeRabbit。
- 1234句固定笑話定稿，逐卡ID對齊；錯配已修，另外補強純重述句。所有卡facts/source/label保留，僅sw165新增交通與短題alias、sw169補通訊與交通界線及正確來源名。
- 兩次完整 coverage 執行在後續有效修正時停止，標示 superseded，不當作完成證據。最新 a3078f1 fresh pytest 已完成：1259 passed、10 skipped、1 warning、83.23% branch coverage；pip check、compileall、離線評估亦通過。正式 deployment 尚待 root 回報。

- GitHub參考限定官方現成專案：[LINE Python SDK Flask範例](https://github.com/line/line-bot-sdk-python/blob/master/examples/flask-echo/app_with_handler.py)、[OpenAI Python SDK](https://github.com/openai/openai-python)。對照簽章驗證、短Webhook路徑、明確timeout/retry與client資源回收；不用範例的簡化同步echo取代現有背景dispatch與持久化保護。

- 2026-10-02 正式發布檢查點：a3078f1 新映像已部署，1259 tests／83.23% coverage及NAS健康、131檔／44依賴、private0700／DB0600通過；ngrok原ID保留。LB-009／LB-010由Review結案，LB-008待main推送與精確SHA CI對帳；Task 8/10 Done（80%）。詳見ST-028。

- 2026-10-02 ST-029：main `fa11654e8c52f425ce18cb74910e2d59d24c1772` 的Main CI1269 tests／83.99%coverage與同SHA Release certification成功；LB-008／LB-E3由Review結案，Task9/10Done（90%）。其後只改結案文件與metadata，runtime仍a3078f1。
