# Mockito Spy와 의존성 주입

## 개념

### Spy란?
- **Spy**는 실제 객체를 감싸서(wrap) 일부 메서드만 stubbing하고, 나머지는 실제 로직을 호출하는 방식
- Mock과 달리 실제 객체의 메서드를 호출하므로 **부분 모킹(Partial Mocking)**이 가능
- 실제 인스턴스가 생성되므로 의존성 주입이 필요한 경우가 많음

### MockitoJUnitRunner에서 Spy 사용
MockitoJUnitRunner 환경에서도 spy를 사용할 수 있으며, `@Spy` 어노테이션으로 간편하게 선언 가능합니다.

## MockitoJUnitRunner에서 @Spy 사용법

### 1. 기본 @Spy 사용 (의존성 없는 경우)

```java
@RunWith(MockitoJUnitRunner.class)
public class SimpleServiceTest {

    @Spy
    private SimpleService simpleService;  // 실제 인스턴스 생성됨

    @Test
    public void testPartialMocking() {
        // 특정 메서드만 stubbing
        doReturn("stubbed").when(simpleService).methodA();

        // methodA는 stubbed 값 반환, methodB는 실제 로직 실행
        assertEquals("stubbed", simpleService.methodA());
        assertEquals("realB", simpleService.methodB());  // 실제 메서드 호출
    }
}
```

### 2. 의존성이 있는 서비스에서 Spy 사용

의존성이 필요한 경우, `@Spy`와 `@InjectMocks`를 조합하여 사용합니다.

```java
@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailService emailService;

    @Spy
    @InjectMocks  // Mock들을 Spy 객체에 주입
    private UserService userService;

    @Test
    public void testPartialMockingWithDependencies() {
        // Given: 의존성 Mock 설정
        User user = new User("john", "john@example.com");
        when(userRepository.findById(1L)).thenReturn(Optional.of(user));

        // When: 일부 메서드만 stubbing
        doReturn("Custom Welcome").when(userService).generateWelcomeMessage(any());

        // Then
        userService.registerUser(1L);

        // generateWelcomeMessage는 stubbed 값 사용
        // sendEmail은 실제 로직 실행 (emailService.send 호출)
        verify(emailService).send(eq("john@example.com"), eq("Custom Welcome"));
    }
}
```

### 3. 생성자를 통한 Spy 생성 (수동 방식)

`@Spy` 어노테이션 대신 수동으로 spy를 생성할 수도 있습니다.

```java
@RunWith(MockitoJUnitRunner.class)
public class OrderServiceTest {

    @Mock
    private OrderRepository orderRepository;

    @Mock
    private PaymentService paymentService;

    private OrderService orderService;

    @Before
    public void setup() {
        // 실제 인스턴스 생성 후 spy로 감싸기
        OrderService realService = new OrderService(orderRepository, paymentService);
        orderService = spy(realService);
    }

    @Test
    public void testWithManualSpy() {
        doReturn(true).when(orderService).validateOrder(any());

        orderService.processOrder(new Order());

        verify(paymentService).charge(any());  // 실제 메서드에서 호출됨
    }
}
```

## 실제 서비스 예시

```java
// 테스트 대상 서비스
public class LibraryService {
    private final LibraryRepository libraryRepository;
    private final S3Util s3Util;
    private final ImageConverter imageConverter;

    public LibraryService(LibraryRepository libraryRepository,
                         S3Util s3Util,
                         ImageConverter imageConverter) {
        this.libraryRepository = libraryRepository;
        this.s3Util = s3Util;
        this.imageConverter = imageConverter;
    }

    public void saveImage(ImageData imageData) {
        String thumbnailPath = makeThumbnail(imageData);  // 이 메서드만 stubbing하고 싶음
        uploadToS3(thumbnailPath, imageData);  // 실제 로직 실행하고 싶음
        saveToDatabase(imageData);  // 실제 로직 실행하고 싶음
    }

    protected String makeThumbnail(ImageData imageData) {
        return imageConverter.convert(imageData);
    }

    private void uploadToS3(String path, ImageData data) {
        s3Util.upload(path, data.getContent());
    }

    private void saveToDatabase(ImageData data) {
        libraryRepository.save(data);
    }
}

// 테스트 코드
@RunWith(MockitoJUnitRunner.class)
public class LibraryServiceTest {

    @Mock
    private LibraryRepository libraryRepository;

    @Mock
    private S3Util s3Util;

    @Mock
    private ImageConverter imageConverter;

    @Spy
    @InjectMocks
    private LibraryService libraryService;

    @Test
    public void testSaveImage_partialMocking() {
        // Given
        ImageData imageData = new ImageData("test.jpg", new byte[]{1, 2, 3});

        // makeThumbnail만 stubbing (무거운 이미지 변환 작업 스킵)
        doReturn("/thumbnails/test.jpg").when(libraryService).makeThumbnail(any());

        // When
        libraryService.saveImage(imageData);

        // Then
        // uploadToS3, saveToDatabase는 실제 로직 실행됨
        verify(s3Util).upload(eq("/thumbnails/test.jpg"), any());
        verify(libraryRepository).save(imageData);
    }
}
```

## @Spy vs @Mock vs @InjectMocks 비교

| 어노테이션 | 생성되는 객체 | 메서드 동작 | 의존성 주입 | 사용 시나리오 |
|-----------|-------------|-----------|-----------|--------------|
| `@Mock` | Mock 객체 | stubbing 안 하면 기본값 반환 | 불가능 | 완전히 제어하고 싶은 의존성 |
| `@Spy` | 실제 객체 | stubbing 안 하면 실제 로직 실행 | 가능 | 부분 모킹이 필요한 테스트 대상 |
| `@InjectMocks` | 실제 객체 | 실제 로직 실행 | Mock/Spy 주입됨 | 테스트 대상 객체 (의존성 필요) |
| `@Spy` + `@InjectMocks` | 실제 객체 (Spy로 감쌈) | stubbing 가능 + 실제 로직 | Mock/Spy 주입됨 | 부분 모킹 + 의존성 필요 |

## Spy 사용 시 주의사항

### 1. when() vs doReturn()
Spy에서는 `doReturn().when()` 방식을 사용해야 합니다.

```java
// ❌ 위험: 실제 메서드가 호출됨
when(spyService.riskyMethod()).thenReturn("stubbed");

// ✅ 안전: 실제 메서드 호출 없이 stubbing
doReturn("stubbed").when(spyService).riskyMethod();
```

**이유**: `when(spy.method())`는 method()를 실제로 호출한 후 stubbing하므로, 부작용이 발생할 수 있습니다.

### 2. final 메서드는 stubbing 불가능
```java
public class Service {
    public final String finalMethod() {  // final 메서드
        return "real";
    }
}

@Spy
private Service service;

@Test
public void test() {
    // ❌ 동작하지 않음: final 메서드는 stubbing 불가
    doReturn("stubbed").when(service).finalMethod();
    assertEquals("real", service.finalMethod());  // "real" 반환됨
}
```

### 3. private 메서드는 직접 stubbing 불가능
private 메서드는 Spy로도 stubbing할 수 없습니다. PowerMock을 사용하거나, 테스트 가능하도록 리팩토링해야 합니다.

```java
// ❌ 불가능
doReturn("stubbed").when(service).privateMethod();  // 컴파일 에러

// ✅ 해결책 1: protected로 변경
protected String method() { ... }

// ✅ 해결책 2: 별도 클래스로 분리
```

### 4. @Spy 필드는 초기화 필요 (의존성 없는 경우)
```java
// ❌ 에러: NullPointerException
@Spy
private Service service;

// ✅ 방법 1: 직접 초기화
@Spy
private Service service = new Service();

// ✅ 방법 2: @InjectMocks로 의존성 주입
@Spy
@InjectMocks
private Service service;
```

### 5. ⚠️ 중요: Spy는 메서드를 실행하지만, Mock 의존성은 stubbing이 필요

**Spy의 가장 혼동하기 쉬운 부분**입니다. Spy는 실제 메서드를 실행하지만, 의존성이 Mock이면 그 Mock도 stubbing해야 합니다.

```java
// 실제 서비스 코드
public class UserService {
    private UserRepository userRepository;  // 이게 Mock으로 주입됨

    public User getUser(Long id) {
        // 이 메서드는 실제로 실행됨 (Spy니까)
        User user = userRepository.findById(id);  // 하지만 여기서 문제!
        return user;
    }

    public String getUserName(Long id) {
        User user = getUser(id);  // user는 null!
        return user.getName();  // NullPointerException!
    }
}

// 테스트 코드
@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;  // Mock! (실제 객체 아님)

    @Spy
    @InjectMocks
    private UserService userService;

    @Test
    public void test_실패_예시() {
        // userService.getUserName()는 실제 메서드 실행
        // 하지만 내부에서 userRepository.findById()를 호출하면
        // stubbing 안 했으므로 null 반환!

        String name = userService.getUserName(1L);  // ❌ NullPointerException!
    }

    @Test
    public void test_성공_예시() {
        // ✅ Mock 의존성을 stubbing해야 함!
        User mockUser = new User(1L, "John");
        when(userRepository.findById(1L)).thenReturn(mockUser);

        // 이제 실제 메서드가 제대로 동작함
        String name = userService.getUserName(1L);  // "John"
        assertEquals("John", name);
    }
}
```

**핵심 정리**:
```
Spy 메서드 실행 = 실제 로직 수행 ✅
           ↓
    Mock 의존성 호출
           ↓
    stubbing 없음? → null/0/false 반환 ❌
    stubbing 있음? → stubbed 값 반환 ✅
```

**왜 이런 일이 발생하나?**
- `@Spy`: 테스트 대상(UserService)의 메서드를 실제로 실행
- `@Mock`: 의존성(UserRepository)은 가짜 객체
- 실제 메서드가 실행되더라도, Mock 의존성을 호출하면 Mock의 기본 동작(null 반환)이 일어남

**실무 시나리오**:
```java
@RunWith(MockitoJUnitRunner.class)
public class LibraryServiceTest {

    @Mock
    private S3Util s3Util;  // Mock

    @Spy
    @InjectMocks
    private LibraryService libraryService;

    @Test
    public void test() {
        // libraryService.uploadImage()는 실제 실행됨
        // 하지만 내부에서 s3Util.upload()를 호출하면?

        // ❌ stubbing 안 함 → s3Util.upload()는 아무것도 안 함 (Mock이니까)
        libraryService.uploadImage(data);

        // ✅ stubbing 필요
        when(s3Util.upload(anyString(), any())).thenReturn(true);
        libraryService.uploadImage(data);  // 이제 정상 동작
    }
}
```

**해결 방법**:
1. **Mock 의존성을 stubbing**: `when(...).thenReturn(...)`으로 Mock 동작 정의
2. **실제 객체 사용**: Mock 대신 실제 객체를 주입 (통합 테스트)
3. **Spy 메서드만 stubbing**: 의존성을 사용하는 부분을 아예 stubbing으로 건너뛰기

```java
// 방법 1: Mock stubbing (권장)
@Test
public void solution1() {
    when(userRepository.findById(1L)).thenReturn(mockUser);
    userService.getUserName(1L);  // 정상 동작
}

// 방법 2: Spy 메서드 자체를 stubbing
@Test
public void solution2() {
    doReturn(mockUser).when(userService).getUser(1L);
    userService.getUserName(1L);  // getUser()가 stubbed되어 정상 동작
}

// 방법 3: 통합 테스트로 전환 (실제 의존성 사용)
@Test
public void solution3() {
    // Mock 대신 실제 UserRepository 사용
    // 하지만 이건 더 이상 단위 테스트가 아님
}
```

## 실무 권장사항

### 언제 Spy를 사용할까?

✅ **Spy 사용이 적합한 경우**
- 레거시 코드 테스트: 리팩토링 없이 일부만 모킹해야 할 때
- 무거운 작업 스킵: 이미지 변환, 파일 I/O 등 특정 메서드만 stubbing
- 실제 로직 검증: 대부분의 로직은 실행하되 일부만 제어하고 싶을 때

❌ **Spy 사용을 피해야 하는 경우**
- 새로운 코드 작성: Mock과 실제 객체로 충분히 테스트 가능
- 모든 메서드를 stubbing: Mock을 사용하는 것이 더 명확
- 복잡한 상태 관리: Spy는 실제 객체의 상태를 유지하므로 테스트가 복잡해짐

### Best Practices

```java
@RunWith(MockitoJUnitRunner.class)
public class GoodPracticeTest {

    @Mock
    private Repository repository;  // 의존성은 Mock

    @Spy
    @InjectMocks
    private Service service;  // 테스트 대상은 Spy (필요시)

    @Test
    public void test() {
        // 1. doReturn 사용
        doReturn("safe").when(service).method();

        // 2. 필요한 메서드만 stubbing
        // 3. 실제 로직이 주로 실행되도록 설계

        service.businessLogic();

        // 4. verify로 상호작용 검증
        verify(repository).save(any());
    }
}
```

### 의존성 주입 방식 비교

```java
// 방법 1: @Spy + @InjectMocks (권장)
@Mock private DepA depA;
@Mock private DepB depB;
@Spy @InjectMocks private Service service;

// 방법 2: 수동 생성
@Mock private DepA depA;
@Mock private DepB depB;
private Service service;

@Before
public void setup() {
    service = spy(new Service(depA, depB));
}

// 방법 3: @Spy 초기화 (의존성이 없는 경우만)
@Spy
private Service service = new Service();
```

## 요약

1. **MockitoJUnitRunner에서 @Spy 사용 가능**: `@Spy` 어노테이션으로 간단히 선언
2. **의존성 있는 서비스**: `@Spy + @InjectMocks` 조합으로 Mock 주입 가능
3. **⚠️ 중요한 함정**: Spy는 메서드를 실제 실행하지만, Mock 의존성은 stubbing하지 않으면 null/기본값 반환
4. **Stubbing 방식**: `doReturn().when()` 사용 (실제 메서드 호출 방지)
5. **제약사항**: final, private, static 메서드는 stubbing 불가
6. **사용 판단**: 부분 모킹이 정말 필요한지 검토 후 사용 (Mock이 더 명확한 경우가 많음)
