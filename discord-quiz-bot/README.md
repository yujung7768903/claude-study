# Discord 복습 퀴즈 봇

`~/claude-study`의 학습 자료를 기반으로 지정된 시각에 퀴즈를 Discord로 전송하고, 답변을 채점해주는 봇.

---

## 구성

```
discord-quiz-bot/
├── bot.py                          # 봇 메인 코드
├── requirements.txt                # Python 패키지 목록
├── .env                            # 환경 변수 (토큰, 채널 ID)
├── venv/                           # Python 가상환경
├── com.claude-study.quiz-bot.plist # macOS LaunchAgents 설정
├── bot.log                         # 실행 로그 (stdout)
└── bot.error.log                   # 에러 로그 (stderr)
```

### 동작 방식

1. 지정된 시각에 `~/claude-study/*.md` 중 랜덤 파일 1개를 선택
2. `claude -p` 로 해당 파일 내용 기반 퀴즈 문제 생성 후 Discord 채널에 전송
3. 사용자가 채널에 답변 입력 시 `claude -p` 로 채점 후 결과 전송

### 출제 시각 (KST)

| 구분 | 시각 |
|------|------|
| 평일 (월~금) | 09:30, 15:00, 19:20, 21:00 |
| 주말 (토~일) | 11:00, 13:10, 15:00, 19:00, 21:00 |

> 시각 변경: `bot.py`의 `WEEKDAY_TIMES`, `WEEKEND_TIMES` 수정 후 봇 재시작

## 환경 세팅
### 1. Discord 봇 생성 (5분)
1. https://discord.com/developers/applications 접속
2. New Application → 이름 입력
3. 좌측 Bot → Add Bot
4. Token 복사 (나중에 필요)
5. Privileged Gateway Intents → MESSAGE CONTENT INTENT 켜기
6. 좌측 OAuth2 → URL Generator → bot 체크 → Permissions: Send Messages, Read Message History → 생성된 URL로 서버에 봇 초대

### 2. 채널 ID 확인
Discord 설정 → 고급 → 개발자 모드 켜기 → 원하는 채널 우클릭 → ID 복사

### 3. 환경 변수 설정
.env 파일에 토큰과 채널 ID 입력

| 변수 | 설명 |
|------|------|
| `DISCORD_TOKEN` | Discord 봇 토큰 |
| `CHANNEL_ID` | 퀴즈를 전송할 채널 ID |

---

## 가상환경

### 활성화

```bash
cd ~/claude-study/discord-quiz-bot
source venv/bin/activate
```

활성화되면 터미널 프롬프트 앞에 `(venv)` 가 표시됨.

### 패키지 설치 (최초 1회)

```bash
pip install -r requirements.txt
```

### 비활성화

```bash
deactivate
```

> LaunchAgents로 실행할 때는 `venv/bin/python`을 직접 지정하므로 별도 활성화 불필요.

---

## 터미널에서 직접 실행 (테스트용)

```bash
cd ~/claude-study/discord-quiz-bot
source venv/bin/activate
python bot.py
```

정상 실행 시 출력:
```
✅ 봇이름#0000 로 접속 완료
```

종료: `Ctrl + C`

---

## LaunchAgents 등록 (백그라운드 상시 실행)

macOS의 LaunchAgents는 사용자 로그인 시 자동으로 프로세스를 시작하고, 종료되면 자동으로 재시작해주는 서비스 관리자.
터미널을 닫아도 봇이 계속 실행됨.

### 등록

```bash
cp ~/claude-study/discord-quiz-bot/com.claude-study.quiz-bot.plist \
   ~/Library/LaunchAgents/

launchctl load ~/Library/LaunchAgents/com.claude-study.quiz-bot.plist
```

### 프로세스 확인

```bash
launchctl list | grep quiz-bot
```

출력 예시:
```
12345  0  com.claude-study.quiz-bot
```
- 첫 번째 숫자: PID (프로세스 ID). `-` 이면 실행 중이 아님
- 두 번째 숫자: 마지막 종료 코드. `0` 이면 정상

### 시작

```bash
launchctl load ~/Library/LaunchAgents/com.claude-study.quiz-bot.plist
```

### 중지

```bash
launchctl unload ~/Library/LaunchAgents/com.claude-study.quiz-bot.plist
```

### 재시작 (코드 변경 후)

```bash
launchctl unload ~/Library/LaunchAgents/com.claude-study.quiz-bot.plist
launchctl load ~/Library/LaunchAgents/com.claude-study.quiz-bot.plist
```

---

## 로그 확인

```bash
# 실행 로그 실시간 확인
tail -f ~/claude-study/discord-quiz-bot/bot.log

# 에러 로그 확인
tail -f ~/claude-study/discord-quiz-bot/bot.error.log
```
