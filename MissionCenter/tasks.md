# 永恆北極星｜任務樹

| ID | Title | Type | Parent | Priority | Status | Owner | Depends on | Next action | Verification | Estimate | Labels | Comments |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LB-E1 | 安全的專案基礎與金鑰遷移 | Epic | - | P0 | Done | Codex | - | 已完成 | LB-001、LB-002 已結案；ST-001、ST-004、ST-005、ST-007、ST-012 與後續審查證據已複核 | L | execution,verification | 2026-10-02 已先轉 Review 再依證據統合結案；本機 .venv 維護限制保留於 notes.md |
| LB-001 | 建立 Python 3.11 專案骨架 | Task | LB-E1 | P0 | Done | Codex | - | 已完成；目前本機虛擬環境退化另列維護限制 | ST-001、ST-005、ST-023：測試、靜態安全與乾淨 Python 3.11 環境驗證 | M | execution,verification | 2026-10-02 依既有通過證據與後續 ST-016／ST-023 審查結案；不宣稱今天修復或重測既有 .venv |
| LB-002 | 建立一次性金鑰遷移工具 | Task | LB-E1 | P0 | Done | Codex | LB-001 | 已完成；原始來源檔保留 | ST-001、ST-004：遷移測試與安全拒絕；ST-007：實際 .env 建立與認證 | M | execution,verification | 2026-10-02 依既有驗證與後續安全審查結案；憑證實際可用，不再保留早期未遷移 blocker |
| LB-E2 | LINE 真實端到端流程 | Epic | - | P0 | Review | Codex | LB-E1 | 評審複核 LB-005 的既有手機證據 | ST-017、ST-019 手機 E2E／四格實點；ST-024 NAS 新模型與健康端點 | L | execution,verification | 2026-10-02 對帳：實作與手機測試已完成，待正式評審複核；GPT-6 Luna 的手機驗收未重跑 |
| LB-003 | 實作健康檢查與 LINE webhook | Task | LB-E2 | P0 | Done | Codex | LB-001 | 已完成 | ST-001、ST-003、ST-016：簽章、事件處理與可靠性；ST-024：NAS 內外 health/ready | L | execution,verification | 2026-10-02 依既有測試、外部審查及正式端點證據結案 |
| LB-004 | 接通 OpenAI 結構化回答 | Task | LB-E2 | P0 | Done | Codex | LB-003 | 已完成；完整評估由 LB-E5 另行追蹤 | ST-001：Mock／結構驗證；ST-024：NAS Responses API 真實 GPT-6 Luna 回答 | L | execution,verification | 2026-10-02 ST-024 已解除 ST-008 的歷史單題配額 blocker；不把單題成功等同 30 題評估完成 |
| LB-005 | 完成 ngrok 與手機 LINE 垂直切片 | Task | LB-E2 | P0 | Review | Codex | LB-002, LB-003, LB-004 | 由評審依 ST-019 與 ST-021 複核手機四格、NAS 健康與 Google 30 題證據 | 手機實際問答、試煉與四格 Menu 截圖，Google 路徑成功 | M | verification | 2026-09-20 iPhone 最終彩色四格與四入口實點通過，NAS／公開健康端點正常；Google 31B 30/30 有效、error_count=0，24 題範圍內回答人工事實核對 24/24，見 ST-019、ST-021 |
| LB-E3 | 天文與科幻知識庫與回答格式 | Epic | - | P1 | Review | Codex | LB-E2 | 對齊正式交付 SHA、NAS 運行映像與同 SHA CI 證據 | ST-015：1234 卡資料契約；ST-024：NAS 回報 1234 卡、300 題 | L | execution,verification | 知識庫與格式已有通過證據；剩餘是發布版本對齊，非重新建立知識庫 |
| LB-E4 | 三輪記憶、錯誤處理與可靠性 | Epic | - | P1 | Done | Codex | LB-E3 | 已完成；維持既有可靠性保護 | ST-016：可靠性、安全與對抗審查；ST-017：三輪手機上下文；ST-023：後續安全修補驗證 | L | execution,verification | 2026-10-02 依既有驗證與 LB-006 已完成審查結案；不擴張為長期可用性或新模型品質保證 |
| LB-E5 | 30 題測試集與評估報表 | Epic | - | P1 | Review | Codex | LB-E4 | 評審複核有效報表與逐題人工明細；另排程更新六題舊 out-of-scope 標籤，使其符合「自由提問」產品契約 | 產生可重跑有效評估報表 | L | verification | 2026-09-20 Google `gemma-4-31b-it` 完成 30/30 有效報告、error_count=0；24 題範圍內回答人工事實核對 24/24。accuracy=0.875、macro F1=0.883861、source match=0.916667；六題 out-of-scope 期待值與現行自由提問契約衝突，未為灌分強制拒答，詳見 ST-021 |
| LB-E6 | 報告、簡報、Demo 與成果封裝 | Epic | - | P2 | In Progress | Codex | LB-E5, LB-005 | 將 ST-019／ST-021 正式證據與題庫契約差異納入最終報告、簡報及 15 分鐘演練 | 書面與 PPT 對照配分，15 分鐘演練及人工驗收 | L | closeout | 2026-09-20 手機 E2E、最終四格、NAS 健康與有效 30 題評估 blocker 已解除；待更新正式成果敘事與演練證據 |
| LB-006 | 全面品質優化與對抗審查 | Task | LB-E4 | P1 | Done | Codex | LB-E3 | 維持可靠性保護並在 NAS 上線前完成手機實機驗收 | 1176 項測試、82.91% coverage、Ruff、Bandit 與鎖定依賴稽核通過；最終無未處置 P0/P1 | L | execution,verification | 兩輪三席盲審與證據仲裁完成；CodeRabbit 六項皆修正或以程式證據駁回。Antigravity 串流中斷，未列入有效審查證據 |
| LB-007 | 切換 GPT-6 Luna 並重啟 NAS 機器人 | Task | LB-E2 | P1 | Done | Codex | LB-004 | 已完成；後續手機 E2E 與模型評估依原任務另行驗收 | ST-024：真實模型回答、運行設定、healthy、內外 health/ready 通過 | S | execution,verification | 2026-10-02 已經 Review 複核；本機與 NAS .env 已更新、bot 已重新建立，image、資料卷及 ngrok 保留；備份權限 600；無原始碼修改，低風險評論 route=skip |

| LB-008 | 曲速索卡修正、CodeRabbit 審查與 main／NAS 發布 | Task | LB-E3 | P1 | In Progress | Codex | LB-007 | 完成最終審查、完整回歸與正式發布 | 現行問題回歸、CodeRabbit 有效問題處置、GitHub CI 與 NAS 健康 | M | execution,verification | 2026-10-02 主人已授權直接 main、Docker 更新；首輪 137 檔審查完成，一項舊模型驗證已修正，尚未發布 |
| LB-009 | 1234 張卡片固定冷知識吐槽 | Task | LB-E3 | P1 | In Progress | Codex | LB-008 | 完成逐卡內容、資料檢查與問答／學習顯示驗證 | 每卡固定一句、嘴賤網友口氣、前綴冷知識:、不新增模型請求 | L | execution,verification | 2026-10-02 使用者選固定一句並指定語氣；內容已全數定稿，第一版候選驗證通過；最終審查及新版發布進行中 |

| LB-010 | 全面抓蟲與三領域嚴格專家複查 | Task | LB-E4 | P1 | In Progress | Codex | LB-008, LB-009 | 收斂玩家／安全／效能審查，重現修正有效問題並複核 | 無未處置P0/P1，所有確認成立低級問題已修；最終回歸與NAS驗證 | L | execution,verification | 2026-10-02 使用者追加全面優化，先延後上傳與正式切換；三位Luna獨立審查，效能變更須有測量，不作無關重構 |
