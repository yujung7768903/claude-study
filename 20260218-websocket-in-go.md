# Go에서 WebSocket 동작 방식 (young-seok-quiz 프로젝트 기준)

## 개념 설명

WebSocket은 HTTP와 달리 한 번 연결되면 **양방향 통신을 지속적으로 유지**하는 프로토콜이다.
HTTP는 요청-응답 후 연결이 끊기지만, WebSocket은 서버가 클라이언트에게 **먼저 메시지를 보낼 수 있다.**
실시간 채팅, 멀티플레이어 게임 등에 활용된다.

---

## 1. 연결 수립 (HTTP → WebSocket 업그레이드)

브라우저가 처음엔 일반 HTTP 요청을 보내고, 서버가 이를 WebSocket으로 업그레이드한다.

```
브라우저                          Go 서버
   |                                |
   |--- HTTP GET /ws -------------▶|  일반 HTTP 요청으로 시작
   |◀-- 101 Switching Protocols ---|  WebSocket으로 업그레이드
   |========= WS 연결 유지 =========|  이후 계속 열려있음
```

**Go 코드 (client.go):**
```go
var upgrader = websocket.Upgrader{
    ReadBufferSize:  1024,
    WriteBufferSize: 1024,
    CheckOrigin: func(r *http.Request) bool { return true },
}

func serveWs(hub *Hub, w http.ResponseWriter, r *http.Request) {
    conn, err := upgrader.Upgrade(w, r, nil)  // HTTP → WebSocket 업그레이드
    // ...
}
```

**프론트엔드 (app.js):**
```js
const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
ws = new WebSocket(`${protocol}//${location.host}/ws`);
```

---

## 2. 연결 후 구조 — 고루틴 2개

연결이 성립되면 클라이언트마다 **고루틴 2개**가 생성된다.
Go는 고루틴이 가볍기 때문에 클라이언트 수만큼 고루틴을 띄워도 부담이 없다.

```go
func serveWs(hub *Hub, w http.ResponseWriter, r *http.Request) {
    // ...
    go c.writePump()  // 서버 → 브라우저 전송 전담
    go c.readPump()   // 브라우저 → 서버 수신 전담
}
```

| 고루틴 | 방향 | 역할 |
|--------|------|------|
| `readPump` | 브라우저 → 서버 | 메시지 수신 후 핸들러 호출 |
| `writePump` | 서버 → 브라우저 | `send` 채널에서 꺼내 전송 |

**readPump — 수신:**
```go
func (c *Client) readPump(hub *Hub) {
    defer func() {
        c.room.unregister <- c  // 연결 끊기면 방에서 제거
        c.conn.Close()
    }()
    for {
        _, msg, err := c.conn.ReadMessage()
        if err != nil { break }
        handleMessage(hub, c, msg)  // 메시지 종류별 처리
    }
}
```

**writePump — 송신:**
```go
func (c *Client) writePump() {
    for {
        select {
        case message := <-c.send:       // send 채널에서 꺼내서
            c.conn.WriteMessage(...)     // 브라우저로 전송
        case <-ticker.C:
            c.conn.WriteMessage(websocket.PingMessage, nil)  // 연결 유지용 핑
        }
    }
}
```

---

## 3. 메시지 형식 — JSON type/data 구조

모든 메시지는 `type`과 `data`를 가진 JSON이다.

```json
// 브라우저 → 서버
{ "type": "join_room", "data": { "room_id": "ABC123", "nickname": "영석" } }
{ "type": "type2_submit_answer", "data": { "answer": "김연아" } }

// 서버 → 브라우저
{ "type": "player_joined", "data": { "players": [...] } }
{ "type": "type2_correct", "data": { "winner_nickname": "지수", "answer": "김연아" } }
```

**서버 메시지 라우팅 (client.go):**
```go
func handleMessage(hub *Hub, c *Client, m InMsg) {
    switch m.Type {
    case "create_room":         handleCreateRoom(hub, c, m.Data)
    case "join_room":           handleJoinRoom(hub, c, m.Data)
    case "type2_submit_answer": handleType2SubmitAnswer(c, m.Data)
    // ...
    }
}
```

---

## 4. 방(Room) 격리 구조

Hub가 모든 Room을 관리하고, 브로드캐스트는 **같은 방 안에서만** 이루어진다.

```
Hub (전체 관리자)
├── Room ABC123
│   ├── Client (영석)  ─ send channel [256]
│   ├── Client (민준)  ─ send channel [256]
│   └── Client (지수)  ─ send channel [256]
└── Room XYZ789
    ├── Client (하은)  ─ send channel [256]
    └── Client (태양)  ─ send channel [256]
```

**broadcastJSON — 같은 방 전체에 전송 (room.go):**
```go
func (r *Room) broadcastJSON(msgType string, data interface{}) {
    b := mustMarshal(msgType, data)
    r.mu.RLock()
    defer r.mu.RUnlock()
    for _, c := range r.clients {    // 같은 방 클라이언트에만
        safeSend(c.send, b)          // 각자의 send 채널에 넣기
    }
}
```

---

## 5. send 채널의 역할

`send`는 **게임 로직과 writePump 사이의 버퍼 채널**이다.
게임 로직은 채널에 메시지를 넣기만 하고, writePump가 꺼내서 전송한다.
이 덕분에 게임 로직이 WebSocket 전송을 기다리지 않아도 된다.

```
게임 로직 (game.go)
    │  broadcastJSON("type2_correct", data)
    ▼
send channel [버퍼 256]  ◀── 논블로킹으로 넣음
    │
    ▼
writePump (고루틴)  ──▶  브라우저로 전송
```

```go
func safeSend(ch chan []byte, data []byte) {
    defer func() { recover() }()
    select {
    case ch <- data:  // 버퍼에 넣기
    default:          // 버퍼가 꽉 차면 버림 (드랍)
    }
}
```

---

## 6. 전체 흐름 예시 — 정답 맞혔을 때

```
지수 브라우저          Go 서버 (game.go)        영석·민준 브라우저
     |                      |                          |
     |-- type2_submit_answer▶|                          |
     |                      | 정답 확인                 |
     |                      | broadcastJSON()           |
     |◀─ type2_correct ─────|──── type2_correct ───────▶|
     | (화면 업데이트)        |               (화면 업데이트)
```

**서버 코드 (game.go):**
```go
func (g *Game) onType2Answer(c *Client, answer string) {
    if normalizeAnswer(answer) == normalizeAnswer(q.Answer) {
        g.room.broadcastJSON("type2_correct", map[string]interface{}{
            "winner_nickname": c.nickname,
            "answer":          q.Answer,
            "image_url":       q.ImageURL,
        })
    }
}
```

---

## 비교 — HTTP vs WebSocket

| | HTTP | WebSocket |
|--|------|-----------|
| 연결 방식 | 요청마다 새 연결 | 한 번 연결 후 유지 |
| 방향 | 단방향 (요청→응답) | 양방향 |
| 서버 → 클라이언트 먼저 보내기 | 불가 | 가능 |
| 용도 | 일반 API | 실시간 (채팅, 게임) |
| Go 라이브러리 | `net/http` | `gorilla/websocket` |

---

## 실무 권장사항

- **Ping/Pong 유지**: 유휴 연결이 끊기지 않도록 주기적으로 Ping을 보낸다 (`pingPeriod = 54초`)
- **send 채널 버퍼**: 버퍼가 꽉 차면 메시지가 드랍된다. 버퍼 크기(256)는 서비스 규모에 맞게 조정
- **고루틴 정리**: `readPump`가 종료될 때 `defer`로 반드시 `unregister`와 `conn.Close()` 호출
- **뮤텍스 주의**: `room.clients` 맵은 여러 고루틴이 동시에 접근하므로 `sync.RWMutex`로 보호
- **채널 닫힘 패닉**: 닫힌 채널에 쓰면 패닉 발생 → `recover()`로 방어 (`safeSend` 참고)
