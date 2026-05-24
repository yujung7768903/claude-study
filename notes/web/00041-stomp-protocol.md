# STOMP 프로토콜 (feat. WebSocket)

> 관련 자료: [00027-websocket.md](./00027-websocket.md)

---

## 1. STOMP란?

**STOMP(Simple Text Oriented Messaging Protocol)**는 WebSocket 위에서 동작하는 메시징 서브프로토콜입니다.

WebSocket 자체는 그냥 "파이프"입니다. 데이터를 양방향으로 전송할 수 있지만, **어느 채널로 보낼지**, **구독은 어떻게 할지**, **메시지 타입을 어떻게 구분할지**에 대한 규칙이 없습니다. STOMP는 이 규칙을 정의한 프로토콜입니다.

```
[WebSocket만 사용할 때]
클라이언트 ──── raw 텍스트/바이너리 ────→ 서버
               (라우팅 규칙 없음)

[WebSocket + STOMP 사용할 때]
클라이언트 ──── STOMP Frame ────→ MessageBroker ──→ 구독자들
               (Command + Header + Body 구조)
```

---

## 2. 핵심 개념: SUBSCRIBE / SEND / MESSAGE

### 방향 정리

```
클라이언트 → 서버:   CONNECT, SUBSCRIBE, UNSUBSCRIBE, SEND, DISCONNECT
서버 → 클라이언트:   CONNECTED, MESSAGE, ERROR
```

맞습니다. `SUBSCRIBE`와 `SEND`는 클라이언트가 서버에게 보내는 것이고, `MESSAGE`는 서버가 클라이언트에게 보내는 것입니다.

### SUBSCRIBE — "이 채널 들을게요"

클라이언트가 서버(브로커)에게 **"나는 이 destination의 메시지를 받고 싶다"** 고 등록하는 행위입니다.

```
SUBSCRIBE
id:sub-0
destination:/topic/article/123

^@
```

- 이후 `/topic/article/123` 으로 메시지가 오면 이 클라이언트에게 전달됩니다.
- `id`는 나중에 `UNSUBSCRIBE` 시 사용합니다.
- **데이터를 요청하는 게 아닙니다.** "앞으로 올 메시지를 수신하겠다" 는 등록입니다.

### SEND — "서버에게 메시지 보내요"

클라이언트가 서버로 **데이터를 전송**할 때 사용합니다.

```
SEND
destination:/app/article/123/lock/acquire
content-type:application/json

{"sessionId":"abc-123"}
^@
```

- `/app` prefix가 붙으면 Spring의 `@MessageMapping` 메서드로 라우팅됩니다.
- REST의 `POST /api/...` 와 비슷한 역할입니다.

### MESSAGE — "서버가 클라이언트에게 전달"

서버(브로커)가 구독자들에게 **메시지를 푸시**할 때 사용합니다.

```
MESSAGE
subscription:sub-0
destination:/topic/article/123
content-type:application/json

{"type":"ARTICLE_SAVED","articleId":123}
^@
```

- 클라이언트가 능동적으로 받는 게 아니라 서버가 밀어주는(push) 것입니다.
- `subscription` 헤더로 어떤 SUBSCRIBE에 대한 응답인지 식별합니다.

### 전체 흐름 한눈에 보기

```
클라이언트 A (편집자)              서버                  클라이언트 B (열람자)
      │                             │                           │
      │── SUBSCRIBE ──────────────→ │                           │
      │   /user/queue/article/lock  │ ←── SUBSCRIBE ────────────│
      │                             │     /topic/article/123/lock
      │                             │
      │── SEND ────────────────────→│
      │   /app/article/123/lock/    │
      │   acquire                   │── DB 처리
      │                             │
      │ ←── MESSAGE ────────────────│
      │  /user/queue/article/lock   │── MESSAGE ────────────────→│
      │  { result: OK }             │  /topic/article/123/lock   │
      │                             │  { type: LOCK_ACQUIRED }   │
```

---

## 3. STOMP Frame 구조

STOMP 메시지는 **Frame** 단위로 전송됩니다.

```
COMMAND
header1:value1
header2:value2

Body^@
```

- `COMMAND`: SEND, SUBSCRIBE, UNSUBSCRIBE, CONNECT, DISCONNECT 등
- `Header`: key:value 형식 (HTTP 헤더와 유사)
- `Body`: 실제 메시지 내용 (JSON 등)
- `^@`: NULL 문자 (Frame 종료)

### 주요 Command 목록

| Command | 방향 | 설명 |
|---|---|---|
| `CONNECT` | 클라이언트→서버 | STOMP 세션 수립 요청 |
| `CONNECTED` | 서버→클라이언트 | STOMP 세션 수립 완료 |
| `SUBSCRIBE` | 클라이언트→서버 | 특정 destination 구독 등록 |
| `UNSUBSCRIBE` | 클라이언트→서버 | 구독 해제 |
| `SEND` | 클라이언트→서버 | 서버로 메시지 전송 |
| `MESSAGE` | 서버→클라이언트 | 구독한 destination으로 메시지 푸시 |
| `DISCONNECT` | 클라이언트→서버 | 연결 종료 요청 |
| `ERROR` | 서버→클라이언트 | 에러 발생 알림 |

---

## 4. SUBSCRIBE vs SEND 차이

REST에 비유하면 이해하기 쉽습니다.

| | REST | STOMP |
|---|---|---|
| 데이터 요청 | `GET /api/article/123` | — (WebSocket은 요청 후 단발 응답 방식이 아님) |
| 데이터 전송 | `POST /api/article/123/lock` | `SEND` to `/app/article/123/lock/acquire` |
| 이벤트 수신 등록 | — (REST는 push 없음) | `SUBSCRIBE` to `/topic/article/123` |
| 서버 → 클라이언트 push | — | `MESSAGE` from `/topic/article/123` |

핵심 차이:
- `SEND`는 **내가 서버에 뭔가를 전달**하는 것 (클라이언트가 주도)
- `SUBSCRIBE`는 **앞으로 올 메시지를 받겠다고 등록**하는 것
- `MESSAGE`는 **서버가 나에게 밀어주는** 것 (서버가 주도)

---

## 5. destination prefix 역할

Spring STOMP에서 prefix로 메시지를 라우팅합니다.

```
/app/...    → @MessageMapping 메서드로 전달 (서버 로직 처리)
/topic/...  → 브로커가 구독자 전체에게 브로드캐스트 (1:N)
/queue/...  → 브로커가 특정 사용자에게 전달 (1:1)
/user/...   → 특정 사용자의 /queue 로 변환되어 전달
```

```
SEND /app/article/123/save
  → ArticleController.handleSave() 메서드 호출

SEND /topic/article/123  (직접 브로커에게)
  → /topic/article/123 구독자 전체에게 즉시 전달 (서버 로직 없음)
```

---

## 6. WebSocket vs WebSocket + STOMP

| 항목 | WebSocket 단독 | WebSocket + STOMP |
|---|---|---|
| 메시지 라우팅 | 직접 구현 | destination 기반 자동 라우팅 |
| pub/sub 패턴 | 직접 구현 | 기본 지원 (`/topic`, `/queue`) |
| 구독 관리 | 직접 구현 | SUBSCRIBE/UNSUBSCRIBE로 자동 관리 |
| 메시지 포맷 | 자유 (규칙 없음) | Command + Header + Body 표준 구조 |
| 브로커 연동 | 어려움 | RabbitMQ, ActiveMQ, Redis 등과 연동 용이 |
| 구현 난이도 | 낮음 (단순 연결) | 중간 (설정 필요하지만 기능 풍부) |

---

## 7. Spring Boot에서 STOMP 구현

### 의존성 추가

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-websocket</artifactId>
</dependency>
```

### WebSocket + STOMP 설정

```java
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // 서버 → 클라이언트: 브로드캐스트 prefix
        config.enableSimpleBroker("/topic", "/queue");

        // 클라이언트 → 서버: 메시지 수신 prefix
        config.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // WebSocket 핸드셰이크 endpoint
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")
                .withSockJS(); // WebSocket 미지원 환경을 위한 fallback
    }
}
```

### 메시지 수신 Controller

```java
@Controller
public class ArticleWebSocketController {

    // 클라이언트가 /app/article/save 로 SEND → 처리 후 /topic/article/{id} 로 브로드캐스트
    @MessageMapping("/article/save")
    @SendTo("/topic/article/{articleId}")
    public ArticleWebSocketMessage handleSave(@DestinationVariable Long articleId,
                                              ArticleWebSocketMessage message) {
        return message;
    }

    // 특정 사용자에게만 전송 (1:1)
    @MessageMapping("/article/private")
    @SendToUser("/queue/article")
    public ArticleWebSocketMessage handlePrivate(ArticleWebSocketMessage message,
                                                 Principal principal) {
        return message;
    }
}
```

### 서버에서 직접 메시지 발행

```java
@Service
public class ArticleWebSocketPublisher {

    private final SimpMessagingTemplate messagingTemplate;

    // 브로드캐스트 (해당 기사를 구독한 모든 클라이언트에게)
    public void broadcast(Long articleId, ArticleWebSocketMessage message) {
        messagingTemplate.convertAndSend("/topic/article/" + articleId, message);
    }

    // 특정 사용자에게만 전송
    public void sendToUser(String userId, ArticleWebSocketMessage message) {
        messagingTemplate.convertAndSendToUser(userId, "/queue/article", message);
    }
}
```

---

## 8. 클라이언트 연동 (JavaScript)

```javascript
import SockJS from 'sockjs-client';
import { Client } from '@stomp/stompjs';

const client = new Client({
    webSocketFactory: () => new SockJS('/ws'),

    onConnect: (frame) => {
        // 1. SUBSCRIBE: 서버 → 나에게 오는 메시지 수신 등록
        client.subscribe('/topic/article/123', (message) => {
            // 서버가 MESSAGE frame 을 보낼 때 실행됨
            const body = JSON.parse(message.body);
            console.log('수신:', body);
        });

        // 2. SEND: 내가 서버로 메시지 전송
        client.publish({
            destination: '/app/article/123/lock/acquire',
            body: JSON.stringify({ sessionId: 'abc' }),
        });
    },

    reconnectDelay: 5000,
});

client.activate();
client.deactivate(); // 연결 해제
```

---

## 9. `/topic` vs `/queue` 차이

| 구분 | `/topic` | `/queue` (`/user/queue`) |
|---|---|---|
| 전송 방식 | 1:N (브로드캐스트) | 1:1 (특정 사용자) |
| 사용 시나리오 | 기사 업데이트 알림, 편집 락 상태 | 락 획득 결과, 개인 알림 |
| 예시 | `/topic/article/123` | `/user/queue/article/lock` |

---

## 10. SockJS가 필요한 이유

일부 환경(회사 방화벽, 구형 브라우저, 일부 프록시)에서는 WebSocket을 차단합니다. **SockJS**는 WebSocket이 불가능할 때 자동으로 대안을 사용합니다.

```
WebSocket 연결 시도
    │ 성공 → WebSocket 사용 (ws://)
    │ 실패 → SockJS Fallback 순서대로 시도
              1. WebSocket
              2. XHR Streaming
              3. XHR Polling
              4. iframe 기반 통신
```

---

## 11. 실무 권장사항

1. **순수 WebSocket보다 STOMP를 권장**: pub/sub, 라우팅, 구독 관리가 자동화됨
2. **다중 서버 환경에서는 외부 브로커 연동**: `enableSimpleBroker` 대신 RabbitMQ, Redis를 메시지 브로커로 사용
3. **인증 처리**: `ChannelInterceptor`로 STOMP CONNECT 시 토큰 검증
4. **Heartbeat 설정**: 유휴 연결 감지를 위해 STOMP heartbeat 활성화
   ```java
   config.enableSimpleBroker("/topic")
         .setHeartbeatValue(new long[]{10000, 10000}); // 10초
   ```
5. **에러 처리**: `@MessageExceptionHandler`로 메시지 처리 중 예외를 클라이언트에게 전달
