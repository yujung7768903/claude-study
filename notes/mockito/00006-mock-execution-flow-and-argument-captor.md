# Mock 객체의 실행 흐름과 ArgumentCaptor

## 핵심 질문

1. Mock은 가짜 객체인데, 어디까지 수행되는가?
2. restTemplate.exchange()를 호출할 때, 실제 URL, requestEntity, parameter를 넣는 것까지 수행하는가?
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

### Stubbing vs 실제 호출

#### 1. Stubbing 단계 (설정)
```java
when(mock.method(...))  // ← "이 메서드가 호출되면"
    .thenReturn(value);  // ← "이 값을 반환하라"
```
- Mock 객체에게 "시나리오"를 알려주는 것
- 아직 실제 호출은 안 됨
- MockHandler의 stubbings 리스트에 저장됨

#### 2. 실제 호출 단계
```java
service.getArticleTagListFromAms(article);
// 내부에서 restTemplate.exchange() 호출
```
- Mock이 저장된 stubbing을 찾아봄
- 매칭되면 thenReturn에서 지정한 값 반환
- HTTP 요청은 실행 안 함

### 왜 "Stub"이라고 부를까?

영화 촬영에서:
- **진짜 총**: 실제로 발사됨 (위험!)
- **소품 총 (Stub)**: 발사 안 되고 그냥 들고만 있음

테스트에서:
- **진짜 RestTemplate**: HTTP 요청 보냄 (느리고 외부 의존)
- **Stub된 RestTemplate**: HTTP 요청 안 보내고 미리 정한 값만 반환 (빠르고 독립적)

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

### 디버깅에서 보이는 것

```
디버거로 restTemplate 객체를 확인하면:

restTemplate: RestTemplate$MockitoMock$1234567890@abc123
  ├─ mockHandler: MockHandlerImpl@def456
  ├─ mockitoInterceptor: MockitoInterceptor@ghi789
  └─ invocationContainer: InvocationContainerImpl@jkl012
      └─ invocations: ArrayList
          └─ [0]: Invocation{method=exchange, args=[...]}
```

### Mock 생성 과정

#### 1단계: 바이트코드 조작 (Bytecode Manipulation)

```java
@Mock
private RestTemplate restTemplate;
```

**Mockito가 하는 일:**

```
[1] 원본 클래스 분석
    RestTemplate.class 로딩
    → 모든 메서드 목록 추출

[2] 동적으로 서브클래스 생성 (ByteBuddy 사용)

    원본 클래스:
    ┌────────────────────────┐
    │ RestTemplate           │
    │ + exchange(...)        │
    │ + getForEntity(...)    │
    └────────────────────────┘
            ↓ 상속
    ┌──────────────────────────────────────────┐
    │ RestTemplate$MockitoMock$1234567890      │  ← 런타임에 동적 생성!
    │                                          │
    │ // 추가된 필드                           │
    │ private MockHandler mockHandler;         │
    │                                          │
    │ // 오버라이드된 메서드들                 │
    │ @Override                                │
    │ public ResponseEntity exchange(...) {    │
    │     return mockHandler.handle(          │
    │         this, "exchange",                │
    │         new Object[]{arg0, arg1, ...}    │
    │     );                                   │
    │ }                                        │
    └──────────────────────────────────────────┘

[3] MockHandler 생성 및 연결
    MockHandler mockHandler = new MockHandlerImpl();
    mockInstance.mockHandler = mockHandler;
```

#### 2단계: MockHandler의 구조

```java
class MockHandlerImpl implements MockHandler {
    private List<StubbedInvocationMatcher> stubbings = new ArrayList<>();
    private InvocationContainer invocationContainer = new InvocationContainerImpl();

    public Object handle(Object mock, Method method, Object[] args) {
        // 1. 현재 호출을 Invocation 객체로 만듦
        Invocation invocation = new Invocation(mock, method, args, SequenceNumber.next());

        // 2. 호출 기록 저장 (verify를 위해!)
        invocationContainer.recordInvocation(invocation);

        // 3. Stubbing 확인 (when-thenReturn이 있는지)
        StubbedInvocationMatcher stubbing = findMatchingStub(invocation);

        if (stubbing != null) {
            // 4. thenReturn 값 반환
            return stubbing.answer(invocation);
        } else {
            // 5. Stubbing 없으면 기본값 반환 (null, 0, false 등)
            return Defaults.defaultValue(method.getReturnType());
        }
    }
}
```

#### 3단계: InvocationContainer의 구조

```java
class InvocationContainerImpl {
    private List<Invocation> invocations = new ArrayList<>();

    public void recordInvocation(Invocation invocation) {
        invocations.add(invocation);
    }
}

class Invocation {
    private Object mock;
    private Method method;
    private Object[] arguments;  // 전달된 인자들 ← 여기에 저장됨!
    private int sequenceNumber;
    private Location location;

    public Object getArgument(int index) {
        return arguments[index];
    }
}
```

### when-thenReturn의 동작 원리

```java
when(restTemplate.exchange(anyString(), any(), any(), any(), anyMap()))
    .thenReturn(mockResponse);
```

**Mockito가 하는 일:**

```
[1] when() 호출
    → Mockito를 "stubbing 모드"로 전환

[2] restTemplate.exchange(...) 호출
    → "stubbing 모드"이므로:
      - 호출 기록은 저장 안 함
      - 대신 InvocationMatcher 생성
        InvocationMatcher {
          method: exchange
          matchers: [anyString(), any(), any(), any(), anyMap()]
        }

[3] thenReturn(mockResponse) 호출
    → StubbedInvocationMatcher 생성 후 MockHandler.stubbings에 추가
    → "stubbing 모드" 종료
```

### verify + ArgumentCaptor의 동작 원리

```java
ArgumentCaptor<HttpEntity> entityCaptor = ArgumentCaptor.forClass(HttpEntity.class);

verify(restTemplate).exchange(
    contains("/tag"),
    eq(HttpMethod.GET),
    entityCaptor.capture(),
    any(),
    anyMap()
);
```

**흐름:**

```
[1] verify(restTemplate) → "verification 모드" ON

[2] exchange(..., entityCaptor.capture(), ...) 호출
    → InvocationMatcher 생성:
      matchers: [contains("/tag"), eq(GET), capturesTo(entityCaptor), any(), anyMap()]

[3] MockHandler에서 invocations 검색
    → 매칭된 invocation 찾음
    → ArgumentCaptor 처리:
      entityCaptor.capture(inv.getArgument(2))
      → arg[2]를 entityCaptor에 저장

[4] entityCaptor.getValue()
    → 저장된 값 반환: HttpEntity@123abc
```

### 디버깅 시 실제로 보이는 구조

```
restTemplate: RestTemplate$MockitoMock$1234567890@abc123
  │
  ├─ mockHandler: MockHandlerImpl@def456
  │   │
  │   ├─ stubbings: ArrayList
  │   │   └─ [0]: StubbedInvocationMatcher
  │   │       ├─ matchers: [anyString(), any(), any(), any(), anyMap()]
  │   │       └─ answer: Returns(mockResponse)
  │   │
  │   └─ invocationContainer: InvocationContainerImpl
  │       └─ invocations: ArrayList
  │           └─ [0]: Invocation
  │               ├─ method: exchange
  │               └─ arguments: Object[5]
  │                   ├─ [0]: "http://ams-api/tag?articleId={...}"
  │                   ├─ [1]: GET
  │                   ├─ [2]: HttpEntity@123abc  ← ArgumentCaptor가 캡처할 객체!
  │                   ├─ [3]: ParameterizedTypeReference@456def
  │                   └─ [4]: HashMap@789ghi
  │
  └─ mockitoInterceptor: MockitoInterceptor@ghi789
```

### 핵심 정리: Mockito의 동작 원리

```
# Mock 객체 생성
원본 클래스 (RestTemplate)
    ↓ ByteBuddy로 바이트코드 조작
동적 생성된 서브클래스 (RestTemplate$MockitoMock$...)
    ↓ 모든 메서드 오버라이드
MockHandler.handle()로 라우팅

# when-thenReturn
when()               → stubbing 모드 ON
mock.method(...)     → InvocationMatcher 생성
thenReturn(value)    → StubbedInvocationMatcher 저장 → stubbing 모드 OFF

# 실제 호출
mock.method(args)    → Invocation 생성 (인자 저장!)
                     → invocations에 추가
                     → stubbing 찾기 → thenReturn 값 반환

# verify + capture
verify(mock)              → verification 모드 ON
mock.method(captor.capture()) → invocations 검색 → Invocation.arguments[i]를 Captor에 복사
captor.getValue()         → 저장된 인자 반환
```

---

## 실행 흐름 상세 분석

### Step 1: Mock 설정 (Stubbing)

```java
when(restTemplate.exchange(anyString(), any(), any(), any(), anyMap()))
    .thenReturn(mockResponse);
```

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
requestHeader.add("X-Batch-User-Id", "BATCH_SYSTEM");   // ✅
HttpEntity<Object> requestEntity = new HttpEntity<>(null, requestHeader);  // ✅
Map<String, String> params = new HashMap<>();
params.put("articleId", rArticle.getArticleId());       // ✅

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
    entityCaptor.capture(),
    any(),
    anyMap()
);
```

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

### Q1: Mock은 어디까지 수행되는가?

**A:**
- ✅ 메서드 호출은 받음
- ✅ 인자들도 받음 (실제 객체!)
- ✅ 호출 기록 저장
- ❌ 메서드 내부 로직은 실행 안 함 (HTTP 요청 없음)
- ✅ when-thenReturn의 값만 반환

### Q2: 실제 URL, requestEntity, parameter를 넣는 것까지 수행하는가?

**A: 네! 모두 수행됩니다!**

```java
// 이 코드들은 모두 실행됨 ✅
HttpEntity requestEntity = new HttpEntity(null, headers);  // 실제 객체 생성
Map<String, String> params = new HashMap<>();              // 실제 객체 생성
params.put("articleId", "A123");                          // 실제 Map에 값 추가
String url = amsServiceUrl + "/tag";                      // 실제 문자열 생성

// Mock 호출도 일어남 ✅
restTemplate.exchange(url, GET, requestEntity, ref, params);
// ↑ 이 줄이 실행되고, 인자들도 모두 전달됨!
// 단지 exchange() 내부의 HTTP 요청 로직만 실행 안 됨!
```

### Q3: Mock 객체에 인자를 전달해서 검증까지만 하는 건가?

**A: 조금 다릅니다.**

1. 서비스 실행 시: Mock에 인자 전달 + 호출 기록 저장
2. verify 실행 시: 저장된 기록을 확인 + Captor에 복사
3. getValue() 실행 시: Captor에서 꺼내서 검증

### Q4: verify는 인자가 전달되는 순간에 캡처하는 건가?

**A: 아닙니다.** Mock은 호출 시점에 인자를 저장하고, verify는 나중에 저장된 기록을 확인해서 Captor에 복사합니다.

**비유: CCTV**
- `[서비스 실행]` = 범인이 범죄 현장에서 행동 → CCTV가 녹화
- `[verify 실행]` = 나중에 CCTV 영상 재생 → 특정 프레임 캡처
- `[getValue()]` = 캡처한 이미지 분석

`capture()`는 "인자가 전달되는 순간"이 아니라 "verify 실행 시점"에 이미 저장된 기록에서 꺼내오는 것.

### ArgumentCaptor 동작 순서

```
Captor 생성 → 서비스 실행 → Mock 호출 → verify + capture → getValue → 검증
```
