# @InjectMocks 주입 조건과 Builder 패턴의 함정

## @InjectMocks 동작 원리

Mockito의 `@InjectMocks`는 다음 순서로 Mock을 주입한다:

1. **생성자 주입** (Constructor Injection) - 우선순위 1
2. **세터 주입** (Setter Injection) - 우선순위 2
3. **필드 주입** (Field Injection) - 우선순위 3

중요한 점: **생성자의 파라미터 타입과 @Mock 필드의 타입이 일치해야 주입된다.**

---

## Case 1: 자동 주입이 되는 경우 ✅

생성자가 의존 객체를 직접 받는 경우:

```java
public class AmsArticleTagService {
    private final RestTemplate restTemplate;

    public AmsArticleTagService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;  // 파라미터를 그대로 저장
    }
}
```

테스트 코드:

```java
@RunWith(MockitoJUnitRunner.class)
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;  // 타입: RestTemplate

    @InjectMocks
    private AmsArticleTagService service;  // 자동 주입 ✅

    @Test
    public void test() {
        // service.restTemplate에 자동으로 Mock이 들어가 있음
        assertNotNull(service);
    }
}
```

**왜 되는가?**
- 생성자 파라미터: `RestTemplate`
- @Mock 필드 타입: `RestTemplate`
- 타입이 일치 → @InjectMocks가 생성자 호출 시 자동 주입 ✅

---

## Case 2: 자동 주입이 안 되는 경우 ❌ (Builder 패턴)

실제 `AmsArticleTagService`는 생성자에서 `RestTemplateBuilder`를 받아 `RestTemplate`을 직접 생성한다:

```java
public class AmsArticleTagService {
    private final RestTemplate restTemplate;

    public AmsArticleTagService(RestTemplateBuilder builder) {
        this.restTemplate = builder
                .setConnectTimeout(Duration.ofSeconds(10))
                .setReadTimeout(Duration.ofSeconds(10))
                .build();  // ← 새로운 RestTemplate 생성!
    }
}
```

테스트 코드:

```java
@RunWith(MockitoJUnitRunner.class)
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;  // 타입: RestTemplate

    @InjectMocks
    private AmsArticleTagService service;  // ❌ Mock이 주입되지 않음!
}
```

**@InjectMocks의 동작 과정:**

1. `AmsArticleTagService` 생성자를 찾음: `public AmsArticleTagService(RestTemplateBuilder builder)`
2. 파라미터로 `RestTemplateBuilder`가 필요함을 확인
3. @Mock 필드 중에서 `RestTemplateBuilder` 타입을 찾음 → **없음**
4. **Mockito가 자동으로 `new RestTemplateBuilder()` 생성** (기본 생성자가 있으므로)
5. 생성자 실행: `this.restTemplate = builder.build();` → **실제 RestTemplate 생성!**
6. **결과: `service.restTemplate`은 Mock이 아니라 실제 RestTemplate!**

### 핵심 문제: 필드의 Mock이 무시된다

```
테스트 클래스의 상태:
┌─────────────────────────────────────┐
│ @Mock                               │
│ private RestTemplate restTemplate   │  ← Mock 객체 (고아 상태)
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ @InjectMocks                        │
│ private AmsArticleTagService        │
│   ├─ restTemplate ────────────┐    │
│   │                            │    │
│   └─ "실제" RestTemplate ◄────┘    │  ← builder.build()로 생성된 실제 객체
└─────────────────────────────────────┘
```

**@Mock으로 만든 RestTemplate과 service 안의 RestTemplate은 다른 객체!**

따라서 이렇게 Mock 설정을 해도:
```java
when(restTemplate.exchange(...)).thenReturn(mockResponse);
```
실제로는 `service` 내부의 "실제 RestTemplate"이 실행되므로 Mock이 동작하지 않는다.

---

## 해결 방법 4가지

### 방법 1: @InjectMocks만 사용 (❌ 실패)

```java
@Mock
private RestTemplate restTemplate;  // 이건 안 쓰임

@InjectMocks
private AmsArticleTagService service;  // RestTemplate이 실제 객체가 됨

@Test
public void test() {
    when(restTemplate.exchange(...)).thenReturn(...);  // ❌ 동작 안 함 (다른 객체)
    service.getArticleTagListFromAms(article);  // 실제 HTTP 요청 발생!
}
```

**문제점:**
- `service.restTemplate` = 실제 RestTemplate (외부 HTTP 요청 시도)
- `@Mock restTemplate` = Mock 객체 (사용되지 않음)
- 테스트가 실패하거나 실제 네트워크 요청 발생

---

### 방법 2: @InjectMocks 없이 직접 생성 + 리플렉션 (✅ 권장)

```java
@Mock
private RestTemplate restTemplate;

private AmsArticleTagService service;  // @InjectMocks 제거

@Before
public void setUp() {
    // @RunWith(MockitoJUnitRunner.class)가 이미 Mock 초기화하므로 initMocks() 불필요
    service = new AmsArticleTagService(new RestTemplateBuilder());

    // Mock으로 교체 (핵심!)
    ReflectionTestUtils.setField(service, "restTemplate", restTemplate);
    ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake-ams.com");
}

@Test
public void test() {
    when(restTemplate.exchange(...)).thenReturn(...);  // ✅ 동작함
    service.getArticleTagListFromAms(article);
}
```

**동작 원리:**
```
1. new AmsArticleTagService(builder)
   → service.restTemplate = builder.build() (실제 객체)

2. ReflectionTestUtils.setField(service, "restTemplate", restTemplate)
   → service.restTemplate = @Mock restTemplate (Mock으로 교체!)
```

**장점:** 간단하고 명확함. 의도가 분명하고 디버깅하기 쉬움.

---

### 방법 3: RestTemplateBuilder도 Mock으로 (✅ 가능하지만 복잡)

```java
@Mock
private RestTemplateBuilder builder;

@Mock
private RestTemplate restTemplate;

@InjectMocks
private AmsArticleTagService service;

@Before
public void setUp() {
    // Builder 체이닝 Mock 설정
    when(builder.setConnectTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.setReadTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.build()).thenReturn(restTemplate);

    ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake-ams.com");
}

@Test
public void test() {
    when(restTemplate.exchange(...)).thenReturn(...);  // ✅ 동작함
    service.getArticleTagListFromAms(article);
}
```

**동작 원리:**
```
1. @InjectMocks가 생성자 호출: new AmsArticleTagService(mockBuilder)
2. 생성자 내부: this.restTemplate = mockBuilder.build()
3. mockBuilder.build()가 mockRestTemplate 반환 (when 설정에 의해)
4. 결과: service.restTemplate = @Mock restTemplate ✅
```

**장점:** @InjectMocks를 그대로 사용.
**단점:** 빌더 체이닝 Mock 설정이 복잡함.

---

### 방법 4: 생성자를 RestTemplate 받도록 변경 (프로덕션 코드 수정)

```java
// AmsArticleTagService.java 수정
@Service
public class AmsArticleTagService {
    private final RestTemplate restTemplate;

    public AmsArticleTagService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }
}

// Config에서 RestTemplate Bean 등록
@Configuration
public class RestTemplateConfig {
    @Bean
    public RestTemplate amsRestTemplate() {
        return new RestTemplateBuilder()
                .setConnectTimeout(Duration.ofSeconds(10))
                .setReadTimeout(Duration.ofSeconds(10))
                .build();
    }
}
```

테스트:
```java
@Mock
private RestTemplate restTemplate;

@InjectMocks
private AmsArticleTagService service;  // ✅ 완벽하게 동작!
```

**장점:** 테스트하기 가장 쉬움, DI 원칙에도 부합.
**단점:** 프로덕션 코드를 수정해야 함.

---

## 결론

| 방법 | @InjectMocks | RestTemplate이 Mock? | 복잡도 |
|------|--------------|---------------------|--------|
| 방법 1: @InjectMocks만 | O | ❌ 실제 객체 | 간단 (하지만 실패) |
| 방법 2: 직접 생성 + 리플렉션 | X | ✅ Mock | 간단 ⭐ |
| 방법 3: Builder도 Mock | O | ✅ Mock | 복잡 |
| 방법 4: 프로덕션 코드 수정 | O | ✅ Mock | 중간 |

**추천: 방법 2 (직접 생성 + 리플렉션)**
- @InjectMocks를 포기하지만 코드가 명확함
- ReflectionTestUtils로 Mock을 확실하게 주입
- 의도가 명확하고 디버깅하기 쉬움

---

## 핵심 개념 정리

| 상황 | @InjectMocks 자동 주입 |
|------|---------------------|
| 생성자 파라미터 = @Mock 타입 | ✅ 자동 주입됨 |
| 생성자 파라미터 ≠ @Mock 타입 | ❌ 주입 안 됨 |

**@InjectMocks는 생성자 파라미터만 주입하지, 생성자 내부의 동작은 제어하지 못한다!**

생성자가 파라미터를 그대로 저장하면 성공, Builder처럼 내부에서 새 객체를 만들면 Mock이 끊긴다.
