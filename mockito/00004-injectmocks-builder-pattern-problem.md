# @InjectMocks에서 Builder 패턴의 함정

## 질문: @InjectMocks하면 RestTemplateBuilder가 알아서 생성되지 않나?

**답: 생성은 되지만, RestTemplate이 Mock이 아니게 됩니다! 🚨**

---

## 실험: @InjectMocks만 사용하면 어떻게 될까?

### 테스트 코드 A (잘못된 접근)

```java
@RunWith(MockitoJUnitRunner.class)
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;  // Mock 생성

    @InjectMocks
    private AmsArticleTagService service;  // 자동 주입

    @Before
    public void setUp() {
        ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake-ams.com");
    }

    @Test
    public void test() {
        // when().thenReturn() 설정
        when(restTemplate.exchange(...)).thenReturn(mockResponse);

        // 실행
        List<RArticleTag> result = service.getArticleTagListFromAms(article);

        // 결과는? ❌ Mock이 동작하지 않음!
    }
}
```

### 무슨 일이 일어났는가?

**@InjectMocks의 동작 과정:**

1. `AmsArticleTagService` 생성자를 찾음
   ```java
   public AmsArticleTagService(RestTemplateBuilder builder)
   ```

2. 파라미터로 `RestTemplateBuilder`가 필요함을 확인

3. @Mock 필드 중에서 `RestTemplateBuilder` 타입을 찾음 → **없음**

4. **Mockito가 자동으로 `new RestTemplateBuilder()` 생성** (기본 생성자가 있으므로)

5. 생성자 실행:
   ```java
   this.restTemplate = builder  // 실제 RestTemplateBuilder
           .setConnectTimeout(Duration.ofSeconds(10))
           .setReadTimeout(Duration.ofSeconds(10))
           .build();  // ← 실제 RestTemplate 생성! (Mock 아님)
   ```

6. **결과: `service.restTemplate`은 Mock이 아니라 실제 RestTemplate!**

---

## 핵심 문제: 필드의 Mock이 무시된다

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
│   └─ "실제" RestTemplate ◄────┘    │  ← 생성자에서 builder.build()로 생성된 실제 객체
└─────────────────────────────────────┘
```

**@Mock으로 만든 RestTemplate과 service 안의 RestTemplate은 다른 객체!**

따라서 이렇게 Mock 설정을 해도:
```java
when(restTemplate.exchange(...)).thenReturn(mockResponse);
```

실제로는 `service` 내부의 "실제 RestTemplate"이 실행되므로 Mock이 동작하지 않습니다.

---

## 정확한 비교: 3가지 방법

### 방법 1: @InjectMocks만 사용 (❌ 실패)

```java
@Mock
private RestTemplate restTemplate;  // 이건 안 쓰임

@InjectMocks
private AmsArticleTagService service;  // RestTemplate이 실제 객체가 됨

@Before
public void setUp() {
    ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake");
}

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

### 방법 2: @InjectMocks 없이 직접 생성 + 리플렉션 (✅ 성공)

```java
@Mock
private RestTemplate restTemplate;  // 이걸 주입할 것

private AmsArticleTagService service;  // @InjectMocks 제거

@Before
public void setUp() {
    // @RunWith(MockitoJUnitRunner.class)가 이미 Mock 초기화하므로 initMocks() 불필요

    // 직접 생성 (실제 Builder 사용)
    service = new AmsArticleTagService(new RestTemplateBuilder());

    // Mock으로 교체 (핵심!)
    ReflectionTestUtils.setField(service, "restTemplate", restTemplate);
    ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake");
}

@Test
public void test() {
    when(restTemplate.exchange(...)).thenReturn(...);  // ✅ 동작함
    service.getArticleTagListFromAms(article);  // Mock이 실행됨
}
```

**동작 원리:**
```
1. new AmsArticleTagService(builder)
   → service.restTemplate = builder.build() (실제 객체 생성)

2. ReflectionTestUtils.setField(service, "restTemplate", restTemplate)
   → service.restTemplate = @Mock restTemplate (Mock으로 교체!)
```

---

### 방법 3: RestTemplateBuilder도 Mock으로 (✅ 성공하지만 복잡)

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
    when(builder.build()).thenReturn(restTemplate);  // Mock RestTemplate 반환하도록

    ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake");
}

@Test
public void test() {
    when(restTemplate.exchange(...)).thenReturn(...);  // ✅ 동작함
    service.getArticleTagListFromAms(article);  // Mock이 실행됨
}
```

**동작 원리:**
```
1. @InjectMocks가 생성자 호출
   → new AmsArticleTagService(mockBuilder)

2. 생성자 내부
   → this.restTemplate = mockBuilder.build()
   → mockBuilder.build()가 mockRestTemplate 반환 (when 설정에 의해)

3. 결과
   → service.restTemplate = @Mock restTemplate ✅
```

---

## 결론

| 방법 | @InjectMocks | RestTemplate이 Mock? | 복잡도 |
|------|--------------|---------------------|--------|
| 방법 1: @InjectMocks만 | O | ❌ 실제 객체 | 간단 (하지만 실패) |
| 방법 2: 직접 생성 + 리플렉션 | X | ✅ Mock | 간단 ⭐ |
| 방법 3: Builder도 Mock | O | ✅ Mock | 복잡 |

**추천: 방법 2 (직접 생성 + 리플렉션)**
- @InjectMocks를 포기하지만 코드가 명확함
- ReflectionTestUtils로 Mock을 확실하게 주입
- 의도가 명확하고 디버깅하기 쉬움

---

## 핵심 개념

**Builder 패턴 + @InjectMocks의 함정:**

```java
// 생성자가 이렇게 생겼으면
public Service(Dependency dependency) {
    this.dependency = dependency;  // 파라미터를 그대로 저장
}
// @InjectMocks가 @Mock dependency를 주입 → ✅ 성공

// 하지만 생성자가 이렇게 생겼으면
public Service(DependencyBuilder builder) {
    this.dependency = builder.build();  // 새로운 객체를 생성!
}
// @InjectMocks가 builder를 생성하더라도
// this.dependency는 builder.build()로 만든 "새로운 실제 객체" → ❌ Mock 아님
```

**@InjectMocks는 생성자 파라미터만 주입하지, 생성자 내부의 동작은 제어하지 못한다!**
