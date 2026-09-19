from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_nas_compose_uses_repository_env_and_image_healthcheck():
    compose = (ROOT / "deploy" / "nas" / "compose.yaml").read_text(encoding="utf-8")
    dockerfile = (ROOT / "deploy" / "nas" / "Dockerfile").read_text(encoding="utf-8")

    assert compose.count("- ../../.env") == 2
    assert "../../../.env" not in compose
    assert "condition: service_healthy" in compose
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:5000/health" in dockerfile
