# Spring MockMvc 동작 원리와 사용 방법

## MockMvc란?

**MockMvc**는 Spring MVC 애플리케이션을 **실제 서버 없이** 테스트할 수 있게 해주는 Spring Test 프레임워크의 핵심 도구입니다.

### 핵심 특징

- **서버 없이 테스트**: 실제 HTTP 서버를 띄우지 않고 Controller 테스트
- **빠른 실행**: 네트워크 오버헤드 없이 빠른 테스트
- **Spring MVC 완전 시뮬레이션**: 실제 요청/응답 처리 흐름과 동일
- **final class**: Mockito로 Mock 불가능 (Spring이 직접 생성)

## 동작 원리

### 1. 전체 아키텍처

```
[테스트 코드]
    ↓
[MockMvc]
    ↓
[DispatcherServlet] (Mock)
    ↓
[Controller]
    ↓
[Service] (실제 또는 Mock)
    ↓
[Repository] (실제 또는 Mock)
```

### 2. MockMvc 내부 구조

```java
MockMvc
├── MockMvcBuilder (생성)
│   ├── standaloneSetup() - 특정 Controller만 테스트
│   └── webAppContextSetup() - 전체 Spring Context 사용
│
├── RequestBuilder (요청 생성)
│   ├── MockMvcRequestBuilders.get()
│   ├── MockMvcRequestBuilders.post()
│   └── MockMvcRequestBuilders.multipart()
│
├── ResultActions (응답 검증)
│   ├── andExpect() - 검증
│   ├── andDo() - 출력/로깅
│   └── andReturn() - 결과 반환
│
└── ResultMatchers (검증 조건)
    ├── status() - HTTP 상태 코드
    ├── content() - 응답 본문
    ├── jsonPath() - JSON 경로
    └── header() - HTTP 헤더
```

### 3. 실행 흐름

```java
mockMvc.perform(get("/api/users/1"))  // 1. 요청 생성
    ↓
MockMvc가 DispatcherServlet 호출
    ↓
DispatcherServlet이 Controller 매핑 찾기
    ↓
Controller 메서드 실행
    ↓
응답 생성
    ↓
.andExpect(status().isOk())  // 2. 검증
    ↓
.andReturn()  // 3. 결과 반환
```

## MockMvc 생성 방법

### 방법 1: @AutoConfigureMockMvc (권장)

```java
@RunWith(SpringRunner.class)
@SpringBootTest
@AutoConfigureMockMvc  // ✅ 자동으로 MockMvc 생성
public class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;  // 자동 주입

    @Test
    public void getUserTest() throws Exception {
        mockMvc.perform(get("/api/users/1"))
            .andExpect(status().isOk());
    }
}
```

**특징**:
- Spring Boot 전체 Context 로드
- 모든 Controller, Filter, Interceptor 포함
- 실제 환경과 가장 유사

### 방법 2: webAppContextSetup (수동)

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class UserControllerTest {

    @Autowired
    private WebApplicationContext webApplicationContext;

    private MockMvc mockMvc;

    @Before
    public void setUp() {
        mockMvc = MockMvcBuilders
            .webAppContextSetup(webApplicationContext)
            .build();
    }

    @Test
    public void getUserTest() throws Exception {
        mockMvc.perform(get("/api/users/1"))
            .andExpect(status().isOk());
    }
}
```

**특징**:
- 전체 Spring Context 사용
- Filter, Interceptor 커스터마이징 가능
- @AutoConfigureMockMvc와 유사하지만 더 세밀한 제어

### 방법 3: standaloneSetup (단위 테스트)

```java
@RunWith(MockitoJUnitRunner.class)  // Spring Runner 불필요!
public class UserControllerTest {

    @Mock
    private UserService userService;

    @InjectMocks
    private UserController userController;

    private MockMvc mockMvc;

    @Before
    public void setUp() {
        mockMvc = MockMvcBuilders
            .standaloneSetup(userController)  // Controller만 등록
            .build();
    }

    @Test
    public void getUserTest() throws Exception {
        when(userService.getUser(1L)).thenReturn(new User("John"));

        mockMvc.perform(get("/api/users/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("John"));
    }
}
```

**특징**:
- Spring Context 로드 없음 (빠름)
- 특정 Controller만 테스트
- Service는 Mock으로 주입
- 단위 테스트에 적합

## MockMvc 사용 방법

### 1. GET 요청

```java
@Test
public void getUserById_정상조회() throws Exception {
    mockMvc.perform(get("/api/users/{id}", 1L))
        .andExpect(status().isOk())
        .andExpect(content().contentType(MediaType.APPLICATION_JSON))
        .andExpect(jsonPath("$.id").value(1))
        .andExpect(jsonPath("$.name").value("John"))
        .andDo(print());  // 결과 출력
}

@Test
public void getUserList_쿼리파라미터() throws Exception {
    mockMvc.perform(get("/api/users")
            .param("page", "1")
            .param("size", "10")
            .param("sort", "name,asc"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content").isArray())
        .andExpect(jsonPath("$.totalElements").exists());
}
```

### 2. POST 요청 (JSON)

```java
@Test
public void createUser_정상생성() throws Exception {
    String userJson = "{\"name\":\"John\",\"email\":\"john@example.com\"}";

    mockMvc.perform(post("/api/users")
            .contentType(MediaType.APPLICATION_JSON)
            .content(userJson))
        .andExpect(status().isCreated())
        .andExpect(header().exists("Location"))
        .andExpect(jsonPath("$.id").exists())
        .andExpect(jsonPath("$.name").value("John"));
}

@Test
public void createUser_검증실패() throws Exception {
    String invalidUserJson = "{\"name\":\"\",\"email\":\"invalid\"}";

    mockMvc.perform(post("/api/users")
            .contentType(MediaType.APPLICATION_JSON)
            .content(invalidUserJson))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.errors").isArray());
}
```

### 3. PUT 요청

```java
@Test
public void updateUser_정상수정() throws Exception {
    String updateJson = "{\"name\":\"Jane\",\"email\":\"jane@example.com\"}";

    mockMvc.perform(put("/api/users/{id}", 1L)
            .contentType(MediaType.APPLICATION_JSON)
            .content(updateJson))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.name").value("Jane"));
}
```

### 4. DELETE 요청

```java
@Test
public void deleteUser_정상삭제() throws Exception {
    mockMvc.perform(delete("/api/users/{id}", 1L))
        .andExpect(status().isNoContent());

    // 삭제 후 조회 시 404
    mockMvc.perform(get("/api/users/{id}", 1L))
        .andExpect(status().isNotFound());
}
```

### 5. Multipart (파일 업로드)

```java
@Test
public void uploadFile_정상업로드() throws Exception {
    MockMultipartFile file = new MockMultipartFile(
        "file",                          // 파라미터 이름
        "test.jpg",                      // 원본 파일명
        MediaType.IMAGE_JPEG_VALUE,      // Content-Type
        "test image content".getBytes()  // 파일 내용
    );

    mockMvc.perform(multipart("/api/library/upload")
            .file(file)
            .param("title", "Test Image")
            .param("category", "IMAGE"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.fileName").value("test.jpg"))
        .andExpect(jsonPath("$.uploadPath").exists());
}

@Test
public void uploadMultipleFiles_다중파일업로드() throws Exception {
    MockMultipartFile file1 = new MockMultipartFile(
        "files", "test1.jpg", MediaType.IMAGE_JPEG_VALUE, "content1".getBytes()
    );
    MockMultipartFile file2 = new MockMultipartFile(
        "files", "test2.jpg", MediaType.IMAGE_JPEG_VALUE, "content2".getBytes()
    );

    mockMvc.perform(multipart("/api/library/upload/multiple")
            .file(file1)
            .file(file2))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$").isArray())
        .andExpect(jsonPath("$.length()").value(2));
}
```

### 6. 헤더 설정

```java
@Test
public void getUserWithAuth_인증헤더() throws Exception {
    mockMvc.perform(get("/api/users/1")
            .header("Authorization", "Bearer token123")
            .header("X-Request-ID", "req-123"))
        .andExpect(status().isOk());
}

@Test
public void getUserWithCookie_쿠키() throws Exception {
    mockMvc.perform(get("/api/users/1")
            .cookie(new Cookie("sessionId", "abc123")))
        .andExpect(status().isOk());
}
```

## 응답 검증 (ResultMatchers)

### 1. HTTP 상태 코드

```java
@Test
public void statusCodeTest() throws Exception {
    mockMvc.perform(get("/api/users/1"))
        .andExpect(status().isOk())           // 200
        .andExpect(status().is(200));         // 200

    mockMvc.perform(post("/api/users"))
        .andExpect(status().isCreated())      // 201
        .andExpect(status().is(201));

    mockMvc.perform(get("/api/users/999"))
        .andExpect(status().isNotFound())     // 404
        .andExpect(status().is(404));

    mockMvc.perform(post("/api/users"))
        .andExpect(status().isBadRequest())   // 400
        .andExpect(status().is4xxClientError());  // 4xx

    mockMvc.perform(get("/api/error"))
        .andExpect(status().isInternalServerError())  // 500
        .andExpect(status().is5xxServerError());      // 5xx
}
```

### 2. JSON 응답 검증 (JsonPath)

```java
@Test
public void jsonPathTest() throws Exception {
    mockMvc.perform(get("/api/users/1"))
        // 필드 값 검증
        .andExpect(jsonPath("$.id").value(1))
        .andExpect(jsonPath("$.name").value("John"))
        .andExpect(jsonPath("$.email").value("john@example.com"))

        // 필드 존재 여부
        .andExpect(jsonPath("$.id").exists())
        .andExpect(jsonPath("$.password").doesNotExist())

        // 배열 검증
        .andExpect(jsonPath("$.roles").isArray())
        .andExpect(jsonPath("$.roles.length()").value(2))
        .andExpect(jsonPath("$.roles[0]").value("USER"))
        .andExpect(jsonPath("$.roles[1]").value("ADMIN"))

        // 중첩 객체
        .andExpect(jsonPath("$.address.city").value("Seoul"))
        .andExpect(jsonPath("$.address.zipCode").value("12345"))

        // 타입 검증
        .andExpect(jsonPath("$.id").isNumber())
        .andExpect(jsonPath("$.name").isString())
        .andExpect(jsonPath("$.active").isBoolean());
}
```

### 3. Content 검증

```java
@Test
public void contentTest() throws Exception {
    mockMvc.perform(get("/api/users/1"))
        // Content-Type 검증
        .andExpect(content().contentType(MediaType.APPLICATION_JSON))
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))

        // 전체 JSON 검증
        .andExpect(content().json("{\"id\":1,\"name\":\"John\"}"))
        .andExpect(content().json("{\"name\":\"John\"}", false))  // 일부만

        // 문자열 포함 검증
        .andExpect(content().string(containsString("John")))

        // 정규식 검증
        .andExpect(content().string(matchesPattern(".*John.*")));
}
```

### 4. 헤더 검증

```java
@Test
public void headerTest() throws Exception {
    mockMvc.perform(get("/api/users/1"))
        .andExpect(header().exists("Content-Type"))
        .andExpect(header().string("Content-Type", "application/json"))
        .andExpect(header().longValue("Content-Length", 123L))

        // Location 헤더 (리다이렉트)
        .andExpect(redirectedUrl("/api/users/1"))
        .andExpect(redirectedUrlPattern("/api/users/*"));
}
```

### 5. Model & View 검증 (MVC)

```java
@Test
public void mvcTest() throws Exception {
    mockMvc.perform(get("/users"))
        // View 이름 검증
        .andExpect(view().name("users/list"))

        // Model 검증
        .andExpect(model().attributeExists("users"))
        .andExpect(model().attribute("users", hasSize(10)))
        .andExpect(model().attribute("totalCount", 100));
}
```

## andDo() - 디버깅 & 로깅

```java
@Test
public void debuggingTest() throws Exception {
    mockMvc.perform(get("/api/users/1"))
        .andDo(print())  // 콘솔에 요청/응답 출력
        .andExpect(status().isOk());
}

// 출력 예시:
/*
MockHttpServletRequest:
      HTTP Method = GET
      Request URI = /api/users/1
       Parameters = {}
          Headers = []
             Body = null
    Session Attrs = {}

MockHttpServletResponse:
           Status = 200
    Error message = null
          Headers = [Content-Type:"application/json"]
     Content type = application/json
             Body = {"id":1,"name":"John","email":"john@example.com"}
    Forwarded URL = null
   Redirected URL = null
*/
```

## andReturn() - 결과 활용

```java
@Test
public void resultHandlingTest() throws Exception {
    MvcResult result = mockMvc.perform(post("/api/users")
            .contentType(MediaType.APPLICATION_JSON)
            .content("{\"name\":\"John\"}"))
        .andExpect(status().isCreated())
        .andReturn();

    // 응답 본문 가져오기
    String responseBody = result.getResponse().getContentAsString();
    System.out.println("응답: " + responseBody);

    // JSON 파싱
    JSONObject json = new JSONObject(responseBody);
    String userId = json.getString("id");

    // 생성된 사용자로 후속 테스트
    mockMvc.perform(get("/api/users/" + userId))
        .andExpect(status().isOk());
}
```

## 실무 예시: HK Library 프로젝트

### 1. 리터치 이미지 업로드 테스트

```java
@RunWith(SpringRunner.class)
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
public class RetouchControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private RetouchService retouchService;

    @MockBean
    private S3Util s3Util;

    private String authKey;

    @Before
    public void setUp() throws Exception {
        // S3 Mock 설정
        when(s3Util.fileUpload(any(), anyString(), anyBoolean(), anyString(), anyString()))
            .thenReturn(true);

        // authKey 생성
        authKey = retouchService.generateValidAuthKey(true);
    }

    @Test
    public void 리터치_이미지_업로드_테스트() throws Exception {
        // Given
        MockMultipartFile testImage = new MockMultipartFile(
            "file",
            "test.jpg",
            MediaType.IMAGE_JPEG_VALUE,
            new ClassPathResource("test.jpg").getInputStream()
        );

        // When & Then
        mockMvc.perform(multipart("/api/retouch/upload/cts")
                .file(testImage)
                .param("authKey", authKey)
                .param("ext", "jpg"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.success").value(true))
            .andExpect(jsonPath("$.fileId").exists())
            .andDo(print());
    }

    @Test
    public void authKey_검증_실패_테스트() throws Exception {
        MockMultipartFile testImage = new MockMultipartFile(
            "file", "test.jpg", MediaType.IMAGE_JPEG_VALUE, "content".getBytes()
        );

        mockMvc.perform(multipart("/api/retouch/upload/cts")
                .file(testImage)
                .param("authKey", "invalid-key")
                .param("ext", "jpg"))
            .andExpect(status().isBadRequest())
            .andExpect(jsonPath("$.error").exists());
    }
}
```

### 2. 라이브러리 조회 테스트

```java
@Test
public void 라이브러리_상세조회_테스트() throws Exception {
    // Given: 테스트 데이터 생성
    RMaterialLibrary library = new RMaterialLibrary();
    library.setId("test-id-123");
    library.setTitle("테스트 이미지");
    library.setFileName("test.jpg");
    libraryRepository.save(library);

    // When & Then
    mockMvc.perform(get("/api/library/{id}", "test-id-123"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.id").value("test-id-123"))
        .andExpect(jsonPath("$.title").value("테스트 이미지"))
        .andExpect(jsonPath("$.fileName").value("test.jpg"))
        .andDo(print());
}

@Test
public void 라이브러리_목록조회_페이징_테스트() throws Exception {
    mockMvc.perform(get("/api/library")
            .param("page", "0")
            .param("size", "20")
            .param("libraryType", "IMAGE"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.content").isArray())
        .andExpect(jsonPath("$.pageable.pageNumber").value(0))
        .andExpect(jsonPath("$.pageable.pageSize").value(20))
        .andExpect(jsonPath("$.totalElements").isNumber());
}
```

## 비교표: MockMvc 설정 방법

| 방법 | Runner | Spring Context | 속도 | 용도 |
|------|--------|---------------|------|------|
| **@AutoConfigureMockMvc** | SpringRunner | ✅ 전체 | 느림 | 통합 테스트 |
| **webAppContextSetup** | SpringRunner | ✅ 전체 | 느림 | 커스터마이징 필요 시 |
| **standaloneSetup** | MockitoJUnitRunner | ❌ 없음 | 빠름 | Controller 단위 테스트 |

## 주의사항

### 1. MockMvc는 final class

```java
@Mock
private MockMvc mockMvc;  // ❌ 에러! final class는 Mock 불가
```

### 2. @RunWith 필수 (JUnit 4)

```java
// ❌ 에러
@SpringBootTest
@AutoConfigureMockMvc
public class MyTest {
    @Autowired
    private MockMvc mockMvc;  // null!
}

// ✅ 정상
@RunWith(SpringRunner.class)  // 필수!
@SpringBootTest
@AutoConfigureMockMvc
public class MyTest {
    @Autowired
    private MockMvc mockMvc;  // 정상 주입
}
```

### 3. Content-Type 설정 필수 (POST/PUT)

```java
// ❌ Content-Type 없으면 415 에러
mockMvc.perform(post("/api/users")
    .content("{\"name\":\"John\"}"))
    .andExpect(status().isOk());  // 실패!

// ✅ Content-Type 설정
mockMvc.perform(post("/api/users")
    .contentType(MediaType.APPLICATION_JSON)
    .content("{\"name\":\"John\"}"))
    .andExpect(status().isOk());
```

### 4. @Transactional 사용 권장

```java
@Test
@Transactional  // ✅ 테스트 후 자동 롤백
public void createUserTest() {
    // 테스트 데이터가 DB에 남지 않음
}
```

## 실무 권장사항

### 1. 테스트 분리

```java
// Controller 단위 테스트 (빠름)
@RunWith(MockitoJUnitRunner.class)
public class UserControllerUnitTest {
    // standaloneSetup 사용
}

// Controller 통합 테스트 (느림)
@RunWith(SpringRunner.class)
@SpringBootTest
@AutoConfigureMockMvc
public class UserControllerIntegrationTest {
    // @AutoConfigureMockMvc 사용
}
```

### 2. 공통 설정 추상 클래스

```java
@RunWith(SpringRunner.class)
@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
@Transactional
public abstract class BaseControllerTest {
    @Autowired
    protected MockMvc mockMvc;

    @Autowired
    protected ObjectMapper objectMapper;

    protected String toJson(Object object) throws Exception {
        return objectMapper.writeValueAsString(object);
    }
}

// 사용
public class UserControllerTest extends BaseControllerTest {
    @Test
    public void test() {
        mockMvc.perform(get("/api/users"))
            .andExpect(status().isOk());
    }
}
```

### 3. 커스텀 ResultMatcher

```java
public class CustomMatchers {
    public static ResultMatcher isSuccess() {
        return result -> {
            MockHttpServletResponse response = result.getResponse();
            assertEquals(200, response.getStatus());

            String content = response.getContentAsString();
            JSONObject json = new JSONObject(content);
            assertTrue(json.getBoolean("success"));
        };
    }
}

// 사용
mockMvc.perform(get("/api/users"))
    .andExpect(isSuccess());
```

## 요약

### MockMvc란?

- Spring MVC를 **서버 없이** 테스트하는 도구
- **final class**로 Mock 불가능
- Spring이 직접 생성해야 함

### 생성 방법

1. **@AutoConfigureMockMvc**: 전체 통합 테스트 (권장)
2. **webAppContextSetup**: 커스터마이징 필요 시
3. **standaloneSetup**: Controller 단위 테스트

### 핵심 사용 패턴

```java
mockMvc.perform(...)      // 요청
    .andExpect(...)       // 검증
    .andDo(...)           // 로깅/출력
    .andReturn();         // 결과 반환
```

### 주의사항

- JUnit 4에서는 @RunWith 필수
- POST/PUT은 Content-Type 설정 필수
- @Transactional로 테스트 데이터 롤백 권장
