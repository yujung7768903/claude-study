# Java 메서드 레퍼런스와 제네릭 타입 시스템

> `Product::getName`이 `Function<Product, String>`이 되는 원리,
> 그리고 `Function<? super T, ? extends K>` 에 전달될 수 있는 이유

---

## Part 1: 메서드 레퍼런스가 함수형 인터페이스로 구체화되는 원리

### 함수형 인터페이스란

`@FunctionalInterface`는 **추상 메서드가 정확히 1개인 인터페이스**다.

```java
@FunctionalInterface
public interface Function<T, R> {
    R apply(T t);  // 추상 메서드 1개
}
```

추상 메서드가 1개이기 때문에, "이 인터페이스의 구현체를 만든다"는 것은
곧 "그 추상 메서드 1개를 어떻게 구현할지 정한다"는 것과 동일하다.

### 컴파일러가 하는 일: 시그니처 매칭

`Product::getName`을 `Function<Product, String>`에 대입할 때,
컴파일러는 다음 두 가지를 확인한다.

| | 타입 | 설명 |
|---|---|---|
| `Function.apply`가 요구하는 것 | `(Product) → String` | T를 받아 R을 반환 |
| `Product::getName`이 제공하는 것 | `(Product) → String` | Product 인스턴스를 받아 String 반환 |

시그니처가 일치하므로 컴파일러가 연결을 허용한다.

`Product::getName`은 인스턴스 메서드 레퍼런스이므로, 실제로는
"Product 인스턴스를 받아서 그 인스턴스의 getName()을 호출한다"는 의미다.

```
apply(product)  →  product.getName()
```

**컴파일러가 이해하는 것 (익명 클래스로 표현하면):**

```java
// 우리가 쓴 코드
Function<Product, String> f = Product::getName;

// 컴파일러가 이해하는 것
Function<Product, String> f = new Function<Product, String>() {
    @Override
    public String apply(Product product) {
        return product.getName();
    }
};
```

실제로는 익명 클래스가 아닌 `invokedynamic` 바이트코드로 처리된다.

### 실제 구현 원리: invokedynamic

Java 8부터 람다/메서드 레퍼런스는 **익명 클래스를 생성하지 않는다.**
대신 JVM의 `invokedynamic` 명령어를 사용한다.

**흐름:**

```
소스코드: Product::getName
    ↓
컴파일: invokedynamic 바이트코드 생성
    ↓
최초 실행: LambdaMetafactory.metafactory() 호출
    ↓
런타임: Function 인터페이스를 구현한 클래스를 동적으로 생성
    ↓
이후 호출: 생성된 클래스의 apply() 메서드 실행
```

**LambdaMetafactory** 는 JVM이 내부적으로 호출하는 클래스. 메서드 레퍼런스를 함수형 인터페이스 구현체로 **동적 연결**한다.

```java
// 내부적으로 이런 일이 일어남 (직접 호출하지 않음)
MethodHandles.Lookup lookup = MethodHandles.lookup();
MethodHandle target = lookup.findVirtual(
    Product.class, "getName", MethodType.methodType(String.class)
);

CallSite callSite = LambdaMetafactory.metafactory(
    lookup,
    "apply",                                             // 구현할 추상 메서드 이름
    MethodType.methodType(Function.class),               // 반환할 함수형 인터페이스 타입
    MethodType.methodType(Object.class, Object.class),   // 소거된 시그니처
    target,                                              // 실제 연결할 메서드
    MethodType.methodType(String.class, Product.class)   // 구체적 시그니처
);

Function<Product, String> f = (Function<Product, String>) callSite.getTarget().invoke();
```

**invokedynamic의 장점:**
- **클래스 파일 생성 없음** → 클래스로더 부담 없음
- **최초 1회만 연결 작업** → 이후 호출은 직접 메서드 호출 수준으로 빠름
- JVM이 JIT 컴파일 시 더 잘 최적화 가능

### 메서드 레퍼런스의 4가지 종류

컴파일러가 시그니처를 맞추는 방식이 종류마다 다르다.

#### (1) 정적 메서드 레퍼런스 `ClassName::staticMethod`

```java
Function<String, Integer> f = Integer::parseInt;
// apply(String s) → Integer.parseInt(s)
```

#### (2) 비한정 인스턴스 메서드 레퍼런스 `ClassName::instanceMethod`

```java
Function<Product, String> f = Product::getName;
// apply(Product p) → p.getName()
// 첫 번째 인자가 메서드를 호출할 인스턴스가 됨

BiFunction<String, String, Boolean> f2 = String::startsWith;
// apply(String s, String prefix) → s.startsWith(prefix)
```

#### (3) 한정 인스턴스 메서드 레퍼런스 `instance::instanceMethod`

```java
Product product = new Product("Apple", 1000);
Supplier<String> f = product::getName;
// get() → product.getName()  (특정 인스턴스가 고정됨)
```

#### (4) 생성자 레퍼런스 `ClassName::new`

```java
Supplier<Product> f = Product::new;
// get() → new Product()

Function<String, Product> f2 = Product::new;
// apply(String name) → new Product(name)
```

#### 요약

| 종류 | 형태 | 첫 번째 인자 역할 |
|------|------|-----------------|
| 정적 메서드 | `Class::staticMethod` | 메서드 인자 |
| 비한정 인스턴스 | `Class::instanceMethod` | 메서드를 호출할 인스턴스 |
| 한정 인스턴스 | `obj::instanceMethod` | 없음 (인스턴스 고정) |
| 생성자 | `Class::new` | 생성자 인자 |

### 메서드 레퍼런스는 그 자체로 타입이 없다

컴파일러가 **대입되는 타입**을 보고 구체화한다.

```java
// 같은 Product::getName이지만 문맥에 따라 다르게 구체화
Function<Product, String> f1 = Product::getName;  // apply(Product) → String
Supplier<String>          f2 = product::getName;   // 한정 레퍼런스 (특정 인스턴스)
Function<Product, Integer> f3 = Product::getName;  // ❌ 컴파일 에러 (String ≠ Integer)
```

### 람다와 메서드 레퍼런스의 차이

메서드 레퍼런스는 람다의 **단축 표현**이다. 내부 구현 방식은 동일하다.

```java
// 아래 두 줄은 완전히 동일하게 동작
Function<Product, String> f1 = Product::getName;
Function<Product, String> f2 = (product) -> product.getName();
```

람다는 `invokedynamic` + 컴파일러가 생성한 `lambda$0` 같은 합성 메서드로 처리된다.
메서드 레퍼런스는 기존 메서드를 직접 참조하므로 합성 메서드 생성이 없다.

---

## Part 2: 제네릭 와일드카드와 타입 추론

### 핵심 질문

```java
// groupingBy 시그니처
public static <T, K> Collector<T, ?, Map<K, List<T>>>
    groupingBy(Function<? super T, ? extends K> classifier)

// 실제 사용
Map<String, List<Product>> result = products.stream()
    .collect(Collectors.groupingBy(Product::getName));
```

`Product::getName`은 `Function<Product, String>` 인데,
파라미터 타입은 `Function<? super T, ? extends K>` — 어떻게 맞는 걸까?

### 1단계: 타입 추론이 먼저 일어난다

컴파일러는 스트림의 타입과 메서드 레퍼런스를 보고 `T`, `K`를 추론한다.

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

### 2단계: 와일드카드 호환성 확인

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

### 와일드카드를 쓰는 이유 (PECS 원칙)

> **PECS: Producer Extends, Consumer Super**

| 와일드카드 | 역할 | 의미 |
|------------|------|------|
| `? extends K` | Producer (값을 꺼냄) | K 또는 K의 하위 타입을 반환 |
| `? super T` | Consumer (값을 받음) | T 또는 T의 상위 타입을 입력으로 받음 |

#### `? super T` 를 쓰는 이유

`Function<Object, String>` 도 `Product`를 분류하는 데 쓸 수 있다.
Product는 Object의 하위 타입이므로, Object를 받는 함수는 당연히 Product도 처리 가능.

```java
Function<Object, String> f = o -> o.toString();

products.stream().collect(Collectors.groupingBy(f)); // ✅ 가능
// Function<Object, String>은 Function<? super Product, String>의 하위 타입
```

#### `? extends K` 를 쓰는 이유

반환 타입이 K의 하위 타입이어도 K로 사용할 수 있다.

```java
// Category extends String 이라면
Function<Product, Category> f = Product::getCategory;
// Map<String, List<Product>> 로 수집 가능 (Category가 String의 하위 타입이므로)
```

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

Function도 동일한 규칙:

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

## 정리

```
Product::getName
     │
     │  컴파일러: "대입 대상이 Function<Product, String>이구나"
     │  → apply(Product) → String 시그니처와 매칭 확인
     │  → invokedynamic 바이트코드 삽입
     │
     ▼
런타임: LambdaMetafactory가 Function 구현체를 동적 생성
     │
     │  내부적으로: apply(product) → product.getName() 으로 연결
     │
     ▼
Function<Product, String> 객체로 사용 가능
```

| 개념 | 설명 |
|------|------|
| 타입 추론 | 컴파일러가 스트림 타입과 메서드 레퍼런스로 T, K를 자동 결정 |
| `? super T` | T 또는 T의 상위 타입을 받는 함수도 허용 (더 유연한 입력) |
| `? extends K` | K 또는 K의 하위 타입을 반환하는 함수도 허용 (더 유연한 출력) |
| 메서드 레퍼런스 | 그 자체는 타입 없음. 문맥에 따라 함수형 인터페이스로 구체화 |
| PECS | Producer → extends, Consumer → super |
| 불공변 | `Function<Product, String>`은 `Function<Object, String>`이 아님. 와일드카드로 해결 |
| invokedynamic | 익명 클래스 없이 런타임에 구현체를 동적 생성 (클래스로더 부담 없음) |

---

## 실무 권장사항

- API를 직접 설계할 때 함수형 파라미터에 `? super` / `? extends`를 붙이면 호출자가 더 다양한 함수를 전달할 수 있어 유연성이 높아진다.
- 내부 사용 API나 단순 유틸에서는 와일드카드 없이 단순하게 유지하는 것이 좋다.
- 타입 추론이 실패할 때는 명시적 타입 힌트를 제공한다:
  ```java
  Collectors.<Product, String>groupingBy(Product::getName)
  ```
