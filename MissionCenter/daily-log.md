# Daily log

## 2026-09-01

- 發布使用者核准的實作計畫並開始第一里程碑。


## 2026-09-08

- 使用者確認最高目標為通過專題考試，交付書面及 PPT，並要求先完成機器人再製作報告。已將正式配分、期限、15 分鐘、文風參考與 Gemini 建議記入 report-requirements.md；不改成只啟動服務即完成。
- Gemini 寫作討論已完成，修正其將 96 題試煉與 30 題評估混用的建議。
- 開啟 LINE Use webhook，API 確認 active=true。30 題 Google 評估全部失敗，最小生成請求500，模型列表200。79 項離線測試通過。
- Gemini 已完成 scripts/start_app.ps1 與 README 的程序限定 Google key 載入功能（request linebot-startup-20260908-01，cascade bfe6af07-ceb2-4237-a83c-80abc83b8024，已觀察完成 marker）。Codex 補修單行集合、來源必填與檔案型態驗證，已驗收前置邏輯。沒有第二個寫入者與其重疊修改。

- Last organized: 2026-09-21

- Timestamp: 2026-09-08T15:51:42+08:00
  - Change: 依使用者要求，從38卡／116題擴充到50卡／150題，加入12張趣味科普卡、34題及10個新的隨機問句。
  - Reason: 保留原進階内容，同時增加小朋友能理解的自然現象、動物冷知識與傳說查核。
  - Impact: 126項自動測試通過，來源與邊界見 `docs/fun-science.md`；不把離線通過視為手機驗收或正式模型評估完成，不變更既有任務生命週期。

## 2026-09-13

- 參考同課程報告的章節節奏，將 `docs/report-outline.md` 重整為本專案專屬的雙路徑故事、八張簡報配置、15 分鐘 Demo 與四層證據矩陣；未沿用對方技術主張或原句。
- 同步 50 張卡／150 題／18 主題至架構、題庫、Demo、交付規格與 release certification；保留原始 96 題作為版本基線。
- Google Demo 預設統一為 2026-09-08 曾成功的 `gemma-4-26b-a4b-it`；31B 保留為官方支援但非交付預設。未執行付費或真實模型呼叫。
- 本機驗證：126 tests passed、branch coverage 79.16%、發布契約 150 題／18 主題、pip check、compile、離線評估與 diff check 通過。手機 E2E、有效 30 題線上評估及同一 SHA 的 GitHub CI 尚未完成。

## 2026-09-19

- Timestamp: 2026-09-19T21:58:35+08:00
  - Change: 封裝 1236 張知識卡、300 題、100 張知識卡圖片、導引式學習、Rich Menu、NAS 永久部署與報告素材；同步遠端 main 的四份最新報告稿。
  - Reason: 保存跨多輪累積成果，並讓正式資料契約、部署設定、驗收文件與實際程式一致。
  - Impact: 本機 main 納入 239 個初始變更檔；圖片、PPT、巨型題庫、秘密與暫存不送入首次 CodeRabbit 審查。
- Timestamp: 2026-09-19T21:58:35+08:00
  - Change: 完成兩次 CodeRabbit 審查。首次 131 份文字檔、8 項 finding：接受 6 項並修正，拒絕 2 項（映像已有 HEALTHCHECK；報告已明示 PPTX 尚未同步）。第二次 5 項 minor finding 全部驗證後修正；保留第三次額度。
  - Reason: 依使用者要求，在推送 main 前進行外部審查，但不自動套用未驗證建議。
  - Impact: 修正 NAS `.env` 路徑、線上評估人工分數污染、300 題 release contract、報告數量漂移、簡報驗證檔名、單位公式與 provider 用詞。
- Timestamp: 2026-09-19T21:58:35+08:00
  - Change: 執行完整本機發布驗證與受影響切片複驗。
  - Reason: 為直接推送 main 建立可重複證據。
  - Impact: `pip check`、compile、1155 項 pytest、81.99% branch coverage、300 題／24 主題 release certification、PPT v9 11 頁匯入驗證與 diff check 全部通過；未把 CI、手機 E2E 或 30 題線上模型評估宣稱為已完成。
- Timestamp: 2026-09-19
  - Change: 移除 `sw483` 代議民主與 `sw485` 抽籤選領導者，將正式知識庫收斂為 1234 張；重製 PPT v11 與逐頁講稿，機器人對話統一使用淺藍色，架構圖明列 Synology NAS／Docker。
  - Reason: 兩張卡偏一般政治制度，與天文、工程、科幻科技主線的耦合最低；同時讓簡報反映 100 張圖片、NAS 部署與目前驗證邊界。
  - Impact: 1153 項 pytest 通過，branch coverage 81.99%；PPT v11 11 頁、原生圖表、字型與版面驗證通過。未把程式測試宣稱為學習成效或模型準確率。

## 2026-09-20

- Timestamp: 2026-09-20T02:02:41+08:00
  - Change: 完成 LB-006 兩輪多領域對抗審查、證據仲裁與 CodeRabbit 差異審查；修正持久化 webhook 收件匣、安全重試分類、中斷事件操作重排、模型請求限流與每日保險絲、PII 遮罩、導引資料遷移與保留、檢索界線、NAS 秘密分離與供應鏈鎖定。
  - Reason: 排除會導致 LINE 不回覆、重複回覆、資料遺失、額度失控、敏感資料外送或 NAS 發布漂移的風險。
  - Impact: 1176 項 pytest 通過，branch coverage 82.91%；Ruff、Bandit、鎖定正式依賴稽核與 diff check 通過；最終未處置 P0=0、P1=0。手機、外部模型與 NAS 真機驗收仍維持誠實邊界。
- Timestamp: 2026-09-20T07:15:00+08:00
  - Change: 透過 iPhone 鏡像完成 LINE 手機 E2E：功能導覽、三輪上下文聊天、帶 NASA 來源的科學回答、試煉選庫／難度／作答／退出，並實際檢查 Rich Menu。
  - Reason: LB-005 的驗證條件要求真實手機收發與試煉證據，不能用本機測試代替。
  - Impact: 功能 E2E 通過；Rich Menu 六格的實機字級偏小，且「問守門人」與「功能說明」重複。建議收旂為 2×2 四格後再點擊驗收；本次不宣稱 30 題線上模型評估或 NAS 真機已完成。
- Timestamp: 2026-09-20T07:32:00+08:00
  - Change: 將 Rich Menu 收旂為 2×2 四格，放大標題與觸控區；套用至 LINE 官方帳號預設選單，並將選單原始碼、產圖腳本與 PNG 同步至 NAS 正式部署目錄。
  - Reason: 手機實機發現六格字級偏小，且兩個入口導向同一份功能導覽。
  - Impact: LINE API 確認四個 1250 寬點擊區與四個既有指令，遠端 PNG 與本機 SHA-256 一致；NAS `/health` 維持 `status=ok`、300 題。iPhone LINE 仍顯示舊六格快取，待客戶端刷新後補做最後四格點擊。
- Timestamp: 2026-09-20T08:08:00+08:00
  - Change: 將四格 Rich Menu 升級為鮮豔外星科幻底圖，副標放大至 68px，第二格改名「引導學習」；繁中文字由程式精準疊印，四個既有訊息動作不變。
  - Reason: iPhone 實機顯示素色版副標仍偏小，且「四座寶庫」入口名稱未直接表達引導式學習；使用者要求圖文並茂、科幻、外星球與鮮豔風格。
  - Impact: LINE 官方預設、遠端圖片與 NAS 四份檔案驗證一致，公開 `/health` 維持正常；iPhone 仍快取上一張素色四格，待再次重新開啟 LINE 後補做最終顯示與點擊驗收。
- Timestamp: 2026-09-20T08:18:00+08:00
  - Change: 完成最終彩色大字 Rich Menu 手機驗收；四格改為「自由提問／引導學習／星之試煉／我的旅程」，iPhone 實點四格均收到對應 Bot 回覆。
  - Reason: 排除 iPhone Rich Menu 快取時差與點擊區錯位，並確保現場實機投影已載入正式版本。
  - Impact: ST-019 完整通過；LINE 官方遠端圖片、本機與 NAS SHA-256 一致，Bot 健康端點正常。
- Timestamp: 2026-09-20T08:22:00+08:00
  - Change: 執行 OpenAI `gpt-5.6-luna` 30 題線上評估，保留首輪與重試結果，並對 24 題範圍內成功回答逐題人工核對事實內容。
  - Reason: 建立評審可查看的逐題真實明細，同時維持來源題庫與生成結果分離，不編造人工分數。
  - Impact: q027 連續兩次 JSON 格式失敗，最終 29/30 有效但整體仍為 invalid；24 題範圍內人工事實分數 24/24，分類 accuracy=0.875、macro F1=0.883861、來源命中率=0.916667、out-of-scope refusal rate=0。ST-020 記為 Fail，LB-E5 保持 In Progress。
- Timestamp: 2026-09-20T09:24:42+08:00
  - Change: 改用與 26B 配額獨立的 Google `gemma-4-31b-it` 完成 30 題線上評估；評估器加入 Google 預設 2.1 秒節流、429 至少 60 秒退避、暫時錯誤有限重試、成功記錄續跑與逐題進度；並對 24 題範圍內回答完成逐題人工事實核對。
  - Reason: 26B 快速批次已碰到每分鐘 30 次限制，31B 首輪另有長回應逾時；需要在不重送既有成功題、不暴衝配額的前提下產出可重跑有效報表。
  - Impact: Google 31B 最終 30/30 有效、error_count=0，人工事實分數 24/24；accuracy=0.875、macro F1=0.883861、source match=0.916667。六題 out-of-scope 舊期待值與現行「自由提問」產品契約衝突，保留為題庫 follow-up，不為灌分修改 Bot。完整 pytest 100%、exit 0；LB-005 與 LB-E5 轉入 Review。修正後原始碼已備份並同步 NAS，但 Compose image 尚未重建，未將原始碼同步誤稱為運行版本更新。

## 2026-09-21

- Timestamp: 2026-09-21T20:34:56+08:00
  - Change: 修復 Mission Center legacy summary 遷移造成的 Project／Goal／Cycle／Objective placeholder 污染；確認歷史 CI 失敗與摘要無因果關係，並依 CodeRabbit 全庫審查補強未分組付款卡號遮罩與科學量測數字保留。
  - Reason: 恢復專案真實身分，避免把已修復的 clean-runner 依賴事故誤歸因於摘要，同時處置跨舊版本審查發現的唯一有效敏感資料邊界。
  - Impact: 一次性 Python 3.11 clean environment 完成 1193 項 pytest、82.69% branch coverage、pip check、compileall 與離線評估；CodeRabbit 審查 129 檔、1 項 Minor 已以失敗測試重現並修正。未重跑歷史 GitHub Actions，亦未把本機驗證冒充遠端 CI 或 NAS 發布證據。
- Timestamp: 2026-09-21T05:44:31+08:00
  - Change: 準備直接發布至 `main` 的收斂版本；將本機最終簡報、逐頁講稿、插圖及簡報產生器加入忽略規則，並把先前已追蹤的簡報交付物與簡報文件排定從目前 Git tree 移除。另依 CodeRabbit 審查修正續跑評估輸入雜湊綁定，以及未標籤分組付款卡號遮罩。
  - Reason: 避免含講者姓名的簡報出現在 GitHub 目前版本，同時防止續跑結果混用不同資料，並補齊敏感號碼外送前的遮罩邊界。
  - Impact: 本機簡報仍完整保留但不會被加入 commit；1191 項 pytest 與靜態／安全／依賴檢查通過；CodeRabbit 兩項有效 Major 已修正且聚焦複審為 0 項。Git 歷史未做破壞性改寫，舊 commit 內既有簡報仍屬另行處理範圍。
