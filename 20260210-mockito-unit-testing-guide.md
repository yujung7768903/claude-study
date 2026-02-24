# Mockito를 사용한 Java 단위 테스트 작성법

## 목차
1. [Mock vs Spy](#mock-vs-spy)
2. [Stubbing with when().thenReturn()](#stubbing)
3. [Verification with verify()](#verification)
4. [ArgumentCaptor로 파라미터 검증](#argumentcaptor)
5. [Argument Matchers 사용법](#argument-matchers)
6. [의존성 주입 with @InjectMocks](#injectmocks)
7. [실전 예제](#실전-예제)

---

## Mock vs Spy

### @Mock - 완전한 가짜 객체

```java
@Mock
private UserRepository userRepository;
```

**특징:**
- 모든 메서드가 기본값 반환 (null, 0, false 등)
- 명시적으로 stubbing 해야만 원하는 값 반환
- 실제 메서드 호출 안 됨

**사용 시나리오:**
- 외부 의존성 (Database, API 호출 등)
- 복잡한 초기화가 필요한 객체
- 완전히 제어하고 싶은 객체

```java
@Mock
private RestTemplate restTemplate;

// stubbing 없으면 null 반환
when(restTemplate.getForObject(anyString(), any())).thenReturn(mockData);
```

### @Spy - 실제 객체를 래핑

```java
@Spy
private ObjectMapper objectMapper = new ObjectMapper();
```

**특징:**
- 실제 메서드가 호출됨
- 필요한 메서드만 선택적으로 stubbing 가능
- 실제 객체 생성 필요

**사용 시나리오:**
- 일부 메서드만 mocking 필요할 때
- 대부분 실제 동작이 필요하지만 특정 부분만 제어하고 싶을 때

```java
@Spy
private List<String> spyList = new ArrayList<>();

spyList.add("real");  // 실제로 리스트에 추가됨
when(spyList.size()).thenReturn(100);  // size()만 mocking
```

### 비교표

| 구분 | @Mock | @Spy |
|------|-------|------|
| 실제 메서드 호출 | ❌ | ✅ |
| 객체 초기화 필요 | ❌ | ✅ |
| 기본 동작 | 모든 메서드 mock | 실제 메서드 호출 |
| Stubbing | 필수 | 선택적 |
| 사용 사례 | 외부 의존성 | 부분적 mocking |

---

## Stubbing

### when().thenReturn() 기본 사용법

```java
@Test
public void stubbing_기본예제() {
    // given
    User mockUser = new User("john", "john@example.com");
    when(userRepository.findById(1L)).thenReturn(Optional.of(mockUser));

    // when
    Optional<User> result = userRepository.findById(1L);

    // then
    assertTrue(result.isPresent());
    assertEquals("john", result.get().getName());
}
```

### 다양한 Stubbing 방법

```java
// 1. 예외 던지기
when(userRepository.findById(999L)).thenThrow(new UserNotFoundException());

// 2. 여러 번 호출 시 다른 값 반환
when(randomService.getNumber())
    .thenReturn(1)
    .thenReturn(2)
    .thenReturn(3);

// 3. void 메서드 예외 처리
doThrow(new RuntimeException()).when(mockService).voidMethod();

// 4. 실제 메서드 호출 (Spy에서 유용)
doCallRealMethod().when(spyService).someMethod();

// 5. Answer를 사용한 동적 응답
when(calculator.add(anyInt(), anyInt())).thenAnswer(invocation -> {
    Integer a = invocation.getArgument(0);
    Integer b = invocation.getArgument(1);
    return a + b;
});
```

---

## Verification

### verify()로 메서드 호출 검증

```java
@Test
public void 메서드_호출_검증() {
    // given
    String userId = "user123";

    // when
    userService.deleteUser(userId);

    // then
    verify(userRepository).deleteById(userId);  // 1번 호출 확인
    verify(eventPublisher).publish(any(UserDeletedEvent.class));  // 이벤트 발행 확인
}
```

### 호출 횟수 검증

```java
// 정확히 1번 호출 (기본값)
verify(mockService).doSomething();
verify(mockService, times(1)).doSomething();

// 정확히 N번 호출
verify(mockService, times(3)).doSomething();

// 최소 N번 호출
verify(mockService, atLeast(2)).doSomething();

// 최대 N번 호출
verify(mockService, atMost(5)).doSomething();

// 한 번도 호출 안 됨
verify(mockService, never()).doSomething();

// 더 이상 상호작용 없음
verifyNoMoreInteractions(mockService);
```

### 호출 순서 검증

```java
@Test
public void 호출순서_검증() {
    // when
    userService.createUser("john");

    // then
    InOrder inOrder = inOrder(userRepository, eventPublisher);
    inOrder.verify(userRepository).save(any(User.class));
    inOrder.verify(eventPublisher).publish(any(UserCreatedEvent.class));
}
```

---

## ArgumentCaptor

### 파라미터 값 캡처 및 검증

```java
@Test
public void ArgumentCaptor_사용예제() {
    // given
    String articleId = "A2026020513000005239";

    // when
    amsArticleTagService.sinkToAms(articleId, tagList);

    // then - ArgumentCaptor로 실제 전달된 값 캡처
    ArgumentCaptor<HttpHeaders> headerCaptor = ArgumentCaptor.forClass(HttpHeaders.class);
    ArgumentCaptor<AmsTagHerbRequestDto> requestCaptor = ArgumentCaptor.forClass(AmsTagHerbRequestDto.class);

    verify(restApiUtil).excute(
        anyString(),
        any(HttpMethod.class),
        requestCaptor.capture(),  // 캡처
        any(Class.class),
        anyString(),
        headerCaptor.capture(),  // 캡처
        anyInt()
    );

    // 캡처한 값 검증
    HttpHeaders capturedHeaders = headerCaptor.getValue();
    assertEquals("BATCH_SYSTEM", capturedHeaders.getFirst("X-Batch-User-Id"));

    AmsTagHerbRequestDto capturedRequest = requestCaptor.getValue();
    assertEquals(articleId, capturedRequest.getArticleId());
    assertFalse(capturedRequest.getTagList().isEmpty());
}
```

### 여러 번 호출 시 모든 값 캡처

```java
@Test
public void 여러번_호출_캡처() {
    // when
    service.process("item1");
    service.process("item2");
    service.process("item3");

    // then
    ArgumentCaptor<String> captor = ArgumentCaptor.forClass(String.class);
    verify(mockRepository, times(3)).save(captor.capture());

    List<String> allCapturedValues = captor.getAllValues();
    assertEquals(3, allCapturedValues.size());
    assertTrue(allCapturedValues.contains("item1"));
    assertTrue(allCapturedValues.contains("item2"));
    assertTrue(allCapturedValues.contains("item3"));
}
```

---

## Argument Matchers

### 기본 Matchers

```java
// 타입 매칭
any()                    // 모든 타입
any(Class.class)         // 특정 클래스
anyString()              // 모든 String
anyInt(), anyLong()      // 기본 타입
anyList(), anyMap()      // 컬렉션

// 값 매칭
eq(value)                // 정확한 값
isNull(), isNotNull()    // null 체크
contains("substring")    // 문자열 포함
startsWith("prefix")     // 문자열 시작
matches("regex")         // 정규식 매칭

// 컬렉션 매칭
anyCollection()
anyIterable()
```

### ⚠️ 중요: Matcher와 Raw Value 혼용 금지

**❌ 잘못된 예제 - 에러 발생!**

```java
// Invalid use of argument matchers!
verify(restApiUtil).excute(
    contains(AmsRequestPath.TAG_HERB),     // matcher ✓
    eq(HttpMethod.POST),                   // matcher ✓
    requestCaptor.capture(),               // matcher ✓
    any(Class.class),                      // matcher ✓
    MediaType.APPLICATION_JSON_UTF8_VALUE, // raw value ✗ - 문제!
    headerCaptor.capture(),                // matcher ✓
    anyInt()                               // matcher ✓
);
```

**에러 메시지:**
```
org.mockito.exceptions.misusing.InvalidUseOfMatchersException:
Invalid use of argument matchers!
7 matchers expected, 6 recorded
```

**✅ 올바른 예제 - Raw value를 eq()로 감싸기**

```java
verify(restApiUtil).excute(
    contains(AmsRequestPath.TAG_HERB),         // matcher ✓
    eq(HttpMethod.POST),                       // matcher ✓
    requestCaptor.capture(),                   // matcher ✓
    any(Class.class),                          // matcher ✓
    eq(MediaType.APPLICATION_JSON_UTF8_VALUE), // eq()로 감싸기! ✓
    headerCaptor.capture(),                    // matcher ✓
    anyInt()                                   // matcher ✓
);
```

### Matcher 사용 규칙

1. **전부 Matcher 또는 전부 Raw Value**
   ```java
   // ✅ 모두 raw value
   verify(service).method("value1", "value2", 123);

   // ✅ 모두 matcher
   verify(service).method(anyString(), anyString(), anyInt());

   // ❌ 혼용 불가
   verify(service).method(anyString(), "value2", anyInt());  // 에러!
   ```

2. **Raw Value를 Matcher처럼 사용하려면 eq() 사용**
   ```java
   verify(service).method(anyString(), eq("specific value"), anyInt());
   ```

3. **null도 matcher 사용**
   ```java
   // ❌ 잘못됨
   verify(service).method(anyString(), null);

   // ✅ 올바름
   verify(service).method(anyString(), isNull());
   ```

### 커스텀 Matcher

```java
// ArgumentMatcher 인터페이스 구현
class UserWithName implements ArgumentMatcher<User> {
    private String expectedName;

    public UserWithName(String expectedName) {
        this.expectedName = expectedName;
    }

    @Override
    public boolean matches(User user) {
        return user != null && expectedName.equals(user.getName());
    }
}

// 사용
verify(userRepository).save(argThat(new UserWithName("john")));
```

---

## @InjectMocks

### 의존성 자동 주입

```java
@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailService emailService;

    @Mock
    private EventPublisher eventPublisher;

    @InjectMocks  // 위 Mock들을 자동 주입
    private UserService userService;

    @Test
    public void 사용자_생성_테스트() {
        // userService에 이미 모든 의존성이 주입됨
        when(userRepository.save(any(User.class))).thenReturn(new User());

        userService.createUser("john", "john@example.com");

        verify(userRepository).save(any(User.class));
        verify(emailService).sendWelcomeEmail(anyString());
        verify(eventPublisher).publish(any(UserCreatedEvent.class));
    }
}
```

### 주입 방식

1. **생성자 주입** (권장)
2. **Setter 주입**
3. **필드 주입**

```java
// Service 클래스
public class UserService {
    private final UserRepository userRepository;
    private final EmailService emailService;

    // 생성자 주입 - Mockito가 자동으로 처리
    public UserService(UserRepository userRepository, EmailService emailService) {
        this.userRepository = userRepository;
        this.emailService = emailService;
    }
}
```

### 수동 주입이 필요한 경우

```java
@Before
public void setUp() {
    // @InjectMocks가 처리 못하는 필드는 수동 주입
    ReflectionTestUtils.setField(userService, "apiKey", "test-api-key");
    ReflectionTestUtils.setField(userService, "timeout", 5000);
}
```

---

## 실전 예제

### 완전한 테스트 클래스 예제

```java
package app.hk.r.domain.ams;

import app.hk.r.common.constant.AmsRequestPath;
import app.hk.r.domain.news.article.ArticleTagRegHistoryRepository;
import app.hk.r.domain.news.article.ArticleTagVo;
import app.hk.r.domain.news.article.TagType;
import app.hk.r.util.RestApiUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@RunWith(MockitoJUnitRunner.class)
public class AmsArticleTagServiceTest {

    @Mock
    private RestApiUtil restApiUtil;

    @Mock
    private ArticleTagRegHistoryRepository articleTagRegHistoryRepository;

    // ObjectMapper는 실제 동작 필요
    private ObjectMapper objectMapper = new ObjectMapper();

    @InjectMocks
    private AmsArticleTagService amsArticleTagService;

    @Before
    public void setUp() {
        // ObjectMapper 수동 주입
        ReflectionTestUtils.setField(amsArticleTagService, "objectMapper", objectMapper);
        ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://test-ams.com");
    }

    @Test
    public void 태그가_존재할경우_ams에_업데이트한다() throws Exception {
        // given
        String articleId = "A2026020513000005239";
        List<ArticleTagVo> tagList = buildRequestTagList();

        // restApiUtil.excute() 호출 시 mock 응답 반환
        when(restApiUtil.excute(
                anyString(),
                any(HttpMethod.class),
                any(),
                any(Class.class),
                anyString(),
                any(HttpHeaders.class),
                anyInt()
        )).thenReturn(buildSuccessResponse());

        // when
        amsArticleTagService.sinkToAms(articleId, tagList);

        // then
        ArgumentCaptor<HttpHeaders> headerCaptor = ArgumentCaptor.forClass(HttpHeaders.class);
        ArgumentCaptor<AmsTagHerbRequestDto> requestCaptor = ArgumentCaptor.forClass(AmsTagHerbRequestDto.class);

        // verify: 올바른 파라미터로 호출되었는지 검증
        verify(restApiUtil).excute(
                contains(AmsRequestPath.TAG_HERB),          // URL에 TAG_HERB 포함
                eq(HttpMethod.POST),                        // POST 메서드
                requestCaptor.capture(),                    // 요청 body 캡처
                any(Class.class),                           // 응답 타입
                eq(MediaType.APPLICATION_JSON_UTF8_VALUE),  // Content-Type (eq로 감싸기!)
                headerCaptor.capture(),                     // 헤더 캡처
                anyInt()                                    // timeout
        );

        // 캡처한 헤더 검증
        HttpHeaders capturedHeaders = headerCaptor.getValue();
        assertEquals("BATCH_SYSTEM", capturedHeaders.getFirst("X-Batch-User-Id"));

        // 캡처한 요청 body 검증
        AmsTagHerbRequestDto capturedRequest = requestCaptor.getValue();
        assertNotNull(capturedRequest);
        assertEquals(articleId, capturedRequest.getArticleId());
        assertFalse(capturedRequest.getTagList().isEmpty());
        assertEquals(1, capturedRequest.getTagList().size());

        TagItem firstTag = capturedRequest.getTagList().get(0);
        assertEquals("test", firstTag.getTag());
        assertEquals(TagType.General, firstTag.getTagType());

        // 히스토리 저장 확인
        verify(articleTagRegHistoryRepository).save(any(ArticleTagRegHistory.class));
    }

    @Test
    public void 태그가_비어있으면_삭제_API를_호출한다() throws Exception {
        // given
        String articleId = "A2026020513000005239";
        List<ArticleTagVo> emptyTagList = new ArrayList<>();

        when(restApiUtil.excute(
                anyString(),
                any(HttpMethod.class),
                any(),
                any(Class.class),
                anyString(),
                any(HttpHeaders.class),
                anyInt()
        )).thenReturn(buildSuccessResponse());

        // when
        amsArticleTagService.sinkToAms(articleId, emptyTagList);

        // then
        verify(restApiUtil).excute(
                contains(AmsRequestPath.TAG_ARTICLE_TAGS),  // 삭제 API 호출
                eq(HttpMethod.POST),
                any(AmsArticleTagRequestDto.class),
                any(Class.class),
                eq(MediaType.APPLICATION_JSON_UTF8_VALUE),
                any(HttpHeaders.class),
                anyInt()
        );
    }

    @Test
    public void API_호출_실패시_예외를_로깅하고_계속_진행한다() {
        // given
        String articleId = "A2026020513000005239";
        List<ArticleTagVo> tagList = buildRequestTagList();

        // API 호출 시 예외 발생
        when(restApiUtil.excute(
                anyString(),
                any(HttpMethod.class),
                any(),
                any(Class.class),
                anyString(),
                any(HttpHeaders.class),
                anyInt()
        )).thenThrow(new RuntimeException("Connection timeout"));

        // when - 예외가 발생해도 테스트는 실패하지 않아야 함
        amsArticleTagService.sinkToAms(articleId, tagList);

        // then - API는 호출되었지만 히스토리는 저장 안 됨
        verify(restApiUtil).excute(anyString(), any(), any(), any(), anyString(), any(), anyInt());
        verify(articleTagRegHistoryRepository, never()).save(any());
    }

    // Helper methods
    private List<ArticleTagVo> buildRequestTagList() {
        List<ArticleTagVo> tagList = new ArrayList<>();
        tagList.add(new ArticleTagVo("test", "id", TagType.General));
        return tagList;
    }

    private AmsResponseDto<Void> buildSuccessResponse() {
        AmsResponseDto<Void> response = new AmsResponseDto<>();
        response.setCode("S3000");
        return response;
    }
}
```

---

## 실무 권장사항

### 1. 테스트 구조 (Given-When-Then)

```java
@Test
public void 명확한_테스트_이름() {
    // given - 테스트 준비
    User user = new User("john");
    when(userRepository.findById(1L)).thenReturn(Optional.of(user));

    // when - 실제 동작
    User result = userService.getUser(1L);

    // then - 결과 검증
    assertNotNull(result);
    assertEquals("john", result.getName());
    verify(userRepository).findById(1L);
}
```

### 2. 테스트 이름 작성 규칙

```java
// ✅ 좋은 예
@Test
public void 존재하지_않는_사용자_조회시_예외_발생() { }

@Test
public void whenUserNotFound_thenThrowException() { }

// ❌ 나쁜 예
@Test
public void test1() { }

@Test
public void getUserTest() { }
```

### 3. Mock 최소화

```java
// ❌ 과도한 mocking
@Mock private UserValidator validator;
@Mock private UserMapper mapper;
@Mock private DateFormatter formatter;

// ✅ 실제 객체 사용
private UserValidator validator = new UserValidator();
private UserMapper mapper = new UserMapper();

@Mock private UserRepository repository;  // 외부 의존성만 mock
```

### 4. Verify 사용 시기

```java
// ✅ 중요한 side effect 검증
verify(emailService).sendEmail(anyString());
verify(auditLogger).log(contains("USER_DELETED"));

// ❌ 불필요한 verify
verify(stringBuilder).append(anyString());  // 내부 구현 세부사항
```

### 5. ArgumentCaptor vs Matcher

```java
// ArgumentCaptor - 복잡한 객체 검증 필요
ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
verify(repository).save(captor.capture());
User capturedUser = captor.getValue();
assertEquals("john", capturedUser.getName());
assertEquals("john@example.com", capturedUser.getEmail());

// Matcher - 단순한 검증
verify(repository).save(argThat(user ->
    "john".equals(user.getName()) &&
    "john@example.com".equals(user.getEmail())
));
```

---

## 체크리스트

테스트 작성 시 확인사항:

- [ ] `@RunWith(MockitoJUnitRunner.class)` 추가했는가?
- [ ] Mock과 Spy를 올바르게 선택했는가?
- [ ] Argument Matcher와 Raw Value를 섞어 쓰지 않았는가?
- [ ] ArgumentCaptor로 중요한 파라미터를 검증했는가?
- [ ] Given-When-Then 구조로 작성했는가?
- [ ] 테스트 이름이 명확한가?
- [ ] 불필요한 verify()를 남발하지 않았는가?
- [ ] 외부 의존성만 mocking 하고 단순 객체는 실제 객체를 사용했는가?

---

## 참고 자료

- [Mockito 공식 문서](https://javadoc.io/doc/org.mockito/mockito-core/latest/org/mockito/Mockito.html)
- [Mockito GitHub](https://github.com/mockito/mockito)
- [Baeldung - Mockito Tutorial](https://www.baeldung.com/mockito-series)
