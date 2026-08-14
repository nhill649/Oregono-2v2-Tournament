FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg tesseract-ocr ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir streamlink
COPY worker/app.py ./app.py
COPY processor ./processor
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8080"]
