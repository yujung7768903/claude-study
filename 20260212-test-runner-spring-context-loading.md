# 테스트 Runner와 Spring Context/application.yaml 로딩

## 핵심 답변

**MockitoJUnitRunner는 application.yaml을 자동으로 로드하지 않습니다.**

- **MockitoJUnitRunner**: Mockito 전용 → Spring 컨텍스트 없음 → application.yaml 로드 안 됨
- **SpringRunner**: Spring 테스트 전용 → Spring 컨텍스트 로드 → application.yaml 로드됨

## Runner별 Spring Context 로딩 비교

| Runner | Spring Context | application.yaml | @Value | @Autowired | 용도 |
|--------|---------------|------------------|--------|------------|------|
| **MockitoJUnitRunner** | ❌ 로드 안 됨 | ❌ 로드 안 됨 | ❌ 동작 안 됨 | ❌ 동작 안 됨 | 단위 테스트 (순수 Mock) |
| **SpringRunner** | ✅ 로드됨 | ✅ 로드됨 | ✅ 동작함 | ✅ 동작함 | 통합 테스트 (Spring 포함) |
| **SpringBootTest** | ✅ 전체 로드 | ✅ 로드됨 | ✅ 동작함 | ✅ 동작함 | E2E 테스트 (전체 앱) |

## 1. MockitoJUnitRunner (단위 테스트)

### 특징
- **Mockito 전용 Runner**
- Spring Context를 로드하지 않음
- 순수 Mock 기반 단위 테스트
- 빠른 실행 속도

### 코드 예시

```java
@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;  // Mock 객체

    @InjectMocks
    private UserService userService;  // Mock 주입

    @Value("${app.name}")  // ❌ 동작 안 함! (Spring Context 없음)
    private String appName;

    @Test
    public void getUserById_정상동작() {
        // Given
        User mockUser = new User(1L, "John");
        when(userRepository.findById(1L)).thenReturn(Optional.of(mockUser));

        // When
        User user = userService.getUserById(1L);

        // Then
        assertEquals("John", user.getName());
    }

    @Test
    public void testApplicationYaml() {
        // ❌ appName은 null! (application.yaml 로드 안 됨)
        assertNull(appName);
    }
}
```

### application.yaml 접근 불가 예시

```yaml
# application.yaml
app:
  name: MyApp
  max-retry: 3
  timeout: 5000
```

```java
@RunWith(MockitoJUnitRunner.class)
public class ConfigTest {

    @Value("${app.name}")  // ❌ null
    private String appName;

    @Value("${app.max-retry}")  // ❌ null
    private Integer maxRetry;

    @InjectMocks
    private SomeService service;

    @Test
    public void test() {
        // application.yaml 값을 사용할 수 없음
        assertNull(appName);  // null
        assertNull(maxRetry); // null
    }
}
```

## 2. SpringRunner (Spring 통합 테스트)

### 특징
- **Spring Context를 로드**
- application.yaml/properties 자동 로드
- @Value, @Autowired 동작
- @MockBean으로 일부 Bean만 Mock 가능

### 코드 예시

```java
@RunWith(SpringRunner.class)  // Spring Context 로드
@ContextConfiguration(classes = AppConfig.class)
public class UserServiceTest {

    @Autowired  // ✅ 실제 Bean 주입
    private UserService userService;

    @MockBean  // ✅ 일부만 Mock으로 교체
    private UserRepository userRepository;

    @Value("${app.name}")  // ✅ 동작함! (application.yaml 로드됨)
    private String appName;

    @Test
    public void testWithSpringContext() {
        // Given
        when(userRepository.findById(1L)).thenReturn(Optional.of(new User("John")));

        // When
        User user = userService.getUserById(1L);

        // Then
        assertEquals("John", user.getName());
        assertEquals("MyApp", appName);  // ✅ application.yaml 값 사용 가능
    }
}
```

### application.yaml 접근 가능

```java
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
@TestPropertySource(locations = "classpath:application-test.yaml")
public class ConfigTest {

    @Value("${app.name}")  // ✅ "MyApp"
    private String appName;

    @Value("${app.max-retry}")  // ✅ 3
    private Integer maxRetry;

    @Test
    public void test() {
        assertEquals("MyApp", appName);
        assertEquals(3, maxRetry);
    }
}
```

## 3. @SpringBootTest (Spring Boot 전체 테스트)

### 특징
- **전체 Spring Boot 애플리케이션 로드**
- 모든 Bean, Configuration 로드
- application.yaml/properties 자동 로드
- 가장 무겁지만 실제 환경과 가장 유사

### 코드 예시

```java
@RunWith(SpringRunner.class)  // 또는 JUnit 5의 @ExtendWith(SpringExtension.class)
@SpringBootTest
public class UserServiceIntegrationTest {

    @Autowired
    private UserService userService;

    @MockBean  // 일부 Bean만 Mock
    private EmailService emailService;

    @Value("${app.name}")  // ✅ 동작
    private String appName;

    @Test
    public void testWithFullContext() {
        // 실제 환경과 유사한 통합 테스트
        User user = userService.getUserById(1L);
        assertNotNull(user);
        assertEquals("MyApp", appName);
    }
}
```

## 비교표: 상세 기능

| 기능 | MockitoJUnitRunner | SpringRunner | @SpringBootTest |
|------|-------------------|--------------|-----------------|
| **Spring Context** | ❌ | ✅ 일부 | ✅ 전체 |
| **application.yaml** | ❌ | ✅ | ✅ |
| **@Value** | ❌ | ✅ | ✅ |
| **@Autowired** | ❌ | ✅ | ✅ |
| **@MockBean** | ❌ (사용 불가) | ✅ | ✅ |
| **@Mock** | ✅ | ✅ | ✅ |
| **@InjectMocks** | ✅ | ⚠️ (비권장) | ⚠️ (비권장) |
| **실행 속도** | 매우 빠름 | 중간 | 느림 |
| **용도** | 단위 테스트 | 통합 테스트 | E2E 테스트 |

## 실무 시나리오별 선택

### 시나리오 1: 순수 비즈니스 로직 테스트

```java
// ✅ MockitoJUnitRunner 사용 (빠름)
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
        // 순수 로직 테스트, Spring 불필요
        when(orderRepository.save(any())).thenReturn(new Order());

        Order result = orderService.processOrder(new OrderRequest());

        assertNotNull(result);
        verify(paymentService).charge(any());
    }
}
```

### 시나리오 2: application.yaml 설정값이 필요한 테스트

```java
// ✅ SpringRunner 사용 (application.yaml 필요)
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
@TestPropertySource("classpath:application-test.yaml")
public class S3ServiceTest {

    @Autowired
    private S3Service s3Service;  // @Value로 설정값 주입받는 서비스

    @MockBean
    private AmazonS3 amazonS3;  // AWS SDK는 Mock

    @Test
    public void uploadFile_정상업로드() {
        // s3Service는 application.yaml의 bucket-name 등을 사용
        when(amazonS3.putObject(any())).thenReturn(new PutObjectResult());

        String url = s3Service.uploadFile(new File("test.jpg"));

        assertNotNull(url);
    }
}
```

### 시나리오 3: 전체 통합 테스트

```java
// ✅ @SpringBootTest 사용 (전체 앱 필요)
@RunWith(SpringRunner.class)
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public class UserControllerIntegrationTest {

    @Autowired
    private TestRestTemplate restTemplate;

    @MockBean
    private EmailService emailService;  // 외부 서비스만 Mock

    @Test
    public void createUser_API호출_정상동작() {
        // 실제 Controller → Service → Repository 흐름 테스트
        UserRequest request = new UserRequest("john@example.com");

        ResponseEntity<User> response = restTemplate.postForEntity(
            "/api/users", request, User.class
        );

        assertEquals(HttpStatus.CREATED, response.getStatusCode());
        verify(emailService).sendWelcome(any());
    }
}
```

## MockitoJUnitRunner에서 application.yaml 값을 사용해야 한다면?

### 방법 1: 하드코딩 (단위 테스트라면 적절)

```java
@RunWith(MockitoJUnitRunner.class)
public class S3ServiceTest {

    @Mock
    private AmazonS3 amazonS3;

    @InjectMocks
    private S3Service s3Service;

    @Before
    public void setup() {
        // application.yaml 값을 직접 설정 (Reflection 사용)
        ReflectionTestUtils.setField(s3Service, "bucketName", "test-bucket");
        ReflectionTestUtils.setField(s3Service, "region", "ap-northeast-2");
    }

    @Test
    public void uploadFile_정상동작() {
        when(amazonS3.putObject(any())).thenReturn(new PutObjectResult());

        String url = s3Service.uploadFile(new File("test.jpg"));

        assertNotNull(url);
    }
}
```

### 방법 2: 테스트용 설정 클래스 (추천하지 않음)

```java
@RunWith(MockitoJUnitRunner.class)
public class S3ServiceTest {

    @Mock
    private AmazonS3 amazonS3;

    private S3Service s3Service;

    @Before
    public void setup() {
        s3Service = new S3Service(amazonS3);
        // 생성자 또는 setter로 설정값 주입
        s3Service.setBucketName("test-bucket");
        s3Service.setRegion("ap-northeast-2");
    }

    @Test
    public void uploadFile_정상동작() {
        // 테스트
    }
}
```

### 방법 3: SpringRunner로 변경 (권장)

```java
// ✅ 설정값이 필요하면 SpringRunner 사용하는 것이 맞음
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = TestConfig.class)
@TestPropertySource("classpath:application-test.yaml")
public class S3ServiceTest {

    @Autowired
    private S3Service s3Service;

    @MockBean
    private AmazonS3 amazonS3;

    @Test
    public void uploadFile_정상동작() {
        // application-test.yaml의 값이 자동 주입됨
        when(amazonS3.putObject(any())).thenReturn(new PutObjectResult());

        String url = s3Service.uploadFile(new File("test.jpg"));

        assertNotNull(url);
    }
}
```

## HK Library 프로젝트 예시

### LibraryService 테스트 (MockitoJUnitRunner)

```java
// HK Library 프로젝트
public class LibraryService {
    @Value("${config.library.upload}")
    private String uploadPath;  // application.yaml에서 주입

    @Value("${config.library.thumbnail}")
    private String uploadThumbnailPath;

    private S3Util s3Util;
    private LibraryRepository libraryRepository;

    // ...
}

// ❌ MockitoJUnitRunner: application.yaml 로드 안 됨
@RunWith(MockitoJUnitRunner.class)
public class LibraryServiceTest {

    @Mock
    private S3Util s3Util;

    @Mock
    private LibraryRepository libraryRepository;

    @InjectMocks
    private LibraryService libraryService;

    // uploadPath, uploadThumbnailPath는 null!

    @Before
    public void setup() {
        // ✅ 해결: ReflectionTestUtils로 수동 주입
        ReflectionTestUtils.setField(libraryService, "uploadPath", "data2/library/upload/");
        ReflectionTestUtils.setField(libraryService, "uploadThumbnailPath", "data2/library/thumbnail/");
    }

    @Test
    public void saveImage_정상저장() {
        // 테스트
    }
}

// ✅ SpringRunner: application.yaml 자동 로드
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
@TestPropertySource("classpath:application-local.yaml")
public class LibraryServiceSpringTest {

    @Autowired
    private LibraryService libraryService;  // uploadPath 자동 주입됨

    @MockBean
    private S3Util s3Util;

    @Test
    public void saveImage_정상저장() {
        // application-local.yaml의 설정값이 자동 주입됨
    }
}
```

## 선택 가이드

### MockitoJUnitRunner를 사용해야 할 때
✅ **순수 비즈니스 로직 테스트**
- Spring 의존성 없음
- @Value로 주입받는 설정값 없음
- 빠른 단위 테스트 필요

```java
@RunWith(MockitoJUnitRunner.class)
public class CalculatorTest {
    @InjectMocks
    private Calculator calculator;

    @Test
    public void add() {
        assertEquals(5, calculator.add(2, 3));
    }
}
```

### SpringRunner를 사용해야 할 때
✅ **설정값(application.yaml)이 필요한 테스트**
- @Value로 설정값 주입
- @ConfigurationProperties 사용
- Spring Bean 간 통합 테스트

```java
@RunWith(SpringRunner.class)
@ContextConfiguration(classes = AppConfig.class)
public class ConfigServiceTest {
    @Autowired
    private ConfigService service;  // @Value 사용

    @Test
    public void testConfig() {
        assertEquals("expected-value", service.getConfigValue());
    }
}
```

### @SpringBootTest를 사용해야 할 때
✅ **전체 애플리케이션 테스트**
- API 통합 테스트
- DB 포함 E2E 테스트
- 실제 환경 재현 필요

```java
@RunWith(SpringRunner.class)
@SpringBootTest(webEnvironment = RANDOM_PORT)
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

## 요약

| 질문 | 답변 |
|------|------|
| **MockitoJUnitRunner는 application.yaml을 로드하는가?** | ❌ 아니오 (Spring Context 없음) |
| **@Value가 동작하는가?** | ❌ 아니오 (null) |
| **설정값이 필요하면?** | SpringRunner 또는 ReflectionTestUtils 사용 |
| **언제 MockitoJUnitRunner를 쓰는가?** | 순수 단위 테스트 (Spring 불필요) |
| **언제 SpringRunner를 쓰는가?** | Spring 설정값/Bean 필요한 통합 테스트 |

### 핵심 정리

1. **MockitoJUnitRunner**: Mockito 전용, Spring 없음, application.yaml 로드 안 됨
2. **SpringRunner**: Spring Context 로드, application.yaml 사용 가능
3. **설정값 필요 시**: SpringRunner 사용하거나 ReflectionTestUtils로 수동 주입
4. **테스트 전략**: 단위 테스트는 MockitoJUnitRunner, 통합 테스트는 SpringRunner
