# JUnit 테스트 메서드 시그니처 규칙

## 핵심 답변

**JUnit 4**: `public void` 권장 (하지만 package-private도 동작)
**JUnit 5**: `public` 불필요, **package-private 권장**
**공통**: 반드시 `void` (반환값 없음), `static` 불가

## JUnit 버전별 규칙

### JUnit 4 (@Test)

```java
// ✅ 권장: public void
@Test
public void testSomething() {
    assertEquals(1, 1);
}

// ✅ 동작함: package-private (default)
@Test
void testSomething() {
    assertEquals(1, 1);
}

// ✅ 동작함: protected
@Test
protected void testSomething() {
    assertEquals(1, 1);
}

// ❌ 동작 안 함: private
@Test
private void testSomething() {  // 무시됨
    assertEquals(1, 1);
}

// ❌ 동작 안 함: static
@Test
public static void testSomething() {  // 에러
    assertEquals(1, 1);
}

// ❌ 컴파일 에러: 반환값 있음
@Test
public String testSomething() {  // void여야 함
    return "test";
}
```

### JUnit 5 (@Test)

```java
// ✅ 권장: package-private (public 불필요)
@Test
void testSomething() {
    assertEquals(1, 1);
}

// ✅ 동작함: public (하지만 불필요)
@Test
public void testSomething() {
    assertEquals(1, 1);
}

// ✅ 동작함: protected
@Test
protected void testSomething() {
    assertEquals(1, 1);
}

// ❌ 동작 안 함: private
@Test
private void testSomething() {  // 무시됨
    assertEquals(1, 1);
}

// ❌ 동작 안 함: static
@Test
static void testSomething() {  // 에러 (단, @TestFactory는 예외)
    assertEquals(1, 1);
}
```

## 접근 제어자 비교표

| 접근 제어자 | JUnit 4 | JUnit 5 | 권장 여부 |
|------------|---------|---------|----------|
| `public` | ✅ 동작 (권장) | ✅ 동작 | JUnit 4: 권장<br>JUnit 5: 불필요 |
| package-private (기본) | ✅ 동작 | ✅ 동작 (권장) | JUnit 5: 권장 |
| `protected` | ✅ 동작 | ✅ 동작 | 상속 시 사용 |
| `private` | ❌ 무시됨 | ❌ 무시됨 | 절대 사용 금지 |

## 반환 타입 규칙

### void만 가능

```java
// ✅ 정상
@Test
public void test() {
    assertTrue(true);
}

// ❌ 컴파일 에러
@Test
public int test() {  // void여야 함
    return 1;
}

// ❌ 컴파일 에러
@Test
public String test() {
    return "result";
}
```

**왜 void인가?**
- 테스트는 성공(pass) 또는 실패(fail)만 있음
- 성공: 예외 없이 종료
- 실패: AssertionError 발생
- 반환값으로 결과를 전달할 필요 없음

## static 메서드 규칙

### 일반 @Test는 static 불가

```java
// ❌ JUnit 4: 에러
@Test
public static void test() {
    assertEquals(1, 1);
}

// ❌ JUnit 5: 에러
@Test
static void test() {
    assertEquals(1, 1);
}
```

### 예외: @BeforeAll, @AfterAll은 static 필수 (JUnit 5)

```java
// ✅ JUnit 5: @BeforeAll은 static이어야 함
@BeforeAll
static void setupOnce() {
    System.out.println("테스트 클래스 실행 전 1회");
}

// ✅ JUnit 5: @AfterAll은 static이어야 함
@AfterAll
static void teardownOnce() {
    System.out.println("테스트 클래스 실행 후 1회");
}

// ❌ static 아니면 에러
@BeforeAll
void setupOnce() {  // 에러!
}
```

**예외의 예외**: `@TestInstance(Lifecycle.PER_CLASS)` 사용 시 non-static 가능

```java
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class MyTest {

    @BeforeAll
    void setupOnce() {  // ✅ static 아니어도 됨
        System.out.println("PER_CLASS 모드에서는 가능");
    }

    @Test
    void test() {
        assertTrue(true);
    }
}
```

## 실무 권장사항

### JUnit 4 프로젝트

```java
@RunWith(MockitoJUnitRunner.class)
public class UserServiceTest {

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    @Test
    public void getUserById_존재하는_유저_반환() {  // public void 권장
        // given
        when(userRepository.findById(1L))
            .thenReturn(Optional.of(new User("John")));

        // when
        User user = userService.getUserById(1L);

        // then
        assertEquals("John", user.getName());
    }
}
```

### JUnit 5 프로젝트

```java
@ExtendWith(MockitoExtension.class)
class UserServiceTest {  // class도 public 불필요

    @Mock
    private UserRepository userRepository;

    @InjectMocks
    private UserService userService;

    @Test
    void getUserById_존재하는_유저_반환() {  // package-private 권장
        // given
        when(userRepository.findById(1L))
            .thenReturn(Optional.of(new User("John")));

        // when
        User user = userService.getUserById(1L);

        // then
        assertEquals("John", user.getName());
    }

    @BeforeAll
    static void setupOnce() {  // static 필수
        System.out.println("전체 테스트 시작 전 1회 실행");
    }

    @BeforeEach
    void setup() {  // non-static (매 테스트마다 실행)
        System.out.println("각 테스트 실행 전");
    }
}
```

## 왜 JUnit 4와 5의 가이드가 다른가?

### 1. 역사적 배경: JUnit 4의 public 권장 이유

#### JUnit 3 시대 (2000년대 초)
```java
// JUnit 3: 반드시 public이어야 했음
public class MyTest extends TestCase {
    public void testSomething() {  // public 필수!
        assertEquals(1, 1);
    }
}
```

- **내부 구현**: `Class.getMethod()` 사용 → public 메서드만 찾을 수 있음
- **제약 사항**: TestCase 상속 필수, test로 시작하는 메서드명 필요
- **결과**: `public` 없으면 테스트가 실행되지 않음

#### JUnit 4 시대 (2006년~)
```java
// JUnit 4: 애노테이션 도입
public class MyTest {
    @Test
    public void testSomething() {  // public 권장 (실제로는 package-private도 동작)
        assertEquals(1, 1);
    }
}
```

- **개선**: 애노테이션 도입, TestCase 상속 불필요
- **내부 구현**: `Class.getDeclaredMethod()` + `setAccessible(true)` 사용
- **하지만**: JUnit 3 호환성과 관습 때문에 **public을 권장**으로 유지
- **실제**: package-private도 동작하지만, 공식 문서는 public 권장

### 2. JUnit 5의 패러다임 변화 (2017년~)

JUnit 5는 **완전한 재작성(from scratch)**으로 만들어졌습니다.

#### 설계 철학 변화

| 측면 | JUnit 4 | JUnit 5 |
|------|---------|---------|
| **Java 버전** | Java 5+ | Java 8+ |
| **설계 원칙** | 하위 호환성 중시 | 모던 Java 활용 |
| **Boilerplate** | public 권장 (관습) | 불필요한 것 제거 |
| **확장성** | @RunWith 단일 방식 | @ExtendWith 다중 가능 |
| **아키텍처** | 단일 모듈 | 모듈화 (Platform, Jupiter, Vintage) |

#### 내부 구현 개선

```java
// JUnit 4 내부 (단순화)
public class BlockJUnit4ClassRunner {
    protected void validatePublicVoidNoArgMethods(...) {
        // public void 검증 (실제로는 package-private도 허용)
    }

    protected Object createTest() {
        return testClass.getConstructor().newInstance();
    }
}

// JUnit 5 내부 (단순화)
public class MethodInvocationContext {
    public void proceed() {
        Method method = findMethod();
        ReflectionUtils.makeAccessible(method);  // public 불필요!
        method.invoke(target, resolvedArguments);
    }
}
```

**JUnit 5의 개선점**:
1. **명시적 접근성 제어**: `setAccessible(true)` 적극 활용
2. **Java 8+ 기능**: Lambda, Stream, Optional 활용
3. **명확한 가이드**: "public은 불필요하다"고 명시
4. **확장 가능**: Extension 모델로 완전히 재설계

### 3. 구체적인 내부 동작 비교

#### JUnit 4 리플렉션 방식
```java
// org.junit.runners.BlockJUnit4ClassRunner
protected void validateTestMethods(List<Throwable> errors) {
    List<FrameworkMethod> methods = getTestClass().getAnnotatedMethods(Test.class);
    for (FrameworkMethod method : methods) {
        method.validatePublicVoidNoArg(false, errors);
        // 실제로는 getDeclaredMethods()를 사용하므로 package-private도 동작
        // 하지만 "public void" 검증 메서드가 존재 (하위 호환성)
    }
}

// 실제 메서드 찾기
public Method getMethod() {
    return method;  // getDeclaredMethod로 찾음 (package-private도 가능)
}
```

**왜 package-private도 동작하는가?**
- JUnit 4는 내부적으로 `getDeclaredMethod()`를 사용
- 하지만 **공식 가이드는 여전히 public 권장** (관습 유지)
- 실제 동작과 권장 사항이 일치하지 않는 상황

#### JUnit 5 리플렉션 방식
```java
// org.junit.jupiter.engine.execution.ExecutableInvoker
public Object invoke(Method method, Object target, Object... args) {
    ReflectionUtils.makeAccessible(method);  // 명시적으로 접근 가능하게 만듦
    return ReflectionSupport.invokeMethod(method, target, args);
}

// ReflectionUtils.java
public static void makeAccessible(Method method) {
    if (!method.canAccess(null)) {
        method.setAccessible(true);  // private만 아니면 접근 가능
    }
}
```

**JUnit 5의 명확한 입장**:
- 공식 문서: "Test methods **must not be** private"
- public에 대한 언급 없음 → **package-private 권장**
- 내부 구현과 가이드가 일치

### 4. 패러다임 변화 요약

```
JUnit 3 (2000년대)
└─ public 필수 (getMethod() 제약)
    ↓
JUnit 4 (2006~)
└─ package-private 동작 (getDeclaredMethod())
   하지만 public 권장 (JUnit 3 호환성, 관습)
    ↓
JUnit 5 (2017~)
└─ package-private 권장 (완전한 재설계)
   "불필요한 boilerplate 제거" 철학
```

### 5. 왜 이런 변화가 중요한가?

#### 철학적 관점
```java
// 테스트 메서드는 외부에서 직접 호출되지 않음
public void test() {  // public이 필요한가?
    // 이 메서드는 JUnit 프레임워크만 호출함
    // 다른 클래스에서 직접 호출할 일 없음
}

// package-private이 더 적절
void test() {  // 같은 패키지 내에서만 접근 가능 (충분함)
    // JUnit은 Reflection으로 호출하므로 문제없음
}
```

#### 실용적 관점
```java
// JUnit 4: 불필요한 public이 많음
public class MyTest {
    public void test1() { }
    public void test2() { }
    public void test3() { }
    // 모든 메서드에 public...
}

// JUnit 5: 간결함
class MyTest {  // class도 public 불필요
    void test1() { }
    void test2() { }
    void test3() { }
    // 깔끔!
}
```

### 6. Java 모듈 시스템과의 관계 (Java 9+)

JUnit 5는 Java 9의 모듈 시스템도 고려했습니다.

```java
// module-info.java
module com.example.app {
    requires org.junit.jupiter.api;

    // 테스트 패키지를 JUnit에 열기
    opens com.example.app.test to org.junit.platform.commons;
}
```

- package-private 메서드도 `opens` 디렉티브로 접근 가능
- public 불필요

## 결론: 왜 가이드가 달라졌는가?

### 기술적 이유
1. **JUnit 4**: 내부적으로는 package-private 가능하지만, 레거시 호환성으로 public 권장
2. **JUnit 5**: 처음부터 Reflection을 적극 활용하도록 설계, public 불필요

### 철학적 이유
1. **JUnit 4**: 보수적 접근 (기존 코드와의 호환성)
2. **JUnit 5**: 모던 Java 철학 (불필요한 boilerplate 제거)

### 실용적 이유
1. **가시성 원칙**: 테스트 메서드는 외부에서 호출할 필요 없음
2. **캡슐화**: package-private이 더 적절한 접근 제어
3. **간결성**: 불필요한 `public` 키워드 제거

## 메서드 명명 규칙

접근 제어자와 반환 타입보다 **메서드 이름**이 더 중요합니다.

### 권장 네이밍 패턴

```java
// 패턴 1: 메서드명_상황_예상결과
@Test
void getUserById_존재하지않는ID_예외발생() {
    assertThrows(UserNotFoundException.class, () -> {
        userService.getUserById(999L);
    });
}

// 패턴 2: given_when_then
@Test
void givenInvalidId_whenGetUser_thenThrowException() {
    assertThrows(UserNotFoundException.class, () -> {
        userService.getUserById(999L);
    });
}

// 패턴 3: 한글 (가독성 우선)
@Test
void 존재하지_않는_사용자_조회시_예외_발생() {
    assertThrows(UserNotFoundException.class, () -> {
        userService.getUserById(999L);
    });
}

// 패턴 4: should 패턴
@Test
void shouldThrowExceptionWhenUserNotFound() {
    assertThrows(UserNotFoundException.class, () -> {
        userService.getUserById(999L);
    });
}
```

### DisplayName 활용 (JUnit 5)

```java
@Test
@DisplayName("존재하지 않는 사용자 조회 시 UserNotFoundException 발생")
void test1() {
    assertThrows(UserNotFoundException.class, () -> {
        userService.getUserById(999L);
    });
}

// 결과 출력:
// ✓ 존재하지 않는 사용자 조회 시 UserNotFoundException 발생
```

## 특수한 경우

### 1. 파라미터가 있는 테스트 (JUnit 5)

```java
@ParameterizedTest
@ValueSource(ints = {1, 2, 3})
void testWithParameter(int number) {  // 파라미터 가능
    assertTrue(number > 0);
}
```

### 2. 동적 테스트 (@TestFactory)

```java
@TestFactory
Collection<DynamicTest> dynamicTests() {  // void 아님! Collection 반환
    return Arrays.asList(
        DynamicTest.dynamicTest("1 + 1 = 2", () -> assertEquals(2, 1 + 1)),
        DynamicTest.dynamicTest("2 + 2 = 4", () -> assertEquals(4, 2 + 2))
    );
}
```

### 3. 템플릿 메서드 패턴

```java
@Test
public void testTemplate() {
    setup();
    execute();
    verify();
}

// 헬퍼 메서드는 private 가능
private void setup() {
    // 준비
}

private void execute() {
    // 실행
}

private void verify() {
    // 검증
}
```

## 요약

| 항목 | JUnit 4 | JUnit 5 | 필수 여부 |
|------|---------|---------|----------|
| **접근 제어자** | `public` 권장 | package-private 권장 | private만 피하면 됨 |
| **반환 타입** | `void` | `void` | **필수** (예외: @TestFactory) |
| **static** | 불가 | 불가 | **금지** (예외: @BeforeAll/@AfterAll) |
| **파라미터** | 불가 | 가능 (@ParameterizedTest) | 일반 @Test는 불가 |

### 핵심 정리

1. **가이드가 다른 이유**:
   - JUnit 4: 레거시 호환성으로 public 권장 (실제로는 package-private도 동작)
   - JUnit 5: 완전 재설계, 불필요한 boilerplate 제거 철학
2. **JUnit 4**: `public void` 사용 (관습)
3. **JUnit 5**: package-private `void` 권장 (더 간결)
4. **반환 타입**: 항상 `void` (예외: @TestFactory)
5. **private**: 절대 안 됨 (JUnit이 찾지 못함)
6. **static**: 일반 @Test는 안 됨 (@BeforeAll/@AfterAll은 필수)

### Best Practice

```java
// JUnit 4
public class MyTest {
    @Test
    public void shouldDoSomething() { }  // public void
}

// JUnit 5
class MyTest {
    @Test
    void shouldDoSomething() { }  // package-private void
}
```
