# Mockito 테스트 설정 완전 가이드: Runner, initMocks(), 패키지 차이

## MockitoJUnitRunner 패키지 비교

Mockito에서 제공하는 두 개의 `MockitoJUnitRunner`는 패키지 위치와 지원하는 Mockito 버전이 다릅니다.

### 1. `org.mockito.runners.MockitoJUnitRunner` (구버전)

- **JUnit 4** 전용
- Mockito **1.x ~ 2.x** 버전에서 사용
- **@Deprecated** (더 이상 사용 권장 안 함)

### 2. `org.mockito.junit.MockitoJUnitRunner` (신버전)

- **JUnit 4** 전용
- Mockito **2.1.0 이상**에서 도입
- 현재 **권장되는 방식**
- 더 나은 성능과 버그 수정 포함

### 비교표

| 항목 | org.mockito.runners | org.mockito.junit |
|------|---------------------|-------------------|
| **도입 시기** | Mockito 1.x | Mockito 2.1.0+ |
| **상태** | Deprecated | Active |
| **JUnit 버전** | JUnit 4 | JUnit 4 |
| **사용 권장** | ❌ | ✅ |

### 버전 호환성

| Mockito 버전 | runners 패키지 | junit 패키지 | JUnit 5 Extension |
|-------------|---------------|--------------|-------------------|
| 1.x | ✅ | ❌ 없음 | ❌ 없음 |
| 2.0.x | ✅ | ❌ 없음 | ❌ 없음 |
| 2.1.0+ | ⚠️ Deprecated | ✅ | ❌ 없음 |
| 2.2.0+ | ⚠️ Deprecated | ✅ | ✅ |
| 3.x+ | ⚠️ Deprecated | ✅ | ✅ |

### 마이그레이션 방법

Import만 변경하면 됩니다. 코드는 그대로 유지됩니다.

```java
// Before
import org.mockito.runners.MockitoJUnitRunner;

// After
import org.mockito.junit.MockitoJUnitRunner;

@RunWith(MockitoJUnitRunner.class)  // 변경 없음
public class MyServiceTest { }
```

---

## MockitoAnnotations.initMocks()는 언제 필요한가?

### @RunWith(MockitoJUnitRunner.class)가 하는 일

`MockitoJUnitRunner`는 테스트 실행 전에 자동으로 다음을 수행합니다:

```java
@RunWith(MockitoJUnitRunner.class)
public class MyTest {

    @Mock
    private SomeDependency dependency;

    @InjectMocks
    private MyService service;

    // Runner가 자동으로 MockitoAnnotations.initMocks(this)를 호출해줌!
    // 따라서 @Before에서 수동으로 호출할 필요 없음
}
```

**내부 동작:**
1. 테스트 클래스 로딩
2. `MockitoJUnitRunner`가 테스트 실행 전 `@Mock`, `@Spy`, `@InjectMocks` 어노테이션을 스캔
3. 자동으로 `MockitoAnnotations.initMocks(this)` 호출
4. Mock 객체 생성 및 주입
5. 테스트 메서드 실행

### initMocks()가 필요한 경우 vs 불필요한 경우

#### Case 1: MockitoJUnitRunner 사용 (✅ initMocks 불필요)

```java
@RunWith(MockitoJUnitRunner.class)  // ← 이게 자동으로 초기화해줌
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private AmsArticleTagService service;

    @Before
    public void setUp() {
        // MockitoAnnotations.initMocks(this); ← 불필요! 이미 Runner가 했음
        ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake");
    }
}
```

#### Case 2: SpringRunner 사용 (⚠️ initMocks 필요)

```java
@RunWith(SpringRunner.class)  // ← Spring 테스트 Runner (Mockito 초기화 안 함)
@SpringBootTest
public class AmsArticleTagServiceTest {

    @Mock  // Spring Runner는 이 어노테이션을 처리하지 않음!
    private RestTemplate restTemplate;

    private AmsArticleTagService service;

    @Before
    public void setUp() {
        MockitoAnnotations.initMocks(this);  // ← 필수! 수동으로 초기화해야 함
        service = new AmsArticleTagService(new RestTemplateBuilder());
        ReflectionTestUtils.setField(service, "restTemplate", restTemplate);
    }
}
```

**왜 필요한가?**
- `SpringRunner`는 Spring Context 로딩에만 집중
- Mockito 어노테이션 처리는 하지 않음
- 따라서 `@Mock`이 무시됨 → `initMocks()`로 수동 초기화 필요

#### Case 3: Runner 없음 (⚠️ initMocks 필요)

```java
public class AmsArticleTagServiceTest {  // @RunWith 없음

    @Mock
    private RestTemplate restTemplate;

    @Before
    public void setUp() {
        MockitoAnnotations.initMocks(this);  // ← 필수!
    }
}
```

#### Case 4: JUnit 5 (MockitoExtension 사용)

```java
@ExtendWith(MockitoExtension.class)  // JUnit 5
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;

    @InjectMocks
    private AmsArticleTagService service;

    @BeforeEach
    public void setUp() {
        // initMocks 불필요! Extension이 자동으로 해줌
    }
}
```

### 정리: initMocks() 필요 여부

| 상황 | initMocks() 필요? | 이유 |
|------|------------------|------|
| `@RunWith(MockitoJUnitRunner.class)` | ❌ 불필요 | Runner가 자동 초기화 |
| `@RunWith(SpringRunner.class)` | ✅ 필요 | Spring Runner는 Mock 초기화 안 함 |
| `@RunWith` 없음 | ✅ 필요 | 아무도 초기화 안 함 |
| `@ExtendWith(MockitoExtension.class)` (JUnit 5) | ❌ 불필요 | Extension이 자동 초기화 |

---

## Runner를 사용하지 않는 대안

### MockitoAnnotations.openMocks() 사용 (Mockito 3.4.0+)

```java
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
        closeable.close();  // 리소스 해제
    }

    @Test
    public void testSomething() {
        // 테스트 코드
    }
}
```

`openMocks()`는 `initMocks()`의 후속 버전으로, `AutoCloseable`을 반환하여 명시적으로 리소스를 해제할 수 있습니다.

---

## 실무 권장사항

### 1. JUnit 4 프로젝트

```java
import org.mockito.junit.MockitoJUnitRunner;

@RunWith(MockitoJUnitRunner.class)
public class MyTest { }
```

### 2. JUnit 5 프로젝트 (새 프로젝트)

```java
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
public class MyTest { }
```

### 3. Spring Boot 테스트

```java
import org.springframework.boot.test.mock.mockito.MockBean;

@SpringBootTest
public class MyTest {
    @MockBean
    private MyRepository repository;
    // @MockBean은 Spring Context에 Mock을 등록하므로 initMocks 불필요
}
```

### 4. 레거시 코드

```java
// Before (구버전 import)
import org.mockito.runners.MockitoJUnitRunner;

// After (신버전 import)
import org.mockito.junit.MockitoJUnitRunner;

@RunWith(MockitoJUnitRunner.class)  // 코드는 그대로
public class MyTest { }
```

---

## 요약

- **`org.mockito.runners.MockitoJUnitRunner`**: 구버전, Deprecated → import만 변경하면 됨
- **`org.mockito.junit.MockitoJUnitRunner`**: 신버전, 현재 권장 (JUnit 4)
- **`MockitoExtension`**: JUnit 5 권장 방식
- **`MockitoAnnotations.initMocks()`**: MockitoJUnitRunner 없을 때만 필요. 최신 버전은 `openMocks()` 사용
