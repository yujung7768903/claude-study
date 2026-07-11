# Spring 테스트 Runner 완전 가이드

## Runner별 비교표

| Runner | Spring Context | application.yaml | @Value | @Autowired | @MockBean | 속도 | 용도 |
|--------|---------------|------------------|--------|------------|-----------|------|------|
| **MockitoJUnitRunner** | ❌ 없음 | ❌ 없음 | ❌ 동작 안 됨 | ❌ 동작 안 됨 | ❌ 사용 불가 | 매우 빠름 | 단위 테스트 |
| **SpringRunner** | ✅ 일부 | ✅ 로드됨 | ✅ 동작함 | ✅ 동작함 | ✅ | 중간 | 통합 테스트 |
| **@SpringBootTest** | ✅ 전체 | ✅ 로드됨 | ✅ 동작함 | ✅ 동작함 | ✅ | 느림 | E2E 테스트 |

---

## 1. MockitoJUnitRunner (단위 테스트)

### 특징

- Spring Context를 로드하지 않음
- application.yaml 자동 로드 안 됨
- @Value로 주입받는 필드는 null
- 순수 Mock 기반 단위 테스트, 빠른 실행 속도

### 코드 예시 (AmsArticleTagService)

외부 API를 호출하는 서비스는 Mock으로 격리하는 것이 일반적이다.

```java
@RunWith(MockitoJUnitRunner.class)
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private AmsArticleTagService amsArticleTagService;

    @Before
    public void setUp() {
        // @Value로 주입되는 필드는 리플렉션으로 직접 설정
        ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
    }

    @Test
    public void getArticleTagListFromAms_성공() {
        RArticle rArticle = new RArticle();
        rArticle.setArticleId("ART001");

        AmsTag tag1 = new AmsTag();
        tag1.setTagId("TAG1");
        tag1.setTag("경제");

        AmsResponseDto<AmsTag> responseDto = new AmsResponseDto<>();
        responseDto.setCode("200");
        responseDto.getData().setList(Arrays.asList(tag1));

        ResponseEntity<AmsResponseDto<AmsTag>> responseEntity =
            new ResponseEntity<>(responseDto, HttpStatus.OK);

        when(restTemplate.exchange(
            anyString(),
            eq(HttpMethod.GET),
            any(HttpEntity.class),
            any(ParameterizedTypeReference.class),
            anyMap()
        )).thenReturn(responseEntity);

        List<RArticleTag> result = amsArticleTagService.getArticleTagListFromAms(rArticle);

        assertEquals(1, result.size());
        assertEquals("경제", result.get(0).getTag());
    }

    @Test
    public void getArticleTagListFromAms_실패시_빈리스트() {
        RArticle rArticle = new RArticle();
        rArticle.setArticleId("ART001");

        when(restTemplate.exchange(
            anyString(), any(), any(), any(ParameterizedTypeReference.class), anyMap()
        )).thenThrow(new RuntimeException("Connection refused"));

        List<RArticleTag> result = amsArticleTagService.getArticleTagListFromAms(rArticle);

        assertTrue(result.isEmpty());
    }
}
```

### 왜 MockitoJUnitRunner인가?

| 특성 | 설명 | 테스트 전략 |
|------|------|------------|
| `RestTemplate` 의존 | 외부 AMS API 호출 | Mock으로 대체 |
| `@Value` 필드 | `amsServiceUrl` 주입 | `ReflectionTestUtils`로 설정 |
| `AbstractService` 상속 | `UserService` 자동주입 | 이 테스트에서는 사용 안 함 |

### application.yaml 접근 불가 예시

```java
@RunWith(MockitoJUnitRunner.class)
public class ConfigTest {

    @Value("${app.name}")   // ❌ null
    private String appName;

    @Value("${app.max-retry}")  // ❌ null
    private Integer maxRetry;

    @Test
    public void test() {
        assertNull(appName);   // null
        assertNull(maxRetry);  // null
    }
}
```

---

## 2. SpringRunner (통합 테스트)

### 특징

- Spring Context를 로드
- application.yaml/properties 자동 로드
- @Value, @Autowired 동작
- @MockBean으로 일부 Bean만 Mock 가능

### 코드 예시

```java
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
public class UserServiceTest {

    @Autowired
    private UserService userService;

    @MockBean
    private UserRepository userRepository;

    @Value("${app.name}")  // ✅ 동작함
    private String appName;

    @Test
    public void testWithSpringContext() {
        when(userRepository.findById(1L)).thenReturn(Optional.of(new User("John")));

        User user = userService.getUserById(1L);

        assertEquals("John", user.getName());
        assertEquals("MyApp", appName);
    }
}
```

### application.yaml 접근 가능

```java
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
@TestPropertySource(locations = "classpath:application-test.yaml")
public class ConfigTest {

    @Value("${app.name}")      // ✅ "MyApp"
    private String appName;

    @Value("${app.max-retry}") // ✅ 3
    private Integer maxRetry;

    @Test
    public void test() {
        assertEquals("MyApp", appName);
        assertEquals(3, maxRetry);
    }
}
```

### SpringRunner 사용 시 주의사항

- `application.yaml`이 gitignore되어 있으면 설정 파일이 없어 Context 로딩 실패
- 실제 AMS 서버가 떠 있어야 테스트 통과 (외부 API 테스트 시)
- DB, Redis 등 모든 인프라 연결 필요
- 테스트 실행 시간이 길어짐

---

## 3. @SpringBootTest (전체 앱 테스트)

### 특징

- 전체 Spring Boot 애플리케이션 로드
- 모든 Bean, Configuration 로드
- application.yaml/properties 자동 로드
- 가장 무겁지만 실제 환경과 가장 유사

### 코드 예시

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class UserServiceIntegrationTest {

    @Autowired
    private UserService userService;

    @MockBean
    private EmailService emailService;

    @Value("${app.name}")  // ✅ 동작
    private String appName;

    @Test
    public void testWithFullContext() {
        User user = userService.getUserById(1L);
        assertNotNull(user);
        assertEquals("MyApp", appName);
    }
}
```

```java
@RunWith(SpringRunner.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class UserControllerIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @MockBean
    private EmailService emailService;

    @Test
    public void createUser_API호출_정상동작() {
        UserRequest request = new UserRequest("john@example.com");

        ResponseEntity<User> response = restTemplate.postForEntity(
            "/api/users", request, User.class
        );

        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        verify(emailService).sendWelcome(any());
    }
}
```

---

## 4. RestTemplateBuilder 생성자 주입 문제

`MockitoJUnitRunner`에서 `@InjectMocks`를 사용할 때, 서비스가 생성자에서 `RestTemplateBuilder`를 받아 `RestTemplate`을 직접 생성하면 Mock 주입에 문제가 생긴다.

```java
// 이런 생성자가 있으면 @InjectMocks + @Mock RestTemplate이 동작 안 함!
public AmsArticleTagService(RestTemplateBuilder builder) {
    this.restTemplate = builder
            .setConnectTimeout(Duration.ofSeconds(10))
            .setReadTimeout(Duration.ofSeconds(10))
            .build();  // ← Mock이 아닌 실제 RestTemplate 생성
}
```

### 방법 A: @InjectMocks + 리플렉션으로 restTemplate 재주입 (권장)

```java
@Mock
private RestTemplate restTemplate;

@InjectMocks
private AmsArticleTagService amsArticleTagService;

@Before
public void setUp() {
    // 생성자 호출 후 Mock으로 교체
    ReflectionTestUtils.setField(amsArticleTagService, "restTemplate", restTemplate);
    ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
}
```

### 방법 A-2: @InjectMocks 없이 직접 생성 (더 명확함)

```java
@Mock
private RestTemplate restTemplate;

private AmsArticleTagService amsArticleTagService;

@Before
public void setUp() {
    amsArticleTagService = new AmsArticleTagService(new RestTemplateBuilder());
    ReflectionTestUtils.setField(amsArticleTagService, "restTemplate", restTemplate);
    ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
}
```

### 방법 B: RestTemplateBuilder Mock 체이닝

```java
@Mock
private RestTemplateBuilder builder;

@Mock
private RestTemplate restTemplate;

@Before
public void setUp() {
    when(builder.setConnectTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.setReadTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.build()).thenReturn(restTemplate);

    amsArticleTagService = new AmsArticleTagService(builder);
    ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
}
```

---

## 5. MockitoJUnitRunner에서 application.yaml 값이 필요할 때

### 방법 1: ReflectionTestUtils로 하드코딩 (권장)

```java
@RunWith(MockitoJUnitRunner.class)
public class S3ServiceTest {

    @Mock
    private AmazonS3 amazonS3;

    @InjectMocks
    private S3Service s3Service;

    @Before
    public void setup() {
        ReflectionTestUtils.setField(s3Service, "bucketName", "test-bucket");
        ReflectionTestUtils.setField(s3Service, "region", "ap-northeast-2");
    }
}
```

### 방법 2: SpringRunner로 변경 (설정값이 많다면)

```java
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = TestConfig.class)
@TestPropertySource("classpath:application-test.yaml")
public class S3ServiceTest {

    @Autowired
    private S3Service s3Service;

    @MockBean
    private AmazonS3 amazonS3;
}
```

---

## 6. 실무 시나리오별 선택

### 시나리오 1: 순수 비즈니스 로직 테스트

```java
// MockitoJUnitRunner 사용
@RunWith(MockitoJUnitRunner.class)
public class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private PaymentService paymentService;

    @InjectMocks
    private OrderService orderService;

    @Test
    public void processOrder_정상처리() {
        when(orderRepository.save(any())).thenReturn(new Order());

        Order result = orderService.processOrder(new OrderRequest());

        assertNotNull(result);
        verify(paymentService).charge(any());
    }
}
```

### 시나리오 2: application.yaml 설정값이 필요한 테스트

```java
// SpringRunner 사용
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
@TestPropertySource("classpath:application-test.yaml")
public class S3ServiceTest {

    @Autowired
    private S3Service s3Service;

    @MockBean
    private AmazonS3 amazonS3;

    @Test
    public void uploadFile_정상업로드() {
        when(amazonS3.putObject(any())).thenReturn(new PutObjectResult());

        String url = s3Service.uploadFile(new File("test.jpg"));

        assertNotNull(url);
    }
}
```

### 시나리오 3: 전체 통합 테스트

```java
// @SpringBootTest 사용
@RunWith(SpringRunner.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class ApiIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @Test
    public void testApi() {
        ResponseEntity<String> response =
            restTemplate.getForEntity("/api/health", String.class);
        assertEquals(HttpStatus.OK, response.getStatusCode());
    }
}
```

---

## 7. 판단 기준 요약

```
외부 API(RestTemplate) 호출하는 서비스를 테스트한다
  → Mock이 필요하다
    → MockitoJUnitRunner를 사용한다

DB 쿼리나 Spring Bean 연동을 검증해야 한다
  → 실제 Context가 필요하다
    → SpringRunner + @SpringBootTest를 사용한다
```

## 8. 실무 권장사항

1. **외부 API를 호출하는 서비스** → `MockitoJUnitRunner` + `@Mock RestTemplate`
2. **Repository(JPA) 테스트** → `SpringRunner` + `@DataJpaTest`
3. **Controller 테스트** → `SpringRunner` + `@WebMvcTest`
4. **전체 통합 테스트** → `SpringRunner` + `@SpringBootTest`
5. Spring Boot 2.x (JUnit 4) 기반: `@RunWith` 필수. JUnit 5라면 `@ExtendWith(MockitoExtension.class)` 사용.
