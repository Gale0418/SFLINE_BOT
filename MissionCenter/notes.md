# Notes

## Research log

| Pre-search idea | Source | Adopted insight | License status |
| --- | --- | --- | --- |
| 使用 Responses API 結構化輸出 | OpenAI 官方 API 文件 | 使用 `text.format` JSON Schema、`store=false` 與 `output_text` | 文件引用 |
| 使用低成本模型 | OpenAI GPT-5.6 Luna 模型文件 | 預設 `gpt-5.6-luna` 並使用 `reasoning.effort=none`，保留環境變數覆寫 | 文件引用 |
| LINE 簽章驗證 | LINE Developers 文件 | 在 JSON 解析前以原始 request body 驗證 | 文件引用 |

## Open questions

- 老師尚未公告正式期限、頁數與報告時間。
- 真實來源檔目前混有未標記內容；遷移工具已安全停止。需依 README 補上四個欄位名稱後才能進行真實 LINE 驗收。

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
