from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_nas_compose_uses_repository_env_and_image_healthcheck():
    compose = (ROOT / "deploy" / "nas" / "compose.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "deploy" / "nas" / "Dockerfile").read_text(encoding="utf-8")

    assert compose.count("- ../../.env") == 1
    assert "NGROK_AUTHTOKEN: ${NGROK_AUTHTOKEN" in compose
    assert "ngrok:\n" in compose
    assert "../../../.env" not in compose
    assert "condition: service_healthy" in compose
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:5000/ready" in dockerfile
    assert '"127.0.0.1:5050:5000"' in compose
    assert "python:3.11-slim@sha256:" in dockerfile
    assert "python -m pip install --require-hashes -r requirements.lock" in dockerfile
