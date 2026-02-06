# 문제 1: 멀티스레드 안전한 방문자 카운터

## 난이도: 하

## 학습 목표
- `AtomicInteger`를 사용하여 thread-safe한 카운터 구현
- `synchronized` vs `AtomicInteger` 성능 비교
- 멀티스레드 환경에서의 race condition 이해

## 문제 설명

웹 사이트의 방문자 수를 카운팅하는 시스템을 만들어야 합니다. 동시에 여러 요청이 들어올 수 있으므로 thread-safe해야 합니다.

다음 3가지 방식으로 카운터를 구현하세요:

1. **UnsafeCounter**: 일반 `int`를 사용 (비교용 - thread-unsafe)
2. **SynchronizedCounter**: `synchronized` 키워드 사용
3. **AtomicCounter**: `AtomicInteger` 사용

## 요구사항

### Counter 인터페이스
모든 카운터는 다음 인터페이스를 구현해야 합니다:
```java
public interface Counter {
    void increment();      // 카운터 1 증가
    int getCount();        // 현재 카운터 값 반환
    void reset();          // 카운터 0으로 초기화
}
```

### UnsafeCounter
- 일반 `int` 필드 사용
- 동기화 없음 (thread-unsafe)

### SynchronizedCounter
- 일반 `int` 필드 사용
- `synchronized` 키워드로 동기화

### AtomicCounter
- `AtomicInteger` 사용
- lock 없이 thread-safe

## 실행 결과 예시

```
=== 단일 스레드 테스트 (각 1000번 증가) ===
UnsafeCounter: 1000
SynchronizedCounter: 1000
AtomicCounter: 1000
✅ 모두 통과

=== 멀티스레드 테스트 (10개 스레드, 각 1000번 증가) ===
예상 결과: 10000

UnsafeCounter: 8742 ❌ (race condition 발생!)
SynchronizedCounter: 10000 ✅
AtomicCounter: 10000 ✅

=== 성능 비교 (10개 스레드, 각 100000번 증가) ===
SynchronizedCounter: 523ms
AtomicCounter: 287ms
→ AtomicCounter가 약 1.8배 빠름
```

## 힌트

### UnsafeCounter
```java
private int count = 0;

public void increment() {
    count++;  // race condition 발생!
}
```

### SynchronizedCounter
```java
private int count = 0;

public synchronized void increment() {
    count++;
}
```

### AtomicCounter
```java
private AtomicInteger count = new AtomicInteger(0);

public void increment() {
    count.incrementAndGet();  // 또는 getAndIncrement()
}
```

## 테스트 방법

`CounterTest.java`를 실행하세요:
```bash
javac Counter*.java
java CounterTest
```

모든 테스트를 통과하면 성공입니다!

## 추가 도전 과제

1. `incrementBy(int delta)` 메서드 추가 (n만큼 증가)
2. `decrementAndGet()` 메서드 추가 (감소 후 반환)
3. `compareAndSet(int expect, int update)` 메서드 추가
4. 더 많은 스레드(100개)와 반복(1000000번)으로 성능 차이 확인

## 관련 학습 자료

- `~/claude-study/atomic-integer.md`
