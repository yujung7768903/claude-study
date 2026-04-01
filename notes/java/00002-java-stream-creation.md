# Java List를 Stream으로 만드는 방법과 차이점

## 1. Collection.stream()

가장 일반적인 방법. `Collection` 인터페이스에 정의된 디폴트 메서드.

```java
List<String> list = Arrays.asList("a", "b", "c");
Stream<String> stream = list.stream();
```

- **순차(sequential) 스트림** 생성
- 단일 스레드에서 처리
- 대부분의 경우 이 방법으로 충분

## 2. Collection.parallelStream()

```java
List<String> list = Arrays.asList("a", "b", "c");
Stream<String> stream = list.parallelStream();
```

- **병렬(parallel) 스트림** 생성
- ForkJoinPool을 사용하여 멀티스레드로 처리
- 주의사항:
  - 원소 수가 적으면 오히려 오버헤드로 느려짐
  - 순서 보장이 필요한 경우 부적합
  - 공유 자원 접근 시 동시성 문제 발생 가능
  - `ArrayList`는 분할이 효율적이지만 `LinkedList`는 비효율적

## 3. Stream.of()

```java
Stream<String> stream = Stream.of("a", "b", "c");
```

- 가변 인자(varargs)로 직접 원소를 지정
- 내부적으로 `Arrays.stream()`을 호출
- List가 아닌 개별 값이나 배열에서 스트림을 만들 때 유용

```java
// 단일 원소
Stream<String> single = Stream.of("a");

// 배열
String[] arr = {"a", "b", "c"};
Stream<String> fromArr = Stream.of(arr);
```

## 4. Arrays.stream()

```java
String[] arr = {"a", "b", "c"};
Stream<String> stream = Arrays.stream(arr);

// 범위 지정 가능 (fromIndex inclusive, toIndex exclusive)
Stream<String> partial = Arrays.stream(arr, 0, 2); // "a", "b"
```

- **배열 전용**
- `Stream.of()`와 달리 범위 지정이 가능
- 원시 타입 배열에 대해 특화 스트림 반환:

```java
int[] nums = {1, 2, 3};
IntStream intStream = Arrays.stream(nums);  // IntStream 반환 (오토박싱 없음)

// Stream.of()와의 차이
Stream<int[]> wrong = Stream.of(nums);      // Stream<int[]> 반환 (배열 자체가 하나의 원소)
```

## 5. StreamSupport.stream()

```java
import java.util.stream.StreamSupport;

Iterable<String> iterable = ...;
Stream<String> stream = StreamSupport.stream(iterable.spliterator(), false);
```

- `Iterable`만 구현하고 `Collection`은 아닌 객체에서 스트림을 만들 때 사용
- 두 번째 인자 `false` = 순차, `true` = 병렬
- 직접 사용할 일은 드물지만, 라이브러리가 `Iterable`만 제공하는 경우 필요

## 6. Stream.builder()

```java
Stream<String> stream = Stream.<String>builder()
        .add("a")
        .add("b")
        .add("c")
        .build();
```

- 빌더 패턴으로 스트림 원소를 하나씩 추가
- `build()` 호출 후에는 `add()` 불가 (IllegalStateException)
- 조건부로 원소를 추가해야 할 때 유용:

```java
Stream.Builder<String> builder = Stream.builder();
builder.add("필수값");
if (condition) {
    builder.add("선택값");
}
Stream<String> stream = builder.build();
```

## 7. Stream.generate() / Stream.iterate()

리스트 변환이 아닌, 스트림 자체를 생성하는 방법.

```java
// 무한 스트림 - 반드시 limit 필요
Stream<String> generated = Stream.generate(() -> "hello").limit(5);

// iterate - 초기값 + 다음 값 생성 함수
Stream<Integer> iterated = Stream.iterate(0, n -> n + 2).limit(10); // 0, 2, 4, ...

// Java 9+ iterate with Predicate (종료 조건)
Stream<Integer> bounded = Stream.iterate(0, n -> n < 20, n -> n + 2); // 0, 2, ..., 18
```

## 비교 요약

| 방법 | 입력 | 주 용도 |
|------|------|---------|
| `list.stream()` | Collection | 가장 일반적, 순차 처리 |
| `list.parallelStream()` | Collection | 대량 데이터 병렬 처리 |
| `Stream.of(...)` | 가변 인자 / 배열 | 개별 값으로 스트림 생성 |
| `Arrays.stream()` | 배열 | 배열 → 스트림, 범위 지정 가능, 원시 타입 특화 |
| `StreamSupport.stream()` | Iterable | Collection이 아닌 Iterable 처리 |
| `Stream.builder()` | 개별 추가 | 조건부 원소 추가 |
| `Stream.generate/iterate` | 함수 | 무한/반복 스트림 생성 |

## 실무에서의 선택 기준

- **List/Set 등 Collection** → `collection.stream()` (99%의 경우)
- **배열** → `Arrays.stream(arr)` (원시 타입이면 특히)
- **개별 값 나열** → `Stream.of(a, b, c)`
- **병렬 처리** → `parallelStream()` (원소 수가 충분히 많고, 순서 무관하며, 스레드 안전할 때만)
