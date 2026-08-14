FROM golang:1.24-bookworm AS r6parser
RUN go install github.com/redraskal/r6-dissect@latest

FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg tesseract-ocr ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir streamlink
COPY --from=r6parser /go/bin/r6-dissect /usr/local/bin/r6-dissect
COPY worker/app.py ./app.py
COPY worker/replay_parser.py ./replay_parser.py
COPY processor ./processor
ENV PYTHONUNBUFFERED=1
ENV R6_DISSECT_BIN=/usr/local/bin/r6-dissect
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8080"]
