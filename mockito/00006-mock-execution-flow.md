# Mock 객체의 실행 흐름과 ArgumentCaptor

## 핵심 질문

1. Mock은 가짜 객체인데, 어디까지 수행되는가?
2. AmsArticleTagService에서 restTemplate.exchange()를 호출할 때, 실제 URL, requestEntity, parameter를 넣는 것까지 수행하는가?
3. Mock 객체에 인자를 전달해서 검증까지만 하는 건가?
4. verify는 인자가 전달되는 순간에 캡처하는 건가?

---

## 답변: Mock 객체의 동작 방식

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
// 이것이 Stubbing입니다!
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

**Stub = 가짜 구현체**

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

### 실제 예시

```java
// [1] Stubbing 설정
when(calculator.add(1, 2)).thenReturn(10);
// "add(1, 2) 호출되면 10을 반환하라"

// [2] 실제 호출
int result = calculator.add(1, 2);
// → Mock이 stubbing을 확인
// → "add(1, 2)"가 설정되어 있네?
// → 실제 덧셈 안 하고 그냥 10 반환
// result == 10 ✅
```

**핵심:**
- Stubbing = Mock 객체의 "대본"을 미리 써주는 것
- 실제 로직 실행 없이 원하는 값만 반환하게 설정
- 테스트를 빠르고 예측 가능하게 만듦

---

## Mockito의 내부 구조 (디버깅으로 확인 가능)

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

**이게 대체 뭐지? 어떻게 만들어진 거지?**

---

### Mockito의 Mock 생성 과정

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
    → public ResponseEntity exchange(...)
    → public ResponseEntity getForEntity(...)
    → ... 등등

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
    │     // 실제 로직 대신:                   │
    │     return mockHandler.handle(          │
    │         this,                            │
    │         "exchange",                      │
    │         new Object[]{arg0, arg1, ...}    │
    │     );                                   │
    │ }                                        │
    │                                          │
    │ @Override                                │
    │ public ResponseEntity getForEntity(...) {│
    │     return mockHandler.handle(...);      │
    │ }                                        │
    └──────────────────────────────────────────┘

[3] MockHandler 생성 및 연결
    MockHandler mockHandler = new MockHandlerImpl();
    mockInstance.mockHandler = mockHandler;
```

---

#### 2단계: MockHandler의 구조

```java
// 개념적 구조 (실제 Mockito 내부 코드 단순화)
class MockHandlerImpl implements MockHandler {
    // 1. Stubbing 저장소 (when-thenReturn 정보)
    private List<StubbedInvocationMatcher> stubbings = new ArrayList<>();

    // 2. 호출 기록 저장소
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

    private StubbedInvocationMatcher findMatchingStub(Invocation invocation) {
        for (StubbedInvocationMatcher stub : stubbings) {
            if (stub.matches(invocation)) {
                return stub;
            }
        }
        return null;
    }
}
```

---

#### 3단계: InvocationContainer의 구조

```java
class InvocationContainerImpl {
    // 모든 호출 기록을 순서대로 저장
    private List<Invocation> invocations = new ArrayList<>();

    public void recordInvocation(Invocation invocation) {
        invocations.add(invocation);
    }

    public List<Invocation> getInvocations() {
        return invocations;
    }
}

class Invocation {
    private Object mock;              // Mock 객체 참조
    private Method method;            // 호출된 메서드 (exchange)
    private Object[] arguments;       // 전달된 인자들 ← 여기에 저장됨!
    private int sequenceNumber;       // 호출 순서
    private Location location;        // 호출된 위치 (스택 트레이스)

    public Object getArgument(int index) {
        return arguments[index];
    }
}
```

---

### when-thenReturn의 동작 원리

```java
when(restTemplate.exchange(anyString(), any(), any(), any(), anyMap()))
    .thenReturn(mockResponse);
```

**Mockito가 하는 일:**

```
[1] when() 호출
    → Mockito를 "stubbing 모드"로 전환
    → 다음 Mock 메서드 호출을 기록하겠다고 표시

[2] restTemplate.exchange(...) 호출
    → 평소처럼 MockHandler.handle() 실행
    → 하지만 "stubbing 모드"이므로:
      - 호출 기록은 저장 안 함
      - 대신 InvocationMatcher 생성
        InvocationMatcher {
          method: exchange
          matchers: [anyString(), any(), any(), any(), anyMap()]
        }

[3] thenReturn(mockResponse) 호출
    → StubbedInvocationMatcher 생성:
      StubbedInvocationMatcher {
        invocationMatcher: 위에서 만든 InvocationMatcher
        answer: Returns(mockResponse)
      }
    → MockHandler.stubbings에 추가
    → "stubbing 모드" 종료
```

**결과: MockHandler 내부 상태**

```
MockHandler {
  stubbings: [
    StubbedInvocationMatcher {
      matches: exchange(anyString(), any(), any(), any(), anyMap())
      answer: Returns(mockResponse)
    }
  ]
  invocations: []  ← 아직 비어있음
}
```

---

### 실제 Mock 메서드 호출 시

```java
// 서비스에서 호출
service.getArticleTagListFromAms(article);

// 내부에서:
restTemplate.exchange(
    "http://ams-api/tag?articleId={articleId}",
    HttpMethod.GET,
    requestEntity,
    new ParameterizedTypeReference<AmsResponseDto<AmsTag>>() {},
    params
)
```

**흐름:**

```
[1] RestTemplate$MockitoMock$1234567890.exchange(...) 호출
    ↓
[2] MockHandler.handle(this, "exchange", [url, GET, entity, ref, params])
    ↓
[3] Invocation 생성
    Invocation {
      mock: restTemplate@abc123
      method: exchange
      arguments: [
        "http://ams-api/tag?articleId={articleId}",  ← arg[0]
        GET,                                           ← arg[1]
        HttpEntity@123abc,                             ← arg[2] (이걸 나중에 캡처!)
        ParameterizedTypeReference@456def,             ← arg[3]
        HashMap@789ghi                                 ← arg[4]
      ]
      sequenceNumber: 1
    }
    ↓
[4] invocationContainer.recordInvocation(invocation)
    invocations.add(invocation)  ← 여기에 저장됨!
    ↓
[5] findMatchingStub(invocation)
    stubbings[0].matches(invocation)?
    → anyString() matches "http://..."? ✅
    → any() matches GET? ✅
    → any() matches HttpEntity@123abc? ✅
    → any() matches ParameterizedTypeRef@456def? ✅
    → anyMap() matches HashMap@789ghi? ✅
    → 매칭 성공! ✅
    ↓
[6] stubbing.answer(invocation)
    return mockResponse;  ← thenReturn에서 지정한 값
```

---

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
[1] verify(restTemplate) 호출
    → Mockito를 "verification 모드"로 전환
    → MockHandler를 가져옴

[2] exchange(..., entityCaptor.capture(), ...) 호출
    → MockHandler.handle() 실행
    → 하지만 "verification 모드"이므로:
      - 실제 메서드 실행 안 함
      - 대신 InvocationMatcher 생성:
        InvocationMatcher {
          method: exchange
          matchers: [
            contains("/tag"),
            eq(GET),
            capturesTo(entityCaptor),  ← ArgumentCaptor 포함!
            any(),
            anyMap()
          ]
        }

[3] MockHandler에서 invocations 검색
    for (Invocation inv : invocationContainer.getInvocations()) {
      if (matches(inv, invocationMatcher)) {
        // 매칭된 invocation 찾음!

        // ArgumentCaptor 처리
        for (int i = 0; i < matchers.length; i++) {
          if (matchers[i] instanceof CapturesArguments) {
            // arg[2]를 entityCaptor에 저장
            entityCaptor.capture(inv.getArgument(i));
          }
        }

        return;  // 검증 성공
      }
    }

    // 매칭 안 되면: WantedButNotInvoked 예외 발생

[4] entityCaptor.getValue()
    → 저장된 값 반환: HttpEntity@123abc
```

---

### 디버깅 시 실제로 보이는 구조

```
restTemplate: RestTemplate$MockitoMock$1234567890@abc123
  │
  ├─ mockHandler: MockHandlerImpl@def456
  │   │
  │   ├─ stubbings: ArrayList
  │   │   └─ [0]: StubbedInvocationMatcher
  │   │       ├─ invocationMatcher: InvocationMatcher
  │   │       │   └─ matchers: [anyString(), any(), any(), any(), anyMap()]
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
      └─ handler: mockHandler (위와 동일한 객체 참조)
```

---

### 핵심 정리: Mockito의 동작 원리

#### Mock 객체 생성

```
원본 클래스 (RestTemplate)
    ↓ ByteBuddy로 바이트코드 조작
동적 생성된 서브클래스 (RestTemplate$MockitoMock$...)
    ↓ 모든 메서드 오버라이드
MockHandler.handle()로 라우팅
```

#### when-thenReturn

```
when()               → stubbing 모드 ON
mock.method(...)     → InvocationMatcher 생성
thenReturn(value)    → StubbedInvocationMatcher 저장
                     → stubbing 모드 OFF
```

#### 실제 호출

```
mock.method(args)         → MockHandler.handle()
                          → Invocation 생성 (인자 저장!)
                          → invocations에 추가
                          → stubbing 찾기
                          → thenReturn 값 반환
```

#### verify + capture

```
verify(mock)              → verification 모드 ON
mock.method(captor.capture()) → InvocationMatcher 생성
                          → invocations 검색
                          → 매칭되는 Invocation 찾기
                          → Invocation.arguments[i]를 Captor에 복사
                          → verification 모드 OFF

captor.getValue()         → 저장된 인자 반환
```

---

### 왜 이렇게 복잡하게?

**이유 1: 타입 안전성**
- 원본 클래스를 상속하므로 타입 체크 통과
- `RestTemplate mock = ...`로 할당 가능

**이유 2: 유연한 Stubbing**
- ArgumentMatcher로 다양한 조건 지원
- anyString(), eq(), contains() 등

**이유 3: 상세한 검증**
- 모든 호출 기록 저장
- 순서, 횟수, 인자 검증 가능

**이유 4: IDE 지원**
- 메서드 자동완성 동작
- 컴파일 타임 체크

---

## 실행 흐름 상세 분석

### 코드 예시

```java
// 테스트 코드
@Test
public void test() {
    // 1. Mock 설정
    when(restTemplate.exchange(anyString(), any(), any(), any(), anyMap()))
        .thenReturn(mockResponse);

    // 2. 서비스 실행
    service.getArticleTagListFromAms(article);

    // 3. verify
    verify(restTemplate).exchange(...);
}
```

---

### Step-by-Step 실행 과정

#### Step 1: Mock 생성 및 설정

```java
@Mock
private RestTemplate restTemplate;  // 가짜 RestTemplate 생성

when(restTemplate.exchange(anyString(), any(), any(), any(), anyMap()))
    .thenReturn(mockResponse);
```

**Mock의 상태:**
```
┌────────────────────────────────┐
│ Mock RestTemplate              │
│                                │
│ - 모든 메서드가 빈 껍데기     │
│ - exchange() 호출 시:          │
│   → mockResponse 반환하라고 등록│
│ - 호출 기록: (비어있음)        │
└────────────────────────────────┘
```

---

#### Step 2: 서비스 메서드 실행

```java
service.getArticleTagListFromAms(article);
```

**서비스 내부에서 일어나는 일:**

```java
public List<RArticleTag> getArticleTagListFromAms(RArticle rArticle) {
    // ==========================================
    // 1단계: 실제 코드 실행 ✅
    // ==========================================

    HttpHeaders requestHeader = new HttpHeaders();
    requestHeader.add("X-Batch-User-Id", "BATCH_SYSTEM");  // ✅ 실행됨
    requestHeader.set("Content-Type", "application/json");  // ✅ 실행됨

    HttpEntity<Object> requestEntity = new HttpEntity<>(null, requestHeader);  // ✅ 실행됨

    Map<String, String> params = new HashMap<>();
    params.put("articleId", rArticle.getArticleId());  // ✅ 실행됨

    // ==========================================
    // 2단계: Mock 메서드 호출 ✅
    // ==========================================

    ResponseEntity<AmsResponseDto<AmsTag>> response = this.restTemplate.exchange(
        amsServiceUrl + AmsRequestPath.TAG + "?articleId={articleId}",  // ✅ 문자열 생성됨!
        HttpMethod.GET,                                                  // ✅ 전달됨!
        requestEntity,                                                   // ✅ 전달됨!
        new ParameterizedTypeReference<AmsResponseDto<AmsTag>>() {},     // ✅ 생성되고 전달됨!
        params                                                           // ✅ 전달됨!
    );

    // ⚠️ 중요: 이 시점에서 무슨 일이 일어나는가?

    // ==========================================
    // 3단계: 반환값 처리 ✅
    // ==========================================

    if (!isRequestSuccessful(response.getBody())) {  // ✅ 실행됨
        return new ArrayList<>();
    }

    return response.getBody().getData().getList()  // ✅ 실행됨
        .stream()
        .map(tag -> new RArticleTag(...))
        .collect(Collectors.toList());
}
```

---

#### Step 3: Mock 메서드 호출 시 내부 동작

```java
this.restTemplate.exchange(
    "http://ams-api/tag?articleId={articleId}",  // arg[0]
    HttpMethod.GET,                               // arg[1]
    requestEntity,                                // arg[2]
    new ParameterizedTypeReference<...>() {},     // arg[3]
    params                                        // arg[4]
)
```

**Mock이 하는 일:**

```
┌───────────────────────────────────────────────────────┐
│ Mock RestTemplate.exchange() 호출됨!                  │
├───────────────────────────────────────────────────────┤
│                                                       │
│ [1] 메서드 호출 받음                                  │
│     exchange() 메서드가 호출되었구나!                │
│                                                       │
│ [2] 인자들 받음 ✅                                    │
│     - arg[0] = "http://ams-api/tag?articleId={...}"  │
│     - arg[1] = GET                                    │
│     - arg[2] = HttpEntity 객체 (실제 객체!)          │
│     - arg[3] = ParameterizedTypeReference 객체       │
│     - arg[4] = Map 객체 (실제 객체!)                 │
│                                                       │
│ [3] 호출 기록 저장 ✅                                 │
│     ┌─────────────────────────────────────────────┐  │
│     │ 호출 기록 저장소                            │  │
│     │ ┌─────────────────────────────────────────┐ │  │
│     │ │ exchange() 호출 #1                      │ │  │
│     │ │ - timestamp: ...                        │ │  │
│     │ │ - arg[0]: "http://ams-api/..."         │ │  │
│     │ │ - arg[1]: GET                           │ │  │
│     │ │ - arg[2]: HttpEntity@123abc ◄──────────┼─┼──┼─ 이 객체 저장!
│     │ │ - arg[3]: ParameterizedTypeRef@456def  │ │  │
│     │ │ - arg[4]: HashMap@789ghi ◄─────────────┼─┼──┼─ 이 객체 저장!
│     │ └─────────────────────────────────────────┘ │  │
│     └─────────────────────────────────────────────┘  │
│                                                       │
│ [4] 실제 로직 실행? ❌ NO!                           │
│     - HTTP 요청 보내지 않음                          │
│     - RestTemplate의 실제 exchange() 로직 실행 안 함│
│     - 네트워크 통신 없음                             │
│                                                       │
│ [5] when-thenReturn에서 지정한 값 반환 ✅           │
│     return mockResponse;                             │
│                                                       │
└───────────────────────────────────────────────────────┘
```

**핵심:**
1. ✅ **서비스 코드는 모두 실행됨** (HttpEntity 생성, Map 생성, URL 문자열 생성)
2. ✅ **Mock 메서드 호출 자체는 일어남**
3. ✅ **인자들도 모두 평가되고 전달됨** (실제 객체들이 Mock에 전달됨)
4. ❌ **Mock 메서드의 내부 로직만 실행 안 됨** (HTTP 요청 안 함)
5. ✅ **Mock은 호출 기록을 저장함**
6. ✅ **when-thenReturn의 mockResponse를 바로 반환**

---

#### Step 4: verify 실행 (나중에)

```java
// 서비스 실행은 이미 끝남!
// Mock의 호출 기록은 이미 저장되어 있음!

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
┌─────────────────────────────────────────────────────┐
│ verify(restTemplate).exchange(...)                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│ [1] Mock의 저장된 호출 기록 확인                    │
│     "restTemplate.exchange()가 호출되었나?"         │
│     → 네, 있습니다! (Step 3에서 저장됨)            │
│                                                     │
│ [2] 조건 확인                                       │
│     - arg[0] contains "/tag"? → ✅                 │
│     - arg[1] == GET? → ✅                          │
│     - arg[2]를 entityCaptor에 저장!               │
│     - arg[3] instanceof ParameterizedTypeRef? → ✅ │
│     - arg[4] instanceof Map? → ✅                  │
│                                                     │
│ [3] ArgumentCaptor에 값 복사                        │
│     ┌───────────────────────────────────────┐      │
│     │ Mock 호출 기록                        │      │
│     │ - arg[2]: HttpEntity@123abc          │      │
│     └───────────────┬─────────────────────┬─┘      │
│                     │                     │        │
│                     │ 복사                │        │
│                     ↓                     │        │
│     ┌───────────────────────────────────┐ │        │
│     │ entityCaptor                      │ │        │
│     │ value: HttpEntity@123abc ◄────────┘ │        │
│     └───────────────────────────────────┘           │
│                                                     │
│     ⚠️ 중요: "전달되는 순간"이 아니라               │
│              "verify 실행 시점"에 기록에서 꺼내옴! │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

#### Step 5: getValue()로 꺼내기

```java
HttpEntity capturedEntity = entityCaptor.getValue();
```

**이제 실제로 전달된 객체를 가져옴:**

```
entityCaptor.getValue()
    ↓
HttpEntity@123abc  (Step 2-1단계에서 생성된 그 객체!)
    ↓
headers.getFirst("X-Batch-User-Id")
    ↓
"BATCH_SYSTEM"  ✅
```

---

## 타임라인 요약

```
시간 →

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
서비스 실행 단계 (when 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[시간 T1] 서비스 코드 실행
    ✅ HttpEntity 생성
    ✅ Map 생성
    ✅ URL 문자열 생성

[시간 T2] Mock 메서드 호출
    ✅ restTemplate.exchange(url, GET, entity, ref, params) 호출
    ✅ 인자들 전달됨 (실제 객체들!)
    ✅ Mock이 호출 기록 저장:
       ┌─────────────────────────┐
       │ arg[2] = HttpEntity@123 │ ◄─── 여기 저장됨!
       │ arg[4] = Map@789        │
       └─────────────────────────┘
    ❌ HTTP 요청은 안 함
    ✅ mockResponse 반환

[시간 T3] 반환값 처리
    ✅ mockResponse를 가공해서 결과 반환

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
검증 단계 (verify 실행)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[시간 T4] verify + capture
    ✅ Mock의 호출 기록 확인 (T2에서 저장된 것)
    ✅ arg[2]를 entityCaptor에 복사
       entityCaptor.value = HttpEntity@123

[시간 T5] getValue()
    ✅ entityCaptor에서 꺼냄
    ✅ HttpEntity@123 반환 (T1에서 생성된 그 객체!)

[시간 T6] 검증
    ✅ headers.getFirst("X-Batch-User-Id") == "BATCH_SYSTEM"
```

---

## 핵심 정리

### Q1: Mock은 어디까지 수행되는가?

**A:**
- ✅ 메서드 호출은 받음
- ✅ 인자들도 받음
- ✅ 호출 기록 저장
- ❌ 메서드 내부 로직은 실행 안 함 (HTTP 요청 안 함)
- ✅ when-thenReturn의 값만 반환

---

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

---

### Q3: Mock 객체에 인자를 전달해서 검증까지만 하는 건가?

**A: 조금 다릅니다.**

1. 서비스 실행 시: Mock에 인자 전달 + 호출 기록 저장
2. verify 실행 시: 저장된 기록을 확인 + Captor에 복사
3. getValue() 실행 시: Captor에서 꺼내서 검증

**Mock은:**
- 인자를 받아서 저장만 함
- 검증은 나중에 verify/getValue()에서 함

---

### Q4: verify는 인자가 전달되는 순간에 캡처하는 건가?

**A: 아닙니다! verify는 "나중에" 저장된 기록을 확인합니다.**

```
[서비스 실행 시]
    restTemplate.exchange(..., requestEntity, ...)
    → Mock이 requestEntity를 받아서 저장 ✅

                [시간 경과...]

[verify 실행 시]
    verify(restTemplate).exchange(..., captor.capture(), ...)
    → 저장된 기록에서 requestEntity를 꺼내서 Captor에 복사 ✅

[getValue() 실행 시]
    HttpEntity entity = captor.getValue()
    → Captor에서 꺼냄 ✅
```

**capture()는:**
- "인자가 전달되는 순간"에 캡처하는 게 아니라
- "verify 실행 시점"에 이미 저장된 기록에서 꺼내오는 것

---

## 비유

### 감시 카메라 비유

```
[서비스 실행] = 범인이 범죄 현장에서 행동
    - 범인이 실제로 행동함 ✅
    - CCTV가 녹화함 ✅

[verify 실행] = 나중에 CCTV 영상 재생
    - 녹화된 영상을 확인 ✅
    - 특정 프레임을 캡처 ✅

[getValue()] = 캡처한 이미지 분석
    - 캡처한 이미지를 자세히 봄 ✅
```

**Mock = CCTV**
- 모든 호출을 녹화
- 나중에 재생해서 확인 가능

---

## 실제 예시

```java
// T1: Mock 설정
when(restTemplate.exchange(...)).thenReturn(mockResponse);

// T2: 서비스 실행
service.getArticleTagListFromAms(article);
// → HttpEntity 생성 ✅
// → Map 생성 ✅
// → restTemplate.exchange(url, GET, entity, ref, params) 호출 ✅
// → Mock이 인자들 저장 ✅
// → HTTP 요청은 안 함 ❌
// → mockResponse 반환 ✅

// T3: 검증 준비
ArgumentCaptor<HttpEntity> captor = ArgumentCaptor.forClass(HttpEntity.class);

// T4: verify (Mock의 녹화 기록 재생)
verify(restTemplate).exchange(..., captor.capture(), ...);
// → "exchange()가 호출되었나?" 확인 ✅
// → 저장된 arg[2]를 captor에 복사 ✅

// T5: 값 꺼내기
HttpEntity entity = captor.getValue();
// → T2에서 생성된 그 HttpEntity 객체!

// T6: 검증
assertEquals("BATCH_SYSTEM", entity.getHeaders().getFirst("X-Batch-User-Id"));
// → T2에서 설정한 그 값!
```

---

## 최종 답변

**Q: Mock은 어디까지 수행되는가?**
A: 서비스 코드는 모두 실행되고, Mock 메서드도 호출되며, 인자들도 모두 전달됩니다. 단지 Mock 메서드의 "내부 로직"(HTTP 요청)만 실행되지 않습니다.

**Q: verify는 인자가 전달되는 순간에 캡처하는가?**
A: 아닙니다. Mock은 호출 시점에 인자를 저장하고, verify는 나중에 저장된 기록을 "회상"해서 Captor에 복사합니다. 마치 CCTV 영상을 나중에 재생하는 것과 같습니다.
