# MockitoAnnotations.initMocks()는 언제 필요한가?

## 질문: @RunWith(MockitoJUnitRunner.class)를 쓰는데 initMocks()가 왜 필요해?

**답: 필요 없습니다! @RunWith(MockitoJUnitRunner.class)가 자동으로 해줍니다.**

---

## @RunWith(MockitoJUnitRunner.class)가 하는 일

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

---

## initMocks()가 필요한 경우 vs 불필요한 경우

### Case 1: MockitoJUnitRunner 사용 (✅ initMocks 불필요)

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

---

### Case 2: SpringRunner 사용 (⚠️ initMocks 필요)

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

---

### Case 3: Runner 없음 (⚠️ initMocks 필요)

```java
public class AmsArticleTagServiceTest {  // @RunWith 없음

    @Mock
    private RestTemplate restTemplate;

    @Before
    public void setUp() {
        MockitoAnnotations.initMocks(this);  // ← 필수!
        // ...
    }
}
```

---

### Case 4: JUnit 5 (MockitoExtension 사용)

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

---

## 정리: initMocks() 필요 여부

| 상황 | initMocks() 필요? | 이유 |
|------|------------------|------|
| `@RunWith(MockitoJUnitRunner.class)` | ❌ 불필요 | Runner가 자동 초기화 |
| `@RunWith(SpringRunner.class)` | ✅ 필요 | Spring Runner는 Mock 초기화 안 함 |
| `@RunWith` 없음 | ✅ 필요 | 아무도 초기화 안 함 |
| `@ExtendWith(MockitoExtension.class)` (JUnit 5) | ❌ 불필요 | Extension이 자동 초기화 |

---

## 올바른 코드 (현재 프로젝트)

이 프로젝트는 **Spring Boot 2.1.5 + JUnit 4 + MockitoJUnitRunner**를 사용하므로:

```java
@RunWith(MockitoJUnitRunner.class)  // Mock 자동 초기화
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;

    private AmsArticleTagService service;  // @InjectMocks 안 씀 (직접 생성)

    @Before
    public void setUp() {
        // initMocks() 불필요!
        service = new AmsArticleTagService(new RestTemplateBuilder());
        ReflectionTestUtils.setField(service, "restTemplate", restTemplate);
        ReflectionTestUtils.setField(service, "amsServiceUrl", "http://fake-ams.com");
    }

    @Test
    public void getArticleTagListFromAms_성공() {
        // given
        RArticle article = new RArticle();
        article.setArticleId("ART001");

        AmsResponseDto<AmsTag> responseDto = new AmsResponseDto<>();
        responseDto.setCode("200");
        // ... 설정

        when(restTemplate.exchange(
            anyString(),
            eq(HttpMethod.GET),
            any(HttpEntity.class),
            any(ParameterizedTypeReference.class),
            anyMap()
        )).thenReturn(new ResponseEntity<>(responseDto, HttpStatus.OK));

        // when
        List<RArticleTag> result = service.getArticleTagListFromAms(article);

        // then
        assertFalse(result.isEmpty());
        verify(restTemplate).exchange(anyString(), any(), any(), any(), anyMap());
    }
}
```

---

## 핵심 요약

**`@RunWith(MockitoJUnitRunner.class)` 사용 시:**
- ✅ `@Mock`, `@Spy`, `@InjectMocks` 자동 처리
- ❌ `MockitoAnnotations.initMocks(this)` 불필요
- 가장 간편한 Mockito 테스트 방법

**다른 Runner 사용 시:**
- `@Before`에서 `MockitoAnnotations.initMocks(this)` 수동 호출 필요
- 또는 `MockitoAnnotations.openMocks(this)` (Mockito 3.4.0+)

이 프로젝트는 `MockitoJUnitRunner`를 사용하므로, `initMocks()`를 쓸 필요가 없습니다!
