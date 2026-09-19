from pathlib import Path

import httpx

from eternal_polaris.rich_menu import (
    BUTTONS,
    HEIGHT,
    WIDTH,
    build_rich_menu_object,
    install_default_rich_menu,
)


def test_rich_menu_uses_six_existing_bot_commands_without_gaps():
    spec = build_rich_menu_object()
    assert spec["size"] == {"width": WIDTH, "height": HEIGHT}
    assert len(spec["areas"]) == len(BUTTONS) == 6
    assert [area["action"]["text"] for area in spec["areas"]] == [message for _, message in BUTTONS]
    assert sum(area["bounds"]["width"] for area in spec["areas"][:3]) == WIDTH
    assert spec["areas"][3]["bounds"]["y"] + spec["areas"][3]["bounds"]["height"] == HEIGHT


def test_installer_calls_official_sequence(tmp_path: Path):
    image = tmp_path / "menu.png"
    image.write_bytes(b"small-png-placeholder")
    requests = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, str(request.url)))
        if str(request.url).endswith("/v2/bot/richmenu"):
            return httpx.Response(200, json={"richMenuId": "richmenu-test"})
        return httpx.Response(200, json={})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        assert install_default_rich_menu("token", image, client=client) == "richmenu-test"
    assert requests == [
        ("POST", "https://api.line.me/v2/bot/richmenu/validate"),
        ("POST", "https://api.line.me/v2/bot/richmenu"),
        ("POST", "https://api-data.line.me/v2/bot/richmenu/richmenu-test/content"),
        ("POST", "https://api.line.me/v2/bot/user/all/richmenu/richmenu-test"),
    ]
