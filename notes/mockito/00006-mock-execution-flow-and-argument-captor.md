# Mock 객체의 실행 흐름과 ArgumentCaptor

## 핵심 질문

1. Mock은 가짜 객체인데, 어디까지 수행되는가?
2. AmsArticleTagService에서 restTemplate.exchange()를 호출할 때, 실제 URL, requestEntity, parameter를 넣는 것까지 수행하는가?
3. Mock 객체에 인자를 전달해서 검증까지만 하는 건가?
4. verify는 인자가 전달되는 순간에 캡처하는 건가?

---

## Mock 객체의 동작 방식

### Mock 객체란?

```java
@Mock
private RestTemplate restTemplate;  // 가짜 RestTemplate
```

**Mock은:**
- 실제 클래스의 "껍데기"만 있는 가짜 객체
- 모든 메서드가 빈 껍데기
- 메서드 호출은 받지만, **내부 로직은 실행하지 않음**
- when().thenReturn()으로 지정한 값만 반환
- **호출 기록을 저장**

---

## Stubbing이란?

### 개념

**Stubbing = Mock 객체의 동작을 미리 정의하는 것**

```java
when(restTemplate.exchange(anyString(), any(), any(), any(), anyMap()))
    .thenReturn(mockResponse);
```

**의미:**
- "restTemplate.exchange()가 호출되면"
- "실제 HTTP 요청을 보내지 말고"
- "그냥 mockResponse를 반환해!"

### 내부 저장 구조

```
MockHandler {
  stubbings: [
    StubbedInvocationMatcher {
      matches: exchange(anyString(), any(), ...)  ← 이 조건에 매칭되면
      answer: Returns(mockResponse)                ← 이 값을 반환
    }
  ]
  invocations: []  ← 실제 호출 기록은 여기 저장
}
```

---

## Mockito의 내부 구조

### Mock 생성: 바이트코드 조작 (ByteBuddy)

```java
@Mock
private RestTemplate restTemplate;
```

**Mockito가 하는 일:**

```
[1] 원본 클래스 분석
    RestTemplate.class 로딩 → 모든 메서드 목록 추출

[2] 동적으로 서브클래스 생성 (ByteBuddy 사용)

    원본 클래스:
    ┌────────────────────────┐
    │ RestTemplate           │
    │ + exchange(...)        │
    └────────────────────────┘
            ↓ 상속
    ┌──────────────────────────────────────────┐
    │ RestTemplate$MockitoMock$1234567890      │  ← 런타임에 동적 생성!
    │                                          │
    │ @Override                                │
    │ public ResponseEntity exchange(...) {    │
    │     return mockHandler.handle(           │
    │         this, "exchange", args           │
    │     );                                   │
    │ }                                        │
    └──────────────────────────────────────────┘

[3] MockHandler 생성 및 연결
```

### MockHandler의 구조

```java
class MockHandlerImpl implements MockHandler {
    private List<StubbedInvocationMatcher> stubbings = new ArrayList<>();
    private InvocationContainer invocationContainer = new InvocationContainerImpl();

    public Object handle(Object mock, Method method, Object[] args) {
        // 1. 호출 기록 저장
        Invocation invocation = new Invocation(mock, method, args, SequenceNumber.next());
        invocationContainer.recordInvocation(invocation);

        // 2. Stubbing 확인
        StubbedInvocationMatcher stubbing = findMatchingStub(invocation);

        if (stubbing != null) {
            return stubbing.answer(invocation);  // thenReturn 값 반환
        } else {
            return Defaults.defaultValue(method.getReturnType());  // null, 0, false 등
        }
    }
}
```

---

## 실행 흐름 상세 분석

### Step 1: Mock 설정 (Stubbing)

```java
when(restTemplate.exchange(anyString(), any(), any(), any(), anyMap()))
    .thenReturn(mockResponse);
```

**Mockito가 하는 일:**
```
[1] when() → "stubbing 모드" ON
[2] restTemplate.exchange(...) → InvocationMatcher 생성
[3] thenReturn(mockResponse) → StubbedInvocationMatcher 저장 → "stubbing 모드" OFF
```

### Step 2: 서비스 메서드 실행

```java
service.getArticleTagListFromAms(article);
```

**서비스 내부:**
```java
// 이 코드들은 모두 실행됨 ✅
HttpHeaders requestHeader = new HttpHeaders();
requestHeader.add("X-Batch-User-Id", "BATCH_SYSTEM");  // ✅
HttpEntity<Object> requestEntity = new HttpEntity<>(null, requestHeader);  // ✅
Map<String, String> params = new HashMap<>();
params.put("articleId", rArticle.getArticleId());  // ✅

// Mock 메서드 호출 ✅
ResponseEntity<...> response = this.restTemplate.exchange(
    "http://ams-api/tag?articleId={articleId}",  // ✅ 문자열 생성됨
    HttpMethod.GET,                               // ✅ 전달됨
    requestEntity,                                // ✅ 전달됨 (실제 객체!)
    new ParameterizedTypeReference<...>() {},     // ✅ 생성되고 전달됨
    params                                        // ✅ 전달됨 (실제 객체!)
);
// HTTP 요청은 실행 안 됨 ❌, mockResponse 반환 ✅
```

### Step 3: Mock이 호출 기록 저장

```
┌───────────────────────────────────────────────────────┐
│ Mock RestTemplate.exchange() 호출됨!                  │
│                                                       │
│ [1] 인자들 받음 ✅                                    │
│     arg[0] = "http://ams-api/tag?articleId={...}"    │
│     arg[2] = HttpEntity 객체 (실제 객체!)            │
│     arg[4] = Map 객체 (실제 객체!)                   │
│                                                       │
│ [2] 호출 기록 저장 ✅                                 │
│     invocations.add(Invocation{method=exchange, ...}) │
│                                                       │
│ [3] 실제 로직 실행? ❌ HTTP 요청 없음                │
│ [4] mockResponse 반환 ✅                              │
└───────────────────────────────────────────────────────┘
```

### Step 4: verify + ArgumentCaptor

```java
ArgumentCaptor<HttpEntity> entityCaptor = ArgumentCaptor.forClass(HttpEntity.class);

verify(restTemplate).exchange(
    contains("/tag"),
    eq(HttpMethod.GET),
    entityCaptor.capture(),  // ← 이 순간 뭐가 일어나나?
    any(),
    anyMap()
);
```

**verify가 하는 일:**
```
[1] verify(restTemplate) → "verification 모드" ON
[2] exchange(..., entityCaptor.capture(), ...) → InvocationMatcher 생성
[3] MockHandler에서 invocations 검색
    → 매칭된 invocation 찾음
    → arg[2]를 entityCaptor에 저장 (capture)
[4] entityCaptor.getValue() → 저장된 값 반환: HttpEntity@123abc
```

---

## ArgumentCaptor 사용 가이드

### 기본 흐름

**Step 1: Captor 생성**
```java
ArgumentCaptor<HttpEntity> entityCaptor = ArgumentCaptor.forClass(HttpEntity.class);
ArgumentCaptor<Map> paramsCaptor = ArgumentCaptor.forClass(Map.class);
// 아직 비어있음 (value: null)
```

**Step 2: 서비스 실행 (Mock 호출 기록 저장)**
```java
amsArticleTagService.getArticleTagListFromAms(article);
// 내부에서 restTemplate.exchange(url, GET, requestEntity, ref, params) 호출
// Mock이 인자들을 호출 기록에 저장
```

**Step 3: verify + capture**
```java
verify(restTemplate).exchange(
    contains("/tag"),
    eq(HttpMethod.GET),
    entityCaptor.capture(),  // Mock 기록에서 arg[2] → entityCaptor에 저장
    any(ParameterizedTypeReference.class),
    paramsCaptor.capture()   // Mock 기록에서 arg[4] → paramsCaptor에 저장
);
```

**Step 4: getValue()로 꺼내기**
```java
HttpEntity capturedEntity = entityCaptor.getValue();
Map<String, String> capturedParams = paramsCaptor.getValue();
```

**Step 5: 검증**
```java
HttpHeaders headers = capturedEntity.getHeaders();
assertEquals("BATCH_SYSTEM", headers.getFirst("X-Batch-User-Id"));
assertEquals("application/json", headers.getFirst("Content-Type"));
assertEquals("A2026020513000005239", capturedParams.get("articleId"));
```

### 여러 번 호출 시 모든 값 캡처

```java
@Test
public void 여러번_호출_캡처() {
    service.process("item1");
    service.process("item2");
    service.process("item3");

    ArgumentCaptor<String> captor = ArgumentCaptor.forClass(String.class);
    verify(mockRepository, times(3)).save(captor.capture());

    List<String> allValues = captor.getAllValues();
    assertEquals(3, allValues.size());
    assertTrue(allValues.contains("item1"));
}
```

---

## ArgumentCaptor vs ArgumentMatcher

### ArgumentMatcher (any(), eq(), contains() 등)

```java
verify(restTemplate).exchange(
    contains("/tag"),       // 매칭만 함 (값은 가져올 수 없음)
    eq(HttpMethod.GET),
    any(),
    any(),
    anyMap()
);
// "이런 조건으로 호출되었나?"만 확인
```

### ArgumentCaptor

```java
ArgumentCaptor<HttpEntity> captor = ArgumentCaptor.forClass(HttpEntity.class);

verify(restTemplate).exchange(
    anyString(),
    any(),
    captor.capture(),   // 매칭 + 캡처!
    any(),
    anyMap()
);

HttpEntity actual = captor.getValue();   // 실제 값 가져옴!
assertEquals("BATCH_SYSTEM", actual.getHeaders().getFirst("X-Batch-User-Id"));
```

### 비교표

| 항목 | ArgumentMatcher | ArgumentCaptor |
|------|----------------|----------------|
| 목적 | 호출 조건 검증 | 실제 전달된 값 캡처 |
| 값 확인 | 불가 | `getValue()` / `getAllValues()` |
| 사용 시점 | 단순 조건 확인 | 내부 필드 값까지 검증 필요할 때 |

### 언제 ArgumentCaptor를 사용하나?

**ArgumentMatcher만으로 충분한 경우:**
```java
verify(restTemplate).exchange(
    contains("/tag"),        // URL에 "/tag"만 포함되면 OK
    eq(HttpMethod.GET),
    any(),                   // HttpEntity는 뭐든 OK
    any(),
    anyMap()
);
```

**ArgumentCaptor가 필요한 경우:**
```java
// Header의 특정 값까지 검증하고 싶을 때
ArgumentCaptor<HttpEntity> captor = ArgumentCaptor.forClass(HttpEntity.class);
verify(restTemplate).exchange(..., captor.capture(), ...);

HttpEntity entity = captor.getValue();
assertEquals("BATCH_SYSTEM", entity.getHeaders().getFirst("X-Batch-User-Id"));

// Map의 각 키-값까지 검증하고 싶을 때
ArgumentCaptor<Map> paramsCaptor = ArgumentCaptor.forClass(Map.class);
verify(restTemplate).exchange(..., paramsCaptor.capture());
assertEquals("A2026020513000005239", paramsCaptor.getValue().get("articleId"));
```

---

## 타임라인 요약

```
시간 →

[T1] Mock 설정
     when(restTemplate.exchange(...)).thenReturn(mockResponse)
     → StubbedInvocationMatcher 저장

[T2] 서비스 실행
     service.getArticleTagListFromAms(article)
     → HttpEntity 생성 ✅
     → Map 생성 ✅
     → restTemplate.exchange(url, GET, entity, ref, params) 호출 ✅
     → Mock이 인자들 저장 ✅
     → HTTP 요청은 안 함 ❌
     → mockResponse 반환 ✅

[T3] verify + capture
     verify(restTemplate).exchange(..., captor.capture(), ...)
     → 저장된 기록에서 arg[2]를 captor에 복사 ✅

[T4] getValue()
     HttpEntity entity = captor.getValue()
     → T2에서 생성된 그 HttpEntity 객체!
```

---

## 핵심 정리

### Q: Mock은 어디까지 수행되는가?
**A:**
- ✅ 메서드 호출은 받음
- ✅ 인자들도 받음 (실제 객체!)
- ✅ 호출 기록 저장
- ❌ 메서드 내부 로직은 실행 안 함 (HTTP 요청 없음)
- ✅ when-thenReturn의 값만 반환

### Q: verify는 인자가 전달되는 순간에 캡처하는 건가?
**A: 아닙니다.** Mock은 호출 시점에 인자를 저장하고, verify는 나중에 저장된 기록을 확인해서 Captor에 복사합니다. CCTV 영상을 나중에 재생하는 것과 같습니다.

### ArgumentCaptor 동작 순서
```
Captor 생성 → 서비스 실행 → Mock 호출 → verify + capture → getValue → 검증
```
