# 메서드 레퍼런스가 함수형 인터페이스로 구체화되는 원리

---

## 핵심 질문

```java
Function<Product, String> f = Product::getName;
```

`Product::getName`은 메서드 그 자체인데, 어떻게 `Function` 객체가 되는걸까?

---

## 1. 함수형 인터페이스란

`@FunctionalInterface`는 **추상 메서드가 정확히 1개인 인터페이스**다.

```java
@FunctionalInterface
public interface Function<T, R> {
    R apply(T t);  // 추상 메서드 1개
}
```

추상 메서드가 1개이기 때문에, "이 인터페이스의 구현체를 만든다"는 것은
곧 "그 추상 메서드 1개를 어떻게 구현할지 정한다"는 것과 동일하다.

---

## 2. 컴파일러가 하는 일

`Product::getName`을 `Function<Product, String>`에 대입할 때,
컴파일러는 다음 두 가지를 확인한다.

### 시그니처 매칭

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

### 컴파일러가 생성하는 코드 (개념적으로)

```java
// 우리가 쓴 코드
Function<Product, String> f = Product::getName;

// 컴파일러가 이해하는 것 (익명 클래스로 표현하면)
Function<Product, String> f = new Function<Product, String>() {
    @Override
    public String apply(Product product) {
        return product.getName(); // Product::getName 을 여기에 연결
    }
};
```

실제로는 익명 클래스가 아닌 `invokedynamic` 바이트코드로 처리된다 (아래 참고).

---

## 3. 실제 구현 원리: invokedynamic

Java 8부터 람다/메서드 레퍼런스는 **익명 클래스를 생성하지 않는다.**
대신 JVM의 `invokedynamic` 명령어를 사용한다.

### 흐름

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

### LambdaMetafactory

JVM이 내부적으로 호출하는 클래스. 메서드 레퍼런스를 함수형 인터페이스 구현체로 **동적 연결**한다.

```java
// 내부적으로 이런 일이 일어남 (직접 호출하지 않음)
MethodHandles.Lookup lookup = MethodHandles.lookup();
MethodHandle target = lookup.findVirtual(
    Product.class,
    "getName",
    MethodType.methodType(String.class)
);
// target = Product 인스턴스를 받아 getName()을 호출하는 핸들

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

### invokedynamic의 장점

익명 클래스 방식 대비:
- **클래스 파일 생성 없음** → 클래스로더 부담 없음
- **최초 1회만 연결 작업** → 이후 호출은 직접 메서드 호출 수준으로 빠름
- JVM이 JIT 컴파일 시 더 잘 최적화 가능

---

## 4. 메서드 레퍼런스의 4가지 종류와 시그니처 변환

컴파일러가 시그니처를 맞추는 방식이 종류마다 다르다.

### (1) 정적 메서드 레퍼런스 `ClassName::staticMethod`

```java
// Integer::parseInt
Function<String, Integer> f = Integer::parseInt;

// 매핑
// apply(String s) → Integer.parseInt(s)
// 인자 그대로 전달
```

### (2) 인스턴스 메서드 레퍼런스 (비한정) `ClassName::instanceMethod`

```java
// Product::getName  ← 가장 흔한 케이스
Function<Product, String> f = Product::getName;

// 매핑
// apply(Product p) → p.getName()
// 첫 번째 인자가 메서드를 호출할 인스턴스가 됨
```

```java
// String::toLowerCase
Function<String, String> f = String::toLowerCase;
// apply(String s) → s.toLowerCase()

// BiFunction도 가능
BiFunction<String, String, Boolean> f2 = String::startsWith;
// apply(String s, String prefix) → s.startsWith(prefix)
```

### (3) 인스턴스 메서드 레퍼런스 (한정) `instance::instanceMethod`

```java
Product product = new Product("Apple", 1000);
Supplier<String> f = product::getName;

// 매핑
// get() → product.getName()  (특정 인스턴스가 고정됨)
// 인자 없이 호출 가능
```

### (4) 생성자 레퍼런스 `ClassName::new`

```java
Supplier<Product> f = Product::new;
// get() → new Product()

Function<String, Product> f2 = Product::new;
// apply(String name) → new Product(name)
```

### 요약

| 종류 | 형태 | 첫 번째 인자 역할 |
|------|------|-----------------|
| 정적 메서드 | `Class::staticMethod` | 메서드 인자 |
| 비한정 인스턴스 | `Class::instanceMethod` | 메서드를 호출할 인스턴스 |
| 한정 인스턴스 | `obj::instanceMethod` | 없음 (인스턴스 고정) |
| 생성자 | `Class::new` | 생성자 인자 |

---

## 5. 타입이 문맥에 따라 달라지는 이유

메서드 레퍼런스는 그 자체로 타입이 없다. 컴파일러가 **대입되는 타입**을 보고 구체화한다.

```java
// 같은 Product::getName 이지만 문맥에 따라 다르게 구체화
Function<Product, String>  f1 = Product::getName; // apply(Product) → String
UnaryOperator<Product>     f2 = ...; // 시그니처 안 맞음 → 컴파일 에러
Supplier<String>           f3 = product::getName; // 한정 레퍼런스는 OK
```

시그니처가 맞지 않으면 컴파일 에러:

```java
// getName()은 String 반환인데 Integer 요구 → 에러
Function<Product, Integer> f = Product::getName; // ❌ 컴파일 에러
```

---

## 6. 람다와 메서드 레퍼런스의 차이

메서드 레퍼런스는 람다의 **단축 표현**이다. 내부 구현 방식은 동일하다.

```java
// 아래 두 줄은 완전히 동일하게 동작
Function<Product, String> f1 = Product::getName;
Function<Product, String> f2 = (product) -> product.getName();
```

람다는 `invokedynamic` + 컴파일러가 생성한 `lambda$0` 같은 합성 메서드로 처리된다.
메서드 레퍼런스는 기존 메서드를 직접 참조하므로 합성 메서드 생성이 없다.

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
     │  내부적으로:
     │  apply(product) → product.getName() 으로 연결
     │
     ▼
Function<Product, String> 객체로 사용 가능
```

**핵심**: 컴파일러가 시그니처를 맞춰주고, JVM이 런타임에 함수형 인터페이스 구현체를 동적으로 생성한다. 우리가 보기에는 메서드가 객체가 된 것처럼 보이지만, 실제로는 그 메서드를 호출하는 구현체가 생성되는 것이다.
