"""Make generated vault art fast enough for mobile Flex Message heroes."""
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path("assets/knowledge")


def main() -> None:
    for source in sorted(ROOT.glob("vault-*.png")):
        target = source.with_suffix(".jpg")
        with Image.open(source) as image:
            fitted = ImageOps.fit(image.convert("RGB"), (1040, 585), method=Image.Resampling.LANCZOS)
            fitted.save(target, "JPEG", quality=86, optimize=True, progressive=True)
        print(f"{target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
