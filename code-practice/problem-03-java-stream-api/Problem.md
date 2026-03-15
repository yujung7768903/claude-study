# 문제 3: 온라인 쇼핑몰 상품 데이터 분석기

## 난이도: 중

## 학습 목표
- `Stream.filter()`, `map()`, `sorted()`, `distinct()` 등 중간 연산 이해
- `collect()`, `reduce()`, `count()`, `findFirst()` 등 최종 연산 이해
- `Collectors.groupingBy()`, `Collectors.counting()`, `Collectors.averagingInt()` 활용
- `flatMap()`으로 중첩 컬렉션 처리
- `Optional`로 null-safe한 결과 처리

## 문제 설명

온라인 쇼핑몰의 상품 데이터를 Stream API로 분석하는 시스템을 구현합니다.

각 상품(`Product`)은 이름, 카테고리, 가격, 재고 수량, 태그 목록을 가집니다.
`StreamAnalyzer` 인터페이스를 구현하여 다양한 분석 기능을 완성하세요.

## 요구사항

### Product 클래스 (완성 제공)
```java
public class Product {
    private String name;       // 상품명
    private String category;   // 카테고리 (전자제품, 의류, 식품 등)
    private int price;         // 가격 (원)
    private int stock;         // 재고 수량
    private List<String> tags; // 태그 목록
}
```

### StreamAnalyzer 인터페이스 (완성 제공)
| 메서드 | 설명 |
|--------|------|
| `getExpensiveProducts(int minPrice)` | minPrice 이상인 상품 목록 (가격 내림차순) |
| `getProductNamesByCategory(String category)` | 특정 카테고리 상품명 목록 (이름 오름차순) |
| `getTotalStockByCategory()` | 카테고리별 총 재고 합계 Map |
| `getAveragePriceByCategory()` | 카테고리별 평균 가격 Map |
| `getMostExpensiveProduct()` | 가장 비싼 상품 (Optional) |
| `getProductCountByCategory()` | 카테고리별 상품 수 Map |
| `getAllTags()` | 전체 상품의 모든 태그 (중복 제거, 정렬) |
| `getTopNByPrice(int n)` | 가격 상위 N개 상품명 목록 |
| `hasOutOfStockProduct()` | 재고 0인 상품 존재 여부 |
| `getTotalRevenuePotential()` | 전체 상품의 가격 × 재고 합계 |

## 실행 결과 예시

```
=== 5만원 이상 상품 (가격 내림차순) ===
[맥북 에어(1200000원), 아이폰 15(900000원), 삼성 TV(800000원), 나이키 운동화(120000원), 애플워치(90000원), 리바이스 청바지(89000원), 아디다스 후드(65000원), 스타벅스 원두(52000원)]

=== 전자제품 카테고리 상품명 (오름차순) ===
[맥북 에어, 삼성 TV, 아이폰 15, 애플워치]

=== 카테고리별 총 재고 ===
{식품=500, 의류=250, 전자제품=130}

=== 카테고리별 평균 가격 ===
식품: 20000원
의류: 91333원
전자제품: 747500원

=== 가장 비싼 상품 ===
맥북 에어 (1200000원)

=== 카테고리별 상품 수 ===
{식품=3, 의류=3, 전자제품=4}

=== 전체 태그 (중복 제거, 정렬) ===
[가성비, 겨울, 국산, 노트북, 단백질, 모바일, 봄, 브랜드, 스마트워치, 스마트폰, 여름, 유기농, 캐주얼, 커피, 할인]

=== 가격 상위 3개 상품명 ===
[맥북 에어, 아이폰 15, 삼성 TV]

=== 품절 상품 존재 여부 ===
true

=== 전체 판매 가능 금액 ===
136,170,000원

✅ 모든 테스트 통과!
```

## 힌트

### filter + sorted + collect
```java
products.stream()
    .filter(p -> p.getPrice() >= minPrice)
    .sorted(Comparator.comparingInt(Product::getPrice).reversed())
    .collect(Collectors.toList());
```

### groupingBy + summingInt
```java
products.stream()
    .collect(Collectors.groupingBy(
        Product::getCategory,
        Collectors.summingInt(Product::getStock)
    ));
```

### flatMap + distinct + sorted
```java
products.stream()
    .flatMap(p -> p.getTags().stream())
    .distinct()
    .sorted()
    .collect(Collectors.toList());
```

### reduce로 합계
```java
products.stream()
    .mapToLong(p -> (long) p.getPrice() * p.getStock())
    .sum();
```

## 테스트 방법

```bash
# 컴파일
javac Product.java StreamAnalyzer.java StreamAnalyzerImpl.java StreamAnalyzerTest.java

# 실행
java StreamAnalyzerTest
```

## 추가 도전 과제

1. `getProductsWithTag(String tag)`: 특정 태그를 가진 상품 목록 반환
2. `getCheapestInCategory(String category)`: 카테고리 내 가장 저렴한 상품 반환 (Optional)
3. `groupByPriceRange()`: 가격대별(~1만, 1만~5만, 5만~20만, 20만~) 상품 그룹화
4. `getStatisticsByCategory()`: 카테고리별 IntSummaryStatistics (min/max/avg/count) 반환
