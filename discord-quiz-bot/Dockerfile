FROM python:3.11-slim

# git: study notes sync + backup push 용
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app/bot

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스코드는 volume으로 마운트 (코드 변경 시 재빌드 불필요)
# 실행: docker compose up -d

CMD ["python", "bot.py"]
