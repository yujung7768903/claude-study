# Java Stream 메서드 정리

> 관련 문서: [20260204-java-stream-creation.md](20260204-java-stream-creation.md) (스트림 생성 방법)

Stream은 **중간 연산(Intermediate)** 과 **최종 연산(Terminal)** 으로 나뉜다.
중간 연산은 lazy하게 실행되며, 최종 연산이 호출될 때 한꺼번에 처리된다.

---

## 중간 연산 (Intermediate Operations)

중간 연산은 **Stream을 반환**하여 체이닝이 가능하다. 최종 연산 전까지 실행되지 않는다.

### filter(Predicate)

조건에 맞는 요소만 통과시킨다.

```java
List<Integer> result = list.stream()
    .filter(n -> n > 3)
    .collect(Collectors.toList());
```

### map(Function)

각 요소를 다른 값으로 변환한다.

```java
List<String> names = users.stream()
    .map(User::getName)
    .collect(Collectors.toList());
```

### flatMap(Function)

각 요소를 스트림으로 변환한 뒤 하나의 스트림으로 평탄화(flatten)한다.

```java
// [[1,2], [3,4]] → [1, 2, 3, 4]
List<List<Integer>> nested = List.of(List.of(1, 2), List.of(3, 4));
List<Integer> flat = nested.stream()
    .flatMap(Collection::stream)
    .collect(Collectors.toList());
```

### distinct()

중복 요소를 제거한다. `equals()`/`hashCode()` 기준.

```java
list.stream().distinct().collect(Collectors.toList());
```

### sorted() / sorted(Comparator)

정렬한다. 인자 없으면 자연 정렬(Comparable).

```java
list.stream().sorted().collect(Collectors.toList());

// 역순
list.stream().sorted(Comparator.reverseOrder()).collect(Collectors.toList());

// 필드 기준
users.stream().sorted(Comparator.comparing(User::getAge)).collect(Collectors.toList());

// 다중 정렬
users.stream()
    .sorted(Comparator.comparing(User::getAge).thenComparing(User::getName))
    .collect(Collectors.toList());
```

### peek(Consumer)

디버깅 용도. 요소를 소비하지 않고 중간에 확인할 때 사용한다.

```java
list.stream()
    .filter(n -> n > 2)
    .peek(n -> System.out.println("filtered: " + n))
    .map(n -> n * 2)
    .peek(n -> System.out.println("mapped: " + n))
    .collect(Collectors.toList());
```

> **주의**: 최종 연산 없이는 실행되지 않는다. 부수 효과(side effect) 목적으로만 사용할 것.

### limit(long)

앞에서 n개만 취한다.

```java
list.stream().limit(5).collect(Collectors.toList());
```

### skip(long)

앞에서 n개를 건너뛴다.

```java
list.stream().skip(2).collect(Collectors.toList());
```

### mapToInt / mapToLong / mapToDouble

객체 스트림 → 원시 타입 특화 스트림으로 변환. 오토박싱 비용 없음.

```java
IntStream ages = users.stream().mapToInt(User::getAge);
int sum = ages.sum();
int max = users.stream().mapToInt(User::getAge).max().getAsInt();
OptionalDouble avg = users.stream().mapToDouble(User::getSalary).average();
```

### mapToObj (IntStream → Stream)

원시 특화 스트림 → 객체 스트림으로 변환.

```java
Stream<String> stream = IntStream.range(1, 5).mapToObj(i -> "item" + i);
```

### boxed (IntStream → Stream\<Integer\>)

`mapToObj(Integer::valueOf)` 와 동일.

```java
List<Integer> list = IntStream.range(1, 5).boxed().collect(Collectors.toList());
```

---

## 최종 연산 (Terminal Operations)

최종 연산은 **스트림을 소비**한다. 한 번 호출되면 스트림을 재사용할 수 없다.

### collect(Collector)

가장 많이 쓰이는 최종 연산. 다양한 컬렉터 활용.

```java
// List
List<String> list = stream.collect(Collectors.toList());

// Set
Set<String> set = stream.collect(Collectors.toSet());

// Map
Map<Integer, String> map = users.stream()
    .collect(Collectors.toMap(User::getId, User::getName));

// groupingBy
Map<String, List<User>> grouped = users.stream()
    .collect(Collectors.groupingBy(User::getDept));

// joining
String csv = stream.collect(Collectors.joining(", "));
String withBrackets = stream.collect(Collectors.joining(", ", "[", "]"));

// counting
Map<String, Long> countByDept = users.stream()
    .collect(Collectors.groupingBy(User::getDept, Collectors.counting()));
```

### forEach(Consumer)

각 요소를 소비한다. 반환값 없음.

```java
list.stream().forEach(System.out::println);
```

### forEachOrdered(Consumer)

병렬 스트림에서도 **순서를 보장**하여 소비.

```java
list.parallelStream().forEachOrdered(System.out::println);
```

### reduce(BinaryOperator) / reduce(identity, BinaryOperator)

요소들을 하나로 합산(누적).

```java
// identity 없으면 Optional 반환
Optional<Integer> sum = list.stream().reduce((a, b) -> a + b);

// identity 있으면 T 반환
int total = list.stream().reduce(0, Integer::sum);

// 3인자: 병렬 스트림용 combiner
int result = list.parallelStream().reduce(0, Integer::sum, Integer::sum);
```

### count()

요소 개수를 반환한다.

```java
long count = list.stream().filter(n -> n > 3).count();
```

### min(Comparator) / max(Comparator)

최솟값/최댓값을 Optional로 반환.

```java
Optional<Integer> min = list.stream().min(Comparator.naturalOrder());
Optional<User> oldest = users.stream().max(Comparator.comparing(User::getAge));
```

### findFirst() / findAny()

- `findFirst()`: 첫 번째 요소 반환 (순서 보장)
- `findAny()`: 아무 요소나 반환 (병렬 스트림에서 성능 우위)

```java
Optional<String> first = list.stream().filter(s -> s.startsWith("A")).findFirst();
Optional<String> any = list.parallelStream().filter(s -> s.startsWith("A")).findAny();
```

### anyMatch / allMatch / noneMatch

조건 충족 여부를 boolean으로 반환. 단락 평가(short-circuit).

```java
boolean hasAdult = users.stream().anyMatch(u -> u.getAge() >= 18);
boolean allAdult = users.stream().allMatch(u -> u.getAge() >= 18);
boolean noneMinor = users.stream().noneMatch(u -> u.getAge() < 18);
```

### toArray()

배열로 변환.

```java
Object[] arr = list.stream().toArray();
String[] strArr = list.stream().toArray(String[]::new);
```

---

## 중간 연산 vs 최종 연산 요약

| 구분 | 메서드 | 반환 타입 |
|------|--------|-----------|
| 중간 | `filter`, `map`, `flatMap` | `Stream<T>` |
| 중간 | `distinct`, `sorted`, `peek` | `Stream<T>` |
| 중간 | `limit`, `skip` | `Stream<T>` |
| 중간 | `mapToInt`, `mapToLong`, `mapToDouble` | `IntStream` 등 |
| 최종 | `collect` | 컬렉션/값 |
| 최종 | `forEach`, `forEachOrdered` | `void` |
| 최종 | `reduce` | `Optional<T>` 또는 `T` |
| 최종 | `count` | `long` |
| 최종 | `min`, `max` | `Optional<T>` |
| 최종 | `findFirst`, `findAny` | `Optional<T>` |
| 최종 | `anyMatch`, `allMatch`, `noneMatch` | `boolean` |
| 최종 | `toArray` | `Object[]` 또는 `T[]` |

---

## 주의사항

### 1. 스트림은 일회용이다

최종 연산 호출 후 재사용 불가. `IllegalStateException` 발생.

```java
Stream<Integer> stream = list.stream();
stream.collect(Collectors.toList());
stream.count(); // ❌ IllegalStateException: stream has already been operated upon or closed
```

### 2. 중간 연산은 Lazy하게 실행된다

최종 연산이 없으면 중간 연산도 실행되지 않는다.

```java
list.stream()
    .filter(n -> { System.out.println("filter: " + n); return n > 3; }); // 아무것도 출력 안 됨
```

### 3. 순서가 성능에 영향을 미친다

`filter`를 먼저, `map`은 뒤에 배치해 불필요한 변환을 줄여야 한다.

```java
// 비효율: 전체를 map 후 filter
list.stream().map(heavyConvert).filter(n -> n > 3).collect(...)

// 효율적: 먼저 filter로 줄이고 map
list.stream().filter(n -> n > 3).map(heavyConvert).collect(...)
```

### 4. peek은 디버깅 전용

`peek`으로 상태를 변경하는 코드(컬렉션에 add 등)는 절대 금지.
최종 연산 타입에 따라 `peek`이 호출되지 않을 수도 있다.

```java
// ❌ 잘못된 사용 - 컬렉션 사이드 이펙트
List<String> sideList = new ArrayList<>();
list.stream().peek(sideList::add).count(); // count는 요소를 보지 않아 peek 미호출될 수 있음
```

### 5. forEach에서 외부 변수 변경 금지

람다에서 참조하는 외부 변수는 effectively final이어야 한다.
외부 상태를 바꾸면 스레드 안전하지 않고 코드도 불명확해진다.

```java
// ❌ 잘못된 사용
int[] count = {0};
list.stream().forEach(n -> count[0]++); // 동작하지만 병렬 시 위험

// ✅ 올바른 사용
long count = list.stream().filter(n -> n > 0).count();
```

### 6. collect(Collectors.toList()) vs Stream.toList() (Java 16+)

- `Collectors.toList()` → 수정 가능한 List
- `Stream.toList()` → **불변 List** (Java 16+, `List.copyOf`와 동일)

```java
List<String> mutable = stream.collect(Collectors.toList());
List<String> immutable = stream.toList(); // Java 16+
```

### 7. Optional 처리를 빠뜨리지 말 것

`findFirst`, `min`, `max`, `reduce`(identity 없을 때) 등은 `Optional`을 반환한다.
무조건 `.get()` 호출하면 `NoSuchElementException` 위험.

```java
// ❌
String name = list.stream().filter(...).findFirst().get();

// ✅
String name = list.stream().filter(...).findFirst().orElse("default");
String name2 = list.stream().filter(...).findFirst().orElseThrow(() -> new RuntimeException("없음"));
```

### 8. 병렬 스트림 남용 금지

- 요소가 적을 때 → 오히려 느림 (ForkJoin 오버헤드)
- 순서 의존 연산 → 결과 보장 안 됨
- 공유 자원 접근 → 동시성 문제
- I/O 작업, DB 연결 → 공유 풀 고갈 위험

```java
// ❌ 요소가 10개인데 병렬
list.parallelStream().map(...).collect(...)

// ✅ 충분히 많고, 독립적인 CPU 바운드 작업에만
largeList.parallelStream().map(cpuHeavyTask).collect(...)
```

### 9. NullPointerException 주의

스트림 요소에 null이 포함되면 `filter`, `map`, `sorted` 등에서 NPE 발생.
`null` 가능성이 있으면 사전에 걸러내거나 `Optional`을 활용할 것.

```java
// ❌
list.stream().filter(s -> s.startsWith("A")).collect(...) // null 있으면 NPE

// ✅
list.stream().filter(Objects::nonNull).filter(s -> s.startsWith("A")).collect(...)
```

---

## 실무 권장사항

- 스트림은 **가독성**이 핵심. 3단계 이상 복잡해지면 분리를 고려한다.
- `collect(Collectors.toList())` 보다 `Stream.toList()`(Java 16+)를 선호한다. (불변 보장)
- `forEach` 대신 `collect`로 결과를 모으는 방식을 선호한다. (함수형 스타일 유지)
- 병렬 스트림은 벤치마크 없이 쓰지 않는다.
- `Optional.get()` 은 쓰지 않는다. `orElse`, `orElseThrow` 를 사용한다.
- `sorted()`는 **안정 정렬(stable sort)** 이므로 동일 키 원소의 순서가 보존된다.
