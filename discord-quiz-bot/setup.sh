#!/bin/bash
# Oracle Cloud Ubuntu 22.04 - 원클릭 설치 스크립트
# 사용법: bash setup.sh

set -e

echo "=== [1/5] 시스템 업데이트 ==="
sudo apt-get update -y

echo "=== [2/5] Docker 설치 ==="
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"

echo "=== [3/5] Docker Compose 플러그인 설치 ==="
sudo apt-get install -y docker-compose-plugin

echo "=== [4/5] 레포 클론 ==="
git clone https://github.com/yujung7768903/claude-study.git ~/claude-study

echo "=== [5/5] 환경변수 설정 ==="
cd ~/claude-study/discord-quiz-bot
cp .env.example .env

echo ""
echo "✅ 설치 완료!"
echo ""
echo "다음 단계:"
echo "  1. .env 파일 편집:  nano ~/claude-study/discord-quiz-bot/.env"
echo "  2. 봇 실행:         cd ~/claude-study/discord-quiz-bot && docker compose up -d"
echo "  3. 로그 확인:       docker compose logs -f"
echo ""
echo "⚠️  Docker 그룹 적용을 위해 재로그인 필요할 수 있음 (또는 newgrp docker)"
