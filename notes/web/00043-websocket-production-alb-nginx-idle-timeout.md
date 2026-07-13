# WebSocket 프로덕션 운영 — ALB/nginx, 유휴 타임아웃, 종료 코드, raw vs STOMP 선택

> 기초 개념은 다음 자료 참고:
> - [00021-websocket-http-upgrade.md](./00021-websocket-http-upgrade.md) — 핸드셰이크(101), Frame 구조
> - [00041-stomp-protocol.md](./00041-stomp-protocol.md) — STOMP 프레임, destination prefix
>
> 이 문서는 위 기초 위에서, **실제 프로덕션에서 WebSocket을 붙일 때 겪는 문제들**(핸드셰이크 400, 연결이 자꾸 끊김, 비정상 종료 로그)과 **raw WebSocket을 선택한 이유**를 정리한다. 실제 사례: Spring `TextWebSocketHandler`(STOMP 미사용) + RxJS `webSocket` + ALB + nginx + Redis pub/sub 구조.

---

## 1. ALB HTTP/2 와 WebSocket

### 증상
```
DEBUG WebSocketHttpRequestHandler - GET /ws/article/123
ERROR DefaultHandshakeHandler - Handshake failed due to invalid Upgrade header: null
Completed 400 BAD_REQUEST
```

### 원인 이해
WebSocket 핸드셰이크는 **HTTP/1.1의 `Upgrade` 헤더 방식**에 의존한다.
- **HTTP/1.1**: `Connection: Upgrade` + `Upgrade: websocket` 으로 "이 연결을 통째로 WebSocket으로 승격"
- **HTTP/2**: 스트림 멀티플렉싱 구조라 "연결 통째로 승격" 개념이 없고, **`Upgrade`/`Connection` 헤더 자체가 금지**됨

따라서 HTTP/2 구간을 지나면 `Upgrade` 헤더가 사라져 서버에 `null`로 도착 → 400.

### 중요한 반전 — HTTP/2를 켜도 브라우저 WebSocket은 정상
실제로 ALB 속성에서 HTTP/2를 켜둔 채로도 WebSocket이 동작하는 경우가 있다. 이유:

- ALB의 `routing.http2.enabled`는 **일반 HTTP 요청**에 HTTP/2를 쓸지 정하는 것
- **브라우저의 `WebSocket` API는 항상 HTTP/1.1 Upgrade로 별도 연결**을 맺음 (RFC 8441 방식을 사실상 안 씀)
- 즉 ALB HTTP/2 설정과 브라우저 WebSocket 핸드셰이크는 서로 간섭하지 않음

> **교훈**: "ALB는 HTTP/2에서 WebSocket 미지원"이라는 말은 **RFC 8441(WebSocket-over-HTTP/2)** 을 안 한다는 뜻이지, HTTP/2를 켜면 브라우저 WebSocket이 깨진다는 뜻이 아니다. 400의 진짜 원인은 대부분 **다른 곳(아래 nginx)** 에 있다.

### RFC 8441 (WebSocket over HTTP/2) 란
- HTTP/2 **스트림 하나만** WebSocket으로 승격시키는 확장 (2018)
- `Upgrade` 대신 **확장 CONNECT**(`:protocol = websocket`) 사용
- 경로상 모든 참여자(브라우저·LB·서버)가 지원해야 켜지고, **서버가 `SETTINGS_ENABLE_CONNECT_PROTOCOL` 신호**를 보내야 브라우저가 사용
- ALB·대부분 인프라가 미지원 → **현실에선 브라우저가 HTTP/1.1로 폴백** → 신경 쓸 필요 없음

---

## 2. 진짜 범인 — nginx 리버스 프록시의 Upgrade 헤더 누락 ⭐

ALB 뒤 EC2 인스턴스에서 nginx가 80 → 톰캣 8080으로 프록시하는 구조라면, **nginx 기본 설정은 `Upgrade`/`Connection` 헤더를 전달하지 않는다**(hop-by-hop 헤더는 명시적으로 재설정해야 통과). 이게 `Upgrade: null`의 실제 원인인 경우가 많다.

### 문제 있는 설정 (WebSocket 통과 안 됨)
```nginx
location / {
    proxy_pass http://localhost:8080;
    proxy_set_header Host $http_host;
    # Upgrade / Connection 헤더 설정 없음 → WebSocket 핸드셰이크 실패
}
```

### 해결 — `/ws/` 전용 location 추가
```nginx
location /ws/ {
    proxy_pass http://localhost:8080;
    proxy_http_version 1.1;                    # 기본 1.0 → 1.1 필수
    proxy_set_header Upgrade $http_upgrade;    # Upgrade 헤더 전달
    proxy_set_header Connection "upgrade";     # Connection 헤더 전달
    proxy_set_header Host $http_host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 3600s;                  # 유휴 끊김 완화 (아래 4장 참고)
}
```

적용:
```bash
sudo nginx -t          # 문법 검사
sudo nginx -s reload   # 무중단 재적용 (톰캣 재배포 불필요)
```

### 결정적 진단법 — 8080 직접 vs 80 경유 비교
```bash
# 톰캣 직접 → 101 이면 앱은 정상
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZQ==" -H "Sec-WebSocket-Version: 13" \
  http://localhost:8080/ws/article/test

# nginx 경유 → 400 이면 nginx가 Upgrade 를 벗긴 것 확정
curl ... http://localhost:80/ws/article/test
```
**8080=101, 80=400** 이면 → nginx 설정 문제.

---

## 3. 그 외 점검 지점 (Upgrade null 이 계속될 때)

| 위치 | 확인 | 값 |
|---|---|---|
| ALB 리스너 속성 | HTTP/2 | 켜도 무방(1장). 400 원인 아님 |
| **ALB 대상 그룹** | **프로토콜 버전** | **HTTP1** 이어야 함 (HTTP2/gRPC면 Upgrade 벗김) |
| **nginx (인스턴스 내)** | **Upgrade/Connection 전달** | **2장 설정 필수** ← 가장 흔한 원인 |
| ALB 속성 | 잘못된 헤더 필드 삭제 | 끔 |

> **핵심 통찰**: HTTP/2가 관여하는 구간이 두 곳이다 — ① 클라↔ALB(리스너 속성), ② ALB↔백엔드(대상 그룹 프로토콜 버전). 그러나 EC2에 리버스 프록시가 있으면 그 프록시(nginx)가 별도로 Upgrade를 벗길 수 있어, 실제 원인은 인프라 체인을 **한 홉씩** 좁혀야 찾을 수 있다.

---

## 4. 유휴 타임아웃(Idle Timeout) — "누가, 어떻게 판단하나"

### 유휴 판단 주체 — 각 홉이 독립적으로
```
브라우저 ──① ALB ──② nginx ──③ 톰캣
```
- **① 브라우저↔ALB**: ALB **유휴 제한 시간**(예: 80초)
- **② ALB↔nginx**: nginx `proxy_read_timeout`(기본 60초)
- 각 홉이 자기 구간의 데이터 흐름을 독립 감시 → **가장 짧은 타임아웃이 먼저 끊는다**

### 유휴 판단 기준 — "사람이 노는지"가 아니라 "바이트가 흐르는지"
- 그 연결 위로 **어떤 바이트든 오가면(양방향)** 타이머 리셋
- 정해진 시간 동안 **1바이트도 안 흐르면** → 유휴 판정 → 연결 종료
- HTTP 요청 수·사용자 클릭과 무관, **순수하게 해당 TCP 연결의 데이터 유무**만 본다

### 함정 — 사용자가 활발히 편집 중이어도 WebSocket은 "유휴"일 수 있다
- 타이핑/자동저장은 **별도 HTTP 요청**으로 나감 → WebSocket 연결 위엔 안 흐름
- WebSocket 위엔 **오직 서버 push 이벤트**만 흐름
- 다른 사용자가 그 리소스를 안 건드리면 → WebSocket은 조용함 → 유휴로 끊김

> **락 연장(예: modifymode/on, 자동저장)과 WebSocket 연결 유지는 완전히 별개다.** 전자는 별도 HTTP 트래픽이라 WebSocket 유휴 타이머를 리셋하지 않는다.

### 해결 — Heartbeat(주기적 트래픽) 또는 타임아웃 상향
1. **Heartbeat(권장)**: 유휴 한계보다 짧은 주기로 ping을 흘려 타이머를 계속 리셋
2. **타임아웃 상향**: ALB 유휴 제한·nginx `proxy_read_timeout`을 크게. 단, 침묵 시간엔 상한이 없어 **불안정**하고 죽은 연결이 오래 남음

→ **Heartbeat가 정석.** ping이 있으면 타임아웃 값이 뭐든 신경 쓸 필요가 없어진다.

### raw WebSocket용 최소 Heartbeat (프론트, RxJS)
```typescript
// ArticleSocketService.connect() 안 — "뷰"가 아니라 "연결 수명"에 묶는다
public connect(articleId: string): Observable<ArticleWsEvent> {
  this.disconnect();
  this._socket$ = webSocket<ArticleWsEvent>(this._buildUrl(articleId));

  // 30초마다 ping (ALB 80초 유휴보다 짧게). 연결과 함께 시작/종료됨
  timer(30000, 30000).pipe(takeUntil(this._disconnect$))
    .subscribe(() => this._socket$?.next({ type: 'PING' } as any));

  return this._socket$.pipe(
    retryWhen(errors => errors.pipe(delayWhen(() => timer(5000)))),
    takeUntil(this._disconnect$)
  );
}
```
- **서비스(연결)에 넣어야** `disconnect()` 시 자동 정리되고, 어떤 뷰가 쓰든 자동 적용됨
- 서버가 클라 메시지를 처리하지 않으면(예: `handleTextMessage` 미오버라이드) 이 PING은 **조용히 무시**됨 → 백엔드 수정 불필요. 목적(트래픽 흘리기)은 달성
- **단방향(클라→서버)이면 충분** — 어느 방향이든 바이트가 흐르면 유휴 타이머는 리셋된다

---

## 5. 종료 코드 — 1000(정상) vs 1006(비정상)과 EOFException

### 증상 (서버 로그)
```
LoggingWebSocketHandlerDecorator - Transport error in StandardWebSocketSession[...]
java.io.EOFException: null
    at ...WsFrameServer.onDataAvailable
WebSocketHandler - Websocket transport error. sessionId=...
... closed with CloseStatus[code=1006, reason=null]
```

### 의미
WebSocket 종료에는 **Close 프레임 교환(종료 인사)** 이 있다:
1. 한쪽이 Close 프레임 전송(코드 포함, 예: `1000` 정상)
2. 상대가 Close 프레임으로 응답
3. TCP 종료 → 양쪽 다 "의도된 정상 종료"로 인식 → **1000**

**종료 인사 없이** TCP가 그냥 사라지면:
- 상대는 읽다가 **EOF(end of stream)** 를 만남 → `EOFException`
- 라이브러리가 **`1006`(abnormal closure)** 을 부여
- `1006`은 **프레임으로 보낼 수 없는 코드** — "Close 프레임 없이 죽음"을 스스로 판단한 표식

### "감지"와 "정상 종료"는 별개
- 서버는 **모든 종료를 감지**한다: 정상 → `afterConnectionClosed`, 비정상 → `handleTransportError`
- 위 로그가 찍혔다는 것 자체가 **감지가 정상 작동**했다는 증거 (버그 아님)
- `1006`이냐 `1000`이냐는 **상대가 어떻게 끊었느냐**에 달림 — 내가 통제 못 함

### 1006의 원인
| 원인 | 성격 |
|---|---|
| **ALB/nginx 유휴 타임아웃** | 중간 장비가 Close 프레임 없이 TCP만 끊음 → **ping으로 제거 가능** |
| 사용자가 탭 강제 종료/크래시/네트워크 끊김 | 프론트가 `disconnect()` 실행할 틈 없음 → **정상 현상, 무해** |

> **진단 요령**: 1006이 **80초(또는 60초) 주기로 규칙적**이면 유휴 타임아웃 → ping 필요. **불규칙하고 드물면** 사용자 이탈이라 무시.

### 정상 종료 인사 구현 (프론트)
```typescript
disconnect(): void {
  this._disconnect$.next();
  if (this._socket$) {
    this._socket$.complete();   // Close 프레임 전송 → 서버는 1000
    this._socket$ = undefined;
  }
}
// beforeunload 에서도 disconnect() 호출 → 창 닫을 때 정상 인사
```

---

## 6. raw WebSocket vs STOMP — 이 프로젝트에 raw가 적합한 이유

### 개념 차이
- **raw WebSocket** = 뚫린 통로. 무엇을 어떤 형식으로 보낼지 직접 정함
- **STOMP** = raw WebSocket **위에 얹는 메시지 규칙 한 겹**(봉투 형식·구독·ack·heartbeat)

### 연결 방식이 근본적으로 다르다
```
[raw] URL에 대상이 박힘, 연결=구독
  wss://.../ws/article/123  →  이 소켓에서 나오는 것을 바로 수신

[STOMP] 브로커에 연결 후, 이름으로 구독 (한 연결에 여러 구독 가능)
  CONNECT → CONNECTED → SUBSCRIBE /topic/article.123 → MESSAGE ...
```

| | raw WebSocket | STOMP |
|---|---|---|
| 연결 단위 | 대상 1개 = 연결 1개 | 브로커에 연결 1개 |
| 대상 지정 | **URL 경로** | **SUBSCRIBE destination** |
| 연결 vs 구독 | 합쳐짐 | 분리 |
| 여러 대상 | 대상마다 새 연결 | 한 연결로 다중 구독 |
| Heartbeat | 직접 구현 | 내장(자동) |
| 도착 확인/재전송 | 없음 | ack/재전송 지원 |
| 서버 세팅 | 핸들러 하나 | 메시지 브로커 설정 |
| 라이브러리 | 불필요(브라우저 기본) | `@stomp/stompjs` 등 |

### STOMP가 빛나는 상황 (= 이 프로젝트엔 불필요한 것)
- 한 연결에서 **여러 topic 동시 구독** (채팅방+알림+상태)
- **ack/재전송/트랜잭션** 등 메시지 신뢰성 보장
- **topic 수십 개**의 복잡한 라우팅

### 이 프로젝트가 raw로 충분한 근거
1. **화면당 리소스 하나**(`/ws/article/{id}`) → 대상 구분을 **URL이 이미** 해줌. 다중 구독 불필요
2. **이벤트 종류 소수**(예: CONTENT_UPDATED / STATUS_UPDATED) → JSON 하나면 됨
3. **인스턴스 간 전파는 Redis pub/sub이 이미 담당** → STOMP 브로커가 할 일을 다른 게 함
4. **ack/트랜잭션/다중 topic 전부 미사용** → STOMP 기능이 다 놀게 됨
5. 놓친 이벤트는 **새로고침·낙관적 버전 체크(CONTENT_VERSION)** 가 최종 안전장치 → 재전송(ack) 불필요

> **결론**: STOMP의 "heartbeat 자동"은 매력적이나, 그거 하나 얻으려 raw→STOMP로 가면 **프론트+백엔드 전면 재작성 + 외부 브로커 도입**이 딸려온다. heartbeat는 ping 3줄로 끝난다. **필요한 만큼만 쓰는 raw가 이 프로젝트엔 정답.**

---

## 7. 다중 인스턴스 팬아웃 — Redis pub/sub (STOMP 브로커의 대체)

ALB 뒤 인스턴스가 여러 대면 **A(열람자)와 B(수정자)가 서로 다른 인스턴스에 붙는다**. WebSocket 세션은 인스턴스마다 흩어져 있는데 이벤트는 아무 인스턴스에서나 발생하므로, **모든 인스턴스에 뿌리는 중계자**가 필요하다.

### 시퀀스 (raw + Redis)
```
 CLIENT A        SERVER 1          REDIS           SERVER 2        CLIENT B
(열람자)                                                          (수정자)
   │  GET /ws/article/123 (Upgrade)  │                │               │
   │───────────────▶│ 101            │                │               │
   │               │ SUBSCRIBE ktcms:article:event    │               │
   │               │───────────────▶│                │               │
   │               │                │◀───────────────│ SUBSCRIBE      │
   │               │                │                │◀──────────────│ GET /ws (101)
   │               │                │                │               │
   │               │                │                │◀──────────────│ ① 기사 저장(HTTP)
   │               │                │  ② PUBLISH      │               │
   │               │                │◀───────────────│               │
   │               │  ③ 전파(모든 구독 인스턴스)       │               │
   │               │◀───────────────│───────────────▶│               │
   │  ④ push       │                │                │  ④ push       │
   │◀──────────────│ sendToArticle  │                │──────────────▶│
   │  A 수신 ✅     │                │                │  B 수신 ✅     │
```

1. 각 인스턴스가 기동 시 Redis 채널 SUBSCRIBE
2. B의 저장을 받은 인스턴스가 Redis에 PUBLISH
3. Redis가 **구독 중인 모든 인스턴스**에 전파
4. 각 인스턴스가 자기한테 붙은 세션에만 push

> Redis가 없으면 B의 저장을 인스턴스 2만 알고, 인스턴스 1의 A는 못 받는다. **Redis = 인스턴스 경계를 넘겨주는 팬아웃 중계자**이며, 이는 **STOMP 외부 브로커(RabbitMQ/ActiveMQ)와 동일한 역할**이다.

```
STOMP:  인스턴스들 ──▶ [ RabbitMQ 브로커 ] ──▶ 인스턴스들
raw:    인스턴스들 ──▶ [   Redis pub/sub  ] ──▶ 인스턴스들
```

> 참고: STOMP **내장 브로커(`enableSimpleBroker`)** 는 메모리 기반이라 **다중 인스턴스 전파가 안 된다.** 결국 외부 브로커가 필요해지므로, 이미 Redis로 해결한 구조를 STOMP로 바꾸는 것은 인프라 중복이다.

---

## 8. STOMP 프레임과 ack 모드 (참고)

> STOMP를 쓸 경우의 세부. 프레임 기본은 [00041](./00041-stomp-protocol.md) 참고. 여기선 **필수/선택 구분**과 **ack 모드**를 보강한다.

### 클라이언트 프레임 — 필수/선택 구분
| 프레임 | 구분 | 언제 |
|---|---|---|
| **CONNECT** | 필수 | STOMP 세션 시작 (유일한 절대 필수) |
| **SUBSCRIBE** | 조건부 | **받으려면** 필수 |
| **SEND** | 조건부 | **보내려면** 필수 |
| DISCONNECT | 선택(권장) | 정상 종료 인사(없으면 1006) |
| UNSUBSCRIBE | 선택 | 종료 시 자동 정리됨 |
| ACK / NACK | 선택 | **client ack 모드**일 때만 |
| BEGIN / COMMIT / ABORT | 선택 | **트랜잭션** 쓸 때만 |

- `MESSAGE`는 **서버 프레임**(server→client)이라 클라 명령어 목록에 없음. `SEND`(발행)의 반대 방향(배달)이 `MESSAGE`.
- 최소 수신 흐름: `CONNECT → CONNECTED → SUBSCRIBE → (MESSAGE …) → DISCONNECT`

### ack 모드 — "메시지를 언제 '받았다'고 인정할지"
SUBSCRIBE 시 `ack` 헤더로 지정한다.

| 모드 | 인정 시점 | 재전송 | 비유 |
|---|---|---|---|
| **auto** (기본) | 서버가 **보내는 순간** | 없음 | 문 앞에 놓고 감(일반 우편) |
| **client** | 클라 **ACK** 받아야, **누적**(N 확인 = 이전 전부) | ACK 없으면 재전송 | 서명받는 등기 |
| **client-individual** | client와 같지만 **개별** 확인 | ACK 없는 것만 | 물건별 개별 서명 |

- **auto** → 클라는 ACK를 아예 안 보냄(대부분의 실시간 알림에 충분)
- **client / client-individual** → 결제·주문 큐처럼 "한 건도 놓치면 안 되는" 경우에만. ACK(처리 완료)/NACK(처리 실패) 전송

---

## 9. 실무 체크리스트

**핸드셰이크가 400일 때 (Upgrade null)**
1. nginx 등 **리버스 프록시의 Upgrade/Connection 헤더 전달** 확인 ← 가장 흔함
2. ALB **대상 그룹 프로토콜 버전 = HTTP1** 확인
3. `curl`로 8080 직접 vs 80 경유 비교해 홉을 좁힘
4. ALB HTTP/2 리스너 속성은 **대개 원인 아님** (브라우저가 HTTP/1.1로 핸드셰이크)

**연결이 자꾸 끊길 때 (1006 반복)**
5. 끊김 간격이 **유휴 한계와 일치**하면 유휴 타임아웃 → **Heartbeat(ping) 추가**
6. ping은 **연결 서비스**에 넣어 연결 수명에 묶기 (뷰에 넣지 말 것)
7. `proxy_read_timeout`·ALB 유휴 제한 상향은 보조책일 뿐, 근본 해결은 ping
8. 락 연장 트래픽(HTTP)은 WebSocket 유휴를 리셋하지 않음을 유의

**구조 선택**
9. 단순 실시간(리소스당 이벤트 몇 개) → **raw WebSocket + URL 라우팅**으로 충분
10. 다중 인스턴스 팬아웃은 **Redis pub/sub**으로 (STOMP 외부 브로커 대체)
11. 놓친 이벤트를 재요청·버전 체크로 복구할 수 있으면 **ack/재전송(STOMP) 불필요**
