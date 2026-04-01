파일 작성 권한이 필요합니다. 허용해 주시면 `/Users/User/claude-study/20260303-mockmvc-setup-methods.md`로 저장하겠습니다.

아래는 정리한 내용 미리보기입니다:

---

# MockMvc를 설정하는 세 가지 방법

## 방법 비교

| 방법 | 컨텍스트 | 속도 | 적합한 용도 |
|---|---|---|---|
| `@WebMvcTest` | Web 레이어만 | 빠름 | 컨트롤러 단위 테스트 |
| `@SpringBootTest` | 전체 | 느림 | 통합 테스트 |
| `standaloneSetup` | 없음 | 가장 빠름 | 순수 단위 테스트 |

---

### 1. `@WebMvcTest` (슬라이스 테스트)

```java
@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    MockMvc mockMvc;

    @MockBean
    UserService userService;

    @Test
    void getUser() throws Exception {
        given(userService.findById(1L)).willReturn(new User(1L, "Alice"));

        mockMvc.perform(get("/users/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("Alice"));
    }
}
```

- **Web 레이어만** 로드 (Controller, Filter, ControllerAdvice 등)
- Service, Repository는 `@MockBean`으로 주입
- 가장 빠르고 가벼운 방식

---

### 2. `@SpringBootTest` + `MockMvc` 수동 설정

```java
@SpringBootTest
class UserControllerTest {

    @Autowired
    WebApplicationContext context;

    MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders
            .webAppContextSetup(context)
            .build();
    }
}
```

- **전체 애플리케이션 컨텍스트** 로드 → 실제 빈이 모두 등록됨
- `@AutoConfigureMockMvc`를 추가하면 `MockMvc`를 `@Autowired`로 바로 주입 가능

---

### 3. `MockMvcBuilders.standaloneSetup()` (단독 설정)

```java
MockMvc mockMvc = MockMvcBuilders
    .standaloneSetup(new UserController(mockUserService))
    .setControllerAdvice(new GlobalExceptionHandler())
    .build();
```

- **Spring 컨텍스트 없이** 컨트롤러 인스턴스를 직접 등록
- 가장 빠르지만 Filter, Interceptor 등을 수동으로 추가해야 함

---

> 일반적으로 **컨트롤러 테스트에는 `@WebMvcTest`**, 전체 플로우 검증에는 **`@SpringBootTest`** 권장