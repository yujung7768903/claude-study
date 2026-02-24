# URI vs URL 인코딩 차이 및 RestTemplate 사용 방식 비교

## 1. URI vs URL 문자열 인코딩 차이

### 개념 정리

| 구분 | URI (Uniform Resource Identifier) | URL (Uniform Resource Locator) |
|------|-----------------------------------|--------------------------------|
| 정의 | 리소스를 **식별**하는 문자열 | 리소스의 **위치**를 나타내는 문자열 |
| 관계 | 상위 개념 | URI의 하위 집합 |

### Java에서의 인코딩 차이

Java에서 `java.net.URI`와 `java.net.URL`은 특수문자 처리 방식이 다르다.

#### `java.net.URI`
- RFC 3986 표준을 따른다.
- 생성 시 **자동으로 퍼센트 인코딩**을 수행한다.
- 예약 문자(`:`, `/`, `?`, `#`, `&`, `=` 등)는 문맥에 따라 구분하여 인코딩 여부를 결정한다.
- 공백 → `%20`으로 인코딩된다.

```java
URI uri = new URI("http", "example.com", "/api/search", "q=hello world", null);
// 결과: http://example.com/api/search?q=hello%20world
```

#### `java.net.URL`
- 인코딩을 **자동으로 수행하지 않는다**.
- 이미 인코딩된 문자열을 그대로 받는다.
- 인코딩되지 않은 특수문자가 포함되면 오류가 발생하거나 잘못된 요청이 될 수 있다.

```java
URL url = new URL("http://example.com/api/search?q=hello world");
// 공백이 그대로 들어가 문제 발생 가능
```

#### 핵심 차이 요약

| 항목 | URI | URL |
|------|-----|-----|
| 공백 처리 | `%20` (RFC 3986) | 자동 인코딩 없음 |
| 한글 등 비ASCII | 자동 퍼센트 인코딩 | 수동 인코딩 필요 |
| 특수문자 안전성 | 문맥에 따라 자동 처리 | 개발자가 직접 관리 |

> **참고**: `URLEncoder.encode()`는 `application/x-www-form-urlencoded` 형식을 따르므로 공백을 `+`로 변환한다. URI의 `%20`과는 다르다.

---

## 2. RestTemplate 사용 방식 비교

### 방식 1: Map을 이용한 URI 변수 치환

```java
String url = "http://example.com/api/users/{id}?name={name}";

Map<String, String> params = new HashMap<>();
params.put("id", "1");
params.put("name", "JohnDoe");

ResponseEntity<String> response = restTemplate.exchange(
    url,
    HttpMethod.GET,
    null,
    String.class,
    params
);
```

#### 동작 방식
- `url`을 **String**으로 전달하면, RestTemplate 내부의 `DefaultUriBuilderFactory`가 `{id}`, `{name}` 플레이스홀더를 Map 값으로 치환한다.
- 치환 후 **자동으로 URI 인코딩**이 적용된다.
- path variable과 query parameter를 동일한 방식으로 처리한다.

#### 특징
- 간단하고 직관적이다.
- 플레이스홀더 기반이므로 URL 템플릿이 고정된 경우에 적합하다.
- 내부적으로 `UriComponentsBuilder`를 사용하여 인코딩한다 (`EncodingMode.TEMPLATE_AND_VALUES` 기본 적용).

#### 주의점
- 값에 이미 인코딩된 문자가 있으면 **이중 인코딩**이 발생할 수 있다.
  - 예: `%20`이 `%2520`으로 변환됨

---

### 방식 2: UriComponentsBuilder를 이용한 URL 생성

```java
URI uri = UriComponentsBuilder.fromHttpUrl("http://example.com/api/users")
    .path("/{id}")
    .queryParam("name", "JohnDoe")
    .buildAndExpand("1")
    .toUri();

ResponseEntity<String> response = restTemplate.exchange(
    uri,
    HttpMethod.GET,
    null,
    String.class
);
```

#### 동작 방식
- `UriComponentsBuilder`가 URL의 각 구성요소(scheme, host, path, query)를 개별적으로 관리한다.
- `buildAndExpand()` 시점에 path variable을 치환하고, `toUri()` 시점에 인코딩을 수행한다.
- **URI 객체**로 전달하므로 RestTemplate이 추가 인코딩을 하지 않는다.

#### 특징
- path, query parameter를 구조적으로 분리하여 조합할 수 있다.
- 인코딩 시점과 방식을 개발자가 제어할 수 있다.
- 동적으로 query parameter를 추가/제거하기 편리하다.

#### 인코딩 제어 옵션
```java
// 기본: 각 컴포넌트별 인코딩
.build().toUri()

// encode() 명시 호출: 전체 인코딩
.build().encode().toUri()

// 이미 인코딩된 값이 있을 때: 이중 인코딩 방지
.build(true).toUri()
```

---

### 핵심 차이 비교

| 항목 | Map 방식 (String URL) | UriComponentsBuilder (URI 객체) |
|------|-----------------------|----------------------------------|
| 인코딩 주체 | RestTemplate 내부에서 자동 | `toUri()` 시점에 수행, RestTemplate은 추가 인코딩 안 함 |
| 이중 인코딩 위험 | 있음 (이미 인코딩된 값 전달 시) | `build(true)` 등으로 제어 가능 |
| 동적 파라미터 | URL 템플릿에 미리 정의 필요 | `queryParam()`으로 자유롭게 추가 |
| 적합한 상황 | URL 구조가 고정적이고 단순한 경우 | 특수문자 처리, 동적 파라미터, 정밀한 인코딩 제어가 필요한 경우 |

### 실무 권장

- **단순한 API 호출**: Map 방식으로 충분
- **한글, 특수문자가 포함된 파라미터**: `UriComponentsBuilder` 사용 권장
- **이미 인코딩된 값을 다뤄야 할 때**: `UriComponentsBuilder` + `build(true)` 사용
