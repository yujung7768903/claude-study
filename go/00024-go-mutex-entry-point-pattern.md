# Go 뮤텍스 Lock 진입점 패턴

## 핵심 개념

여러 메서드 중 하나를 조건에 따라 호출할 때, **조건 체크와 실행은 하나의 Lock 안에서 원자적으로 이루어져야 한다.**
Lock은 내부 메서드가 아닌 **진입점(entry point) 메서드에서만** 잡는 것이 원칙이다.

---

## 왜 진입점에서만 Lock을 잡아야 하는가?

### 문제: 각 메서드에서 Lock을 잡는 경우

```go
// ❌ 잘못된 패턴
func (g *Game) onType2Answer(c *Client, answer string) {
    // Lock 없이 상태 체크
    if g.state != "type2_question" || g.t2RoundDone {
        return
    }
    // ← 여기서 다른 고루틴이 state를 바꿀 수 있음 (TOCTOU 문제)
    if correct {
        g.showType2Correct()   // 내부에서 Lock
    } else {
        g.showType2Wrong()     // 내부에서 Lock
    }
}
```

체크(Time Of Check)와 실행(Time Of Use) 사이에 다른 고루틴이 끼어들어 상태를 바꿀 수 있다.
이를 **TOCTOU(Time-Of-Check-Time-Of-Use) 경쟁 조건**이라 한다.

### 해결: 진입점에서 Lock을 잡는 경우

```go
// ✅ 올바른 패턴
func (g *Game) onType2Answer(c *Client, answer string) {
    g.mu.Lock()
    defer g.mu.Unlock()

    // 체크와 실행이 같은 Lock 안에서 원자적으로 수행됨
    if g.state != "type2_question" || g.t2RoundDone {
        return
    }

    if correct {
        g.showType2Correct(...)   // Lock 없이 호출
    } else if someWrong {
        g.showType2Wrong(...)     // Lock 없이 호출
    } else {
        g.showType2ResultFail()   // Lock 없이 호출
    }
}

// 내부 메서드는 Lock 없이 구현
func (g *Game) showType2Correct(answer string, imageURL string) {
    g.state = "type2_result"
    g.room.broadcastJSON("type2_correct", map[string]interface{}{
        "answer":    answer,
        "image_url": imageURL,
    })
}
```

---

## 예시 상황

### 상황 1: 게임 중복 시작 방지

```go
// ❌ 위험
func handleStartGame(c *Client) {
    if c.room.game != nil {   // Lock 없이 체크
        return
    }
    // ← 두 고루틴이 동시에 여기까지 올 수 있음
    c.room.game = newGame()   // 게임이 두 번 생성될 수 있음
}

// ✅ 안전
func handleStartGame(c *Client) {
    c.room.mu.Lock()
    defer c.room.mu.Unlock()

    if c.room.game != nil {   // Lock 안에서 체크
        return
    }
    c.room.game = newGame()   // 정확히 한 번만 실행 보장
}
```

### 상황 2: 준비 완료 인원 집계 후 다음 단계 진행

```go
// ❌ 위험
func (g *Game) onReadyNext(c *Client) {
    g.t1ReadyPlayers[c.id] = true       // 맵 쓰기 (비보호)
    total := g.room.clientCount()
    if len(g.t1ReadyPlayers) >= total { // 조건 체크 (비보호)
        g.nextType1Round()              // 두 고루틴이 동시에 실행 가능
    }
}

// ✅ 안전
func (g *Game) onReadyNext(c *Client) {
    g.mu.Lock()
    defer g.mu.Unlock()

    g.t1ReadyPlayers[c.id] = true
    total := g.room.clientCount()
    if len(g.t1ReadyPlayers) >= total {
        g.t1ReadyPlayers = make(map[string]bool) // 초기화도 Lock 안에서
        g.nextType1Round()                        // 정확히 한 번만 실행
    }
}
```

### 상황 3: 타이머 콜백에서의 Lock

타이머 콜백은 `time.AfterFunc`에 의해 **새 고루틴**으로 실행되므로, 콜백 자체에서 Lock을 잡아야 한다.

```go
g.resetTimer(type2QTime, func() {
    g.mu.Lock()              // 새 고루틴에서 Lock 획득
    defer g.mu.Unlock()
    if g.state != "type2_question" {
        return               // 이미 다른 고루틴이 상태 변경했을 수 있음
    }
    g.showType2Fail()
})
```

콜백이 실행될 시점에는 이전 Lock이 이미 해제되어 있으므로 데드락이 발생하지 않는다.

---

## 내부 메서드에서 Lock을 잡으면 안 되는 경우

진입점에서 이미 Lock을 잡고 있을 때, 내부 메서드에서 **같은 뮤텍스**를 또 잡으면 데드락이 발생한다.

```go
// ❌ 데드락
func (r *Room) broadcastJSON(...) {
    r.mu.RLock()         // Room 뮤텍스 RLock
    defer r.mu.RUnlock()
    // ...
}

func handleReadyStart(...) {
    room.mu.Lock()           // Room 뮤텍스 Lock
    defer room.mu.Unlock()
    room.broadcastJSON(...)  // 내부에서 같은 뮤텍스 RLock 시도 → 데드락
}

// ✅ 해결: Lock 해제 후 호출
func handleReadyStart(...) {
    room.mu.Lock()
    room.startReadyPlayers[c.id] = true
    readyCount := len(room.startReadyPlayers)
    total := len(room.clients)
    room.mu.Unlock()          // 먼저 해제

    room.broadcastJSON(...)   // 해제 후 호출
}
```

---

## 비교표

| 패턴 | 장점 | 단점 |
|------|------|------|
| **진입점에서 Lock** | 원자성 보장, 데드락 위험 없음 | 진입점 메서드가 Lock 책임 가짐 |
| **내부 메서드에서 Lock** | 각 메서드가 독립적 | TOCTOU 문제, 데드락 위험 |

---

## 실무 권장사항

1. **Lock은 진입점에서만** - 공개 메서드(외부에서 호출되는 메서드)에서 Lock을 잡고, 내부 헬퍼 메서드는 Lock 없이 구현한다.
2. **내부 메서드 네이밍** - Lock 없이 호출되어야 하는 내부 메서드는 `Locked` 접미사를 붙이는 관례도 있다. (예: `playerListLocked()`)
3. **뮤텍스 종류 구분** - 서로 다른 구조체의 뮤텍스(`g.mu`, `r.mu`)는 별개이므로 중첩 사용이 가능하지만, 항상 **일정한 순서**로 잡아야 데드락을 방지할 수 있다.
4. **defer vs 명시적 Unlock** - `broadcastJSON`처럼 Lock 안에서 호출하면 안 되는 함수가 있다면 `defer` 대신 명시적 `Unlock()`을 사용한다.
