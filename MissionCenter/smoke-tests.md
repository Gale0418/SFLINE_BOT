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

## ST-009｜Google key 本機 LINE 服務煙霧測試

- What was tested: 使用 `D:\MyGame\OWO.TXT` 第 4 行的 Google key 啟動本機 LINE webhook，並實際呼叫 Google Gemini 回答。
- How it was tested: 以程序限定環境變數設定 `AI_PROVIDER=google`、`GEMINI_MODEL=gemma-4-31b-it` 與模型逾時；未修改 `.env` 或輸出金鑰值。執行 `/health`、無簽章 `/callback`，以及一題模型煙霧測試。
- Expected result: 設定載入成功；`/health` 回 HTTP 200；無簽章 webhook 回 HTTP 400；Google 回傳可通過本機 JSON／知識卡驗證。
- Observed result: `provider=google`、模型回答 `label=out_of_scope` 且通過驗證；`/health` 回 `status=ok`、`quiz_questions=96`；無簽章 `/callback` 回 400；服務持續監聽 `127.0.0.1:5000`。
- Result: Pass
- Date: 2026-09-05
- Linked task ID: LB-004, LB-005
- Run type: live integration

## ST-010｜LINE Webhook 開關與通道驗收

- What was tested: 永恆北極星頻道、ngrok、LINE 官方 Webhook 測試及 Use webhook 開關。
- How it was tested: 本機 `/health`；LINE bot info、設定／測試 Webhook API；Chrome 後台啟用 Use webhook 後以 GET endpoint 複核。
- Expected result: health 正常、官方 test success=true、active=true。
- Observed result: health=ok，quiz_questions=96；頻道名稱符合；更新200、測試200且success=true。原 active=false，開啟後 API 確認 active=true。
- Result: Pass（通道層）；手機真實收發仍待確認，不等同完整 E2E。
- Date: 2026-09-08
- Linked task ID: LB-005
- Run type: live integration

## ST-011｜Google 30 題生成評估

- How it was tested: 程序設定 AI_PROVIDER=google、MODEL_TIMEOUT_SECONDS=5，執行 `python -m eternal_polaris.evaluation --online --output results/google-evaluation-20260908.json`。
- Expected result: 30 題均產生可驗證回答，輸出有效指標。
- Observed result: invalid，30 題錯誤（26 HTTPStatusError、4 ReadTimeout）。最小 generateContent 請求另回 HTTP500 INTERNAL；模型清單 HTTP200 且包含 gemma-4-31b-it。
- Result: Fail。零值分類指標是失敗占位結果，不得拿來當模型準確率。既有 2026-09-05 單題成功不能替代本次失敗。
- Date: 2026-09-08
- Linked task ID: LB-004, LB-E5
- Run type: live integration

## ST-012｜離線回歸與可重複啟動

- How it was tested: `python -m pytest`；PowerShell Parser 語法檢查；啟動腳本缺少來源、行號超界失敗檢查；以假值替代 Get-Content 驗證單行與空白行前置邏輯；git diff --check。
- Expected result: 測試通過，key 不輸出不寫入 .env，無效參數安全拒絕。
- Observed result: 79 passed in 1.37s；語法、參數檢查、單行與空白行檢查通過；diff check 通過。新啟動腳本尚未用來替換運行中程序。`黑洞照片是真的嗎？` 本地匹配 ov001、observed_verified。
- Result: Pass
- Date: 2026-09-08
- Linked task ID: LB-001, LB-002, LB-003, LB-E4
- Run type: automated + local smoke

## ST-013｜150 題發布契約與報告一致性

- What was tested: 150 題／18 主題／50 張卡工作樹、26B Demo 預設、Release certification、完整自動測試與離線評估。
- How it was tested: `pip check`、`compileall`、126 項 pytest 與 branch coverage、離線 evaluator、`git diff --check`；另從 workflow 擷取原始 certification Python，在本機以忽略且未追蹤的 `.env` 條件分開驗證。
- Expected result: 新資料契約與發布檢查一致；原始 96 題、20 題科學史及 34 題趣味科普均被辨識；測試與 coverage gate 通過。
- Observed result: 126 passed，branch coverage 79.16%；Release certification 輸出 questions=150、topics=18；`.env` 為 ignored 且未追蹤；`pip check`、compile、離線評估與 diff check exit 0。未呼叫真實模型 API，手機 E2E 與有效 30 題線上評估仍待完成。
- Result: Pass（本機發布契約）；GitHub 同 SHA CI 與手機證據仍是交付 blocker。
- Date: 2026-09-13
- Linked task ID: LB-001, LB-E3, LB-E6
- Run type: automated + local certification

## ST-014｜1236 卡／300 題封版與 CodeRabbit 修正驗證

- What was tested: 1236 張知識卡、300 題／24 主題、NAS Compose 路徑與映像健康檢查、線上評估人工分數邊界、最新 v9 簡報驗證器，以及兩輪 CodeRabbit finding 的最小修正。
- How it was tested: `pip check`、`compileall`、`pytest --cov=eternal_polaris --cov-branch`；從 release workflow 擷取 certification Python 執行，另檢查 `.env` ignored 且未追蹤；執行 `node scripts/verify_project_presentation.mjs` 與 `git diff --check`。
- Expected result: 程式、資料契約、部署與報告數量一致；預填人工分數不會進入新生成回答；PPT v9 可匯入並驗證 11 頁；無 diff 格式錯誤。
- Observed result: 1155 passed，branch coverage 81.99%；Release certification 輸出 questions=300、topics=24；PPT 驗證輸出 slides=11、totalSpeechCharacters=6926；比鄰星換算 6620.4 年；`.env` ignored=true、tracked=false；diff check exit 0。
- Result: Pass（本機發布契約與外部審查修正）；同一 SHA 的 GitHub CI、手機實機 E2E 與有效 30 題線上模型評估仍須分開取得證據。
- Date: 2026-09-19
- Linked task ID: LB-001, LB-003, LB-E3, LB-E5, LB-E6
- Run type: automated + local certification + external review

## ST-015｜1234 卡策展收斂與 PPT v11 驗證

- What was tested: 移除兩張偏一般政治制度卡片後的 1234 張知識卡契約、300 題／24 主題、PPT v11、逐頁演講稿、淺藍色機器人對話規則與 NAS 架構節點。
- How it was tested: `pip check`、`compileall`、`pytest --cov=eternal_polaris --cov-branch`、簡報 finalizer、Artifact Tool 重新匯入與全頁縮圖檢查；另執行 `git diff --check`。
- Expected result: `sw483`／`sw485` 不再載入；1234 卡與健康檢查契約一致；PPT v11 可匯入 11 頁，原生圖表、字型與版面驗證通過；架構圖明列 Synology NAS／Docker；講稿不混淆程式測試、學習成效與模型效能。
- Observed result: 1153 passed，branch coverage 81.99%；PPT v11 finalizer finding 0、slides=11、totalSpeechCharacters=7370，原生長條圖位於 P6；視覺檢查確認 P5 有 NAS／Docker 節點，P8 守門人對話為淺藍色、使用者訊息為淡綠色。
- Result: Pass（本機資料契約與簡報驗證）；手機實機 E2E 與有效 30 題線上模型評估仍需分開取得證據。
- Date: 2026-09-19
- Linked task ID: LB-001, LB-003, LB-E3, LB-E6
- Run type: automated + presentation validation

## ST-016｜可靠性、資安與效能對抗審查封箱

- What was tested: LINE webhook 持久化收件匣、事件去重與隔離重送、回覆邊界、模型用量保險絲、PII 遮罩、導引學習保留策略、檢索上限、NAS 映像鎖定、健康檢查及操作復原流程。
- How it was tested: 兩輪三席獨立盲審加證據仲裁；CodeRabbit 針對基準差異審查；完整 pytest 與 branch coverage；Ruff、Bandit、鎖定依賴 pip-audit、git diff check。
- Expected result: 無未處置 P0/P1；所有可重現發現完成修復或留下可驗證的處置理由；不把本機測試冒充手機、外部模型或 NAS 實機證據。
- Observed result: 1176 tests passed，82.91% branch coverage；Ruff、Bandit、鎖定正式依賴弱點稽核與 diff check 通過。安全的回覆前 SQLite 失敗可重試；不確定的 LINE 回覆結果不重送；中斷事件可由操作者明確承擔重複回覆風險後單次重排。最終未處置 P0=0、P1=0。
- Result: Pass（本機發布與對抗審查）。手機實機 E2E、有效 30 題線上模型評估、NAS 真機部署與外部監控仍需獨立驗收。
- Date: 2026-09-20
- Linked task ID: LB-003, LB-005, LB-E3, LB-E4, LB-E5, LB-006
- Run type: automated + adversarial review + external code review
