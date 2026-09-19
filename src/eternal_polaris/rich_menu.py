"""Rich Menu definition and explicit, recoverable installer."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


WIDTH, HEIGHT = 2500, 843
BUTTONS = (
    ("觀星入門", "星等是什麼？"),
    ("問守門人", "你會什麼？"),
    ("四座寶庫", "學習"),
    ("星之試煉", "挑戰"),
    ("我的旅程", "學習進度"),
    ("功能說明", "幫助"),
)


def build_rich_menu_object() -> dict:
    """Return one 3×2 menu whose six actions already exist in the bot."""
    widths = (834, 833, 833)
    heights = (421, 422)
    areas = []
    y = 0
    index = 0
    for row_height in heights:
        x = 0
        for column_width in widths:
            label, message = BUTTONS[index]
            areas.append({
                "bounds": {"x": x, "y": y, "width": column_width, "height": row_height},
                "action": {"type": "message", "label": label, "text": message},
            })
            x += column_width
            index += 1
        y += row_height
    return {
        "size": {"width": WIDTH, "height": HEIGHT},
        "selected": False,
        "name": "永恆北極星主選單",
        "chatBarText": "展開星圖",
        "areas": areas,
    }


def install_default_rich_menu(
    access_token: str,
    image_path: Path,
    *,
    client: httpx.Client | None = None,
) -> str:
    """Validate, create, upload and set the menu; delete our orphan on failure."""
    image = Path(image_path).read_bytes()
    if not image or len(image) > 1_000_000:
        raise ValueError("Rich Menu PNG 必須存在且不可超過 1 MB")
    headers = {"Authorization": f"Bearer {access_token}"}
    owns_client = client is None
    client = client or httpx.Client(timeout=10.0)
    rich_menu_id: str | None = None
    try:
        spec = build_rich_menu_object()
        response = client.post(
            "https://api.line.me/v2/bot/richmenu/validate",
            headers={**headers, "Content-Type": "application/json"},
            json=spec,
        )
        response.raise_for_status()
        response = client.post(
            "https://api.line.me/v2/bot/richmenu",
            headers={**headers, "Content-Type": "application/json"},
            json=spec,
        )
        response.raise_for_status()
        rich_menu_id = str(response.json()["richMenuId"])
        response = client.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers={**headers, "Content-Type": "image/png"},
            content=image,
        )
        response.raise_for_status()
        response = client.post(
            f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
            headers=headers,
        )
        response.raise_for_status()
        return rich_menu_id
    except Exception:
        if rich_menu_id:
            client.delete(
                f"https://api.line.me/v2/bot/richmenu/{rich_menu_id}",
                headers=headers,
            )
        raise
    finally:
        if owns_client:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="建立永恆北極星 LINE Rich Menu")
    parser.add_argument("--apply", action="store_true", help="真的建立並設為預設選單")
    parser.add_argument(
        "--image", type=Path, default=Path("assets/line/rich-menu.png"),
        help="2500×843、1 MB 以下的 PNG",
    )
    args = parser.parse_args()
    spec = build_rich_menu_object()
    if not args.apply:
        print(json.dumps(spec, ensure_ascii=False, indent=2))
        print("\n目前為預覽模式；加入 --apply 才會修改 LINE 官方帳號。")
        return
    load_dotenv()
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        raise SystemExit("缺少 LINE_CHANNEL_ACCESS_TOKEN，未修改任何線上設定。")
    rich_menu_id = install_default_rich_menu(token, args.image)
    print(f"Rich Menu 已設為預設選單：{rich_menu_id}")


if __name__ == "__main__":
    main()
