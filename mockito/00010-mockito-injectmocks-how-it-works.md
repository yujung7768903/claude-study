# @InjectMocks는 언제 자동 주입이 될까?

## 질문: @Mock으로 RestTemplate 만들면 @InjectMocks가 알아서 주입 안 해주나?

**답: 생성자의 파라미터 타입에 따라 다르다.**

---

## @InjectMocks 동작 원리

Mockito의 `@InjectMocks`는 다음 순서로 Mock을 주입한다:

1. **생성자 주입** (Constructor Injection) - 우선순위 1
2. **세터 주입** (Setter Injection) - 우선순위 2
3. **필드 주입** (Field Injection) - 우선순위 3

중요한 점: **생성자의 파라미터 타입과 @Mock 필드의 타입이 일치해야 주입된다.**

---

## Case 1: 자동 주입이 되는 경우 ✅

만약 `AmsArticleTagService`가 이렇게 생겼다면:

```java
public class AmsArticleTagService {
    private final RestTemplate restTemplate;

    // 생성자가 RestTemplate을 직접 받음
    public AmsArticleTagService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
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
    private AmsArticleTagService service;  // 알아서 주입됨! ✅

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
- **타입이 일치** → @InjectMocks가 생성자 호출 시 자동 주입 ✅

---

## Case 2: 자동 주입이 안 되는 경우 ❌ (현재 코드)

실제 `AmsArticleTagService`는 이렇게 생겼다:

```java
public class AmsArticleTagService {
    private final RestTemplate restTemplate;

    // 생성자가 RestTemplateBuilder를 받음
    public AmsArticleTagService(RestTemplateBuilder builder) {
        this.restTemplate = builder
                .setConnectTimeout(Duration.ofSeconds(10))
                .setReadTimeout(Duration.ofSeconds(10))
                .build();  // 여기서 RestTemplate을 생성
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
    private AmsArticleTagService service;  // ❌ 주입 안 됨!

    // 에러 발생: Unable to initialize @InjectMocks
}
```

**왜 안 되는가?**
- 생성자 파라미터: `RestTemplateBuilder` ← 이게 필요함
- @Mock 필드 타입: `RestTemplate` ← 이게 있음
- **타입이 불일치** → @InjectMocks가 생성자를 호출할 수 없음 ❌

@InjectMocks는 `RestTemplateBuilder`를 찾지만, 없으므로 실패한다.

---

## 해결 방법 3가지

### 방법 1: RestTemplateBuilder도 Mock으로 만들기

```java
@Mock
private RestTemplateBuilder builder;

@Mock
private RestTemplate restTemplate;

@InjectMocks
private AmsArticleTagService service;  // ✅ 이제 주입됨

@Before
public void setUp() {
    // 하지만 빌더 체이닝 설정이 필요함
    when(builder.setConnectTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.setReadTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.build()).thenReturn(restTemplate);

    ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake-ams.com");
}
```

**장점:** @InjectMocks를 그대로 사용
**단점:** 빌더 체이닝 Mock 설정이 복잡함

---

### 방법 2: @InjectMocks 안 쓰고 직접 생성 (권장 ⭐)

```java
@Mock
private RestTemplate restTemplate;

private AmsArticleTagService service;  // @InjectMocks 제거

@Before
public void setUp() {
    MockitoAnnotations.initMocks(this);  // @Mock 초기화

    // 직접 생성 (Builder는 실제 인스턴스 사용)
    service = new AmsArticleTagService(new RestTemplateBuilder());

    // RestTemplate 필드만 Mock으로 교체
    ReflectionTestUtils.setField(service, "restTemplate", restTemplate);
    ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake-ams.com");
}
```

**장점:** 간단하고 명확함
**단점:** @InjectMocks의 편의성을 포기

---

### 방법 3: 생성자를 RestTemplate 받도록 변경 (프로덕션 코드 수정)

```java
// AmsArticleTagService.java 수정
@Service
public class AmsArticleTagService {
    private final RestTemplate restTemplate;

    // 이미 생성된 RestTemplate을 주입받도록 변경
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

**장점:** 테스트하기 가장 쉬움, DI 원칙에도 부합
**단점:** 프로덕션 코드를 수정해야 함

---

## 핵심 요약

| 상황 | @InjectMocks 자동 주입 |
|-----|---------------------|
| 생성자 파라미터 = @Mock 타입 | ✅ 자동 주입됨 |
| 생성자 파라미터 ≠ @Mock 타입 | ❌ 주입 안 됨 (현재 상황) |

**현재 AmsArticleTagService는:**
- 생성자가 `RestTemplateBuilder`를 받음
- @Mock으로 `RestTemplate`을 만들어도 타입이 안 맞음
- 그래서 @InjectMocks가 자동으로 주입하지 못함

**가장 현실적인 방법:**
@InjectMocks를 포기하고 `@Before`에서 직접 생성 + `ReflectionTestUtils.setField()` 사용 (방법 2)
