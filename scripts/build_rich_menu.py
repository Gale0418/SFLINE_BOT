"""Generate the deterministic 2500×843 Rich Menu artwork."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path("assets/line/rich-menu.png")
FONT = Path("C:/Windows/Fonts/msjh.ttc")
WIDTH, HEIGHT = 2500, 843
CELLS = (
    ("觀", "觀星入門", "從肉眼可見的星空開始"),
    ("問", "問守門人", "看看我能回答哪些問題"),
    ("學", "四座寶庫", "選路線循序學習"),
    ("試", "星之試煉", "挑戰五道知識星門"),
    ("旅", "我的旅程", "查看解鎖與最高分"),
    ("助", "功能說明", "回到所有功能入口"),
)


def centered(draw, box, text, font, fill):
    left, top, right, bottom = box
    bounds = draw.textbbox((0, 0), text, font=font)
    width, height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    draw.text(((left + right - width) / 2, (top + bottom - height) / 2 - bounds[1]), text, font=font, fill=fill)


def main():
    image = Image.new("RGB", (WIDTH, HEIGHT), "#EAF6FF")
    pixels = image.load()
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        for x in range(WIDTH):
            glow = max(0.0, 1.0 - abs(x / WIDTH - 0.5) * 1.6)
            pixels[x, y] = (
                int(232 - 12 * ratio), int(246 - 8 * ratio + 3 * glow), int(255 - 4 * ratio)
            )
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = ImageFont.truetype(str(FONT), 68)
    subtitle_font = ImageFont.truetype(str(FONT), 31)
    icon_font = ImageFont.truetype(str(FONT), 54)
    cell_widths, row_heights = (834, 833, 833), (421, 422)
    index, y = 0, 0
    for row_height in row_heights:
        x = 0
        for cell_width in cell_widths:
            icon, title, subtitle = CELLS[index]
            inset = (x + 18, y + 18, x + cell_width - 18, y + row_height - 18)
            draw.rounded_rectangle(inset, radius=34, fill=(249, 253, 255, 235), outline=(87, 141, 177, 220), width=3)
            centered(draw, (x, y + 38, x + cell_width, y + 138), icon, icon_font, "#5C88A8")
            centered(draw, (x, y + 137, x + cell_width, y + 257), title, title_font, "#17324D")
            centered(draw, (x + 30, y + 260, x + cell_width - 30, y + 345), subtitle, subtitle_font, "#55758D")
            x += cell_width
            index += 1
        y += row_height
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(f"{OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
