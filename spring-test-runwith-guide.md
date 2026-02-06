# Spring 테스트에서 @RunWith 선택 가이드

## 핵심 질문: AmsArticleTagService 테스트에 어떤 @RunWith를 써야 할까?

`AmsArticleTagService`는 `RestTemplate`으로 외부 AMS API를 호출하는 서비스다.
이런 클래스를 테스트할 때 **두 가지 접근법**이 있고, 각각 다른 `@RunWith`를 사용한다.

---

## 1. @RunWith 비교

| Runner | 용도 | Spring Context 로딩 | 속도 |
|--------|------|---------------------|------|
| `MockitoJUnitRunner.class` | 단위 테스트 (Mock 사용) | X (로딩 안 함) | 빠름 |
| `SpringRunner.class` | 통합 테스트 (실제 Bean 사용) | O (전체 로딩) | 느림 |

---

## 2. MockitoJUnitRunner (단위 테스트) - 권장

외부 API를 호출하는 서비스는 **Mock으로 격리**하는 것이 일반적이다.

```java
@RunWith(MockitoJUnitRunner.class)  // Spring Context 안 띄움
public class AmsArticleTagServiceTest {

    @Mock
    private RestTemplate restTemplate;  // 외부 호출을 Mock 처리

    @InjectMocks
    private AmsArticleTagService amsArticleTagService;  // 테스트 대상

    @Before
    public void setUp() {
        // @Value로 주입되는 필드는 리플렉션으로 직접 설정
        ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
    }

    @Test
    public void getArticleTagListFromAms_성공() {
        // given
        RArticle rArticle = new RArticle();
        rArticle.setArticleId("ART001");

        AmsTag tag1 = new AmsTag();
        tag1.setTagId("TAG1");
        tag1.setTag("경제");

        AmsResponseDto<AmsTag> responseDto = new AmsResponseDto<>();
        responseDto.setCode("200");
        responseDto.getData().setList(Arrays.asList(tag1));

        ResponseEntity<AmsResponseDto<AmsTag>> responseEntity =
            new ResponseEntity<>(responseDto, HttpStatus.OK);

        when(restTemplate.exchange(
            anyString(),
            eq(HttpMethod.GET),
            any(HttpEntity.class),
            any(ParameterizedTypeReference.class),
            anyMap()
        )).thenReturn(responseEntity);

        // when
        List<RArticleTag> result = amsArticleTagService.getArticleTagListFromAms(rArticle);

        // then
        assertEquals(1, result.size());
        assertEquals("경제", result.get(0).getTag());
    }

    @Test
    public void getArticleTagListFromAms_실패시_빈리스트() {
        // given
        RArticle rArticle = new RArticle();
        rArticle.setArticleId("ART001");

        when(restTemplate.exchange(
            anyString(), any(), any(), any(ParameterizedTypeReference.class), anyMap()
        )).thenThrow(new RuntimeException("Connection refused"));

        // when
        List<RArticleTag> result = amsArticleTagService.getArticleTagListFromAms(rArticle);

        // then
        assertTrue(result.isEmpty());
    }
}
```

### 왜 MockitoJUnitRunner인가?

`AmsArticleTagService`의 특성을 보면:

| 특성 | 설명 | 테스트 전략 |
|------|------|------------|
| `RestTemplate` 의존 | 외부 AMS API 호출 | Mock으로 대체 |
| `@Value` 필드 | `amsServiceUrl` 주입 | `ReflectionTestUtils`로 설정 |
| `AbstractService` 상속 | `UserService` 자동주입 | 이 테스트에서는 사용 안 함 |

외부 API에 실제로 요청을 보내면 테스트가 불안정해지므로, Mock이 적합하다.

---

## 3. SpringRunner (통합 테스트) - 특수한 경우

실제 Spring Context가 필요한 경우에만 사용한다.

```java
@RunWith(SpringRunner.class)
@SpringBootTest(classes = Application.class)
@ActiveProfiles("local")
public class AmsArticleTagServiceIntegrationTest {

    @Autowired
    private AmsArticleTagService amsArticleTagService;

    @Test
    public void getArticleTagListFromAms_실제호출() {
        // 실제 AMS 서버가 떠 있어야 동작
        RArticle rArticle = new RArticle();
        rArticle.setArticleId("실제아티클ID");

        List<RArticleTag> result = amsArticleTagService.getArticleTagListFromAms(rArticle);
        assertNotNull(result);
    }
}
```

### SpringRunner를 쓸 때의 문제점

- `application.yaml`이 gitignore되어 있어 설정 파일이 없으면 Context 로딩 실패
- 실제 AMS 서버가 떠 있어야 테스트 통과
- DB, Redis 등 모든 인프라 연결 필요 (AbstractService → UserService → DB)
- 테스트 실행 시간이 길어짐

---

## 4. 주의사항: RestTemplate 생성자 주입 문제

현재 `AmsArticleTagService`는 생성자에서 `RestTemplateBuilder`를 받아 `RestTemplate`을 직접 생성한다:

```java
public AmsArticleTagService(RestTemplateBuilder builder) {
    this.restTemplate = builder
            .setConnectTimeout(Duration.ofSeconds(10))
            .setReadTimeout(Duration.ofSeconds(10))
            .build();
}
```

`MockitoJUnitRunner`에서 `@InjectMocks`를 사용하면 `RestTemplateBuilder`를 Mock으로 넣어야 하는데,
빌더 패턴의 체이닝이 복잡해진다. **두 가지 해결법**이 있다:

### 방법 A: @InjectMocks + 리플렉션으로 restTemplate 재주입

```java
@Mock
private RestTemplate restTemplate;

@InjectMocks
private AmsArticleTagService amsArticleTagService;

@Before
public void setUp() throws Exception {
    // ⚠️ 중요: restTemplate도 다시 주입해야 함!
    ReflectionTestUtils.setField(amsArticleTagService, "restTemplate", restTemplate);
    ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
}
```

### 방법 A-2: @InjectMocks 없이 직접 생성 (더 명확함)

```java
@Mock
private RestTemplate restTemplate;

private AmsArticleTagService amsArticleTagService;  // @InjectMocks 제거

@Before
public void setUp() throws Exception {
    // @RunWith(MockitoJUnitRunner.class)가 이미 Mock을 초기화하므로 initMocks() 불필요
    amsArticleTagService = new AmsArticleTagService(new RestTemplateBuilder());
    ReflectionTestUtils.setField(amsArticleTagService, "restTemplate", restTemplate);
    ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
}
```

### 방법 B: RestTemplateBuilder Mock 체이닝

```java
@Mock
private RestTemplateBuilder builder;

@Mock
private RestTemplate restTemplate;

@Before
public void setUp() {
    when(builder.setConnectTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.setReadTimeout(any(Duration.class))).thenReturn(builder);
    when(builder.build()).thenReturn(restTemplate);

    amsArticleTagService = new AmsArticleTagService(builder);
    ReflectionTestUtils.setField(amsArticleTagService, "amsServiceUrl", "http://fake-ams.com");
}
```

---

## 5. 판단 기준 요약

```
외부 API(RestTemplate) 호출하는 서비스를 테스트한다
  → Mock이 필요하다
    → MockitoJUnitRunner를 사용한다

DB 쿼리나 Spring Bean 연동을 검증해야 한다
  → 실제 Context가 필요하다
    → SpringRunner + @SpringBootTest를 사용한다
```

## 6. 실무 권장사항

1. **AmsArticleTagService처럼 외부 API를 호출하는 서비스** → `MockitoJUnitRunner` + `@Mock RestTemplate`
2. **Repository(JPA) 테스트** → `SpringRunner` + `@DataJpaTest`
3. **Controller 테스트** → `SpringRunner` + `@WebMvcTest`
4. **전체 통합 테스트** → `SpringRunner` + `@SpringBootTest`
5. 이 프로젝트는 **Spring Boot 2.1.5 (JUnit 4)** 기반이므로 `@RunWith`가 필수. JUnit 5라면 `@ExtendWith(MockitoExtension.class)`를 사용한다.
