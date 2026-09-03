from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path


REQUIRED_NAMES = (
    "NGROK_AUTHTOKEN",
    "OPENAI_API_KEY",
    "LINE_CHANNEL_SECRET",
    "LINE_CHANNEL_ACCESS_TOKEN",
)


class SecretMigrationError(RuntimeError):
    pass


def _parse_source(path: Path, *, allow_single_ngrok_token: bool) -> dict[str, str]:
    if not path.is_file():
        raise SecretMigrationError(f"找不到來源檔：{path}")
    named: dict[str, str] = {}
    unnamed: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" not in stripped:
            unnamed.append(stripped)
            continue
        name, value = (part.strip() for part in stripped.split("=", 1))
        if name not in REQUIRED_NAMES or not value or name in named:
            raise SecretMigrationError(f"來源檔格式不明：{path.name}")
        named[name] = value
    if unnamed:
        if allow_single_ngrok_token and len(unnamed) == 1 and "NGROK_AUTHTOKEN" not in named:
            named["NGROK_AUTHTOKEN"] = unnamed[0]
        else:
            raise SecretMigrationError(f"來源檔含無法判定用途的內容：{path.name}")
    return named


def migrate(ngrok_source: Path, app_source: Path, output: Path) -> tuple[str, ...]:
    if output.exists():
        raise SecretMigrationError(f"拒絕覆寫既有檔案：{output}")
    merged = _parse_source(ngrok_source, allow_single_ngrok_token=True)
    for name, value in _parse_source(app_source, allow_single_ngrok_token=False).items():
        if name in merged:
            raise SecretMigrationError(f"設定重複：{name}")
        merged[name] = value
    missing = [name for name in REQUIRED_NAMES if not merged.get(name, "").strip()]
    if missing:
        raise SecretMigrationError("缺少必要設定：" + ", ".join(missing))

    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".env.", dir=output.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for name in REQUIRED_NAMES:
                handle.write(f"{name}={merged[name]}\n")
            handle.write("OPENAI_MODEL=gpt-5.6-luna\nAPP_PORT=5000\nOPENAI_TIMEOUT_SECONDS=15\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temp_name, output)
        except FileExistsError as exc:
            raise SecretMigrationError(f"拒絕覆寫既有檔案：{output}") from exc
        Path(temp_name).unlink()
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        finally:
            pass
        raise
    return REQUIRED_NAMES


def main() -> None:
    parser = argparse.ArgumentParser(description="安全地將既有金鑰來源遷移為 .env")
    parser.add_argument("--ngrok-source", type=Path, required=True)
    parser.add_argument("--app-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(".env"))
    args = parser.parse_args()
    try:
        names = migrate(args.ngrok_source, args.app_source, args.output)
    except SecretMigrationError as exc:
        raise SystemExit(str(exc)) from exc
    print("遷移完成；已寫入欄位：" + ", ".join(names))
    print("原始 TXT 未刪除，請確認服務正常後自行移至安全位置。")


if __name__ == "__main__":
    main()
