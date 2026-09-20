"""Generate the deterministic 2500×843 Rich Menu artwork."""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path("assets/line/rich-menu.png")
BACKGROUND = Path("assets/line/rich-menu-cosmic-background.png")
FONT = Path("C:/Windows/Fonts/msjh.ttc")
WIDTH, HEIGHT = 2500, 843
CELLS = (
    ("自由提問", "問知識、想法與功能", "#FFD84D", "#FFF1A8"),
    ("引導學習", "四座寶庫循序帶你學", "#62E8FF", "#C6F7FF"),
    ("星之試煉", "挑戰五道知識星門", "#FF72D2", "#FFD0EE"),
    ("我的旅程", "查看進度與最高分", "#79F2B2", "#D0FFE6"),
)


def centered(draw, box, text, font, fill, *, stroke_width=0, stroke_fill=None):
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), text, font=font)
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    draw.text(
        ((left + right - width) / 2, (top + bottom - height) / 2 - bounds[1]),
        text,
        font=font,
        fill=fill,
        stroke_width=stroke_width,
        stroke_fill=stroke_fill,
    )


def resolve_font() -> Path:
    candidates = (
        Path(os.environ["RICH_MENU_FONT"]) if os.environ.get("RICH_MENU_FONT") else None,
        FONT,
        Path("/System/Library/Fonts/STHeiti Medium.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    )
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate
    raise FileNotFoundError("找不到支援中文的字型，請設定 RICH_MENU_FONT")


def main():
    if not BACKGROUND.is_file():
        raise FileNotFoundError(f"找不到 Rich Menu 科幻底圖：{BACKGROUND}")
    image = Image.open(BACKGROUND).convert("RGB").resize(
        (WIDTH, HEIGHT), Image.Resampling.LANCZOS
    )
    draw = ImageDraw.Draw(image, "RGBA")
    font_path = resolve_font()
    title_font = ImageFont.truetype(str(font_path), 128)
    subtitle_font = ImageFont.truetype(str(font_path), 80)
    cell_widths, row_heights = (1250, 1250), (421, 422)
    index, y = 0, 0
    for row_height in row_heights:
        x = 0
        for cell_width in cell_widths:
            title, subtitle, title_color, subtitle_color = CELLS[index]
            inset = (x + 18, y + 18, x + cell_width - 18, y + row_height - 18)
            draw.rounded_rectangle(
                inset,
                radius=34,
                fill=(4, 17, 51, 158),
                outline=title_color,
                width=4,
            )
            centered(
                draw,
                (x, y + 46, x + cell_width, y + 214),
                title,
                title_font,
                title_color,
                stroke_width=2,
                stroke_fill="#07152E",
            )
            centered(
                draw,
                (x + 44, y + 208, x + cell_width - 44, y + 372),
                subtitle,
                subtitle_font,
                subtitle_color,
                stroke_width=1,
                stroke_fill="#07152E",
            )
            x += cell_width
            index += 1
        y += row_height
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    optimized = image.quantize(
        colors=256,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.FLOYDSTEINBERG,
    )
    optimized.save(OUTPUT, "PNG", optimize=True)
    print(f"{OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
