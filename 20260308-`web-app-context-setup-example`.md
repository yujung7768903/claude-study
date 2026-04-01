파일 저장 권한이 필요합니다. 허용해 주시면 `/Users/User/claude-study/20260308-webappcontextsetup-usage.md`로 저장하겠습니다.

아래는 정리한 내용 미리보기입니다:

---

# webAppContextSetup 사용 예시

`@SpringBootTest`와 함께 전체 Spring 컨텍스트를 로드해서 MockMvc를 구성하는 방식.

---

### 1. 기본 사용법

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

    @Test
    void getUser() throws Exception {
        mockMvc.perform(get("/users/1"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.name").value("Alice"));
    }
}
```

---

### 2. 필터 / Security 적용

```java
@SpringBootTest
class UserControllerTest {

    @Autowired
    WebApplicationContext context;

    @Autowired
    Filter springSecurityFilterChain;

    MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders
            .webAppContextSetup(context)
            .addFilter(springSecurityFilterChain)  // Security 필터 적용
            .build();
    }

    @Test
    @WithMockUser(username = "alice", roles = "USER")
    void getUser() throws Exception { ... }

    @Test
    void getUser_unauthorized() throws Exception { ... }
}
```

---

### 3. `@AutoConfigureMockMvc`로 간소화

```java
@SpringBootTest
@AutoConfigureMockMvc
class UserControllerTest {

    @Autowired
    MockMvc mockMvc;  // 자동 주입
}
```

---

## 세 가지 MockMvc 설정 방법 비교

| 방법 | 컨텍스트 | Security 필터 | 속도 |
|---|---|---|---|
| `@WebMvcTest` | Web 레이어만 | 부분 적용 | 빠름 |
| `webAppContextSetup` | 전체 | 수동 추가 가능 | 느림 |
| `standaloneSetup` | 없음 | 수동 추가 | 가장 빠름 |

> - 실제 빈을 그대로 쓰는 통합 테스트 → `webAppContextSetup`
> - Security 포함 전체 플로우 검증 → `webAppContextSetup` + `addFilter`
> - 컨트롤러만 빠르게 테스트 → `@WebMvcTest`