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

## ST-017｜iPhone 鏡像 LINE 端到端與 Rich Menu 驗收

- What was tested: 手機 LINE 功能導覽、三輪自然聊天上下文、科學回答分類與來源、星之試煉入口／選庫／難度／作答／退出，以及 3×2 Rich Menu 實際顯示與點擊目的地。
- How it was tested: 透過 macOS iPhone 鏡像操作 LINE；中文測試訊息以剪貼簿貼入。依序送出功能導覽、三輪上台緊張／忘詞追問、「為什麼星星會閃爍，行星通常比較不會？」，再進入星海之庫見習試煉，作答 Apophis 題 C 後退出。另實際點擊「我的旅程」、「觀星入門」、「問守門人」與「功能說明」。
- Expected result: 手機可完成真實收發；聊天保留最近上下文且不冒用科學來源；科學回答顯示分類與可追溯來源；試煉可得分、進入下一題並退出；Rich Menu 無死入口且手機可讀。
- Observed result: 功能導覽正常；三輪聊天持續理解「上台忘詞」並給出救場句型；星星閃爍題顯示「已觀測／已驗證」與 NASA Science 來源；Apophis 題選 C 得分 1/1，進度 1/5 並可正常退出。Rich Menu 六個目的地皆可用，但實機字級偏小，且「問守門人」與「功能說明」都導向同一份功能導覽，屬重複入口。
- Result: Pass（功能 E2E）／UX follow-up（建議收旂為 2×2 四格：問守門人、四座寶庫、星之試煉、我的旅程）。不代表 30 題線上模型評估或 NAS 真機部署通過。
- Date: 2026-09-20
- Linked task ID: LB-005, LB-E2
- Run type: manual iPhone E2E

## ST-018｜2×2 四格 Rich Menu 發布與 NAS 同步

- What was tested: 六格 Rich Menu 收旂為四格後的圖片、點擊區、現有指令對應、LINE 官方帳號預設選單、NAS 原始碼同步與對外健康端點。
- How it was tested: 重新生成 2500×843 PNG；執行 Rich Menu 專屬 pytest 與完整 pytest；透過 LINE Messaging API 驗證預設 `richMenuId`、四個區域與訊息文字，並下載遠端圖片比對 SHA-256；將選單原始碼、產圖腳本與 PNG 同步至 `/volume1/docker/eternal-polaris/app`，後比對雜湊；呼叫固定 ngrok `/health`。
- Expected result: 選單只有「問守門人」、「四座寶庫」、「星之試煉」、「我的旅程」四格；官方預設與本機圖片完全一致；NAS Bot 仍健康；手機重載後顯示四格並可點擊。
- Observed result: PNG 92,460 bytes；Rich Menu 專屬測試 2/2 與完整 pytest exit 0；Impeccable detector 0 finding。LINE 預設 ID 為 `richmenu-e88328e4d841d1c17be0400614d79b4e`，4 個區域皆為 1250 寬，遠端與本機 PNG SHA-256 同為 `f159968e601a903abf51903406d0de31d07e3dae79d7f6f5b63e1d5cd9544e5a`。NAS 三份檔案雜湊一致，公開 `/health` 回 `status=ok`、`quiz_questions=300`。LINE iPhone 用戶端仍顯示舊六格快取，待用戶端重新取得預設選單後補做四格點擊驗收。
- Result: Pass（本機、LINE 供應者與 NAS 同步）／Pending（iPhone 快取刷新與四格點擊）。
- Date: 2026-09-20
- Linked task ID: LB-005, LB-E2
- Run type: automated + live provider + NAS sync + manual iPhone inspection

## ST-019｜科幻彩色大字 Rich Menu 與四格手機實點

- What was tested: AI 生成的 2×2 外星科幻底圖、程式疊字可讀性、手機約 16px 主標／10px 副標、黃／青／粉紫／薄荷綠四格配色、「自由提問」與「引導學習」命名、四個透明點擊區、LINE 預設選單、NAS 檔案同步與公開健康端點。
- How it was tested: 生成並視覺檢查 2500×843 PNG；執行 Rich Menu 專屬 pytest、compileall、圖片尺寸／1 MB 限制檢查；透過 LINE Messaging API 回讀預設選單與遠端圖片 SHA-256；將產圖腳本、底圖、最終 PNG 與選單定義同步至 NAS 後比對 SHA-256；呼叫固定 ngrok `/health`；以 iPhone 鏡像檢查客戶端。
- Expected result: 手機顯示鮮豔科幻四格；「自由提問」與「引導學習」清楚可見；主副標達目標尺寸；四格分別送出 `你會什麼？`、`學習`、`挑戰`、`學習進度` 並收到對應回覆；NAS Bot 維持健康。
- Observed result: 專屬測試 2/2、compileall、Impeccable type detector 與圖片限制檢查通過；最終 PNG 958,331 bytes。LINE 預設 ID 為 `richmenu-7d56cd7dbdfd50ecc3c9793e9fd4ae30`，遠端與本機 SHA-256 同為 `f6ee51dab81884b6ce3dd808b8a916c12691f50214afce7a4c0f3159ddff9f7f`，四個標籤與動作文字回讀正確。NAS 檔案雜湊一致，公開 `/health` 回 `status=ok`、`quiz_questions=300`。iPhone 完整重載後已顯示最終彩色四格；實點「自由提問」收到功能導覽、「引導學習」收到四座寶庫卡、「星之試煉」收到試煉入口、「我的旅程」收到學習地圖。
- Result: Pass（圖片、本機測試、LINE 供應者、NAS 同步與 iPhone 四格實點）。
- Date: 2026-09-20
- Linked task ID: LB-005, LB-E2
- Run type: image generation + automated + live provider + NAS sync + manual iPhone inspection

## ST-020｜OpenAI 30 題線上評估與逐題人工事實核對

- What was tested: `data/eval_questions.csv` 的 30 題自由問答分類集，以 OpenAI `gpt-5.6-luna` 真實產生回答；範圍內 24 題依指定知識卡逐題人工核對事實正確性；六題 out-of-scope 檢查拒答標籤。
- How it was tested: 先做 q001 單題探針，成功後執行 `python -m eternal_polaris.evaluation --online`；首輪保留原始結果，只重試兩個失敗記錄一次；人工逐題比較回答、expected source 與回傳 source，將結果寫入獨立 reviewed JSON／manual CSV，不修改來源題庫的空白 `manual_fact_score`。
- Expected result: 30 題皆通過結構與知識卡驗證、`run_status=valid`、`error_count=0`；範圍內題目可人工評分；out-of-scope 題預測為 `out_of_scope`。
- Observed result: 首輪 28/30 成功；q014 重試成功，q027（Python list comprehension）連續兩次 `JSONDecodeError`，最終 29/30 有效、`run_status=invalid`、`error_count=1`。在此無效邊界內，24 題範圍內回答皆完成逐題人工核對，事實分數 24/24；分類 accuracy=0.875、macro F1=0.883861、source match rate=0.916667、平均延遲 2408.93ms、p95=3313ms。六題 out-of-scope 沒有任何一題標記為 `out_of_scope`，refusal rate=0；其中 q027 為格式錯誤，其他題多標為 `uncertain` 或 `general`。原始 `data/eval_questions.csv` 仍有 30 個空白 `manual_fact_score`，避免把特定生成結果回填污染題庫。
- Result: Fail（整體 30 題報告無效；不得宣稱通過）。人工事實核對僅代表 24 題成功生成的範圍內回答，不抵銷 q027 錯誤、分類錯誤或 out-of-scope 契約失敗。
- Evidence: `results/openai-evaluation-20260920.json`（首輪）、`results/openai-evaluation-20260920-final.json`（重試）、`results/openai-evaluation-20260920-reviewed.json`（人工核對）、`results/openai-evaluation-20260920-manual.csv`（每題明細）。
- Date: 2026-09-20
- Linked task ID: LB-E5, LB-005
- Run type: live model evaluation + manual source-card review

## ST-021｜Google 31B 30 題有效評估與限流復原

- What was tested: `data/eval_questions.csv` 的 30 題自由問答分類集，以 Google `gemma-4-31b-it` 真實產生回答；24 題知識範圍內回答依指定知識卡逐題人工核對；同時驗證 Google 每分鐘 30 次限制下的節流、429 退避、逾時重試與可續跑報表。
- How it was tested: 先以 26B 單題探針確認 API 可用，但快速批次碰到獨立配額 429 後停止使用該模型；改走獨立 31B 配額，以至少 2.1 秒請求起始間隔、429 至少 60 秒退避、最多 2 次嘗試與 50–52 秒逾時執行。續跑只沿用既有成功記錄，最後重試 q010／q015；另執行受影響測試與完整 `pytest -q`，並把人工核對寫入獨立 reviewed JSON／manual CSV，不修改來源題庫。
- Expected result: 30 題皆產生可解析答案，`run_status=valid`、`error_count=0`；遇到暫時性 429、5xx、逾時或無效 JSON 可受控退避／重試，不會在一分鐘內無節制轟炸 API；可查看每題人工評分明細。
- Observed result: Google 31B 最終 30/30 有效、`error_count=0`，24 題範圍內回答人工事實核對 24/24；classification accuracy=0.875、macro F1=0.883861、source match rate=0.916667、平均延遲 35947.4ms、p95=80795.0ms。24 題首試成功、6 題第二試成功。分類差異為 q010、q013、q014 與 q025–q030；來源未命中 q010、q014。q025–q030 的六個舊期待值均為 `out_of_scope`，但現行「自由提問」指令明確允許人物、歷史、日常與一般知識，故 refusal rate=0 是評估契約漂移，未反向修改 Bot 來灌分。完整 pytest 顯示 100% 且 exit 0。
- Result: Pass（30 題執行與報表有效、人工事實核對完成、限流復原可重跑）；Follow-up（更新六題 out-of-scope 舊期待值，並持續改善三題分類與兩題來源命中）。
- Evidence: `results/google-31b-evaluation-20260920-valid.json`（有效報表；SHA-256 `7c492be9f1b0fbf0b4ea23cfd675bb9e5a4b829d3191af0c2bd192c7cbeff72a`）、`results/google-31b-evaluation-20260920-reviewed.json`（人工核對；SHA-256 `2c678c0408d86f16fc80d35afab810d57b56959bceeea6ffffa503b8c9d5ae42`）、`results/google-31b-evaluation-20260920-manual.csv`（每題明細；SHA-256 `3525efa7e5f348e2d5bef27c2763842a20e8a8a15065a27369a44f40d1c88087`）、`MissionCenter/google-31b-evaluation-20260920.md`。
- Date: 2026-09-20
- Linked task ID: LB-E5, LB-005, LB-E6
- Run type: live Google model evaluation + rate-limit recovery + manual source-card review + automated regression

## ST-022｜main 發布隱私清理與 CodeRabbit 收斂

- What was tested: GitHub `main` 發布候選內容是否移除所有受版控的新舊簡報，同時保留本機簡報；續跑評估是否綁定相同題目與知識資料；未標籤、含空格或連字號的有效付款卡號是否會遮罩。
- How it was tested: 以全套 `pytest`、Ruff、Bandit、`pip-audit`、`compileall` 與 staged diff check 驗證；另建立只含 16 個小型文字／程式檔的隔離 Git sandbox 執行 CodeRabbit 完整差異審查，修正兩項有效問題後，再對 4 個受影響檔案執行聚焦複審。
- Expected result: staged tree 不含簡報、演講稿、簡報插圖與簡報產生器；本機最終檔維持存在但被忽略；測試與靜態檢查通過；CodeRabbit 不留下未處置的有效重大問題。
- Observed result: 全套 1191 項 pytest 通過；Ruff、Bandit、`pip-audit`、`compileall` 與 diff check 通過。CodeRabbit 完整審查提出 3 項：2 項 Major 已修正，1 項 Minor 經產品行為與 iPhone 實測證據確認為刻意設計；聚焦複審為 0 項。最終 v38、報告插圖與產生器留在本機並受 `.gitignore` 保護，舊簡報與舊簡報文件已排定自目前 Git tree 移除。
- Result: Pass（本機發布候選；遠端 `main` 於推送後另行核對 commit）。
- Date: 2026-09-21
- Linked task ID: LB-E5, LB-006
- Run type: automated regression + security audit + isolated external code review + privacy release gate

## ST-023｜摘要污染修復、clean-runner CI 重現與付款卡遮罩補強

- What was tested: `project.md`／`progress.md` 專案身分是否恢復且保留現有進度；目前 `requirements-ci.lock` 與 workflow 是否可在全新 Python 3.11 環境完成 CI；未分組付款卡號遮罩與科學量測數字非回歸。
- How it was tested: 執行 Mission Center doctor、`git diff --check`；建立一次性 Python 3.11 環境並依 `requirements-ci.lock` 執行 `pip check`、`compileall`、完整 pytest branch coverage 與離線評估；另以隔離 Git fixture 對 129 個現存程式／測試／設定／文件檔執行 CodeRabbit 審查，排除密鑰、二進位、簡報、知識卡、鎖檔與產物。
- Expected result: 摘要不再退化成 Mission Center placeholder；乾淨 CI 環境可完成測試；有效未分組卡號遮罩，同時保留緊接科學單位的長整數；外部審查無未處置有效問題。
- Observed result: doctor 與 diff check 通過；完整 1193 項 pytest 通過，branch coverage 82.69%；CodeRabbit 提出 1 項 Minor，已先以失敗測試重現，再補上 Luhn 與科學單位邊界，8 個聚焦案例及完整回歸皆通過。未使用第三次審查額度追逐 clean badge。
- Result: Pass（本機 metadata、clean-runner 模擬、回歸測試與外部審查處置）；GitHub push CI 與 NAS 運行版本仍須在發布後分別核對。
- Date: 2026-09-21
- Linked task ID: LB-006
- Run type: metadata repair + clean-environment CI simulation + isolated external code review + automated regression
