# WebSocket 개념과 통신 과정

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
| 사용 사례 | 일반 웹 페이지 | 채팅, 실시간 알림, 게임 |

---

## 3. WebSocket 통신 과정

### 3-1. 핸드셰이크 (HTTP → WebSocket 업그레이드)

WebSocket은 HTTP 연결로 시작하여 프로토콜을 업그레이드하는 방식으로 연결을 수립합니다.

#### 클라이언트 요청
```http
GET /chat HTTP/1.1
Host: example.com
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

#### 서버 응답
```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

- `101 Switching Protocols`: 프로토콜 전환 성공
- `Sec-WebSocket-Key` / `Sec-WebSocket-Accept`: 핸드셰이크 유효성 검증에 사용

### 3-2. 데이터 통신 (Frame 기반)

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

### 3-3. 연결 종료

클라이언트 또는 서버 중 어느 쪽이든 **Close Frame**을 전송하여 연결을 종료할 수 있습니다.

---

## 4. 코드 예시

### 클라이언트 (JavaScript)

```javascript
const socket = new WebSocket('wss://example.com/chat');

// 연결 성공
socket.addEventListener('open', (event) => {
    console.log('WebSocket 연결 성공');
    socket.send('Hello, Server!');
});

// 메시지 수신
socket.addEventListener('message', (event) => {
    console.log('서버로부터 수신:', event.data);
});

// 연결 종료
socket.addEventListener('close', (event) => {
    console.log('연결 종료:', event.code, event.reason);
});

// 에러 처리
socket.addEventListener('error', (event) => {
    console.error('WebSocket 에러:', event);
});

// 메시지 전송
socket.send('메시지 내용');

// 연결 종료 요청
socket.close();
```

### 서버 (Java - Spring WebSocket)

```java
@Component
public class ChatWebSocketHandler extends TextWebSocketHandler {

    private final List<WebSocketSession> sessions = new CopyOnWriteArrayList<>();

    // 연결 수립
    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.add(session);
        System.out.println("연결됨: " + session.getId());
    }

    // 메시지 수신
    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        System.out.println("수신: " + payload);

        // 모든 클라이언트에게 브로드캐스트
        for (WebSocketSession s : sessions) {
            if (s.isOpen()) {
                s.sendMessage(new TextMessage("Echo: " + payload));
            }
        }
    }

    // 연결 종료
    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session);
        System.out.println("연결 종료: " + session.getId());
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

## 7. SockJS와 STOMP

| 기술 | 역할 |
|------|------|
| **WebSocket** | 기반 프로토콜 |
| **SockJS** | WebSocket을 지원하지 않는 환경에서 폴백 제공 (Long Polling 등) |
| **STOMP** | WebSocket 위에서 동작하는 메시징 프로토콜 (pub/sub 패턴 지원) |

---

## 8. 실무 권장사항

1. **보안**: 반드시 `wss://` (TLS) 사용 — 평문 `ws://`는 운영 환경에서 지양
2. **재연결 로직**: 네트워크 불안정 시 자동 재연결 구현 (exponential backoff)
3. **STOMP 사용 권장**: 순수 WebSocket보다 STOMP를 사용하면 pub/sub, 구독 관리가 편리
4. **메시지 크기 제한**: 대용량 메시지는 청크(chunk) 단위로 분할 전송
5. **연결 수 모니터링**: 서버의 최대 동시 연결 수를 고려한 스케일 아웃 설계
6. **Heartbeat 설정**: 유휴 연결 감지를 위해 Ping/Pong 또는 STOMP heartbeat 설정
7. **Redis Pub/Sub 연동**: 다중 서버 환경에서는 Redis를 메시지 브로커로 사용
