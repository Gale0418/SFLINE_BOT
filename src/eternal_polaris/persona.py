from __future__ import annotations


WELCOME_TEXT = """歡迎。已經很久沒有人走到這張星圖前了。

我是「永恆北極星」。平常，我樂意陪你談宇宙、地球、生命、物理與未來科技，並替你分清已知、理論與科幻。

想知道我會做什麼，可以說「幫助」；若覺得光聽還不夠，就說一聲「挑戰」。寶庫的大門會為求知者開啟。"""

HELP_TEXT = """呵呵，第一次來也不用拘謹。我是「永恆北極星」，可以陪你做四件事：

🔭 問我萬象
黑洞、恆星、地震、演化、量子、能源與太空工程，都可以試著問。

🧭 分清邊界
我會標示哪些已有觀測、哪些只有理論、哪些仍屬科幻設定。

🗝️ 接受星之試煉
說「挑戰」或「出題」，我會開啟五題式知識寶庫。

📜 查看狀態
試煉中可說「分數」；想離開則說「退出」。

想知道什麼，儘管問吧。若想敲響寶庫的門，只要說一聲「挑戰」。"""

RULES_TEXT = """星之試煉共有五道門：

1. 先選一座寶庫與難度。
2. 每題四選一，可按按鈕，也可直接輸入 A、B、C 或 D。
3. 作答後會立即公布正解與科學解說。
4. 舊題答案、別人的答案符文與遭竄改的符文都不算數。
5. 答錯不會被嘲笑；寶庫在意的是你有沒有把知識帶走。

準備好時，說「挑戰」。"""

CHALLENGE_INTRO_TEXT = """……原來如此。你不是來索取答案，而是來證明自己是否配得上它。

老人將茶杯輕輕放下。沉睡的星圖逐一亮起，牆後傳來古老機關甦醒的低鳴。

「寶庫不拒絕求知之人——但它從不白白交出自己的秘密。」

選擇你要叩問的寶庫吧，旅人。"""

NO_ACTIVE_QUIZ_TEXT = "目前沒有正在進行的試煉。若想讓寶庫開門，說一聲「挑戰」即可。"

QUIT_TEXT = """石門在你身後安靜闔上。守門人重新端起茶杯，神情又恢復了原先的溫和。

「知道何時暫停，也是一種判斷。想再試一次，隨時回來；若有疑問，我仍在這裡。」"""

QUIZ_EXPIRED_TEXT = "星圖上的光已經熄滅，這場試煉因等待過久而結束了。不要緊，說「挑戰」便能重新敲門。"

INVALID_TOKEN_TEXT = """守門人看了看那枚符文，緩緩搖頭。

「這不是屬於眼前這道門的答案。請使用目前題目下方的選項，或直接輸入 A、B、C、D。」"""


def render_score(*, answered: int, total: int, score: int, streak: int) -> str:
    if answered >= total:
        return f"這場試煉已完成：{score} / {total} 題正確，最高連續答對 {streak} 題。"
    return (
        f"目前已走過 {answered} / {total} 道門，答對 {score} 題，"
        f"最高連續答對 {streak} 題。下一道門仍在等你。"
    )


def render_question(
    *,
    vault_name: str,
    number: int,
    total: int,
    difficulty_name: str,
    question: str,
    choices: tuple[str, str, str, str],
) -> str:
    letters = "ABCD"
    options = "\n".join(f"{letters[index]}. {choice}" for index, choice in enumerate(choices))
    return (
        f"【{vault_name}｜{difficulty_name}】\n"
        f"第 {number} / {total} 道星門\n\n"
        f"{question}\n\n{options}"
    )


def render_feedback(
    *,
    correct: bool,
    chosen_letter: str,
    correct_letter: str,
    correct_text: str,
    explanation: str,
    source_name: str,
    score: int,
    answered: int,
    total: int,
) -> str:
    if correct:
        opening = "「很好。」守門人微微頷首，石門伴著低鳴向兩側退去。"
        verdict = f"✅ 答對了：{correct_letter}. {correct_text}"
    else:
        opening = "守門人沒有動怒，只是輕輕搖了搖頭。\n「勇氣值得肯定，但寶庫只接受正確的答案。」"
        verdict = f"❌ 你選了 {chosen_letter}\n✅ 正確答案：{correct_letter}. {correct_text}"
    return (
        f"{opening}\n\n{verdict}\n\n"
        f"解說：{explanation}\n"
        f"來源：{source_name}\n\n"
        f"目前得分：{score} / {answered}　進度：{answered} / {total}"
    )


def render_final(*, score: int, total: int, best_streak: int) -> str:
    ratio = score / total if total else 0.0
    if ratio == 1.0:
        title = "🌠 群星寶庫的持鑰者"
        judgment = "五道門全數開啟。守門人向你行了一個久違而鄭重的禮。"
    elif ratio >= 0.8:
        title = "🛰️ 深空領航者"
        judgment = "最後一道鎖扣落下。你已證明自己不只記得答案，也理解它們。"
    elif ratio >= 0.6:
        title = "🔭 星圖研習者"
        judgment = "數道石門為你開啟。尚未揭露的房間，正好留作下一次遠征。"
    elif ratio >= 0.4:
        title = "🧭 求知旅人"
        judgment = "寶庫沒有完全開啟，但你帶走的每個修正，都比空手而回更有價值。"
    else:
        title = "🕯️ 初燃的探問者"
        judgment = "石門仍然沉重。守門人卻替你留下一盞燈——因為願意再問一次，才是知識真正的起點。"
    return (
        f"【星之試煉完成】\n\n{title}\n{judgment}\n\n"
        f"最終得分：{score} / {total}\n最高連續答對：{best_streak}\n\n"
        "老人重新坐回星圖旁，語氣恢復溫和。\n"
        "「想再叩問另一座寶庫，就說『挑戰』；想聊聊剛才的知識，也儘管問吧。」"
    )
