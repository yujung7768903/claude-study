# HTTP Connection Pool 크기 결정 및 타임아웃 설정

## 목차
1. [RestTemplate 타임아웃 종류](#1-resttemplate-타임아웃-종류)
2. [커넥션 풀 크기 산정](#2-커넥션-풀-크기-산정)
3. [서버 환경과 리소스 제약](#3-서버-환경과-리소스-제약)
4. [RestTemplate URL 파라미터 전달 방식](#4-resttemplate-url-파라미터-전달-방식)

---

## 1. RestTemplate 타임아웃 종류

### 1.1 타임아웃 설정 방법

```java
HttpComponentsClientHttpRequestFactory factory =
    new HttpComponentsClientHttpRequestFactory(httpClient);

// 1. Connection Timeout (연결 타임아웃)
factory.setConnectTimeout(5000); // 5초

// 2. Read Timeout (읽기 타임아웃)
factory.setReadTimeout(10000); // 10초

// 3. Connection Request Timeout (커넥션 풀에서 커넥션을 가져오는 타임아웃)
factory.setConnectionRequestTimeout(5000); // 5초
```

### 1.2 각 타임아웃의 의미

#### Connection Timeout (연결 타임아웃)
- **의미**: TCP 연결을 맺는데 걸리는 시간 제한
- **발생 시점**: 서버에 도달하지 못하거나 네트워크가 느릴 때
- **예외**: `SocketTimeoutException: connect timed out`
- **적절한 값**: 5~10초 (네트워크 환경에 따라)

```java
// TCP 3-way handshake 완료까지의 시간 제한
Socket socket = new Socket();
socket.connect(serverAddress, connectTimeout); // ← 이 시간 제한
```

#### Read Timeout (읽기/응답 타임아웃)
- **의미**: 연결은 성공했지만 서버로부터 응답을 받는데 걸리는 시간 제한
- **발생 시점**: 서버 처리가 오래 걸릴 때
- **예외**: `SocketTimeoutException: Read timed out`
- **적절한 값**: 10~30초 (API 특성에 따라)

```java
// 서버가 응답을 보내기까지 대기하는 시간 제한
socket.setSoTimeout(readTimeout); // ← 이 시간 제한
InputStream in = socket.getInputStream();
in.read(); // 여기서 대기
```

#### Connection Request Timeout (커넥션 풀 대기 타임아웃)
- **의미**: Connection Pool에서 커넥션을 가져올 때까지의 시간 제한
- **발생 시점**: 풀의 커넥션이 모두 사용 중일 때
- **예외**: `ConnectionPoolTimeoutException: Timeout waiting for connection from pool`
- **적절한 값**: 5~10초

```java
// Pool에서 커넥션을 빌릴 때까지 대기하는 시간
ConnectionRequest connRequest = connManager.requestConnection(route, null);
HttpClientConnection conn = connRequest.get(connectionRequestTimeout, TimeUnit.MILLISECONDS);
```

### 1.3 실제 적용 예시

```java
private ClientHttpRequestFactory createRequestFactory() {
    // Connection Pool Manager 생성
    PoolingHttpClientConnectionManager connectionManager =
        new PoolingHttpClientConnectionManager();
    connectionManager.setMaxTotal(100);              // 전체 최대 커넥션
    connectionManager.setDefaultMaxPerRoute(50);      // 호스트당 최대 커넥션
    connectionManager.setValidateAfterInactivity(2000); // 2초 후 검증

    // HttpClient 생성
    CloseableHttpClient httpClient = HttpClients.custom()
        .setConnectionManager(connectionManager)
        .evictIdleConnections(30, TimeUnit.SECONDS)  // 유휴 커넥션 정리
        .build();

    // RequestFactory 설정
    HttpComponentsClientHttpRequestFactory factory =
        new HttpComponentsClientHttpRequestFactory();
    factory.setHttpClient(httpClient);
    factory.setConnectTimeout(10_000);              // TCP 연결: 10초
    factory.setReadTimeout(10_000);                 // 응답 대기: 10초
    factory.setConnectionRequestTimeout(5_000);     // Pool 대기: 5초

    return factory;
}
```

---

## 2. 커넥션 풀 크기 산정

### 2.1 커넥션 풀의 종류

Spring Boot 애플리케이션에서 관리하는 주요 커넥션 풀:

| 종류 | 용도 | 기본값 | 권장값 |
|------|------|--------|--------|
| **DB Connection Pool** (HikariCP) | 데이터베이스 연결 | 10 | vCPU * 10 |
| **HTTP Connection Pool** (RestTemplate) | 외부 API 호출 | 설정 안하면 pooling 없음 | 100~200 |
| **S3 Connection Pool** (AWS SDK) | S3 API 호출 | 50 | 200 |

### 2.2 DB Connection Pool 크기 계산

#### 일반 공식
```
connections = ((core_count * 2) + effective_spindle_count)
```

#### 실제 예시 (r7i.xlarge: 4 vCPU)
```
최소: 4 * 2 + 1 (SSD) = 9개
권장: 4 * 10 = 40개 (피크 + 백그라운드 작업 고려)
```

#### HikariCP 설정
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 40      # 최대 커넥션 수
      minimum-idle: 20           # 최소 유휴 커넥션
      connection-timeout: 5000   # 커넥션 대기 시간 (5초)
      idle-timeout: 300000       # 유휴 커넥션 유지 시간 (5분)
      max-lifetime: 600000       # 커넥션 최대 생존 시간 (10분)
```

### 2.3 HTTP Connection Pool 크기 계산

#### 피크 시간대 시나리오
```
동시 사용자: 200명
초당 요청: 200 * 5 (클릭/사용자) / 60 = 약 16 req/s
요청당 평균 처리 시간: 200ms

필요한 동시 커넥션:
- 정상: 16 req/s * 0.2초 = 약 3개
- 외부 API 응답 지연 시 (3초): 16 * 3 = 48개
- 권장: 100~200개 (여유 확보)
```

#### 문제 상황 예시
```
느린 쿼리 발생 시:
- DB Pool: 10개 설정
- 쿼리 하나가 2초 걸리면: 16 req/s * 2초 = 32개 필요
- 결과: Pool 고갈 → 전체 서비스 마비 ❌

외부 API 지연 시:
- HTTP Pool: 100개 설정
- API가 3초 걸리면: 10 req/s * 3초 = 30개 필요
- 결과: 여유 있음 ✅
```

### 2.4 실전 권장 설정

```java
// HTTP Connection Pool (외부 API 호출용)
PoolingHttpClientConnectionManager connectionManager =
    new PoolingHttpClientConnectionManager();
connectionManager.setMaxTotal(200);           // 100 → 200 (피크 대응)
connectionManager.setDefaultMaxPerRoute(100); // 50 → 100 (호스트당)
```

---

## 3. 서버 환경과 리소스 제약

### 3.1 서버 스펙 예시

```
서버: r7i.xlarge (4 vCPU, 32GB RAM)
DB: db.r7i.2xlarge (Writer 1 + Reader 1)
```

### 3.2 ulimit 제약

```bash
# 현재 설정 확인
ulimit -a

# 주요 제약
open files:              1024
max user processes:      125268
```

#### 필요한 File Descriptor 계산
```
DB Connection:        40개
HTTP Connection:     200개
S3 Connection:       200개
기타 (로그, 소켓):   100개
------------------------
총 필요:             540개

현재 ulimit:        1024개  ✅ 여유 있음
권장 설정:          2048개  (더 안전)
```

#### ulimit 증가 방법
```bash
# 임시 변경 (현재 세션만)
ulimit -n 2048

# 영구 변경 (/etc/security/limits.conf)
* soft nofile 2048
* hard nofile 4096
```

### 3.3 커넥션 풀 균형 잡기

```
올바른 균형:
┌─────────────────────────────────────┐
│ DB Pool: 40                         │  ← 가장 중요! 부족하면 전체 마비
│ HTTP Pool: 200                      │  ← 외부 API 지연 대응
│ S3 Pool: 200                        │  ← 파일 업로드/다운로드 대응
│ 기타: 100                           │
├─────────────────────────────────────┤
│ 총 FD 필요: ~540                    │
│ ulimit: 1024 (여유: 484)            │
└─────────────────────────────────────┘
```

### 3.4 실제 프로덕션 체크리스트

- [ ] **DB Pool**: HikariCP 기본값(10) → 40으로 증가 ⚠️ 최우선
- [ ] **HTTP Pool**: SimpleClientHttpRequestFactory → PoolingHttpClientConnectionManager 적용
- [ ] **S3 Pool**: 기본값(50) → 200으로 증가
- [ ] **ulimit**: 1024 → 2048로 증가 (여유 확보)
- [ ] **모니터링**:
  - Pool 사용률 (최대 80% 이하 유지)
  - Connection wait time
  - Timeout 예외 발생 빈도

---

## 4. RestTemplate URL 파라미터 전달 방식

### 4.1 템플릿 변수 방식 (현재 방식)

```java
Map<String, String> params = new HashMap<>();
params.put("articleId", "12345");

restTemplate.exchange(
    amsServiceUrl + "/tag?articleId={articleId}",  // 템플릿
    HttpMethod.GET,
    requestEntity,
    responseType,
    params  // Map에서 "articleId" 키를 찾아서 {articleId} 치환
);

// 결과: http://ams-api.com/tag?articleId=12345
```

**동작 원리:**
1. URL에 `{articleId}` placeholder 작성
2. params Map에서 `"articleId"` 키의 값 조회
3. `{articleId}`를 실제 값으로 치환
4. 자동 URL 인코딩 처리

**장점**: URL 인코딩 자동 처리
**단점**: 약간 헷갈림 (쿼리스트링 형태인데 템플릿 변수 사용)

### 4.2 직접 삽입 방식 (간단한 경우 권장)

```java
String url = amsServiceUrl + "/tag?articleId=" + articleId;

restTemplate.exchange(
    url,
    HttpMethod.GET,
    requestEntity,
    responseType
);
```

**장점**: 직관적이고 명확
**단점**: URL 인코딩을 수동으로 처리해야 할 수도 있음

### 4.3 UriComponentsBuilder 방식 (권장)

```java
String url = UriComponentsBuilder
    .fromHttpUrl(amsServiceUrl + "/tag")
    .queryParam("articleId", articleId)
    .queryParam("status", "published")  // 여러 파라미터 추가 쉬움
    .build()
    .toUriString();

restTemplate.exchange(url, HttpMethod.GET, requestEntity, responseType);
```

**장점**:
- 자동 URL 인코딩
- 여러 파라미터 관리 쉬움
- 가독성 좋음

**권장 사용**: 쿼리 파라미터가 2개 이상일 때

### 4.4 Path Variable 방식

```java
Map<String, String> params = new HashMap<>();
params.put("articleId", "12345");

restTemplate.exchange(
    amsServiceUrl + "/tag/{articleId}",  // Path Variable (물음표 없음)
    HttpMethod.GET,
    requestEntity,
    responseType,
    params
);

// 결과: http://ams-api.com/tag/12345
```

**사용 시점**: RESTful API에서 리소스 식별자를 URL 경로에 포함할 때

### 4.5 비교 정리

| 방식 | 코드 | 결과 URL | 권장 |
|------|------|----------|------|
| 템플릿 변수 (Query) | `?id={id}` + Map | `/api?id=123` | △ |
| 직접 삽입 | `?id=" + id` | `/api?id=123` | ○ (단순할 때) |
| UriComponentsBuilder | `.queryParam("id", id)` | `/api?id=123` | ◎ (복잡할 때) |
| Path Variable | `/{id}` + Map | `/api/123` | ◎ (RESTful) |

---

## 5. 실전 트러블슈팅

### 5.1 "Timeout waiting for connection from pool" 에러

**원인:**
- Connection Pool이 모두 사용 중
- 커넥션 누수 (반환 안됨)
- Pool 크기가 작음

**해결:**
```java
// 1. Pool 크기 증가
connectionManager.setMaxTotal(200);

// 2. Connection Request Timeout 설정
factory.setConnectionRequestTimeout(5000);

// 3. 유휴 커넥션 정리
httpClient.evictIdleConnections(30, TimeUnit.SECONDS);

// 4. try-with-resources로 확실한 닫기
try (CloseableHttpResponse response = httpClient.execute(request)) {
    // 처리
}
```

### 5.2 "Read timed out" 에러

**원인:**
- 서버 응답이 너무 느림
- Read Timeout 설정이 너무 짧음

**해결:**
```java
// 1. Read Timeout 증가 (API 특성에 맞게)
factory.setReadTimeout(30_000); // 10초 → 30초

// 2. 백엔드 서버 성능 개선 (근본 해결)
```

### 5.3 DB Pool 고갈

**증상:**
```
HikariPool-1 - Connection is not available, request timed out after 5000ms.
```

**해결:**
```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 40  # 10 → 40
      leak-detection-threshold: 60000  # 커넥션 누수 감지 (1분)
```

### 5.4 모니터링 쿼리

```java
// HikariCP 모니터링
HikariPoolMXBean poolBean = hikariDataSource.getHikariPoolMXBean();
logger.info("Active connections: {}", poolBean.getActiveConnections());
logger.info("Idle connections: {}", poolBean.getIdleConnections());
logger.info("Total connections: {}", poolBean.getTotalConnections());
logger.info("Threads awaiting connection: {}", poolBean.getThreadsAwaitingConnection());

// HTTP Connection Pool 모니터링
PoolStats totalStats = connectionManager.getTotalStats();
logger.info("HTTP Pool - Available: {}, Leased: {}, Max: {}",
    totalStats.getAvailable(),
    totalStats.getLeased(),
    totalStats.getMax());
```

---

## 6. 요약

### 핵심 포인트

1. **타임아웃 3종 세트 반드시 설정**
   - Connection Timeout: 10초
   - Read Timeout: 10~30초 (API 특성에 따라)
   - Connection Request Timeout: 5초

2. **DB Pool이 가장 중요**
   - HikariCP 기본값 10은 너무 작음
   - 최소 vCPU * 10 권장

3. **HTTP Pool도 필수**
   - SimpleClientHttpRequestFactory는 pooling 없음
   - PoolingHttpClientConnectionManager 사용

4. **ulimit 여유 확보**
   - 1024 → 2048 권장

5. **항상 try-with-resources 사용**
   - 커넥션 누수 방지
