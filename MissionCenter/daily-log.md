# Daily log

## 2026-09-01

- 發布使用者核准的實作計畫並開始第一里程碑。


## 2026-09-08

- 使用者確認最高目標為通過專題考試，交付書面及 PPT，並要求先完成機器人再製作報告。已將正式配分、期限、15 分鐘、文風參考與 Gemini 建議記入 report-requirements.md；不改成只啟動服務即完成。
- Gemini 寫作討論已完成，修正其將 96 題試煉與 30 題評估混用的建議。
- 開啟 LINE Use webhook，API 確認 active=true。30 題 Google 評估全部失敗，最小生成請求500，模型列表200。79 項離線測試通過。
- Gemini 已完成 scripts/start_app.ps1 與 README 的程序限定 Google key 載入功能（request linebot-startup-20260908-01，cascade bfe6af07-ceb2-4237-a83c-80abc83b8024，已觀察完成 marker）。Codex 補修單行集合、來源必填與檔案型態驗證，已驗收前置邏輯。沒有第二個寫入者與其重疊修改。

- Last organized: 2026-09-19

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
