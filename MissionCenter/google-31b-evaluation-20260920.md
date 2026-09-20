# Google 31B 30 題線上評估證據｜2026-09-20

## 結論

- Provider／model：Google `gemma-4-31b-it`
- 有效記錄：30/30
- `run_status`：`valid`
- `error_count`：0
- 24 題知識範圍內回答人工事實核對：24/24
- 分類 accuracy：0.875
- macro F1：0.8838612368024132
- source match rate：0.9166666666666666
- 平均延遲：35947.4ms
- p95 延遲：80795.0ms

## 配額與復原策略

26B 的快速批次已碰到 Google 每分鐘 30 次限制，因此停止沿用該流量桶，改以配額獨立的 31B 執行。評估器對 Google 預設至少 2.1 秒請求起始間隔；429 至少等待 60 秒；429、5xx、逾時、無效 JSON 與暫時知識解析錯誤採有限重試；續跑只沿用成功記錄，不會重送整批。最終 24 題第一次成功、6 題第二次成功。

API key 僅從 `/Volumes/MyGame/OWO.TXT` 最後一個非空白行於執行期讀取，未輸出、未寫入專案 `.env`、未寫入報表或本證據檔。

## 品質邊界

- 分類差異：q010、q013、q014、q025–q030。
- 來源未命中：q010、q014。
- q025–q030 的題庫期待值仍為 `out_of_scope`，但目前正式 Bot 指令明確允許人物、歷史、日常與其他一般知識，並將 Rich Menu 第一格命名為「自由提問」。因此 refusal rate=0 反映的是題庫契約漂移，不應為提高分數而把產品倒改成拒答。
- `data/eval_questions.csv` 的 `manual_fact_score` 仍保持空白；人工分數屬於本次生成回答，寫在獨立 reviewed JSON 與 manual CSV，避免污染可重跑來源題庫。

## 可稽核檔案

| 檔案 | SHA-256 |
| --- | --- |
| `results/google-31b-evaluation-20260920-valid.json` | `7c492be9f1b0fbf0b4ea23cfd675bb9e5a4b829d3191af0c2bd192c7cbeff72a` |
| `results/google-31b-evaluation-20260920-reviewed.json` | `2c678c0408d86f16fc80d35afab810d57b56959bceeea6ffffa503b8c9d5ae42` |
| `results/google-31b-evaluation-20260920-manual.csv` | `3525efa7e5f348e2d5bef27c2763842a20e8a8a15065a27369a44f40d1c88087` |

## 驗證

- 受影響切片：`tests/test_evaluation.py tests/test_answer_service.py`，35 passed。
- 完整回歸：`pytest -q` 顯示 100%，exit 0。
- Python compile：`python -m compileall -q src tests`，exit 0。

## NAS 同步邊界

- `evaluation.py` 與 `answer_service.py` 已先備份 NAS 舊版，再同步至 `/volume1/docker/eternal-polaris/app/src/eternal_polaris/`；工作區與 NAS 原始碼 SHA-256 分別一致為 `0e9908c2ff25d31c4a79a99f280a395cc67716ae36ece74d1f8f39b8e134a2f7`、`9d8f22fb656ffbf8f24ccadf6c025947bed2bb87f62ed0b07cb730be39278169`。
- 備份位於 `/volume1/docker/eternal-polaris/backups/google-eval-fixes-20260920-0924/`。
- NAS Compose 以原始碼建置 image，未把 `app/src` 掛入運行中容器；目前環境沒有 NAS Docker CLI／SSH 認證，因此本輪沒有重建或重啟容器。公開 `/health` 在同步後仍回 `status=ok`、`quiz_questions=300`，但此健康結果代表既有運行版本正常，不冒充新 prompt 已上線。
