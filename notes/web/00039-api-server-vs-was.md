# API 서버는 WAS인가?

## 결론부터

**맞다. API 서버는 WAS의 일종이다.**

다만 두 용어는 바라보는 관점이 다르다.

| 용어 | 관점 | 초점 |
|------|------|------|
| WAS | 기술/구조 | "동적 요청을 처리하는 서버 런타임" |
| API 서버 | 역할/목적 | "데이터를 JSON으로 반환하는 서버" |

API 서버는 WAS라는 그릇 위에서 동작하는 애플리케이션이다.

---

## 공통점 (왜 WAS라 부를 수 있는가)

- HTTP 요청을 받아 **동적으로** 응답을 생성한다
- **비즈니스 로직**을 실행한다
- **DB와 연동**한다
- 요청마다 다른 결과를 반환한다

---

## 차이점 (관점의 차이)

### 전통적 WAS (SSR 시대)

```
클라이언트 요청 → WAS → HTML 생성(JSP/Thymeleaf) → 브라우저에 HTML 반환
```

- 서버가 HTML까지 만들어서 반환 (Server-Side Rendering)
- Tomcat + JSP, JBoss + EJB 등
- 화면 렌더링 책임이 서버에 있음

### 현대 API 서버 (CSR 시대)

```
클라이언트 요청 → API 서버 → JSON 반환 → 클라이언트(React/Vue)가 화면 구성
```

- 서버는 데이터(JSON/XML)만 반환
- 화면 렌더링 책임이 클라이언트에 있음
- REST API, GraphQL 등

---

## Spring Boot로 보는 실제 구조

Spring Boot REST API 서버는 내장 Tomcat(WAS) 위에서 동작한다.

```
Spring Boot 애플리케이션
└── 내장 Tomcat (WAS 런타임)
    └── DispatcherServlet
        └── @RestController (JSON 반환)
```

```java
@RestController  // HTML 대신 JSON 반환 → "API 서버"
@RequestMapping("/api")
public class UserController {

    @GetMapping("/users/{id}")
    public UserResponse getUser(@PathVariable Long id) {
        return userService.findById(id);  // JSON으로 직렬화되어 반환
    }
}
```

WAS 기술(`Tomcat`) + API 서버 역할(`@RestController`) 이 함께 동작한다.

---

## 포함 관계 정리

```
WAS (넓은 개념)
├── 전통적 WAS: SSR 방식으로 HTML 반환 (Tomcat + JSP)
└── API 서버: 데이터(JSON)만 반환 (Spring Boot REST API, Node.js Express 등)
```

API 서버 ⊆ WAS

---

## 실무에서의 용어 사용

실무에서는 아래 용어들을 혼용하는 경우가 많다.

| 용어 | 실제 의미 |
|------|-----------|
| WAS | Java 진영에서 Tomcat/JBoss 같은 서버 런타임을 가리킬 때 주로 사용 |
| API 서버 | REST API를 제공하는 백엔드 서버를 가리킬 때 사용 |
| 애플리케이션 서버 | WAS와 거의 동의어 |
| 백엔드 서버 | API 서버와 거의 동의어 |

---

## 실무 권장사항

- 팀 내 대화에서 "WAS"와 "API 서버"를 구분해서 쓸 필요는 없다. 맥락으로 충분히 통한다.
- 아키텍처 문서에서는 역할 기준으로 "API 서버", 기술 기준으로 "Tomcat" 등 구체적인 제품명을 쓰는 것이 명확하다.
- Node.js Express, Python FastAPI 등도 동적 요청을 처리하므로 넓은 의미의 WAS/API 서버에 해당한다. (Java 전용 개념이 아님)
