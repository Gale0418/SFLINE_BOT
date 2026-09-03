# Smoke tests

## ST-001｜自動化測試與覆蓋率

- What was tested: 設定、知識庫、記憶、去重、LINE 簽章、Webhook、OpenAI 結構化輸出、遷移工具與評估指標。
- How it was tested: `.\.venv\Scripts\python.exe -m pytest --cov=src/eternal_polaris --cov-report=term-missing`
- Expected result: 全部測試通過，沒有外部 API 呼叫。
- Observed result: 25 passed；總覆蓋率 79%。
- Result: Pass
- Date: 2026-09-01
- Linked task ID: LB-001, LB-002, LB-003, LB-004
- Run type: automated

## ST-002｜資料集結構

- What was tested: 24 張知識卡與 30 題評估資料。
- How it was tested: `.\.venv\Scripts\python.exe -m eternal_polaris.evaluation`
- Expected result: 三類知識卡各 8 張；評估題三類各 8 題並有 6 題超出範圍；不呼叫 OpenAI。
- Observed result: 資料驗證完成，未產生虛構指標。
- Result: Pass
- Date: 2026-09-01
- Linked task ID: LB-E3, LB-E5
- Run type: automated

## ST-003｜本機健康端點

- What was tested: Waitress 啟動後的 `/health`。
- How it was tested: 使用測試環境變數啟動 `.venv` 內的 `python -m eternal_polaris`，再執行 `Invoke-RestMethod http://127.0.0.1:5000/health`。
- Expected result: HTTP 200 且只回傳 `{"status":"ok"}`。
- Observed result: `{"status":"ok"}`。
- Result: Pass
- Date: 2026-09-01
- Linked task ID: LB-001, LB-003
- Run type: manual

## ST-004｜秘密遷移 fail-closed

- What was tested: 對目前兩個來源 TXT 執行一次性遷移。
- How it was tested: 使用遷移 CLI 指定 `NGROK.txt`、`OWO.TXT` 與 `.env`。
- Expected result: 混有未標記內容時不得猜測、不得建立 `.env`、不得輸出值。
- Observed result: 以安全格式錯誤停止，`.env` 未建立，來源檔未修改。
- Result: Pass
- Date: 2026-09-01
- Linked task ID: LB-002
- Run type: manual

## ST-005｜靜態與依賴安全

- What was tested: Python 原始碼弱點模式與鎖定依賴的已知漏洞。
- How it was tested: `bandit -q -r src` 與 `python -m pip_audit -r requirements.lock`。
- Expected result: 0 個靜態安全 issue、0 個已知依賴漏洞。
- Observed result: Bandit exit 0；pip-audit 回報 `No known vulnerabilities found`。掃描曾找出 pytest 8.4.2 漏洞，升級至 9.1.1 後重跑通過。
- Result: Pass
- Date: 2026-09-01
- Linked task ID: LB-001
- Run type: automated

## ST-006｜知識卡官方來源連結

- What was tested: 24 張知識卡的 `source_url` 是否仍可取得，並人工核對搜尋結果與卡片事實是否相符。
- How it was tested: 對每個 URL 發送限時 HTTP GET，並以官方網站搜尋結果複核遭反爬阻擋的頁面。
- Expected result: 沒有 404 或失效搬遷頁；來源均為官方、原始論文或具編輯責任的參考資料。
- Observed result: 20 個 URL 回傳 200；4 個官方站回傳 403 反爬限制，但可由搜尋索引核對；0 個 404。
- Result: Pass
- Date: 2026-09-01
- Linked task ID: LB-E3
- Run type: automated + manual

## ST-007｜真實憑證與 LINE Webhook

- What was tested: OpenAI key、LINE access token、ngrok authtoken 與 LINE 官方 Webhook 測試。
- How it was tested: 只在程序記憶體內讀取候選值；OpenAI 執行唯讀模型列表、LINE 執行 bot info、ngrok 建立暫時 tunnel；完成 `.env` 後設定並測試 `/callback`。
- Expected result: 不輸出憑證值；三種認證成功；LINE bot 名稱符合「永恆北極星」；Webhook 官方測試成功。
- Observed result: 三種認證均成功；bot 名稱符合；Webhook 更新回傳 200，測試回傳 `success=true`；測試用 ngrok 程序已回收。
- Result: Pass
- Date: 2026-09-01
- Linked task ID: LB-002, LB-005
- Run type: live integration

## ST-008｜OpenAI 真實回答煙霧測試

- What was tested: Responses API 嚴格 JSON Schema 與真實回答。
- How it was tested: 先執行 30 題線上評估，再用單題重測修正後 Schema。
- Expected result: API 接受 Schema 並產生受知識卡約束的回答。
- Observed result: 首輪發現 `uniqueItems` 不受 Structured Outputs 支援，已移至程式端驗證並新增測試；修正後帳戶回傳 `insufficient_quota`，無法完成有效評估。評估器已改為遇到 API 錯誤即標記無效並非零退出。
- Result: Blocked
- Date: 2026-09-01
- Linked task ID: LB-004, LB-E5
- Run type: live integration
