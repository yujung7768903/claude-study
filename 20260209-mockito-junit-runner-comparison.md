# MockitoJUnitRunner 비교: runners vs junit 패키지

## 개념 설명

Mockito에서 제공하는 두 개의 `MockitoJUnitRunner`는 패키지 위치와 지원하는 JUnit 버전이 다릅니다.

### 1. `org.mockito.runners.MockitoJUnitRunner` (구버전)
- **JUnit 4** 전용
- Mockito **1.x ~ 2.x** 버전에서 사용
- **@Deprecated** (더 이상 사용 권장 안 함)
- `@RunWith(MockitoJUnitRunner.class)` 형태로 사용

### 2. `org.mockito.junit.MockitoJUnitRunner` (신버전)
- **JUnit 4** 전용
- Mockito **2.1.0 이상** 버전에서 도입
- 현재 **권장되는 방식**
- `runners` 패키지의 후속 버전
- 더 나은 성능과 버그 수정 포함

## 주요 차이점

| 항목 | org.mockito.runners | org.mockito.junit |
|------|---------------------|-------------------|
| **도입 시기** | Mockito 1.x | Mockito 2.1.0+ |
| **상태** | Deprecated | Active |
| **JUnit 버전** | JUnit 4 | JUnit 4 |
| **사용 권장** | ❌ 사용 중단 | ✅ 권장 |
| **기능** | 기본 기능만 | 개선된 기능 + 버그 수정 |

## 코드 예시

### 구버전 (사용 지양)
```java
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.runners.MockitoJUnitRunner;  // ❌ Deprecated

@RunWith(MockitoJUnitRunner.class)
public class MyServiceTest {

    @Mock
    private MyRepository repository;

    @Test
    public void testSomething() {
        // 테스트 코드
    }
}
```

### 신버전 (권장)
```java
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.junit.MockitoJUnitRunner;  // ✅ 권장

@RunWith(MockitoJUnitRunner.class)
public class MyServiceTest {

    @Mock
    private MyRepository repository;

    @Test
    public void testSomething() {
        // 테스트 코드
    }
}
```

### JUnit 5를 사용한다면 (최신 방식)
```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;  // JUnit 5용

@ExtendWith(MockitoExtension.class)
public class MyServiceTest {

    @Mock
    private MyRepository repository;

    @Test
    public void testSomething() {
        // 테스트 코드
    }
}
```

## Runner를 사용하지 않는 대안

### MockitoAnnotations.openMocks() 사용
```java
import org.junit.Before;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

public class MyServiceTest {

    @Mock
    private MyRepository repository;

    private AutoCloseable closeable;

    @Before
    public void setUp() {
        closeable = MockitoAnnotations.openMocks(this);
    }

    @After
    public void tearDown() throws Exception {
        closeable.close();
    }

    @Test
    public void testSomething() {
        // 테스트 코드
    }
}
```

## 마이그레이션 가이드

### 1단계: Import 변경
```java
// Before
import org.mockito.runners.MockitoJUnitRunner;

// After
import org.mockito.junit.MockitoJUnitRunner;
```

### 2단계: 코드는 그대로 유지
```java
@RunWith(MockitoJUnitRunner.class)  // 변경 없음
public class MyServiceTest {
    // 테스트 코드 그대로
}
```

## 실무 권장사항

### 1. JUnit 4 프로젝트
✅ **권장**: `org.mockito.junit.MockitoJUnitRunner` 사용
```java
import org.mockito.junit.MockitoJUnitRunner;

@RunWith(MockitoJUnitRunner.class)
public class MyTest { }
```

### 2. JUnit 5 프로젝트 (새 프로젝트)
✅ **최선**: `MockitoExtension` 사용
```java
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
public class MyTest { }
```

### 3. Spring Boot 테스트
✅ **권장**: `@MockBean` 사용
```java
import org.springframework.boot.test.mock.mockito.MockBean;

@SpringBootTest
public class MyTest {
    @MockBean
    private MyRepository repository;
}
```

### 4. 레거시 코드
⚠️ 기존 `org.mockito.runners.MockitoJUnitRunner`를 발견하면:
- Import만 `org.mockito.junit.MockitoJUnitRunner`로 변경
- 다른 코드는 수정 불필요
- 점진적으로 JUnit 5로 마이그레이션 고려

## 버전 호환성

| Mockito 버전 | runners 패키지 | junit 패키지 | JUnit 5 Extension |
|-------------|---------------|--------------|-------------------|
| 1.x | ✅ 사용 가능 | ❌ 없음 | ❌ 없음 |
| 2.0.x | ✅ 사용 가능 | ❌ 없음 | ❌ 없음 |
| 2.1.0+ | ⚠️ Deprecated | ✅ 권장 | ❌ 없음 |
| 2.2.0+ | ⚠️ Deprecated | ✅ 권장 | ✅ 사용 가능 |
| 3.x+ | ⚠️ Deprecated | ✅ 권장 | ✅ 권장 |

## 요약

- **`org.mockito.runners.MockitoJUnitRunner`**: 구버전, Deprecated
- **`org.mockito.junit.MockitoJUnitRunner`**: 신버전, 현재 권장
- 두 클래스 모두 **JUnit 4** 전용
- **JUnit 5** 사용 시 `MockitoExtension` 사용 권장
- 마이그레이션은 import 변경만으로 가능 (매우 간단)
