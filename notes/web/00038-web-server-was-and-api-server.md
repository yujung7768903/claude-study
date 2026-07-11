# 웹 서버(Web Server) vs WAS vs API 서버

## 개념 설명

### 웹 서버 (Web Server)

정적 콘텐츠(HTML, CSS, JS, 이미지 등)를 클라이언트에게 제공하는 서버다. HTTP 요청을 받아 파일 시스템에서 해당 파일을 찾아 응답한다.

- 대표 제품: **Nginx**, **Apache HTTP Server**
- 역할: 정적 파일 서빙, 리버스 프록시, 로드 밸런싱, SSL 종료

### 웹 애플리케이션 서버 (WAS, Web Application Server)

동적 콘텐츠를 처리하는 서버다. 비즈니스 로직을 실행하고, DB와 연동하여 요청에 맞는 응답을 생성한다.

- 대표 제품: **Tomcat**, **Jetty**, **JBoss/WildFly**, **WebLogic**
- 역할: 서블릿/JSP 실행, 비즈니스 로직 처리, DB 연동, 세션 관리

---

## 웹 서버 vs WAS 비교표

| 구분 | 웹 서버 | WAS |
|------|---------|-----|
| 처리 대상 | 정적 콘텐츠 | 동적 콘텐츠 |
| 주요 기능 | 파일 서빙, 프록시 | 비즈니스 로직, DB 연동 |
| 대표 제품 | Nginx, Apache | Tomcat, Jetty, JBoss |
| 성능 | 매우 빠름 | 상대적으로 느림 |
| 부하 | CPU/메모리 낮음 | CPU/메모리 높음 |
| 프로토콜 | HTTP/HTTPS | HTTP + 자체 프로토콜 (AJP 등) |

---

## 일반적인 아키텍처

```
클라이언트
    ↓ HTTP 요청
[웹 서버 - Nginx]
    ├── 정적 파일 요청 → 직접 파일 반환
    └── 동적 요청 → 프록시 전달
             ↓
        [WAS - Tomcat]
             ↓ DB 쿼리
         [Database]
```

### 왜 앞에 웹 서버를 두는가?

1. **정적/동적 요청 분리**: 정적 파일은 웹 서버가 직접 처리해 WAS 부하를 줄임
2. **로드 밸런싱**: 여러 WAS 인스턴스로 트래픽 분산
3. **SSL 종료**: HTTPS 처리를 웹 서버에서 담당
4. **보안**: WAS를 외부에 직접 노출하지 않음
5. **캐싱**: 웹 서버 레벨에서 응답 캐싱 가능

---

## Nginx + Tomcat 설정 예시

**Nginx 리버스 프록시 설정 (`nginx.conf`)**

```nginx
server {
    listen 80;
    server_name example.com;

    # 정적 파일 직접 서빙
    location /static/ {
        root /var/www/html;
    }

    # 동적 요청은 Tomcat으로 프록시
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## Spring Boot와 내장 WAS

Spring Boot는 Tomcat을 내장하고 있어 별도 WAS 설치 없이 실행 가능하다.

```xml
<!-- 기본: 내장 Tomcat -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<!-- Jetty로 교체 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
    <exclusions>
        <exclusion>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-tomcat</artifactId>
        </exclusion>
    </exclusions>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-jetty</artifactId>
</dependency>
```

---

## API 서버는 WAS인가?

**맞다. API 서버는 WAS의 일종이다.**

다만 두 용어는 바라보는 관점이 다르다.

| 용어 | 관점 | 초점 |
|------|------|------|
| WAS | 기술/구조 | "동적 요청을 처리하는 서버 런타임" |
| API 서버 | 역할/목적 | "데이터를 JSON으로 반환하는 서버" |

API 서버는 WAS라는 그릇 위에서 동작하는 애플리케이션이다.

### 공통점 (왜 WAS라 부를 수 있는가)

- HTTP 요청을 받아 **동적으로** 응답을 생성한다
- **비즈니스 로직**을 실행한다
- **DB와 연동**한다
- 요청마다 다른 결과를 반환한다

### 차이점: SSR 시대 vs CSR 시대

**전통적 WAS (SSR 시대)**

```
클라이언트 요청 → WAS → HTML 생성(JSP/Thymeleaf) → 브라우저에 HTML 반환
```

- 서버가 HTML까지 만들어서 반환 (Server-Side Rendering)
- Tomcat + JSP, JBoss + EJB 등
- 화면 렌더링 책임이 서버에 있음

**현대 API 서버 (CSR 시대)**

```
클라이언트 요청 → API 서버 → JSON 반환 → 클라이언트(React/Vue)가 화면 구성
```

- 서버는 데이터(JSON/XML)만 반환
- 화면 렌더링 책임이 클라이언트에 있음
- REST API, GraphQL 등

### Spring Boot로 보는 실제 구조

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

### 포함 관계 정리

```
WAS (넓은 개념)
├── 전통적 WAS: SSR 방식으로 HTML 반환 (Tomcat + JSP)
└── API 서버: 데이터(JSON)만 반환 (Spring Boot REST API, Node.js Express 등)
```

API 서버 ⊆ WAS

---

## 실무 권장사항

- **소규모/단순 서비스**: Spring Boot 내장 Tomcat만 사용해도 충분하다. Nginx를 앞에 두면 SSL과 정적 파일 처리가 편리해진다.
- **대규모 서비스**: Nginx(웹 서버) + 여러 WAS 인스턴스 구성으로 수평 확장한다.
- **클라우드 환경**: ALB(AWS Application Load Balancer)가 Nginx 역할을 대체할 수 있으므로, 웹 서버 없이 WAS만 두는 경우도 많다.
- **정적 자산**: CDN(CloudFront 등)을 활용하면 웹 서버의 정적 파일 서빙 역할도 대체 가능하다.
- 실무에서 "WAS"와 "API 서버"를 구분해서 쓸 필요는 없다. 맥락으로 충분히 통한다. 아키텍처 문서에서는 역할 기준으로 "API 서버", 기술 기준으로 "Tomcat" 등 구체적인 제품명을 쓰는 것이 명확하다.
- Node.js Express, Python FastAPI 등도 동적 요청을 처리하므로 넓은 의미의 WAS/API 서버에 해당한다. (Java 전용 개념이 아님)
