# Java 제네릭 와일드카드와 타입 추론

> `Function<? super T, ? extends K>` 에 `Product::getName` 같은 메서드 레퍼런스를 넣을 수 있는 이유

---

## 핵심 질문

```java
// groupingBy 시그니처
public static <T, K> Collector<T, ?, Map<K, List<T>>>
    groupingBy(Function<? super T, ? extends K> classifier)

// 실제 사용
Map<String, List<Product>> result = products.stream()
    .collect(Collectors.groupingBy(Product::getName)); // 왜 가능?
```

`Product::getName`은 `Function<Product, String>` 인데,
파라미터 타입은 `Function<? super T, ? extends K>` — 어떻게 맞는 걸까?

---

## 1단계: 타입 추론이 먼저 일어난다

컴파일러는 `groupingBy`를 호출하는 스트림의 타입과 메서드 레퍼런스를 보고 `T`, `K`를 추론한다.

```
Stream<Product> → T = Product
Product::getName 의 반환 타입 String → K = String
```

따라서 실제로는 아래처럼 해석된다:

```java
// 컴파일러가 추론한 실제 타입
Collectors.<Product, String>groupingBy(Product::getName)
// 즉, Function<? super Product, ? extends String> classifier
```

---

## 2단계: 와일드카드 호환성 확인

T=Product, K=String 이 결정되면, 컴파일러는 다음을 확인한다.

```
요구 타입: Function<? super Product, ? extends String>
전달 타입: Function<Product, String>  ← Product::getName
```

- `? super Product` : Product 또는 Product의 상위 타입을 입력으로 받아야 함
  → `Function<Product, String>`은 Product를 받으므로 ✅
- `? extends String` : String 또는 String의 하위 타입을 반환해야 함
  → `Function<Product, String>`은 String을 반환하므로 ✅

**결론: 완전히 호환된다.**

---

## 와일드카드를 쓰는 이유 (PECS 원칙)

> **PECS: Producer Extends, Consumer Super**

| 와일드카드 | 역할 | 의미 |
|------------|------|------|
| `? extends K` | Producer (값을 꺼냄) | K 또는 K의 하위 타입을 반환 |
| `? super T` | Consumer (값을 받음) | T 또는 T의 상위 타입을 입력으로 받음 |

### `? super T` 를 쓰는 이유

`Function<Object, String>` 도 `Product`를 분류하는 데 쓸 수 있다.
Product는 Object의 하위 타입이므로, Object를 받는 함수는 당연히 Product도 처리 가능.

```java
Function<Object, String> f = o -> o.toString();
// Product::toString 과 동일한 효과

products.stream().collect(Collectors.groupingBy(f)); // ✅ 가능
// Function<Object, String>은 Function<? super Product, String>의 하위 타입
```

### `? extends K` 를 쓰는 이유

반환 타입이 K의 하위 타입이어도 K로 사용할 수 있다.

```java
// Category는 String의 하위 타입이라고 가정
Function<Product, Category> f = Product::getCategory;
// Category extends String 이면 Map<String, List<Product>> 로 수집 가능
```

---

## 메서드 레퍼런스와 Function의 관계

`Product::getName`은 그 자체로는 타입이 없다. **문맥에 따라 타입이 결정**된다.

```java
// 같은 Product::getName 이지만 문맥에 따라 다른 타입으로 해석됨
Function<Product, String> f1 = Product::getName;    // Function
Supplier<String>          f2 = product::getName;    // Supplier (인스턴스 메서드 레퍼런스)
UnaryOperator<Product>    f3 = ...;                 // 맞지 않으면 컴파일 에러
```

`groupingBy(Product::getName)` 호출 시:
1. 컴파일러가 `groupingBy`의 파라미터 타입 `Function<? super T, ? extends K>` 를 확인
2. 스트림 타입 `Stream<Product>` 에서 `T = Product` 추론
3. `Product::getName` → `Product`를 받아 `String` 반환 → `K = String` 추론
4. `Product::getName`을 `Function<Product, String>` 으로 구체화
5. `Function<Product, String>` 이 `Function<? super Product, ? extends String>` 에 호환되는지 확인 → ✅

---

## 자주 헷갈리는 포인트

### 제네릭은 불공변(invariant)이다

```java
// 일반 클래스: 공변
Object o = new String("hi"); // ✅ String은 Object의 하위 타입

// 제네릭: 불공변
List<Object> list = new ArrayList<String>(); // ❌ 컴파일 에러
```

`List<String>`은 `List<Object>`가 **아니다**.
이 때문에 와일드카드(`? super`, `? extends`)가 필요하다.

```java
// 와일드카드로 유연성 확보
List<? super String> list = new ArrayList<Object>(); // ✅
List<? extends Object> list2 = new ArrayList<String>(); // ✅
```

### Function도 동일한 규칙

```java
Function<Product, String> f = Product::getName;

// 불공변이므로 직접 대입 불가
Function<Object, String> f2 = f;   // ❌
Function<Product, Object> f3 = f;  // ❌

// 와일드카드 사용 시 가능
Function<? super Product, ? extends String> f4 = f; // ✅
```

---

## 실제 코드로 전체 흐름 확인

```java
class Product {
    private String name;
    private int price;

    public String getName() { return name; }
    public int getPrice() { return price; }
}

List<Product> products = List.of(
    new Product("Apple", 1000),
    new Product("Banana", 500),
    new Product("Apple", 1500)
);

// 컴파일러 추론 흐름:
// 1. products.stream() → Stream<Product>  ∴ T = Product
// 2. Product::getName → Function<Product, String>  ∴ K = String
// 3. groupingBy의 실제 타입 = Collector<Product, ?, Map<String, List<Product>>>
Map<String, List<Product>> grouped = products.stream()
    .collect(Collectors.groupingBy(Product::getName));
// {Apple=[...], Banana=[...]}

// 상위 타입 함수도 가능 (? super T 덕분에)
Function<Object, String> byToString = Object::toString;
Map<String, List<Product>> grouped2 = products.stream()
    .collect(Collectors.groupingBy(byToString)); // ✅
```

---

## 요약

| 개념 | 설명 |
|------|------|
| 타입 추론 | 컴파일러가 스트림 타입과 메서드 레퍼런스로 T, K를 자동 결정 |
| `? super T` | T 또는 T의 상위 타입을 받는 함수도 허용 (더 유연한 입력) |
| `? extends K` | K 또는 K의 하위 타입을 반환하는 함수도 허용 (더 유연한 출력) |
| 메서드 레퍼런스 | 그 자체는 타입 없음. 문맥에 따라 함수형 인터페이스로 구체화 |
| PECS | Producer → extends, Consumer → super |
| 불공변 | `Function<Product, String>`은 `Function<Object, String>`이 아님. 와일드카드로 해결 |

---

## 실무 권장사항

- API를 직접 설계할 때, 함수형 파라미터에 `? super` / `? extends` 를 붙이면 호출자가 더 다양한 함수를 전달할 수 있어 유연성이 높아진다.
- 단, 내부 사용 API나 단순 유틸에서는 와일드카드가 없어도 무방하다. 복잡도만 늘어날 수 있다.
- 타입 추론이 실패할 때는 명시적 타입 힌트를 제공한다:
  ```java
  Collectors.<Product, String>groupingBy(Product::getName)
  ```
