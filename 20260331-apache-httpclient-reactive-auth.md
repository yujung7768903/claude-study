# Apache HttpClient Reactive 인증 방식

## 개념 설명

Apache HttpClient의 **Reactive 인증(Challenge-Response Authentication)** 은 HTTP 표준 인증 흐름을 따릅니다.

### 기본 흐름

```
Client                          Server
  |                               |
  |------- Request (인증 없음) --->|
  |                               |
  |<-- 401 Unauthorized ----------|
  |    WWW-Authenticate: Basic    |
  |    realm="OpenSearch"         |
  |                               |
  |--- Request + Authorization -->|
  |    Authorization: Basic xxx   |
  |                               |
  |<------- 200 OK ---------------|
```

1. 클라이언트가 인증 없이 요청
2. 서버가 `401 Unauthorized` + `WWW-Authenticate` 헤더로 챌린지
3. 클라이언트가 `CredentialsProvider`에서 자격증명을 꺼내 재요청
4. 서버가 인증 성공 응답

### 코드 예시 (Reactive 방식 - HttpClient 동기)

```java
CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
credentialsProvider.setCredentials(
    AuthScope.ANY,
    new UsernamePasswordCredentials("user", "password")
);

CloseableHttpClient httpClient = HttpClients.custom()
    .setDefaultCredentialsProvider(credentialsProvider)
    .build();
```

이 방식은 **동기 HttpClient**에서는 잘 동작합니다. 401을 받으면 자동으로 재시도합니다.

---

## 문제: HttpAsyncClient(비동기)에서의 동작 차이

`RestHighLevelClient`(OpenSearch/Elasticsearch)는 내부적으로 **Apache HttpAsyncClient**를 사용합니다.

```
RestHighLevelClient
    └── RestClient
            └── CloseableHttpAsyncClient  ← 비동기 I/O
```

비동기 클라이언트에서 `CredentialsProvider`를 설정해도, 401 챌린지 후 **자동 재시도가 보장되지 않습니다**.

### 이유

- 동기 클라이언트: 응답을 기다리다가 401이 오면 즉시 재요청 가능
- 비동기 클라이언트: 콜백 기반 처리라 401 후 재시도 로직이 복잡하고 기본 구현이 제한적

또한 AWS OpenSearch는 `WWW-Authenticate` 챌린지 헤더를 표준 형식으로 보내지 않는 경우가 있어 클라이언트가 챌린지를 인식하지 못합니다.

---

## 해결 방법 비교

### 방법 1: Preemptive(선제적) 인증 — CredentialsProvider + Interceptor

챌린지를 기다리지 않고 처음부터 Authorization 헤더를 포함하도록 인터셉터를 추가합니다.

```java
CredentialsProvider credentialsProvider = new BasicCredentialsProvider();
credentialsProvider.setCredentials(AuthScope.ANY,
    new UsernamePasswordCredentials(username, password));

return new RestHighLevelClient(
    RestClient.builder(new HttpHost(host, port, "https"))
        .setHttpClientConfigCallback(httpClientBuilder ->
            httpClientBuilder
                .setDefaultCredentialsProvider(credentialsProvider)
                .addInterceptorFirst((HttpRequestInterceptor) (request, context) -> {
                    // 모든 요청에 선제적으로 Authorization 헤더 추가
                    String auth = username + ":" + password;
                    String encoded = Base64.getEncoder()
                        .encodeToString(auth.getBytes(StandardCharsets.UTF_8));
                    request.addHeader("Authorization", "Basic " + encoded);
                })
        )
);
```

복잡하고 `username`/`password`를 람다 안에서 따로 참조해야 하는 단점이 있습니다.

### 방법 2: setDefaultHeaders — Authorization 헤더 직접 설정 (권장)

```java
String encoded = Base64.getEncoder()
    .encodeToString((username + ":" + password).getBytes(StandardCharsets.UTF_8));

Header[] defaultHeaders = new Header[]{
    new BasicHeader("Authorization", "Basic " + encoded)
};

return new RestHighLevelClient(
    RestClient.builder(new HttpHost(host, port, "https"))
        .setDefaultHeaders(defaultHeaders)
);
```

모든 요청에 Authorization 헤더가 포함됩니다. 챌린지-응답 과정 자체를 생략합니다.

---

## 비교표

| 항목 | Reactive (CredentialsProvider만) | Preemptive Interceptor | setDefaultHeaders |
|------|----------------------------------|------------------------|-------------------|
| 동작 방식 | 401 챌린지 후 재시도 | 처음부터 인증 헤더 포함 | 처음부터 인증 헤더 포함 |
| 동기 HttpClient | 정상 동작 | 가능 | 가능 |
| 비동기 HttpAsyncClient | **불안정** | 가능 | **가장 안정적** |
| AWS OpenSearch | **실패 가능** | 가능 | **권장** |
| 코드 복잡도 | 낮음 | 높음 | **낮음** |
| 불필요한 왕복 | 있음 (401 → 재요청) | 없음 | 없음 |

---

## 실무 권장사항

- **OpenSearch / Elasticsearch RestHighLevelClient + Basic Auth** 조합에서는 `setDefaultHeaders`를 사용하세요.
- AWS OpenSearch Service는 표준 챌린지 헤더를 보장하지 않으므로 Reactive 방식은 신뢰할 수 없습니다.
- `setDefaultHeaders`는 단순하고, 불필요한 왕복 요청(401 → 재시도)도 없어 성능상으로도 유리합니다.

```java
// 최종 권장 구현
@Bean(destroyMethod = "close")
public RestHighLevelClient client() {
    String encoded = Base64.getEncoder()
        .encodeToString((username + ":" + password).getBytes(StandardCharsets.UTF_8));

    return new RestHighLevelClient(
        RestClient.builder(new HttpHost(host, restPort, "https"))
            .setDefaultHeaders(new Header[]{
                new BasicHeader("Authorization", "Basic " + encoded)
            })
    );
}
```
