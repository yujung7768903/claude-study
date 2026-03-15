# 정답 및 해설

> ⚠️ **먼저 스스로 풀어보세요!**
> 정답을 보기 전에 충분히 고민하는 것이 학습에 훨씬 효과적입니다.

---

## 정답 코드 (StreamAnalyzerImpl.java)

```java
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

public class StreamAnalyzerImpl implements StreamAnalyzer {

    private final List<Product> products;

    public StreamAnalyzerImpl(List<Product> products) {
        this.products = products;
    }

    @Override
    public List<Product> getExpensiveProducts(int minPrice) {
        return products.stream()
                .filter(p -> p.getPrice() >= minPrice)
                .sorted(Comparator.comparingInt(Product::getPrice).reversed())
                .collect(Collectors.toList());
    }

    @Override
    public List<String> getProductNamesByCategory(String category) {
        return products.stream()
                .filter(p -> p.getCategory().equals(category))
                .map(Product::getName)
                .sorted()
                .collect(Collectors.toList());
    }

    @Override
    public Map<String, Integer> getTotalStockByCategory() {
        return products.stream()
                .collect(Collectors.groupingBy(
                        Product::getCategory,
                        Collectors.summingInt(Product::getStock)
                ));
    }

    @Override
    public Map<String, Integer> getAveragePriceByCategory() {
        return products.stream()
                .collect(Collectors.groupingBy(
                        Product::getCategory,
                        Collectors.collectingAndThen(
                                Collectors.averagingInt(Product::getPrice),
                                avg -> (int) avg.doubleValue()
                        )
                ));
    }

    @Override
    public Optional<Product> getMostExpensiveProduct() {
        return products.stream()
                .max(Comparator.comparingInt(Product::getPrice));
    }

    @Override
    public Map<String, Long> getProductCountByCategory() {
        return products.stream()
                .collect(Collectors.groupingBy(
                        Product::getCategory,
                        Collectors.counting()
                ));
    }

    @Override
    public List<String> getAllTags() {
        return products.stream()
                .flatMap(p -> p.getTags().stream())
                .distinct()
                .sorted()
                .collect(Collectors.toList());
    }

    @Override
    public List<String> getTopNByPrice(int n) {
        return products.stream()
                .sorted(Comparator.comparingInt(Product::getPrice).reversed())
                .limit(n)
                .map(Product::getName)
                .collect(Collectors.toList());
    }

    @Override
    public boolean hasOutOfStockProduct() {
        return products.stream()
                .anyMatch(p -> p.getStock() == 0);
    }

    @Override
    public long getTotalRevenuePotential() {
        return products.stream()
                .mapToLong(p -> (long) p.getPrice() * p.getStock())
                .sum();
    }
}
```

---

## 메서드별 해설

### 1. `getExpensiveProducts` — filter + sorted + collect
```java
.filter(p -> p.getPrice() >= minPrice)          // 조건에 맞는 상품만 추출
.sorted(Comparator.comparingInt(Product::getPrice).reversed()) // 가격 내림차순
.collect(Collectors.toList())                    // List로 수집
```
- `Comparator.comparingInt(...).reversed()`로 내림차순 정렬
- `naturalOrder()` / `reverseOrder()`는 Comparable 타입에 사용, 필드 기준 정렬은 `comparingInt` 활용

---

### 2. `getProductNamesByCategory` — filter + map + sorted
```java
.filter(p -> p.getCategory().equals(category))  // 카테고리 일치 필터
.map(Product::getName)                           // 상품명으로 변환 (String 스트림)
.sorted()                                        // 문자열 자연 정렬 (가나다/ABC 오름차순)
```
- `map()`으로 `Stream<Product>` → `Stream<String>` 변환

---

### 3. `getTotalStockByCategory` — groupingBy + summingInt
```java
Collectors.groupingBy(
    Product::getCategory,           // key: 카테고리
    Collectors.summingInt(Product::getStock) // value: stock 합계
)
```
- `groupingBy`의 두 번째 인자(downstream collector)로 집계 방식을 지정

---

### 4. `getAveragePriceByCategory` — groupingBy + averagingInt
```java
Collectors.collectingAndThen(
    Collectors.averagingInt(Product::getPrice),  // Double 평균
    avg -> (int) avg.doubleValue()               // int로 변환 (소수점 버림)
)
```
- `averagingInt`는 `Double`을 반환 → `collectingAndThen`으로 후처리
- `(int) avg.doubleValue()`는 소수점 이하를 버림 (floor와 동일)

---

### 5. `getMostExpensiveProduct` — max
```java
products.stream()
    .max(Comparator.comparingInt(Product::getPrice));
```
- `max()` / `min()`은 `Optional<T>`를 반환
- 스트림이 비어있으면 `Optional.empty()` 자동 반환

---

### 6. `getProductCountByCategory` — groupingBy + counting
```java
Collectors.groupingBy(
    Product::getCategory,
    Collectors.counting()  // Long 타입 카운트
)
```
- `counting()`은 `Long`을 반환하므로 `Map<String, Long>`

---

### 7. `getAllTags` — flatMap + distinct + sorted
```java
.flatMap(p -> p.getTags().stream())  // List<String> 여러 개 → 단일 Stream<String>
.distinct()                           // 중복 제거
.sorted()                             // 정렬
```
- `flatMap`은 중첩 스트림을 펼치는 핵심 연산
- `map`을 쓰면 `Stream<List<String>>`이 되어 flatten이 안 됨

---

### 8. `getTopNByPrice` — sorted + limit + map
```java
.sorted(Comparator.comparingInt(Product::getPrice).reversed())
.limit(n)          // 상위 n개만 취함
.map(Product::getName)
```
- `limit()`은 스트림을 n개로 잘라내는 단락(short-circuit) 연산

---

### 9. `hasOutOfStockProduct` — anyMatch
```java
products.stream().anyMatch(p -> p.getStock() == 0);
```
- `anyMatch`: 하나라도 조건 만족 → true, 즉시 반환 (단락 평가)
- 유사 연산: `allMatch`(모두), `noneMatch`(하나도 없음)

---

### 10. `getTotalRevenuePotential` — mapToLong + sum
```java
.mapToLong(p -> (long) p.getPrice() * p.getStock())
.sum()
```
- `mapToLong`으로 `LongStream`으로 변환 → `.sum()` 직접 사용 가능
- `(long) p.getPrice() * p.getStock()` — 곱셈 전에 long 캐스팅 필수 (int 오버플로 방지)

---

## 핵심 개념 정리

| 연산 | 종류 | 반환 타입 | 설명 |
|------|------|-----------|------|
| `filter` | 중간 | `Stream<T>` | 조건에 맞는 요소만 통과 |
| `map` | 중간 | `Stream<R>` | 요소를 다른 타입으로 변환 |
| `flatMap` | 중간 | `Stream<R>` | 중첩 스트림 평탄화 |
| `sorted` | 중간 | `Stream<T>` | 정렬 |
| `distinct` | 중간 | `Stream<T>` | 중복 제거 |
| `limit` | 중간 | `Stream<T>` | n개로 제한 (단락) |
| `collect` | 최종 | R | Collector로 수집 |
| `max/min` | 최종 | `Optional<T>` | 최대/최소 |
| `anyMatch` | 최종 | boolean | 하나라도 조건 충족 여부 (단락) |
| `mapToLong` | 중간 | `LongStream` | long 기본형 스트림 변환 |

---

## 추가 학습 포인트

- **단락 평가(Short-circuit)**: `anyMatch`, `findFirst`, `limit` 등은 조건 충족 시 나머지 요소를 처리하지 않아 성능상 유리합니다.
- **기본형 스트림**: `mapToInt`, `mapToLong`, `mapToDouble`을 사용하면 박싱/언박싱 없이 `sum()`, `average()`, `statistics()` 등을 바로 사용할 수 있습니다.
- **Collectors 조합**: `groupingBy` + `counting/summingInt/averagingInt/collectingAndThen` 조합 패턴을 익혀두면 복잡한 집계도 간결하게 작성할 수 있습니다.
- **지연 평가(Lazy Evaluation)**: 중간 연산은 최종 연산이 호출되기 전까지 실제로 실행되지 않습니다.
