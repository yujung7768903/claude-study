# AtomicInteger

## 개념

`java.util.concurrent.atomic.AtomicInteger`는 **멀티스레드 환경에서 int 값을 thread-safe하게 다루기 위한 클래스**다. 내부적으로 CAS(Compare-And-Swap) 연산을 사용하여 `synchronized` 없이도 원자적(atomic) 연산을 보장한다.

## 왜 필요한가

일반 `int`나 `Integer`는 멀티스레드에서 안전하지 않다.

```java
// 위험한 코드 - race condition 발생
private int count = 0;

public void increment() {
    count++; // 읽기 → 증가 → 쓰기, 3단계 연산이라 중간에 다른 스레드가 개입 가능
}
```

`count++`는 단일 연산처럼 보이지만 실제로는:
1. 메모리에서 값 읽기
2. 값 증가
3. 메모리에 쓰기

이 3단계 사이에 다른 스레드가 끼어들면 값이 유실된다.

## 기본 사용법

```java
import java.util.concurrent.atomic.AtomicInteger;

AtomicInteger counter = new AtomicInteger(0);

counter.get();                // 현재 값 조회: 0
counter.set(5);               // 값 설정: 5
counter.incrementAndGet();    // 증가 후 반환: 6 (++i)
counter.getAndIncrement();    // 반환 후 증가: 6 반환, 내부 값은 7 (i++)
counter.decrementAndGet();    // 감소 후 반환: 6 (--i)
counter.getAndDecrement();    // 반환 후 감소: 6 반환, 내부 값은 5 (i--)
counter.addAndGet(10);        // 더한 후 반환: 15
counter.getAndAdd(10);        // 반환 후 더하기: 15 반환, 내부 값은 25
counter.compareAndSet(25, 0); // 현재 값이 25이면 0으로 변경, 성공 시 true
```

## CAS (Compare-And-Swap) 동작 원리

```
1. 메모리에서 현재 값을 읽는다 (expected = 5)
2. 새 값을 계산한다 (new = 6)
3. 메모리의 값이 여전히 expected(5)인지 확인
   → 맞으면: new(6)로 교체 (성공)
   → 다르면: 다시 1번부터 재시도 (다른 스레드가 먼저 변경한 것)
```

이 과정이 CPU 레벨의 단일 명령어(하드웨어 지원)로 수행되므로 lock 없이 빠르다.

## synchronized vs AtomicInteger

```java
// 방법 1: synchronized
private int count = 0;
public synchronized void increment() {
    count++;
}

// 방법 2: AtomicInteger
private AtomicInteger count = new AtomicInteger(0);
public void increment() {
    count.incrementAndGet();
}
```

| 항목 | synchronized | AtomicInteger |
|------|-------------|---------------|
| 방식 | lock 기반 (모니터 획득/해제) | lock-free (CAS 연산) |
| 성능 | 경합(contention)이 많으면 느림 | 경합이 적을 때 빠름 |
| 경합이 심할 때 | 대기 큐에서 순서대로 처리 | CAS 재시도가 반복되어 CPU 낭비 가능 |
| 사용 범위 | 여러 변수를 묶어서 보호 가능 | 단일 변수만 보호 |
| 복잡도 | 블록 전체를 보호 | 개별 연산 단위 |

## 실무 사용 예시

### 1. 카운터

```java
// 동시 요청 수 카운팅
private final AtomicInteger activeRequests = new AtomicInteger(0);

public void handleRequest() {
    activeRequests.incrementAndGet();
    try {
        // 요청 처리
    } finally {
        activeRequests.decrementAndGet();
    }
}
```

### 2. Stream에서 인덱스가 필요할 때

```java
AtomicInteger index = new AtomicInteger(1);
List<RArticleTag> tagList = list.stream()
        .map(tag -> new RArticleTag(tag.getTagId(), rArticle, tag.getTag(), index.getAndIncrement()))
        .collect(Collectors.toList());
```

이 경우 순차 스트림이므로 사실 `AtomicInteger`의 thread-safety가 필요하지는 않지만, **lambda 안에서 외부 변수를 변경해야 할 때** `int`는 effectively final 제약으로 사용할 수 없기 때문에 `AtomicInteger`를 쓴다.

> 참고: `int[] counter = {0}` 배열로 우회하는 방법도 있지만, 의도가 불명확해서 `AtomicInteger`가 더 관용적이다.

### 3. compareAndSet으로 상태 전환

```java
private final AtomicInteger state = new AtomicInteger(0); // 0: 초기, 1: 실행 중, 2: 완료

public boolean start() {
    return state.compareAndSet(0, 1); // 초기 상태일 때만 실행 상태로 전환
}

public void complete() {
    state.set(2);
}
```

## 관련 Atomic 클래스

| 클래스 | 대상 타입 |
|--------|----------|
| `AtomicInteger` | int |
| `AtomicLong` | long |
| `AtomicBoolean` | boolean |
| `AtomicReference<T>` | 객체 참조 |
| `AtomicIntegerArray` | int 배열의 각 원소 |
| `LongAdder` | long (높은 경합 상황에서 AtomicLong보다 빠름) |

## 실무 권장사항

- **단일 변수의 원자적 연산**이 필요하면 `AtomicInteger` 사용
- **여러 변수를 함께 보호**해야 하면 `synchronized` 또는 `Lock` 사용
- **높은 경합 + 카운터** 용도라면 `LongAdder`가 `AtomicLong`보다 성능이 좋음
- **Stream lambda에서 인덱스 카운터**로 쓸 때는 동작하지만, 순차 스트림에서만 사용할 것 (병렬 스트림에서는 순서 보장 안 됨)
