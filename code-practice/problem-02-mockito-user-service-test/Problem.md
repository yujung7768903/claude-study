# 문제 2: Mockito를 활용한 UserService 테스트 작성

## 난이도: 중

## 학습 목표
- `@Mock`과 `@InjectMocks`를 사용하여 의존성 주입
- `when().thenReturn()`으로 mock 객체 stubbing
- `verify()`로 메서드 호출 검증
- `ArgumentCaptor`로 메서드에 전달된 파라미터 캡처 및 검증
- Argument Matcher와 Raw Value 혼용 시 주의사항 이해

## 문제 설명

사용자 관리 서비스(`UserService`)를 테스트하는 단위 테스트를 작성해야 합니다.
`UserService`는 사용자를 생성할 때 다음과 같은 동작을 수행합니다:

1. 사용자 정보를 Repository에 저장
2. 환영 이메일 발송
3. 사용자 생성 이벤트 발행

외부 의존성(Repository, EmailService, EventPublisher)은 실제로 동작하지 않고, Mockito를 사용하여 mocking해야 합니다.

## 제공된 클래스

### User.java (도메인 모델)
```java
public class User {
    private Long id;
    private String name;
    private String email;

    // 생성자, getter, setter 제공
}
```

### UserRepository.java (인터페이스)
```java
public interface UserRepository {
    User save(User user);
    Optional<User> findById(Long id);
    void deleteById(Long id);
}
```

### EmailService.java (인터페이스)
```java
public interface EmailService {
    void sendWelcomeEmail(String email, String userName);
}
```

### EventPublisher.java (인터페이스)
```java
public interface EventPublisher {
    void publish(UserCreatedEvent event);
}
```

### UserService.java (테스트 대상)
```java
public class UserService {
    private final UserRepository userRepository;
    private final EmailService emailService;
    private final EventPublisher eventPublisher;

    // 생성자 주입
    public UserService(UserRepository userRepository,
                      EmailService emailService,
                      EventPublisher eventPublisher) {
        this.userRepository = userRepository;
        this.emailService = emailService;
        this.eventPublisher = eventPublisher;
    }

    public User createUser(String name, String email) {
        User user = new User(name, email);
        User savedUser = userRepository.save(user);
        emailService.sendWelcomeEmail(email, name);
        eventPublisher.publish(new UserCreatedEvent(savedUser));
        return savedUser;
    }
}
```

## 요구사항

`UserServiceTest.java`를 완성하세요:

### 1. 테스트 환경 설정
- [ ] `@RunWith(MockitoJUnitRunner.class)` 추가
- [ ] `UserRepository`, `EmailService`, `EventPublisher`를 `@Mock`으로 선언
- [ ] `UserService`를 `@InjectMocks`로 선언하여 의존성 자동 주입

### 2. 테스트 케이스 1: `사용자_생성_성공_테스트()`
- [ ] Given: `userRepository.save()` stubbing (저장된 User 반환하도록)
- [ ] When: `userService.createUser()` 호출
- [ ] Then:
  - 반환된 User가 null이 아님
  - User의 name과 email이 정확함
  - `userRepository.save()` 1번 호출 검증
  - `emailService.sendWelcomeEmail()` 1번 호출 검증
  - `eventPublisher.publish()` 1번 호출 검증

### 3. 테스트 케이스 2: `사용자_생성시_올바른_이메일_파라미터_전달_확인()`
- [ ] `ArgumentCaptor<String>`을 사용하여 `sendWelcomeEmail()`에 전달된 파라미터 캡처
- [ ] 캡처한 email과 userName이 정확한지 검증
- [ ] **주의**: Argument Matcher와 Raw Value를 섞어 쓰지 말 것!

### 4. 테스트 케이스 3: `사용자_생성시_이벤트에_올바른_사용자_정보_포함_확인()`
- [ ] `ArgumentCaptor<UserCreatedEvent>`를 사용하여 이벤트 객체 캡처
- [ ] 캡처한 이벤트의 사용자 정보가 정확한지 검증

## 실행 결과 예시

```
=== UserServiceTest 실행 ===

✅ 사용자_생성_성공_테스트
✅ 사용자_생성시_올바른_이메일_파라미터_전달_확인
✅ 사용자_생성시_이벤트에_올바른_사용자_정보_포함_확인

모든 테스트 통과!
```

## 힌트

### Mock 선언
```java
@Mock
private UserRepository userRepository;
```

### Stubbing
```java
User mockUser = new User(1L, "john", "john@example.com");
when(userRepository.save(any(User.class))).thenReturn(mockUser);
```

### Verify
```java
verify(userRepository).save(any(User.class));
verify(emailService).sendWelcomeEmail(anyString(), anyString());
```

### ArgumentCaptor
```java
ArgumentCaptor<String> emailCaptor = ArgumentCaptor.forClass(String.class);
ArgumentCaptor<String> nameCaptor = ArgumentCaptor.forClass(String.class);

verify(emailService).sendWelcomeEmail(emailCaptor.capture(), nameCaptor.capture());

String capturedEmail = emailCaptor.getValue();
String capturedName = nameCaptor.getValue();
```

### ⚠️ Matcher와 Raw Value 혼용 금지!
```java
// ❌ 에러 발생
verify(emailService).sendWelcomeEmail(emailCaptor.capture(), "john");

// ✅ 올바름
verify(emailService).sendWelcomeEmail(emailCaptor.capture(), eq("john"));
```

## 테스트 방법

```bash
cd C:\Users\D4006124\claude-study\code-practice\problem-02-mockito-user-service-test

# 컴파일 (JUnit 4, Mockito 필요)
javac -cp ".;junit-4.13.2.jar;mockito-core-4.0.0.jar" *.java

# 실행
java -cp ".;junit-4.13.2.jar;mockito-core-4.0.0.jar" org.junit.runner.JUnitCore UserServiceTest
```

## 추가 도전 과제

1. **예외 처리 테스트**: Repository에서 예외 발생 시 서비스가 어떻게 동작하는지 테스트
   ```java
   when(userRepository.save(any())).thenThrow(new RuntimeException("DB 오류"));
   ```

2. **호출 순서 검증**: `InOrder`를 사용하여 save → sendEmail → publish 순서 확인
   ```java
   InOrder inOrder = inOrder(userRepository, emailService, eventPublisher);
   inOrder.verify(userRepository).save(any(User.class));
   inOrder.verify(emailService).sendWelcomeEmail(anyString(), anyString());
   inOrder.verify(eventPublisher).publish(any(UserCreatedEvent.class));
   ```

3. **Spy 활용**: `UserService`의 일부 메서드만 mocking하는 테스트 작성

## 관련 학습 자료

- `~/claude-study/20260210-mockito-unit-testing-guide.md`
- `~/claude-study/20260205-mockito-argument-captor.md`
- `~/claude-study/20260209-mockito-junit-runner-comparison.md`
