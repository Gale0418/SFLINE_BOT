# SFLINE_BOT 程式與報告檢視紀錄｜2026-09-20

## 這次先看過的重點

- `README.md`：目前主線已改為 1234 張知識卡、300 題、80 段導引教材、100 張重點圖片，並包含 Rich Menu / Flex Message / NAS 方向。
- `data/`：目前資料檔包含 `knowledge_cards.json`、`quiz_questions.tsv`、`eval_questions.csv`。知識卡檔案約 914 KB，題庫 TSV 約 97 KB。
- `src/eternal_polaris/app.py`：主流程是 Flask + LINE Webhook，先驗簽、排程、去重，再分流到指令、試煉、導引或自由問答。
- `src/eternal_polaris/knowledge.py`：本機知識卡以 exact / containment / n-gram + SequenceMatcher 做高信心匹配；模型回答會被來源與長度約束。
- `src/eternal_polaris/line_gateway.py`：已經有 Flex Message，非試煉回覆會包成淺藍卡；試煉回覆也有專門版面。這表示簡報不能再說它只是純文字 Bot。
- `MissionCenter/closeout.md`：記錄 1234 卡、300 題、100 圖片、1153 tests passed、branch coverage 81.99%、NAS 服務曾完成健康檢查與 LINE webhook 測試，也明確說 30 題線上模型評估未完成。
- GitHub Actions：最新 main SHA `9a38d2a...` 的 Main CI 與 Release certification 均為 success。
- `deliverables/`：v11 PPT 是 11 頁；v11 演講稿仍有明顯 AI 腔，例如「天才少女學生風格」、「我們」過多、「這就是永恆北極星想填補的空間」等，不適合秋芸羊本人直接念。

## 我判定要改的地方

1. **演講稿人格錯位**  
   原稿把講者寫成活潑天才少女，和使用者要的陰沉、內向、不想講太多完全衝突。已改成短句、停頓、吐槽式講法。

2. **數字混亂**  
   之前同時有 96、220、300、1001、1234 等不同版本。新版簡報只講：1234 知識卡、300 題、80 教材、100 圖片；1001 只作為早期彩蛋，不再當現行契約。

3. **PPT 不能再用企業式大綱塞滿**  
   11 頁 v12 直接以「為什麼做 → 為什麼膨脹 → 現況數字 → 三種玩法 → 架構 → 模型 → 導引 → 驗證 → Demo → 結論」走完，不再硬塞 NotebookLM / Kahoot 長篇比較。

4. **測試結果要講邊界**  
   1153 passed 和 81.99% coverage 可以講，但只能代表程式規則與本機測試，不代表科學答案永遠正確，也不代表學習成效。

5. **現場 Demo 要保守**  
   不臨時問怪題。建議只跑：啟明星/長庚星 → 追問 → 學習 → 挑戰。API 掛掉就展示本機題庫與導引，不硬撐。

## 新增交付物

- `deliverables/永恆北極星_正常版_v12.pptx`（本次已在對話沙盒產出；若需 GitHub 二進位版請另行上傳）
- `deliverables/永恆北極星_正常版_v12_逐頁演講稿.md`
- 本檢視紀錄

## 未處理

- 沒有改 Bot 程式。
- 沒有重算整份知識卡內容品質。
- 沒有完成 30 題線上模型評估。
- 沒有把 v11 舊 PPT 刪掉；保留歷史版本，v12 作為正常版。 
