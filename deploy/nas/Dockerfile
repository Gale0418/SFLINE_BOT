FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.lock pyproject.toml README.md ./

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.lock

COPY src ./src
COPY data/knowledge_cards.json data/quiz_questions.tsv ./data/
COPY assets/knowledge ./assets/knowledge

RUN python -m pip install --no-deps . \
    && mkdir -p /app/data/private \
    && chown -R 1026:100 /app

USER 1026:100

HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import json,urllib.request; data=json.load(urllib.request.urlopen('http://127.0.0.1:5000/health',timeout=3)); assert data['status']=='ok'"

CMD ["python", "-m", "eternal_polaris"]
