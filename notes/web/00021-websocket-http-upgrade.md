# WebSocket과 HTTP 업그레이드 (101 Switching Protocols)

## 1. WebSocket이란?

WebSocket은 **하나의 TCP 연결 위에서 클라이언트와 서버 간의 양방향(Full-Duplex) 통신**을 가능하게 하는 프로토콜입니다. HTTP와 달리 연결을 유지하면서 서버가 클라이언트에게 먼저 데이터를 보낼 수 있습니다.

- **RFC 6455**로 표준화
- 기본 포트: HTTP와 동일하게 `80` (ws://), `443` (wss://)
- 프로토콜 식별자: `ws://`, `wss://`

---

## 2. HTTP vs WebSocket 비교

| 항목 | HTTP | WebSocket |
|------|------|-----------|
| 통신 방식 | 단방향 (요청-응답) | 양방향 (Full-Duplex) |
| 연결 유지 | 요청마다 연결/해제 (기본) | 연결 유지 (Persistent) |
| 서버 Push | 불가 (Polling 필요) | 가능 |
| 헤더 오버헤드 | 매 요청마다 헤더 포함 | 최초 핸드셰이크 이후 최소화 |
| 실시간성 | 낮음 | 높음 |
| 포트 | 80 (HTTP), 443 (HTTPS) | 80 (ws), 443 (wss) — 같은 포트 공유 |
| 사용 사례 | 일반 웹 페이지 | 채팅, 실시간 알림, 게임 |

> 같은 포트를 공유하기 때문에 방화벽 설정 변경 없이 WebSocket을 쓸 수 있다.
> 이것이 업그레이드 방식을 채택한 주요 이유 중 하나다.

---

## 3. HTTP 업그레이드 과정 (101 Switching Protocols)

### 왜 업그레이드가 필요한가?

WebSocket은 HTTP와 **다른 프로토콜**이다. 브라우저는 기본적으로 HTTP만 말할 수 있으므로, 처음엔 HTTP로 접근한 뒤 "앞으로는 WebSocket으로 통신하자"고 합의하는 과정이 필요하다. 이 합의 과정이 **HTTP 업그레이드**이고, 성공하면 서버가 **101**을 응답한다.

> **101 Switching Protocols** = "요청한 프로토콜로 전환할게요"

### 1단계 — 클라이언트 업그레이드 요청

```http
GET /ws HTTP/1.1
Host: localhost:8080
Upgrade: websocket              ← "WebSocket으로 바꾸고 싶어요"
Connection: Upgrade             ← "이 연결을 업그레이드할게요"
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==   ← 보안 키 (랜덤)
Sec-WebSocket-Version: 13
```

### 2단계 — 서버 101 응답

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket              ← "WebSocket으로 전환 수락"
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=  ← 키 검증값
```

- `101 Switching Protocols`: 프로토콜 전환 성공
- `Sec-WebSocket-Key` / `Sec-WebSocket-Accept`: 핸드셰이크 유효성 검증에 사용

### 3단계 — 이후 WebSocket 프레임으로 통신

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

### HTTP 상태코드와 비교

| 상태코드 | 의미 | 예시 |
|----------|------|------|
| 200 | 성공 | 일반 API 응답 |
| 301 | 영구 이동 | URL 리다이렉트 |
| 404 | 없음 | 잘못된 경로 |
| **101** | **프로토콜 전환** | **WebSocket 업그레이드** |
| 400 | 잘못된 요청 | 업그레이드 헤더 누락 시 |

---

## 4. 데이터 통신 (Frame 기반)

핸드셰이크 이후 TCP 연결이 유지되고, **Frame** 단위로 데이터를 주고받습니다.

```
클라이언트                       서버
    |                             |
    |--- HTTP Upgrade 요청 ------>|
    |<-- 101 Switching Protocols -|
    |                             |
    |<======= WebSocket 연결 ====>|
    |                             |
    |--- 메시지 전송 ------------>|
    |<-- 메시지 수신 -------------|
    |--- 메시지 전송 ------------>|
    |<-- 메시지 수신 -------------|
    |                             |
    |--- 연결 종료 (Close) ------>|
    |<-- 연결 종료 (Close) -------|
```

클라이언트 또는 서버 중 어느 쪽이든 **Close Frame**을 전송하여 연결을 종료할 수 있습니다.

---

## 5. WebSocket Frame 구조

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-------+-+-------------+-------------------------------+
|F|R|R|R| opcode|M| Payload len |    Extended payload length    |
|I|S|S|S|  (4)  |A|     (7)    |             (16/64)           |
|N|V|V|V|       |S|             |   (if payload len==126/127)   |
| |1|2|3|       |K|             |                               |
+-+-+-+-+-------+-+-------------+-------------------------------+
```

| 필드 | 설명 |
|------|------|
| FIN | 마지막 프레임 여부 |
| opcode | 프레임 유형 (0x1: 텍스트, 0x2: 바이너리, 0x8: Close, 0x9: Ping, 0xA: Pong) |
| MASK | 클라이언트→서버 전송 시 반드시 1 (마스킹 필수) |
| Payload len | 페이로드 길이 |

---

## 6. Ping/Pong (연결 유지)

연결이 끊기지 않았는지 확인하기 위해 **Heartbeat** 메커니즘을 사용합니다.

- **Ping**: 서버 또는 클라이언트가 상대방에게 생존 여부 확인
- **Pong**: Ping에 대한 응답
- 일정 시간 내 Pong이 없으면 연결을 종료

---

## 7. 코드 예시

### 클라이언트 (JavaScript)

```javascript
const socket = new WebSocket('wss://example.com/chat');

socket.addEventListener('open', (event) => {
    console.log('WebSocket 연결 성공');
    socket.send('Hello, Server!');
    // new WebSocket() 호출만으로 업그레이드가 자동으로 일어남
    // 101 수신 후 onopen이 실행됨
});

socket.addEventListener('message', (event) => {
    console.log('서버로부터 수신:', event.data);
});

socket.addEventListener('close', (event) => {
    console.log('연결 종료:', event.code, event.reason);
});

socket.addEventListener('error', (event) => {
    console.error('WebSocket 에러:', event);
});

socket.close();
```

개발자 도구 Network 탭: Status **101 Switching Protocols**, Type **websocket**, Messages 탭에서 주고받은 프레임 확인 가능.

### 서버 (Go — upgrader.Upgrade())

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

### 서버 (Java - Spring WebSocket)

```java
@Component
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final List<WebSocketSession> sessions = new CopyOnWriteArrayList<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.add(session);
        System.out.println("연결됨: " + session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();

        // 모든 클라이언트에게 브로드캐스트
        for (WebSocketSession s : sessions) {
            if (s.isOpen()) {
                s.sendMessage(new TextMessage("Echo: " + payload));
            }
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session);
    }
}
```

```java
@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    @Autowired
    private ChatWebSocketHandler chatWebSocketHandler;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(chatWebSocketHandler, "/chat")
                .setAllowedOrigins("*");
    }
}
```

### 서버 (Java - Spring WebSocket + STOMP)

실무에서는 STOMP 프로토콜과 함께 사용하는 경우가 많습니다.

```java
@Configuration
@EnableWebSocketMessageBroker
public class StompWebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        registry.enableSimpleBroker("/topic", "/queue"); // 구독 prefix
        registry.setApplicationDestinationPrefixes("/app"); // 발행 prefix
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")
                .withSockJS(); // SockJS 폴백 지원
    }
}

@Controller
public class ChatController {

    @MessageMapping("/chat.send")          // /app/chat.send 로 수신
    @SendTo("/topic/chat")                 // /topic/chat 구독자에게 전송
    public ChatMessage sendMessage(ChatMessage message) {
        return message;
    }
}
```

---

## 8. SockJS와 STOMP

| 기술 | 역할 |
|------|------|
| **WebSocket** | 기반 프로토콜 |
| **SockJS** | WebSocket을 지원하지 않는 환경에서 폴백 제공 (Long Polling 등) |
| **STOMP** | WebSocket 위에서 동작하는 메시징 프로토콜 (pub/sub 패턴 지원) |

---

## 9. 실무 권장사항

1. **항상 wss:// 사용**: 프로덕션에서는 암호화된 `wss://` 사용. `http://` → `ws://`, `https://` → `wss://`
2. **CheckOrigin 주의**: `return true`로 열어두면 CSRF 취약점 가능. 프로덕션에서는 허용 출처를 명시적으로 검증
   ```go
   CheckOrigin: func(r *http.Request) bool {
       origin := r.Header.Get("Origin")
       return origin == "https://my-domain.com"
   }
   ```
3. **업그레이드 실패 처리**: 클라이언트가 일반 HTTP로 `/ws`에 접근하면 400 응답. 에러 로깅 필수
4. **Nginx 프록시 설정**: Nginx 뒤에 서버가 있다면 업그레이드 헤더를 프록시가 전달하도록 설정 필요
   ```nginx
   proxy_http_version 1.1;
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   ```
5. **재연결 로직**: 네트워크 불안정 시 자동 재연결 구현 (exponential backoff)
6. **STOMP 사용 권장**: 순수 WebSocket보다 STOMP를 사용하면 pub/sub, 구독 관리가 편리
7. **메시지 크기 제한**: 대용량 메시지는 청크(chunk) 단위로 분할 전송
8. **Heartbeat 설정**: 유휴 연결 감지를 위해 Ping/Pong 또는 STOMP heartbeat 설정
9. **Redis Pub/Sub 연동**: 다중 서버 환경에서는 Redis를 메시지 브로커로 사용
