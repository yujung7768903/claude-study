# JUnit 4 Assertion 메서드 완벽 가이드

## 목차
1. [기본 Assertion 메서드](#기본-assertion-메서드)
2. [assertEquals vs assertSame](#assertequals-vs-assertsame)
3. [배열 검증](#배열-검증)
4. [예외 검증](#예외-검증)
5. [타임아웃 검증](#타임아웃-검증)
6. [Assertion 메서드 요약표](#assertion-메서드-요약표)
7. [실무 권장사항](#실무-권장사항)

---

## 빠른 참조 - Assertion 메서드 요약

### 기본 검증

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `assertEquals(expected, actual)` | 값 동등성 검증 (equals() 사용) | `assertEquals(5, result)` |
| `assertEquals(expected, actual, delta)` | 실수 비교 (오차 허용) | `assertEquals(3.14, pi, 0.01)` |
| `assertNotEquals(unexpected, actual)` | 값 불일치 검증 | `assertNotEquals(0, list.size())` |
| `assertTrue(condition)` | true 검증 | `assertTrue(user.isActive())` |
| `assertFalse(condition)` | false 검증 | `assertFalse(list.isEmpty())` |
| `assertNull(object)` | null 검증 | `assertNull(error)` |
| `assertNotNull(object)` | not null 검증 | `assertNotNull(user)` |

### 참조 검증

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `assertSame(expected, actual)` | 같은 객체 인스턴스 검증 (== 사용) | `assertSame(singleton1, singleton2)` |
| `assertNotSame(unexpected, actual)` | 다른 객체 인스턴스 검증 | `assertNotSame(user1, user2)` |

### 배열 검증

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `assertArrayEquals(expected, actual)` | 배열 비교 (순서, 길이, 각 요소) | `assertArrayEquals(arr1, arr2)` |
| `assertArrayEquals(expected, actual, delta)` | 실수 배열 비교 (오차 허용) | `assertArrayEquals(expected, actual, 0.01)` |

### 기타

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `fail()` | 테스트 강제 실패 | `fail("여기 도달하면 안 됨")` |
| `fail(message)` | 메시지와 함께 실패 | `fail("예외가 발생해야 함")` |

### 테스트 어노테이션

| 어노테이션 | 설명 | 예시 |
|-----------|------|------|
| `@Test(expected = Exception.class)` | 예외 발생 검증 | `@Test(expected = IllegalArgumentException.class)` |
| `@Test(timeout = 1000)` | 타임아웃 검증 (밀리초) | `@Test(timeout = 1000)` |

> 💡 **팁**: 모든 assertion 메서드는 첫 번째 파라미터로 실패 메시지를 받을 수 있습니다.
> 예: `assertEquals("사용자 이름이 일치해야 함", expected, actual)`

---

## 기본 Assertion 메서드

JUnit 4의 모든 assertion 메서드는 `org.junit.Assert` 클래스에 정의되어 있습니다.

### import 문
```java
import static org.junit.Assert.*;
```

static import를 사용하면 `Assert.`를 생략하고 바로 `assertEquals()` 등을 사용할 수 있습니다.

---

### 1. assertEquals - 값 동등성 검증

두 값이 같은지 확인합니다.

```java
@Test
public void assertEquals_예제() {
    // 기본 사용법
    assertEquals(expected, actual);

    // 메시지 포함 (실패 시 출력)
    assertEquals("사용자 이름이 일치해야 함", "john", user.getName());

    // 기본 타입
    assertEquals(10, calculator.add(5, 5));
    assertEquals('A', result.charAt(0));
    assertEquals(true, user.isActive());

    // 객체 (equals() 메서드 사용)
    User expected = new User("john", "john@example.com");
    User actual = userService.getUser(1L);
    assertEquals(expected, actual);
}
```

**실수(float, double) 비교 - delta 필요:**
```java
@Test
public void 실수_비교() {
    // ❌ 잘못된 방법 - 부동소수점 오차로 실패할 수 있음
    // assertEquals(0.3, 0.1 + 0.2);

    // ✅ 올바른 방법 - delta(허용 오차) 사용
    assertEquals(0.3, 0.1 + 0.2, 0.0001);

    double expected = 3.14159;
    double actual = Math.PI;
    assertEquals(expected, actual, 0.00001);  // 소수점 5자리까지 같으면 통과
}
```

---

### 2. assertNotEquals - 값 불일치 검증

두 값이 다른지 확인합니다.

```java
@Test
public void assertNotEquals_예제() {
    assertNotEquals("관리자", user.getRole());
    assertNotEquals(0, list.size());

    User user1 = new User("john");
    User user2 = new User("jane");
    assertNotEquals(user1, user2);
}
```

---

### 3. assertTrue / assertFalse - boolean 검증

```java
@Test
public void assertTrue_예제() {
    assertTrue(user.isActive());
    assertTrue("리스트가 비어있지 않아야 함", !list.isEmpty());
    assertTrue(number > 0);
    assertTrue(name.startsWith("test"));
}

@Test
public void assertFalse_예제() {
    assertFalse(user.isDeleted());
    assertFalse("중복된 이메일이 없어야 함", isDuplicate);
    assertFalse(list.contains("invalid"));
}
```

---

### 4. assertNull / assertNotNull - null 검증

```java
@Test
public void assertNull_예제() {
    User user = userRepository.findById(999L);
    assertNull("존재하지 않는 사용자는 null이어야 함", user);

    String error = validator.validate(validData);
    assertNull(error);  // 에러가 없으면 null
}

@Test
public void assertNotNull_예제() {
    User user = userService.createUser("john", "john@example.com");
    assertNotNull("생성된 사용자는 null이 아니어야 함", user);

    assertNotNull(user.getId());
    assertNotNull(user.getCreatedAt());
}
```

---

### 5. assertSame / assertNotSame - 참조 동일성 검증

같은 객체 인스턴스인지 확인합니다 (== 비교).

```java
@Test
public void assertSame_예제() {
    // 싱글톤 패턴 검증
    UserService service1 = UserService.getInstance();
    UserService service2 = UserService.getInstance();
    assertSame("싱글톤은 같은 인스턴스여야 함", service1, service2);

    // 캐시된 객체 검증
    User user1 = userCache.get(1L);
    User user2 = userCache.get(1L);
    assertSame(user1, user2);
}

@Test
public void assertNotSame_예제() {
    User user1 = new User("john");
    User user2 = new User("john");

    // 값은 같지만 다른 인스턴스
    assertEquals(user1, user2);       // equals() 비교 - 통과
    assertNotSame(user1, user2);      // == 비교 - 통과
}
```

---

### 6. fail - 테스트 강제 실패

```java
@Test
public void fail_예제() {
    try {
        service.invalidOperation();
        fail("예외가 발생해야 함");  // 여기 도달하면 안 됨
    } catch (IllegalArgumentException e) {
        // 예외 발생 예상 - 성공
    }
}

@Test
public void 조건부_실패() {
    if (user.getAge() < 0) {
        fail("나이는 음수가 될 수 없음");
    }
}
```

---

## assertEquals vs assertSame

| 구분 | assertEquals | assertSame |
|------|-------------|-----------|
| 비교 방식 | `equals()` 메서드 | `==` 연산자 |
| 검증 대상 | **값의 동등성** | **참조의 동일성** |
| 사용 시나리오 | 객체의 내용이 같은지 | 정확히 같은 객체 인스턴스인지 |

### 예제로 이해하기

```java
@Test
public void assertEquals_vs_assertSame() {
    String str1 = new String("hello");
    String str2 = new String("hello");
    String str3 = str1;

    // assertEquals - equals() 비교
    assertEquals(str1, str2);         // ✅ 통과 (내용이 같음)

    // assertSame - == 비교
    assertSame(str1, str2);           // ❌ 실패 (다른 객체)
    assertSame(str1, str3);           // ✅ 통과 (같은 객체)

    // String literal의 경우
    String a = "hello";
    String b = "hello";
    assertSame(a, b);                 // ✅ 통과 (String pool에서 같은 객체)
}
```

---

## 배열 검증

### assertArrayEquals - 배열 비교

```java
@Test
public void assertArrayEquals_예제() {
    // int 배열
    int[] expected = {1, 2, 3, 4, 5};
    int[] actual = service.getNumbers();
    assertArrayEquals(expected, actual);

    // String 배열
    String[] expectedNames = {"john", "jane", "bob"};
    String[] actualNames = userService.getAllNames();
    assertArrayEquals("사용자 이름 배열이 일치해야 함", expectedNames, actualNames);

    // byte 배열
    byte[] expectedBytes = {0x01, 0x02, 0x03};
    byte[] actualBytes = file.readBytes();
    assertArrayEquals(expectedBytes, actualBytes);
}

@Test
public void 실수_배열_비교() {
    double[] expected = {1.1, 2.2, 3.3};
    double[] actual = calculator.calculate();

    // delta 사용
    assertArrayEquals(expected, actual, 0.001);
}
```

**주의사항:**
- 배열의 **순서**와 **길이**가 모두 같아야 함
- 각 요소를 `equals()`로 비교

```java
@Test
public void 배열_검증_예제() {
    int[] arr1 = {1, 2, 3};
    int[] arr2 = {1, 2, 3};
    int[] arr3 = {3, 2, 1};
    int[] arr4 = {1, 2};

    assertArrayEquals(arr1, arr2);    // ✅ 통과
    assertArrayEquals(arr1, arr3);    // ❌ 실패 (순서 다름)
    assertArrayEquals(arr1, arr4);    // ❌ 실패 (길이 다름)
}
```

---

## 예외 검증

### 방법 1: @Test(expected = ...)

```java
@Test(expected = IllegalArgumentException.class)
public void 잘못된_입력시_예외_발생() {
    userService.createUser(null, "");  // 예외 발생 예상
}

@Test(expected = NullPointerException.class)
public void null_처리_예외() {
    service.process(null);
}
```

**장점:** 간단하고 읽기 쉬움
**단점:** 예외 메시지나 상세 내용 검증 불가

### 방법 2: try-catch + fail()

```java
@Test
public void 예외_메시지_검증() {
    try {
        userService.createUser("", "invalid-email");
        fail("예외가 발생해야 함");
    } catch (IllegalArgumentException e) {
        // 예외 메시지 검증
        assertEquals("이메일 형식이 올바르지 않습니다", e.getMessage());
        assertTrue(e.getMessage().contains("이메일"));
    }
}

@Test
public void 여러_검증이_필요한_경우() {
    try {
        service.dangerousOperation();
        fail("예외가 발생해야 함");
    } catch (CustomException e) {
        assertEquals(ErrorCode.INVALID_STATE, e.getErrorCode());
        assertEquals(400, e.getHttpStatus());
        assertNotNull(e.getDetails());
    }
}
```

**장점:** 예외의 상세 내용 검증 가능
**단점:** 코드가 길어짐

### 방법 3: ExpectedException Rule (JUnit 4.7+)

```java
import org.junit.Rule;
import org.junit.rules.ExpectedException;

public class UserServiceTest {

    @Rule
    public ExpectedException thrown = ExpectedException.none();

    @Test
    public void 예외_상세_검증() {
        thrown.expect(IllegalArgumentException.class);
        thrown.expectMessage("이메일");
        thrown.expectMessage(containsString("형식"));

        userService.createUser("", "invalid-email");
    }
}
```

**장점:** 예외 타입과 메시지 모두 검증 가능, 깔끔한 코드
**단점:** Rule 설정 필요

---

## 타임아웃 검증

### @Test(timeout = ...)

```java
@Test(timeout = 1000)  // 1초 안에 완료되어야 함
public void 성능_테스트() {
    List<User> users = userService.getAllUsers();
    // 1초 이내에 완료되지 않으면 실패
}

@Test(timeout = 100)
public void 빠른_조회_테스트() {
    User user = userCache.get(1L);
    assertNotNull(user);
    // 캐시 조회는 100ms 이내여야 함
}
```

**주의사항:**
- timeout 단위는 **밀리초(ms)**
- 너무 짧게 설정하면 불안정한 테스트 발생
- CI/CD 환경에서는 여유있게 설정

---

## Assertion 메서드 요약표

### 기본 검증

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `assertEquals(expected, actual)` | 값 동등성 검증 | `assertEquals(5, result)` |
| `assertEquals(expected, actual, delta)` | 실수 비교 (오차 허용) | `assertEquals(3.14, pi, 0.01)` |
| `assertNotEquals(unexpected, actual)` | 값 불일치 검증 | `assertNotEquals(0, list.size())` |
| `assertTrue(condition)` | true 검증 | `assertTrue(user.isActive())` |
| `assertFalse(condition)` | false 검증 | `assertFalse(list.isEmpty())` |
| `assertNull(object)` | null 검증 | `assertNull(error)` |
| `assertNotNull(object)` | not null 검증 | `assertNotNull(user)` |

### 참조 검증

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `assertSame(expected, actual)` | 같은 객체 인스턴스 검증 | `assertSame(singleton1, singleton2)` |
| `assertNotSame(unexpected, actual)` | 다른 객체 인스턴스 검증 | `assertNotSame(user1, user2)` |

### 배열 검증

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `assertArrayEquals(expected, actual)` | 배열 비교 | `assertArrayEquals(arr1, arr2)` |
| `assertArrayEquals(expected, actual, delta)` | 실수 배열 비교 | `assertArrayEquals(expected, actual, 0.01)` |

### 기타

| 메서드 | 설명 | 예시 |
|--------|------|------|
| `fail()` | 테스트 강제 실패 | `fail("여기 도달하면 안 됨")` |
| `fail(message)` | 메시지와 함께 실패 | `fail("예외가 발생해야 함")` |

### 메시지 오버로딩

모든 assertion 메서드는 첫 번째 파라미터로 **실패 메시지**를 받을 수 있습니다:

```java
assertEquals("사용자 이름이 일치해야 함", expected, actual);
assertTrue("리스트가 비어있지 않아야 함", !list.isEmpty());
assertNotNull("생성된 사용자는 null이 아니어야 함", user);
```

---

## 실무 권장사항

### 1. 의미 있는 실패 메시지 작성

**❌ 나쁜 예:**
```java
assertEquals(5, result);
assertTrue(user.isActive());
```

**✅ 좋은 예:**
```java
assertEquals("총합 계산 결과가 5여야 함", 5, result);
assertTrue("활성 사용자여야 함", user.isActive());
```

실패 메시지가 있으면 테스트 실패 원인을 빠르게 파악할 수 있습니다.

### 2. 적절한 Assertion 메서드 선택

**❌ 나쁜 예:**
```java
assertTrue(result == 5);              // assertEquals 사용해야 함
assertTrue(user != null);             // assertNotNull 사용해야 함
assertTrue(list.size() == 0);         // assertEquals 또는 assertTrue(isEmpty()) 사용
```

**✅ 좋은 예:**
```java
assertEquals(5, result);
assertNotNull(user);
assertEquals(0, list.size());  // 또는 assertTrue(list.isEmpty());
```

### 3. assertEquals의 파라미터 순서 지키기

**올바른 순서: `assertEquals(expected, actual)`**

```java
// ✅ 올바름
int expected = 5;
int actual = calculator.add(2, 3);
assertEquals(expected, actual);

// ❌ 잘못됨 (순서 바뀜)
assertEquals(actual, expected);  // 실패 메시지가 헷갈림
```

실패 시 메시지:
```
Expected: 5
Actual: 3
```

순서가 바뀌면 메시지도 바뀌어서 혼란스러움.

### 4. 실수 비교 시 항상 delta 사용

**❌ 나쁜 예:**
```java
assertEquals(0.3, 0.1 + 0.2);  // 부동소수점 오차로 실패 가능
```

**✅ 좋은 예:**
```java
assertEquals(0.3, 0.1 + 0.2, 0.0001);
```

### 5. 예외 검증은 구체적으로

**❌ 나쁜 예:**
```java
@Test(expected = Exception.class)  // 너무 광범위
public void 예외_테스트() {
    service.invalidOperation();
}
```

**✅ 좋은 예:**
```java
@Test(expected = IllegalArgumentException.class)  // 구체적인 예외
public void 잘못된_인자_전달시_예외_발생() {
    service.invalidOperation();
}
```

### 6. 여러 검증은 명확하게 분리

**❌ 나쁜 예:**
```java
@Test
public void 사용자_생성_테스트() {
    User user = userService.createUser("john", "john@example.com");
    assertTrue(user != null && user.getName().equals("john") && user.getEmail().equals("john@example.com"));
}
```

**✅ 좋은 예:**
```java
@Test
public void 사용자_생성_테스트() {
    User user = userService.createUser("john", "john@example.com");

    assertNotNull(user);
    assertEquals("john", user.getName());
    assertEquals("john@example.com", user.getEmail());
}
```

### 7. 컬렉션 검증 팁

```java
@Test
public void 컬렉션_검증() {
    List<User> users = userService.findAll();

    // 크기 검증
    assertEquals("사용자가 3명이어야 함", 3, users.size());

    // 비어있지 않음 검증
    assertFalse("리스트가 비어있지 않아야 함", users.isEmpty());

    // 특정 요소 포함 검증
    assertTrue("john이 포함되어야 함", users.stream()
        .anyMatch(u -> "john".equals(u.getName())));

    // 첫 번째 요소 검증
    assertEquals("john", users.get(0).getName());
}
```

### 8. null vs empty 구분

```java
@Test
public void null_vs_empty() {
    String result1 = service.getOptionalValue();  // null 반환 가능
    String result2 = service.getRequiredValue();  // 빈 문자열 반환 가능

    // null 검증
    assertNull("값이 없으면 null이어야 함", result1);

    // empty 검증
    assertNotNull("null이 아니어야 함", result2);
    assertEquals("빈 문자열이어야 함", "", result2);
    assertTrue("비어있어야 함", result2.isEmpty());
}
```

---

## Hamcrest Matchers와 함께 사용 (선택)

JUnit 4는 Hamcrest matchers를 지원합니다 (더 읽기 쉬운 assertion):

```java
import static org.hamcrest.CoreMatchers.*;
import static org.junit.Assert.assertThat;

@Test
public void hamcrest_예제() {
    String result = "hello world";

    // assertThat 사용
    assertThat(result, is("hello world"));
    assertThat(result, startsWith("hello"));
    assertThat(result, containsString("world"));
    assertThat(result, not(containsString("foo")));

    // 숫자 비교
    assertThat(result.length(), is(11));
    assertThat(10, greaterThan(5));
    assertThat(3, lessThan(5));

    // 컬렉션
    List<String> list = Arrays.asList("a", "b", "c");
    assertThat(list, hasItem("b"));
    assertThat(list, hasItems("a", "c"));
}
```

하지만 기본 assertion 메서드만으로도 충분하므로 선택사항입니다.

---

## 체크리스트

테스트 작성 시 확인사항:

- [ ] 적절한 assertion 메서드를 사용했는가? (assertEquals, assertNull 등)
- [ ] assertEquals의 파라미터 순서가 올바른가? (expected, actual)
- [ ] 실수 비교 시 delta를 사용했는가?
- [ ] 의미 있는 실패 메시지를 작성했는가?
- [ ] 예외 검증이 필요하면 적절한 방법을 사용했는가?
- [ ] 하나의 테스트에서 너무 많은 것을 검증하지 않는가?
- [ ] null과 empty를 구분하여 검증했는가?

---

## 참고 자료

- [JUnit 4 공식 문서](https://junit.org/junit4/)
- [JUnit 4 API - Assert](https://junit.org/junit4/javadoc/latest/org/junit/Assert.html)
- [JUnit 4 Wiki](https://github.com/junit-team/junit4/wiki)

---

## JUnit 5와의 차이점 (참고)

JUnit 5에서는 assertion 패키지와 일부 메서드명이 변경되었습니다:

| JUnit 4 | JUnit 5 |
|---------|---------|
| `org.junit.Assert.*` | `org.junit.jupiter.api.Assertions.*` |
| `@Test(expected = ...)` | `assertThrows()` |
| `@Test(timeout = ...)` | `assertTimeout()` |

JUnit 4를 사용 중이라면 이 가이드를 따르고, JUnit 5로 마이그레이션 시 참고하세요.
