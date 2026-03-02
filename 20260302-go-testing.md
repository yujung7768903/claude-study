# Go 테스트 방법

## 기본 구조

테스트 파일명은 반드시 `_test.go`로 끝나야 하고, 같은 패키지에 위치한다.

```go
// room_test.go
package main

import "testing"

func TestFunctionName(t *testing.T) {
    // 테스트 코드
}
```

**규칙**
- 함수명은 반드시 `Test`로 시작
- 인자는 반드시 `*testing.T`
- 파일명은 `_test.go`로 끝남

---

## 실행 명령어

```bash
# 현재 패키지 테스트
go test .

# 모든 패키지 테스트 (재귀)
go test ./...

# 특정 테스트만 실행 (-run은 정규식)
go test -run TestCreateRoom

# 상세 출력
go test -v ./...

# 레이스 컨디션 감지 (동시성 코드 필수)
go test -race ./...

# 타임아웃 지정 (데드락 방지)
go test -race -timeout 10s ./...

# 커버리지 측정
go test -cover ./...

# 커버리지 HTML 리포트 생성
go test -coverprofile=coverage.out ./...
go tool cover -html=coverage.out
```

---

## 테스트 실패 처리

| 함수 | 동작 |
|---|---|
| `t.Errorf("msg")` | 실패 기록, 테스트 계속 진행 |
| `t.Fatalf("msg")` | 실패 기록 후 즉시 종료 |
| `t.Logf("msg")` | 로그 출력 (-v 옵션 시 표시) |
| `t.Helper()` | 헬퍼 함수임을 선언 (에러 위치를 호출 측으로 표시) |

```go
func TestValidRanking(t *testing.T) {
    result := validRanking([]int{1, 2, 3, 4})
    if !result {
        t.Errorf("expected true, got false")  // 실패해도 계속 진행
    }

    result2 := validRanking([]int{1, 1, 3, 4})
    if result2 {
        t.Fatalf("expected false, got true")  // 실패 시 즉시 종료
    }
}
```

---

## 테이블 드리븐 테스트 (Table-Driven Test)

Go에서 가장 권장하는 패턴. 입력/기대값을 테이블로 정의하고 반복한다.

```go
func TestValidRanking(t *testing.T) {
    tests := []struct {
        name    string
        input   []int
        want    bool
    }{
        {"정상 입력",          []int{1, 2, 3, 4}, true},
        {"역순도 정상",        []int{4, 3, 2, 1}, true},
        {"길이 부족",          []int{1, 2, 3},    false},
        {"중복 포함",          []int{1, 1, 3, 4}, false},
        {"범위 초과",          []int{1, 2, 3, 5}, false},
        {"빈 슬라이스",        []int{},            false},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got := validRanking(tt.input)
            if got != tt.want {
                t.Errorf("validRanking(%v) = %v, want %v", tt.input, got, tt.want)
            }
        })
    }
}
```

`t.Run()`으로 서브테스트를 만들면:
- 특정 케이스만 실행 가능: `go test -run TestValidRanking/중복_포함`
- 각 케이스의 실패가 독립적으로 보고됨

---

## 동시성 테스트 (-race)

`-race` 플래그를 붙이면 Go 런타임이 고루틴 간 데이터 경쟁을 감지한다.

```go
func TestConcurrentRegister(t *testing.T) {
    hub := newHub()
    room := hub.createRoom()
    go room.run()

    var wg sync.WaitGroup
    for i := 0; i < 10; i++ {
        wg.Add(1)
        go func(i int) {
            defer wg.Done()
            c := &Client{
                id:   fmt.Sprintf("client-%d", i),
                send: make(chan []byte, 256),
            }
            room.register <- c
        }(i)
    }
    wg.Wait()

    // 잠시 후 clientCount 확인 (register 채널 처리 대기)
    time.Sleep(10 * time.Millisecond)
    if room.clientCount() != 10 {
        t.Errorf("expected 10 clients, got %d", room.clientCount())
    }
}
```

```bash
go test -race ./...
# DATA RACE 감지 시 상세 스택 트레이스 출력됨
```

---

## 데드락 테스트

데드락 발생 시 테스트가 영원히 hang되므로, `-timeout`으로 방어한다.

```go
func TestNoDeadlockOnUnregisterDuringBroadcast(t *testing.T) {
    hub := newHub()
    room := hub.createRoom()
    go room.run()

    // 클라이언트 등록
    c1 := &Client{id: "c1", send: make(chan []byte, 256)}
    c2 := &Client{id: "c2", send: make(chan []byte, 256)}
    room.register <- c1
    room.register <- c2
    time.Sleep(5 * time.Millisecond)

    // 동시에: unregister + broadcastJSON
    var wg sync.WaitGroup
    wg.Add(2)
    go func() {
        defer wg.Done()
        room.unregister <- c1
    }()
    go func() {
        defer wg.Done()
        room.broadcastJSON("test", map[string]interface{}{"msg": "hello"})
    }()

    // 데드락이 없다면 완료됨
    done := make(chan struct{})
    go func() {
        wg.Wait()
        close(done)
    }()

    select {
    case <-done:
        // 정상 완료
    case <-time.After(3 * time.Second):
        t.Fatal("데드락 발생 의심: 3초 내에 완료되지 않음")
    }
}
```

```bash
# timeout 지정으로 hang 방지
go test -race -timeout 10s ./...
```

---

## 락 순서 규칙과 데드락

이 프로젝트의 락은 두 개다.

```
g.mu  (Game의 sync.Mutex)
r.mu  (Room의 sync.RWMutex)
```

**반드시 지켜야 할 락 획득 순서:**

```
항상: g.mu → r.mu (RLock)
절대 금지: r.mu → g.mu
```

위 순서가 역전되면 데드락 발생:

```
고루틴 A: g.mu 보유 → r.mu.RLock() 대기 중
고루틴 B: r.mu.Lock() 보유 → g.mu 획득 시도
→ A는 B를 기다리고, B는 A를 기다리는 상태
```

테스트 시 `-race`와 `-timeout`으로 이를 조기 발견할 수 있다.

---

## setup / teardown

`TestMain`을 사용하면 전체 테스트 전후에 공통 설정을 처리할 수 있다.

```go
func TestMain(m *testing.M) {
    // 전체 테스트 전 setup
    fmt.Println("테스트 시작")

    code := m.Run()  // 테스트 실행

    // 전체 테스트 후 teardown
    fmt.Println("테스트 종료")
    os.Exit(code)
}
```

서브테스트 단위 setup/teardown은 헬퍼 함수로 처리한다.

```go
func setupRoom(t *testing.T) (*Hub, *Room) {
    t.Helper()  // 에러 발생 위치를 호출 측으로 표시
    hub := newHub()
    room := hub.createRoom()
    go room.run()
    return hub, room
}

func TestSomething(t *testing.T) {
    _, room := setupRoom(t)
    // ...
}
```

---

## 실무 권장사항

- **`-race`는 항상 붙여서 실행**: 동시성 코드에서 race condition은 재현이 어려워 테스트에서만 잡을 수 있다
- **`-timeout` 지정**: 데드락 발생 시 CI가 멈추는 것을 방지
- **테이블 드리븐 테스트 우선**: 케이스 추가가 쉽고 가독성이 좋다
- **`t.Helper()` 습관화**: 헬퍼 함수에서 에러 위치가 정확하게 표시됨
- **테스트 파일에 외부 의존성 최소화**: 실제 WebSocket 연결 대신 채널/구조체만으로 테스트 가능하게 설계
- **커버리지 80% 이상 목표**: `go test -cover`로 측정

```bash
# CI에서 권장하는 실행 명령
go test -race -timeout 30s -cover ./...
```
