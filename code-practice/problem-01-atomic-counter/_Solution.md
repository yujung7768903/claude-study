# 정답 및 해설

⚠️ **먼저 스스로 문제를 풀어보세요!** 막혔을 때만 이 파일을 참고하세요.

---

## UnsafeCounter 정답

```java
public class UnsafeCounter implements Counter {
    private int count = 0;

    @Override
    public void increment() {
        count++;
    }

    @Override
    public int getCount() {
        return count;
    }

    @Override
    public void reset() {
        count = 0;
    }
}
```

### 해설
- 가장 단순한 구현이지만 **thread-unsafe**
- `count++`는 실제로 3단계 연산:
  1. 메모리에서 값 읽기
  2. 값 증가
  3. 메모리에 쓰기
- 멀티스레드 환경에서 이 3단계 사이에 다른 스레드가 끼어들면 **race condition** 발생
- 결과적으로 일부 증가 연산이 유실됨

---

## SynchronizedCounter 정답

```java
public class SynchronizedCounter implements Counter {
    private int count = 0;

    @Override
    public synchronized void increment() {
        count++;
    }

    @Override
    public synchronized int getCount() {
        return count;
    }

    @Override
    public synchronized void reset() {
        count = 0;
    }
}
```

### 해설
- `synchronized` 키워드로 메서드 전체를 동기화
- 한 번에 하나의 스레드만 메서드 실행 가능 (mutual exclusion)
- **장점**: 구현이 간단하고 안전
- **단점**: lock 획득/해제 오버헤드가 있어 상대적으로 느림
- **주의**: `getCount()`와 `reset()`도 동기화해야 일관성 보장

---

## AtomicCounter 정답

```java
import java.util.concurrent.atomic.AtomicInteger;

public class AtomicCounter implements Counter {
    private AtomicInteger count = new AtomicInteger(0);

    @Override
    public void increment() {
        count.incrementAndGet();
        // 또는 count.getAndIncrement();
    }

    @Override
    public int getCount() {
        return count.get();
    }

    @Override
    public void reset() {
        count.set(0);
    }
}
```

### 해설
- `AtomicInteger`는 CAS(Compare-And-Swap) 연산으로 lock 없이 thread-safe
- **CAS 동작 원리**:
  1. 현재 값 읽기 (expected)
  2. 새 값 계산 (new)
  3. 메모리 값이 여전히 expected면 new로 교체
  4. 아니면 1번부터 재시도
- **장점**: lock이 없어서 빠름 (lock-free)
- **단점**: 경합이 심하면 재시도가 많아져 CPU 낭비 가능

### incrementAndGet() vs getAndIncrement()
```java
count.incrementAndGet();  // 증가 후 반환 (++i)
count.getAndIncrement();  // 반환 후 증가 (i++)
```
- 이 문제에서는 반환값을 사용하지 않으므로 둘 다 동일

---

## 성능 비교 결과 해석

```
SynchronizedCounter: 523ms
AtomicCounter: 287ms
→ AtomicCounter가 약 1.8배 빠름
```

### 왜 AtomicInteger가 더 빠를까?

**SynchronizedCounter**:
- 모니터 lock 획득/해제 오버헤드
- 스레드가 lock을 기다리는 시간 (blocking)
- 컨텍스트 스위칭 비용

**AtomicCounter**:
- CPU의 단일 명령어로 처리 (하드웨어 지원)
- 대기 없이 계속 시도 (non-blocking)
- lock 오버헤드 없음

### 언제 AtomicInteger를 쓸까?
- ✅ 단일 변수의 원자적 연산 (카운터, 플래그)
- ✅ 경합이 적거나 중간 정도인 경우
- ✅ 빠른 응답이 중요한 경우

### 언제 synchronized를 쓸까?
- ✅ 여러 변수를 묶어서 보호해야 할 때
- ✅ 복잡한 비즈니스 로직이 있을 때
- ✅ 경합이 매우 심한 경우 (차라리 순차 처리가 나음)

---

## 추가 도전 과제 힌트

### 1. incrementBy(int delta) 구현
```java
// AtomicCounter에 추가
public void incrementBy(int delta) {
    count.addAndGet(delta);
}
```

### 2. decrementAndGet() 구현
```java
public int decrementAndGet() {
    return count.decrementAndGet();
}
```

### 3. compareAndSet() 구현
```java
public boolean compareAndSet(int expect, int update) {
    return count.compareAndSet(expect, update);
}

// 사용 예
if (counter.compareAndSet(10, 0)) {
    System.out.println("10이었을 때만 0으로 변경 성공!");
}
```

---

## 더 알아보기

### volatile은 왜 안 될까?
```java
private volatile int count = 0;  // thread-safe 아님!

public void increment() {
    count++;  // 여전히 race condition 발생
}
```
- `volatile`은 가시성(visibility)만 보장
- `count++`는 여전히 읽기-증가-쓰기 3단계이므로 atomic 아님
- **atomic 연산**과 **가시성**은 다른 개념!

### LongAdder는 뭐가 다를까?
```java
LongAdder adder = new LongAdder();
adder.increment();
long sum = adder.sum();
```
- 높은 경합 상황에서 `AtomicLong`보다 훨씬 빠름
- 내부적으로 여러 셀(cell)에 분산 저장
- 쓰기가 많고 읽기가 적을 때 유리
- 대신 `sum()` 호출 시 모든 셀을 합산해야 해서 약간 느림

---

## 관련 학습 자료

- `~/claude-study/atomic-integer.md` - AtomicInteger 상세 설명
- Java Concurrency in Practice (책)
- Java Memory Model 이해하기
