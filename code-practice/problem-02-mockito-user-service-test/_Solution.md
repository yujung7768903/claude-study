# 정답 및 해설

⚠️ **경고**: 먼저 스스로 풀어보세요! 정답을 보기 전에 최소 30분은 고민해보는 것을 권장합니다.

---

## 정답 코드

### UserServiceTest.java

```java
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;

import static org.junit.Assert.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @Mock
    private EmailService emailService;

    @Mock
    private EventPublisher eventPublisher;

    @InjectMocks
    private UserService userService;

    @Test
    public void 사용자_생성_성공_테스트() {
        // given
        User mockUser = new User(1L, "john", "john@example.com");
        when(userRepository.save(any(User.class))).thenReturn(mockUser);

        // when
        User result = userService.createUser("john", "john@example.com");

        // then
        assertNotNull(result);
        assertEquals("john", result.getName());
        assertEquals("john@example.com", result.getEmail());

        verify(userRepository).save(any(User.class));
        verify(emailService).sendWelcomeEmail(anyString(), anyString());
        verify(eventPublisher).publish(any(UserCreatedEvent.class));
    }

    @Test
    public void 사용자_생성시_올바른_이메일_파라미터_전달_확인() {
        // given
        User mockUser = new User(1L, "john", "john@example.com");
        when(userRepository.save(any(User.class))).thenReturn(mockUser);

        // when
        userService.createUser("john", "john@example.com");

        // then
        ArgumentCaptor<String> emailCaptor = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> nameCaptor = ArgumentCaptor.forClass(String.class);

        verify(emailService).sendWelcomeEmail(emailCaptor.capture(), nameCaptor.capture());

        String capturedEmail = emailCaptor.getValue();
        String capturedName = nameCaptor.getValue();

        assertEquals("john@example.com", capturedEmail);
        assertEquals("john", capturedName);
    }

    @Test
    public void 사용자_생성시_이벤트에_올바른_사용자_정보_포함_확인() {
        // given
        User mockUser = new User(1L, "john", "john@example.com");
        when(userRepository.save(any(User.class))).thenReturn(mockUser);

        // when
        userService.createUser("john", "john@example.com");

        // then
        ArgumentCaptor<UserCreatedEvent> eventCaptor = ArgumentCaptor.forClass(UserCreatedEvent.class);

        verify(eventPublisher).publish(eventCaptor.capture());

        UserCreatedEvent capturedEvent = eventCaptor.getValue();

        assertNotNull(capturedEvent.getUser());
        assertEquals("john", capturedEvent.getUser().getName());
        assertEquals("john@example.com", capturedEvent.getUser().getEmail());
    }
}
```

---

## 상세 해설

### 핵심 개념

#### 1. @RunWith(MockitoJUnitRunner.class)
```java
@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {
```

**역할:**
- Mockito 어노테이션(`@Mock`, `@InjectMocks`)을 자동으로 초기화
- 각 테스트 실행 전에 Mock 객체들을 새로 생성
- `MockitoAnnotations.initMocks(this)`를 수동으로 호출할 필요 없음

**대안:**
```java
@Before
public void setUp() {
    MockitoAnnotations.initMocks(this);
}
```

#### 2. @Mock - 가짜 객체 생성

```java
@Mock
private UserRepository userRepository;
```

**특징:**
- 모든 메서드가 기본값 반환 (객체는 null, 숫자는 0, boolean은 false)
- 실제 메서드는 호출되지 않음
- Stubbing 하지 않으면 null 반환

**언제 사용?**
- 외부 의존성 (Database, API, File I/O 등)
- 복잡한 초기화가 필요한 객체
- 완전히 제어하고 싶은 객체

#### 3. @InjectMocks - 의존성 자동 주입

```java
@InjectMocks
private UserService userService;
```

**동작 방식:**
1. `UserService`의 생성자를 찾음
2. 생성자 파라미터 타입과 일치하는 `@Mock` 객체들을 찾음
3. 자동으로 주입하여 `UserService` 인스턴스 생성

**생성자:**
```java
public UserService(UserRepository userRepository,
                  EmailService emailService,
                  EventPublisher eventPublisher) {
    // @Mock으로 선언된 객체들이 자동으로 주입됨
}
```

**주입 우선순위:**
1. 생성자 주입 (권장)
2. Setter 주입
3. 필드 주입

---

### 구현 포인트

#### 1. Stubbing with when().thenReturn()

```java
User mockUser = new User(1L, "john", "john@example.com");
when(userRepository.save(any(User.class))).thenReturn(mockUser);
```

**의미:**
- `userRepository.save()` 메서드가 호출되면
- 어떤 `User` 객체가 파라미터로 전달되든 (`any(User.class)`)
- 항상 `mockUser`를 반환

**왜 필요한가?**
- Mock 객체는 기본적으로 null을 반환
- 테스트에서 실제 동작을 시뮬레이션하기 위해 반환값 지정

#### 2. Verification with verify()

```java
verify(userRepository).save(any(User.class));
verify(emailService).sendWelcomeEmail(anyString(), anyString());
verify(eventPublisher).publish(any(UserCreatedEvent.class));
```

**의미:**
- 해당 메서드가 정확히 1번 호출되었는지 검증
- 파라미터 타입이 일치하는지 확인

**검증 목적:**
- `UserService.createUser()`가 올바른 순서로 의존성들을 호출하는지 확인
- 비즈니스 로직이 제대로 구현되었는지 확인

**호출 횟수 옵션:**
```java
verify(service, times(1)).method();      // 정확히 1번 (기본값)
verify(service, times(3)).method();      // 정확히 3번
verify(service, atLeast(2)).method();    // 최소 2번
verify(service, never()).method();       // 호출 안 됨
```

#### 3. ArgumentCaptor로 파라미터 검증

```java
ArgumentCaptor<String> emailCaptor = ArgumentCaptor.forClass(String.class);
ArgumentCaptor<String> nameCaptor = ArgumentCaptor.forClass(String.class);

verify(emailService).sendWelcomeEmail(emailCaptor.capture(), nameCaptor.capture());

String capturedEmail = emailCaptor.getValue();
String capturedName = nameCaptor.getValue();

assertEquals("john@example.com", capturedEmail);
assertEquals("john", capturedName);
```

**왜 사용하는가?**
- 메서드 호출 여부만이 아니라 **정확한 파라미터 값**을 검증
- 복잡한 객체의 내부 필드까지 상세히 검증 가능

**언제 사용하는가?**
- 파라미터가 올바른 값인지 확인 필요
- 객체의 특정 필드만 검증하고 싶을 때
- 여러 번 호출된 모든 파라미터를 검증할 때

**대안 - argThat() 사용:**
```java
verify(emailService).sendWelcomeEmail(
    eq("john@example.com"),
    eq("john")
);
```

하지만 ArgumentCaptor가 더 유연하고 복잡한 검증에 유리합니다.

---

### 주의사항

#### 1. Argument Matcher와 Raw Value 혼용 금지!

**❌ 잘못된 코드:**
```java
verify(emailService).sendWelcomeEmail(emailCaptor.capture(), "john");
```

**에러 메시지:**
```
org.mockito.exceptions.misusing.InvalidUseOfMatchersException:
Invalid use of argument matchers!
2 matchers expected, 1 recorded.
```

**✅ 올바른 코드:**
```java
verify(emailService).sendWelcomeEmail(emailCaptor.capture(), nameCaptor.capture());
```

또는

```java
verify(emailService).sendWelcomeEmail(emailCaptor.capture(), eq("john"));
```

**규칙:**
- 모든 파라미터를 Matcher로 감싸거나
- 모든 파라미터를 Raw Value로 사용
- 혼용하려면 Raw Value를 `eq()`로 감싸기

#### 2. any() vs eq()

```java
// any() - 어떤 값이든 허용
when(userRepository.save(any(User.class))).thenReturn(mockUser);

// eq() - 정확한 값만 허용
when(userRepository.findById(eq(1L))).thenReturn(Optional.of(mockUser));
```

#### 3. verify() 순서는 중요하지 않음

```java
// 순서 상관없음
verify(eventPublisher).publish(any(UserCreatedEvent.class));
verify(emailService).sendWelcomeEmail(anyString(), anyString());
verify(userRepository).save(any(User.class));
```

**순서를 검증하려면 InOrder 사용:**
```java
InOrder inOrder = inOrder(userRepository, emailService, eventPublisher);
inOrder.verify(userRepository).save(any(User.class));
inOrder.verify(emailService).sendWelcomeEmail(anyString(), anyString());
inOrder.verify(eventPublisher).publish(any(UserCreatedEvent.class));
```

---

### 추가 학습 포인트

#### 1. Mock vs Spy

**Mock:**
- 모든 메서드가 가짜
- 실제 메서드 호출 안 됨

**Spy:**
- 실제 객체를 래핑
- 실제 메서드가 호출됨
- 일부만 선택적으로 stubbing 가능

```java
@Spy
private ObjectMapper objectMapper = new ObjectMapper();

// 대부분 실제 동작하지만, 특정 메서드만 mocking 가능
when(objectMapper.readValue(anyString(), any(Class.class))).thenReturn(mockData);
```

#### 2. doThrow(), doNothing(), doAnswer()

**void 메서드 stubbing:**
```java
// 예외 발생
doThrow(new RuntimeException()).when(emailService).sendWelcomeEmail(anyString(), anyString());

// 아무것도 안 함 (기본 동작)
doNothing().when(emailService).sendWelcomeEmail(anyString(), anyString());

// 커스텀 동작
doAnswer(invocation -> {
    String email = invocation.getArgument(0);
    System.out.println("Sending email to: " + email);
    return null;
}).when(emailService).sendWelcomeEmail(anyString(), anyString());
```

#### 3. @Captor 어노테이션

```java
@Captor
private ArgumentCaptor<String> emailCaptor;

// 사용
verify(emailService).sendWelcomeEmail(emailCaptor.capture(), anyString());
```

`ArgumentCaptor.forClass(String.class)` 대신 어노테이션으로 선언 가능.

---

## 추가 도전 과제 정답

### 1. 예외 처리 테스트

```java
@Test(expected = RuntimeException.class)
public void Repository_예외_발생시_전파() {
    // given
    when(userRepository.save(any(User.class)))
        .thenThrow(new RuntimeException("DB 오류"));

    // when
    userService.createUser("john", "john@example.com");

    // then - 예외 발생하여 여기까지 도달 안 됨
}
```

또는 try-catch 사용:

```java
@Test
public void Repository_예외_발생시_이메일_발송_안됨() {
    // given
    when(userRepository.save(any(User.class)))
        .thenThrow(new RuntimeException("DB 오류"));

    // when
    try {
        userService.createUser("john", "john@example.com");
        fail("예외가 발생해야 함");
    } catch (RuntimeException e) {
        // expected
    }

    // then
    verify(emailService, never()).sendWelcomeEmail(anyString(), anyString());
    verify(eventPublisher, never()).publish(any(UserCreatedEvent.class));
}
```

### 2. 호출 순서 검증

```java
@Test
public void 올바른_순서로_호출됨() {
    // given
    User mockUser = new User(1L, "john", "john@example.com");
    when(userRepository.save(any(User.class))).thenReturn(mockUser);

    // when
    userService.createUser("john", "john@example.com");

    // then
    InOrder inOrder = inOrder(userRepository, emailService, eventPublisher);
    inOrder.verify(userRepository).save(any(User.class));
    inOrder.verify(emailService).sendWelcomeEmail(anyString(), anyString());
    inOrder.verify(eventPublisher).publish(any(UserCreatedEvent.class));
}
```

### 3. Spy 활용

만약 `UserService`에 로깅 메서드가 있다면:

```java
public class UserService {
    // ...

    private void logUserCreation(User user) {
        System.out.println("User created: " + user.getName());
    }
}
```

Spy로 테스트:

```java
@Spy
@InjectMocks
private UserService userService;

@Test
public void Spy를_사용한_부분_모킹() {
    // given
    User mockUser = new User(1L, "john", "john@example.com");
    when(userRepository.save(any(User.class))).thenReturn(mockUser);

    // logUserCreation()은 실제로 호출되지만,
    // 다른 의존성 호출은 mocking됨

    // when
    userService.createUser("john", "john@example.com");

    // then
    verify(userService).logUserCreation(any(User.class));
}
```

---

## 실전 팁

### 1. Given-When-Then 패턴 준수
```java
@Test
public void 명확한_테스트() {
    // given - 테스트 준비

    // when - 실제 동작

    // then - 결과 검증
}
```

### 2. 테스트 이름은 한글 또는 영문으로 명확하게
```java
@Test
public void 존재하지_않는_사용자_조회시_예외_발생() { }

@Test
public void whenUserNotFound_thenThrowException() { }
```

### 3. 하나의 테스트는 하나의 시나리오만
- 여러 검증을 하더라도 하나의 시나리오에 집중
- 너무 많은 것을 검증하면 테스트가 복잡해짐

### 4. Mock은 최소한으로
- 외부 의존성만 mocking
- 단순 객체는 실제 객체 사용
