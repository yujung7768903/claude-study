# Mockito의 제네릭 타입 매칭 원리

## 질문 1: HttpEntity<?>도 제네릭인데 왜 any()만으로 되나?

### 와일드카드 vs 타입 변수

```java
public <T> ResponseEntity<T> exchange(
    String url,
    HttpMethod method,
    @Nullable HttpEntity<?> requestEntity,           // ← 와일드카드
    ParameterizedTypeReference<T> responseType,      // ← 타입 변수
    Map<String, ?> uriVariables                      // ← 와일드카드
)
```

### 차이점 상세

#### 와일드카드 `<?>` - "무엇이든 OK"

```java
// HttpEntity<?>는 "제네릭 안에 무슨 타입이든 올 수 있다"는 의미
HttpEntity<?> entity1 = new HttpEntity<String>("hello");
HttpEntity<?> entity2 = new HttpEntity<Integer>(123);
HttpEntity<?> entity3 = new HttpEntity<List<Object>>(list);
// 모두 가능!

// Mockito에서
any()  // → Object 반환
// 컴파일러: "HttpEntity<?>는 '어떤 타입이든 상관없다'니까 OK!" ✅

// 타입 체크
HttpEntity<?> param = any();  // ✅ 컴파일 성공
// ?는 "알 필요 없다"는 의미
```

---

#### 타입 변수 `<T>` - "특정 타입이 결정되어야 함"

```java
// 메서드 시그니처
public <T> ResponseEntity<T> exchange(
    ...,
    ParameterizedTypeReference<T> responseType,  // T는 메서드 레벨 타입 변수
    ...
) {
    // T는 메서드 전체에서 일관되어야 함
    ResponseEntity<T> response = ...;  // 여기도 T
    return response;  // 반환 타입도 T
}

// Mockito에서
any()  // → Object 반환
// 컴파일러: "T가 뭔지 알아야 하는데... exchange의 <T>와 연결해야 하는데... 모르겠어!" ❌

// 타입 체크
ParameterizedTypeReference<T> param = any();  // ❌ 컴파일 에러
// Error: cannot infer type arguments

// 해결책
ParameterizedTypeReference<T> param = any(ParameterizedTypeReference.class);  // ✅
// 컴파일러에게 "이 타입은 ParameterizedTypeReference야"라고 힌트
```

---

### 핵심 차이 비교

```java
// 와일드카드 - 추론 불필요
void method1(List<?> param) {
    // param은 "어떤 타입의 List든 OK"
}
when(method1(any())).thenReturn(...);  // ✅ OK

// 타입 변수 - 추론 필요
<T> void method2(List<T> param) {
    // T가 뭔지 알아야 함 (메서드 시그니처와 연결)
}
when(method2(any())).thenReturn(...);  // ❌ 에러
when(method2(any(List.class))).thenReturn(...);  // ✅ OK
```

---

## 질문 2: ParameterizedTypeReference.class만 알려줘도 되나? T 타입은?

### any(ParameterizedTypeReference.class)의 실체

```java
any(ParameterizedTypeReference.class)

// 이것의 실제 타입:
ParameterizedTypeReference<?>  // T가 와일드카드가 됨!

// 즉, T 타입을 알려주는 게 아니라
// "이 자리에는 ParameterizedTypeReference 타입이 온다"고만 알려줌
```

---

### 실제 vs Mock의 타입 불일치

```java
// 실제 코드
restTemplate.exchange(
    "url",
    HttpMethod.GET,
    new HttpEntity<>(null, headers),
    new ParameterizedTypeReference<AmsResponseDto<AmsTag>>() {},  // 구체적 타입!
    params
)

// Mock 설정
when(restTemplate.exchange(
    anyString(),
    any(),
    any(),
    any(ParameterizedTypeReference.class),  // ParameterizedTypeReference<?>
    anyMap()
))

// 타입 비교
// 실제: ParameterizedTypeReference<AmsResponseDto<AmsTag>>
// Mock: ParameterizedTypeReference<?>
// 다른데 왜 매칭되나?
```

---

### Mockito는 제네릭 내부 타입을 체크하지 않음

```java
// Mockito의 any() ArgumentMatcher는:
any(ParameterizedTypeReference.class)

// 내부 로직 (개념적):
public boolean matches(Object actual) {
    return actual instanceof ParameterizedTypeReference;  // 타입만 체크!
    // 제네릭 안의 타입(<AmsResponseDto<AmsTag>>)은 체크 안 함!
}

// 왜?
// Java의 제네릭은 Type Erasure 때문에 런타임에 소거됨!
```

---

### Type Erasure (타입 소거)

```java
// 컴파일 전
ParameterizedTypeReference<AmsResponseDto<AmsTag>> ref = new ParameterizedTypeReference<>() {};

// 컴파일 후 (런타임)
ParameterizedTypeReference ref = new ParameterizedTypeReference() {};
// 제네릭 정보가 사라짐!

// 따라서 Mockito도 런타임에는 제네릭 내부 타입을 알 수 없음
// instanceof ParameterizedTypeReference만 체크 가능
```

---

### 정확한 타입 매칭을 원한다면?

```java
// 방법 1: eq()로 정확한 객체 매칭
ParameterizedTypeReference<AmsResponseDto<AmsTag>> expectedType =
    new ParameterizedTypeReference<AmsResponseDto<AmsTag>>() {};

when(restTemplate.exchange(
    anyString(),
    any(),
    any(),
    eq(expectedType),  // 정확히 이 객체와 같은지 확인
    anyMap()
))

// 방법 2: ArgumentMatcher 커스텀
when(restTemplate.exchange(
    anyString(),
    any(),
    any(),
    argThat(ref -> {
        // 커스텀 매칭 로직
        return ref instanceof ParameterizedTypeReference;
    }),
    anyMap()
))

// 하지만 보통은 any(ParameterizedTypeReference.class)로 충분!
```

---

## 정리

### 왜 HttpEntity<?>는 any()로 되고, ParameterizedTypeReference<T>는 any(Class)가 필요한가?

| 특성 | HttpEntity<?> | ParameterizedTypeReference<T> |
|------|---------------|------------------------------|
| 제네릭 타입 | 와일드카드 `<?>` | 타입 변수 `<T>` |
| 의미 | "어떤 타입이든 OK" | "메서드 시그니처의 T와 연결됨" |
| 타입 추론 | 불필요 | 필요 |
| Mockito 매칭 | `any()` ✅ | `any(ParameterizedTypeReference.class)` ✅ |

### any(ParameterizedTypeReference.class)는 무엇을 의미하나?

```java
any(ParameterizedTypeReference.class)
// = "ParameterizedTypeReference<?> 타입이면 매칭"
// ≠ "ParameterizedTypeReference<AmsResponseDto<AmsTag>> 타입이면 매칭"

// Mockito는:
// 1. instanceof ParameterizedTypeReference만 체크
// 2. 제네릭 내부 타입(<AmsResponseDto<AmsTag>>)은 체크 안 함
// 3. Java Type Erasure 때문에 런타임에 제네릭 정보는 소거됨
```

---

## 핵심 요약

**질문 1: HttpEntity<?>도 제네릭인데 왜 any()만으로 되나?**
- `<?>` = 와일드카드 = "무엇이든 OK" → 타입 추론 불필요
- `<T>` = 타입 변수 = "메서드 시그니처와 연결됨" → 타입 추론 필요

**질문 2: ParameterizedTypeReference.class만 알려줘도 되나? T 타입은?**
- 네, T 타입은 알려주지 않습니다
- `any(ParameterizedTypeReference.class)` = `ParameterizedTypeReference<?>` 의미
- Mockito는 instanceof만 체크, 제네릭 내부 타입은 체크 안 함
- Java Type Erasure 때문에 런타임에 제네릭 정보는 소거됨
