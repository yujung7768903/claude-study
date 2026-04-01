# HTTP 101 Switching Protocols — WebSocket 업그레이드

## 개념 설명

### 왜 업그레이드가 필요한가?

WebSocket은 HTTP와 **다른 프로토콜**이다.
브라우저는 기본적으로 HTTP만 말할 수 있으므로, 처음엔 HTTP로 접근한 뒤
"앞으로는 WebSocket으로 통신하자"고 합의하는 과정이 필요하다.
이 합의 과정이 **HTTP 업그레이드**이고, 성공하면 서버가 **101**을 응답한다.

> **101 Switching Protocols** = "요청한 프로토콜로 전환할게요"

---

## 업그레이드 과정 상세

### 1단계 — 브라우저가 업그레이드 요청

```http
GET /ws HTTP/1.1
Host: localhost:8080
Upgrade: websocket              ← "WebSocket으로 바꾸고 싶어요"
Connection: Upgrade             ← "이 연결을 업그레이드할게요"
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==   ← 보안 키 (랜덤)
Sec-WebSocket-Version: 13
```

### 2단계 — 서버가 101로 수락

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket              ← "WebSocket으로 전환 수락"
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=  ← 키 검증값
```

### 3단계 — 이후 WebSocket 프레임으로 통신

```
이전: HTTP 텍스트 요청/응답
이후: WebSocket 바이너리 프레임 (양방향, 연결 유지)
```

---

## 전체 흐름 다이어그램

```
브라우저                                서버
   |                                      |
   |── GET /ws (HTTP 업그레이드 요청) ───▶|
   |                                      |  upgrader.Upgrade() 호출
   |◀── 101 Switching Protocols ─────────|
   |                                      |
   |======= WebSocket 연결 수립 ==========|
   |                                      |
   |── { type: "join_room", ... } (WS) ─▶|
   |◀── { type: "player_joined", ... } ──|
   |◀── { type: "game_started", ... } ───|  서버가 먼저 보낼 수도 있음
   |                                      |
   |  (연결은 브라우저를 닫을 때까지 유지)  |
```

---

## HTTP 상태코드와 비교

| 상태코드 | 의미 | 예시 |
|----------|------|------|
| 200 | 성공 | 일반 API 응답 |
| 301 | 영구 이동 | URL 리다이렉트 |
| 404 | 없음 | 잘못된 경로 |
| **101** | **프로토콜 전환** | **WebSocket 업그레이드** |
| 400 | 잘못된 요청 | 업그레이드 헤더 누락 시 |

---

## Go 코드에서의 처리 (client.go)

```go
var upgrader = websocket.Upgrader{
    ReadBufferSize:  1024,
    WriteBufferSize: 1024,
    CheckOrigin: func(r *http.Request) bool { return true },
    //           └─ CORS 검증. true = 모든 출처 허용
}

func serveWs(hub *Hub, w http.ResponseWriter, r *http.Request) {
    // 이 한 줄이 101 응답 + WebSocket 핸드셰이크를 모두 처리
    conn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
        log.Println("WebSocket upgrade error:", err)
        return
        // 업그레이드 실패 시 자동으로 400 Bad Request 응답
    }
    // 여기서부터 conn은 HTTP가 아닌 WebSocket 연결
}
```

`upgrader.Upgrade()` 내부에서 하는 일:
1. 요청 헤더 검증 (`Upgrade: websocket` 있는지 확인)
2. `Sec-WebSocket-Key`로 `Sec-WebSocket-Accept` 계산
3. HTTP 101 응답 전송
4. WebSocket `Conn` 객체 반환

---

## 브라우저 JavaScript에서의 처리

```js
// new WebSocket()만 호출하면 업그레이드가 자동으로 일어남
const ws = new WebSocket('ws://localhost:8080/ws');

ws.onopen = () => {
    // 101 수신 후 여기가 실행됨 (WebSocket 연결 완료)
    console.log('연결됨');
    ws.send(JSON.stringify({ type: 'join_room', data: { ... } }));
};
```

개발자 도구 Network 탭에서 확인하면:
- Status: **101 Switching Protocols**
- Type: **websocket**
- Messages 탭에서 주고받은 프레임 확인 가능

---

## HTTP vs WebSocket 프로토콜 비교

| | HTTP/1.1 | WebSocket |
|--|----------|-----------|
| 연결 | 요청마다 새로 (또는 Keep-Alive) | 한 번 연결 후 계속 유지 |
| 방향 | 단방향 (클라이언트 요청 → 서버 응답) | 양방향 (서버가 먼저 보낼 수 있음) |
| 오버헤드 | 매 요청마다 헤더 전송 | 첫 연결만 헤더, 이후 프레임 단위 |
| 포트 | 80 (HTTP), 443 (HTTPS) | 80 (ws), 443 (wss) — 같은 포트 공유 |
| 시작 방법 | 바로 사용 | HTTP 업그레이드(101) 필요 |

> 같은 포트를 공유하기 때문에 방화벽 설정 변경 없이 WebSocket을 쓸 수 있다.
> 이것이 업그레이드 방식을 채택한 주요 이유 중 하나다.

---

## 실무 권장사항

- **항상 wss:// 사용**: 프로덕션에서는 암호화된 `wss://`(WebSocket Secure) 사용. `http://` → `ws://`, `https://` → `wss://`
- **CheckOrigin 주의**: `return true`로 열어두면 CSRF 취약점 가능. 프로덕션에서는 허용할 출처를 명시적으로 검증
  ```go
  CheckOrigin: func(r *http.Request) bool {
      origin := r.Header.Get("Origin")
      return origin == "https://my-domain.com"
  }
  ```
- **업그레이드 실패 처리**: 클라이언트가 일반 HTTP로 `/ws`에 접근하면 400 응답. 에러 로깅 필수
- **Nginx 프록시 설정**: Nginx 뒤에 Go 서버가 있다면 업그레이드 헤더를 프록시가 전달하도록 설정 필요
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```
