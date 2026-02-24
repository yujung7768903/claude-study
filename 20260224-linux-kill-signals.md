# 리눅스 kill 명령어와 시그널(Signal) 완벽 가이드

## 개념 설명

### kill 명령어란?

`kill`은 프로세스에 **시그널(Signal)** 을 보내는 명령어입니다.
이름이 "kill"이라서 항상 프로세스를 종료하는 것처럼 보이지만, 실제로는 다양한 시그널을 전달할 수 있습니다.

```bash
kill [옵션] <PID>
kill -<시그널번호> <PID>
kill -<시그널이름> <PID>
```

### 시그널(Signal)이란?

시그널은 프로세스 간 통신(IPC)의 일종으로, 운영체제가 프로세스에게 보내는 **비동기 알림**입니다.
프로세스는 시그널을 받으면 미리 정의된 동작(또는 커스텀 핸들러)을 수행합니다.

---

## 자주 쓰는 시그널: 9 vs 15

### SIGTERM (15) — 정상 종료 요청

```bash
kill -15 <PID>
kill -SIGTERM <PID>
kill <PID>        # 기본값이 15(SIGTERM)
```

| 항목 | 내용 |
|------|------|
| 번호 | 15 |
| 이름 | SIGTERM (Signal Terminate) |
| 의미 | "지금 종료해주세요" 라는 **요청** |
| 프로세스 반응 | 핸들링 가능 → 정리 작업 후 종료 |
| 무시 가능 | 가능 (프로세스가 무시할 수 있음) |
| 기본 동작 | 종료 |

**동작 방식:**
- 프로세스가 시그널을 받고 **스스로 정리(cleanup)** 할 기회를 줌
- 열린 파일 닫기, DB 연결 해제, 임시 파일 삭제 등 graceful shutdown 수행
- 프로세스가 시그널을 무시하거나 처리 중이면 종료되지 않을 수 있음

---

### SIGKILL (9) — 강제 종료

```bash
kill -9 <PID>
kill -SIGKILL <PID>
```

| 항목 | 내용 |
|------|------|
| 번호 | 9 |
| 이름 | SIGKILL (Signal Kill) |
| 의미 | "지금 당장 죽여라" 라는 **명령** |
| 프로세스 반응 | 핸들링 불가 → 커널이 직접 강제 종료 |
| 무시 가능 | 불가능 (커널 수준에서 처리) |
| 기본 동작 | 즉시 종료 |

**동작 방식:**
- 커널이 직접 프로세스를 메모리에서 제거
- 프로세스에게 정리할 기회를 **전혀 주지 않음**
- 데이터 손실, 파일 손상, 좀비 프로세스 발생 가능성 있음

---

## 시그널 비교표

| 번호 | 이름 | 설명 | 핸들링 | 주요 용도 |
|------|------|------|--------|-----------|
| 1 | SIGHUP | 연결 끊김 / 재시작 요청 | 가능 | 설정 파일 재로딩 |
| 2 | SIGINT | 인터럽트 (Ctrl+C) | 가능 | 터미널에서 종료 |
| 3 | SIGQUIT | 종료 + 코어 덤프 | 가능 | 디버깅용 종료 |
| **9** | **SIGKILL** | **강제 종료** | **불가** | **응답 없는 프로세스 강제 제거** |
| 15 | SIGTERM | 정상 종료 요청 | 가능 | 일반적인 종료 요청 |
| 18 | SIGCONT | 일시 정지된 프로세스 재개 | 불가 | fg/bg 재개 |
| 19 | SIGSTOP | 프로세스 일시 정지 | 불가 | 프로세스 중단 |
| 20 | SIGTSTP | 터미널 정지 (Ctrl+Z) | 가능 | 백그라운드로 보내기 |

---

## 전체 시그널 목록 확인

```bash
kill -l        # 전체 시그널 목록 출력
```

```
 1) SIGHUP       2) SIGINT       3) SIGQUIT      4) SIGILL
 5) SIGTRAP      6) SIGABRT      7) SIGBUS        8) SIGFPE
 9) SIGKILL     10) SIGUSR1     11) SIGSEGV      12) SIGUSR2
13) SIGPIPE     14) SIGALRM     15) SIGTERM      ...
```

---

## PID 찾는 방법

```bash
# 프로세스 이름으로 PID 확인
ps aux | grep <프로세스명>

# pidof 사용
pidof nginx

# pgrep 사용
pgrep nginx

# 이름으로 직접 kill (pkill)
pkill nginx          # SIGTERM으로 종료
pkill -9 nginx       # SIGKILL로 강제 종료
```

---

## 코드 예시: Java에서 시그널 핸들링

Java 애플리케이션은 SIGTERM(15)을 받으면 종료 훅(Shutdown Hook)을 실행할 수 있습니다.
SIGKILL(9)은 JVM도 핸들링할 수 없어 바로 종료됩니다.

```java
// SIGTERM 수신 시 실행될 종료 훅 등록
Runtime.getRuntime().addShutdownHook(new Thread(() -> {
    System.out.println("SIGTERM 수신 - 정리 작업 시작");
    // DB 연결 해제, 파일 닫기, 진행 중인 요청 완료 처리 등
    cleanupResources();
    System.out.println("정리 완료 - 종료");
}));
```

```bash
# 정상 종료 시도 (Java 앱에게 정리 기회 부여)
kill -15 <java-pid>

# 응답 없을 때 강제 종료 (정리 훅 실행 안 됨)
kill -9 <java-pid>
```

---

## 실무 권장사항

### 올바른 종료 순서

```
1. kill -15 <PID>   → 정상 종료 시도 (Graceful Shutdown)
2. 몇 초 기다린다   → 프로세스가 정리 중
3. 아직 살아있으면 → kill -9 <PID>  (강제 종료)
```

```bash
# 실무에서 자주 쓰는 패턴
PID=1234
kill -15 $PID
sleep 5
kill -0 $PID 2>/dev/null && kill -9 $PID
# kill -0: 프로세스 존재 여부만 확인 (시그널 전달 안 함)
```

### 언제 어떤 시그널을 쓸까?

| 상황 | 추천 시그널 | 이유 |
|------|-------------|------|
| 일반적인 서비스 종료 | `kill -15` (SIGTERM) | 정리 작업 보장 |
| 응답 없는 프로세스 제거 | `kill -9` (SIGKILL) | 즉시 강제 종료 |
| nginx/apache 설정 재로딩 | `kill -1` (SIGHUP) | 재시작 없이 설정 반영 |
| Ctrl+C 동일 효과 | `kill -2` (SIGINT) | 인터랙티브 종료 |
| 프로세스 일시 중단 | `kill -19` (SIGSTOP) | 디버깅, 리소스 절약 |

### 주의사항

- **`kill -9`는 최후의 수단**으로 사용해야 합니다.
  - 데이터 손실 가능성 (DB 트랜잭션 롤백 안 됨, 파일 미완성 등)
  - 좀비(zombie) 프로세스나 고아(orphan) 프로세스 발생 가능
- Docker 컨테이너도 `docker stop` = SIGTERM, `docker kill` = SIGKILL
- Spring Boot, Tomcat 등 서버 애플리케이션은 SIGTERM으로 graceful shutdown 지원
- 쿠버네티스(K8s)는 파드 종료 시 기본적으로 SIGTERM → 30초 대기 → SIGKILL 순서로 처리

---

## 요약

```
kill -15 (SIGTERM) : "부탁이야, 정리하고 종료해줘" → 프로세스가 선택 가능
kill -9  (SIGKILL) : "지금 당장 죽어!"              → 커널이 강제 실행, 거부 불가
```

> **기억법**: 15는 '부탁', 9는 '명령'
