# Mockito ArgumentCaptor 동작 원리

## ArgumentCaptor란?

Mock에 전달된 인자를 "캡처"해서 나중에 검증할 수 있게 하는 도구입니다.

---

## 동작 흐름 (시각화)

### Step 1: Captor 생성

```java
ArgumentCaptor<HttpEntity> entityCaptor = ArgumentCaptor.forClass(HttpEntity.class);
ArgumentCaptor<Map> paramsCaptor = ArgumentCaptor.forClass(Map.class);
```

```
┌─────────────────────────┐
│ entityCaptor (빈 상자)  │  ← 아직 비어있음
│ value: null             │
└─────────────────────────┘

┌─────────────────────────┐
│ paramsCaptor (빈 상자)  │  ← 아직 비어있음
│ value: null             │
└─────────────────────────┘
```

---

### Step 2: 서비스 메서드 실행

```java
amsArticleTagService.getArticleTagListFromAms(article);
```

**서비스 내부에서 일어나는 일:**

```java
public List<RArticleTag> getArticleTagListFromAms(RArticle rArticle) {
    // 1. Header 생성
    HttpHeaders requestHeader = new HttpHeaders();
    requestHeader.add("X-Batch-User-Id", "BATCH_SYSTEM");
    requestHeader.set("Content-Type", "application/json");

    // 2. HttpEntity 생성
    HttpEntity<Object> requestEntity = new HttpEntity<>(null, requestHeader);
    //                                  ↑
    //                    이 객체를 나중에 캡처할 것!

    // 3. Params 생성
    Map<String, String> params = new HashMap<>();
    params.put("articleId", rArticle.getArticleId());
    //          ↑
    //    이 Map도 나중에 캡처할 것!

    // 4. Mock RestTemplate 호출
    ResponseEntity<AmsResponseDto<AmsTag>> response = restTemplate.exchange(
        amsServiceUrl + AmsRequestPath.TAG + "?articleId={articleId}",
        HttpMethod.GET,
        requestEntity,  // ← 이 객체가 Mock에 전달됨
        new ParameterizedTypeReference<AmsResponseDto<AmsTag>>() {},
        params         // ← 이 객체가 Mock에 전달됨
    );
}
```

**Mock RestTemplate의 상태:**

```
┌────────────────────────────────────────┐
│ Mock RestTemplate                      │
│                                        │
│ exchange() 호출 기록:                  │
│ ┌────────────────────────────────────┐ │
│ │ 호출 #1                            │ │
│ │ - arg[0]: "http://...?articleId=..."│ │
│ │ - arg[1]: GET                      │ │
│ │ - arg[2]: HttpEntity 객체 ────┐   │ │  ← requestEntity
│ │ - arg[3]: ParameterizedTypeRef │   │ │
│ │ - arg[4]: Map 객체 ───────────┼───┤ │  ← params
│ └────────────────────────────────│───┘ │
└──────────────────────────────────│─────┘
                                   │
                     이 객체들을 캡처할 것!
```

---

### Step 3: verify + capture

```java
verify(restTemplate).exchange(
    contains("/tag"),
    eq(HttpMethod.GET),
    entityCaptor.capture(),  // ← 캡처!
    any(ParameterizedTypeReference.class),
    paramsCaptor.capture()   // ← 캡처!
);
```

**Mockito가 하는 일:**

```
1. Mock의 호출 기록 확인
   "restTemplate.exchange()가 호출되었나?" ✅

2. 각 인자 확인
   - arg[0] contains "/tag"? ✅
   - arg[1] == GET? ✅
   - arg[2] → entityCaptor에 저장! ← capture()
   - arg[3] instanceof ParameterizedTypeReference? ✅
   - arg[4] → paramsCaptor에 저장! ← capture()

3. Captor에 값 저장
   ┌─────────────────────────────────┐
   │ entityCaptor                    │
   │ value: HttpEntity 객체 ◄────────┼─── arg[2]
   └─────────────────────────────────┘

   ┌─────────────────────────────────┐
   │ paramsCaptor                    │
   │ value: Map 객체 ◄───────────────┼─── arg[4]
   └─────────────────────────────────┘
```

---

### Step 4: getValue()로 꺼내기

```java
HttpEntity capturedEntity = entityCaptor.getValue();
Map capturedParams = paramsCaptor.getValue();
```

**이제 실제로 전달된 객체를 가져옴:**

```
┌─────────────────────────────────┐
│ entityCaptor.getValue()         │
│   ↓                             │
│ HttpEntity 객체                 │
│ - headers:                      │
│   - X-Batch-User-Id: BATCH_SYSTEM
│   - Content-Type: application/json
│ - body: null                    │
└─────────────────────────────────┘

┌─────────────────────────────────┐
│ paramsCaptor.getValue()         │
│   ↓                             │
│ Map 객체                        │
│ - articleId: A2026020513000005239
└─────────────────────────────────┘
```

---

### Step 5: 검증

```java
// Header 검증
HttpHeaders headers = capturedEntity.getHeaders();
assertEquals("BATCH_SYSTEM", headers.getFirst("X-Batch-User-Id"));
assertEquals("application/json", headers.getFirst("Content-Type"));

// 파라미터 검증
assertEquals("A2026020513000005239", capturedParams.get("articleId"));
```

---

## 핵심 개념

### "어떤 객체의 어떤 순간의 값을 가져오는가?"

| 질문 | 답변 |
|------|------|
| 어떤 객체? | Mock 객체 (restTemplate) |
| 어떤 순간? | `service.getArticleTagListFromAms()` 실행 중<br>`restTemplate.exchange()`가 호출된 순간 |
| 어떤 값? | 그 순간 `exchange()`의 인자로 전달된 실제 객체 |

### 타임라인

```
시간 →

[1] Captor 생성
    entityCaptor = ArgumentCaptor.forClass(HttpEntity.class)
    상태: value = null

[2] 서비스 메서드 실행
    service.getArticleTagListFromAms(article)

    [2-1] 서비스 내부: HttpEntity 생성
          requestEntity = new HttpEntity(null, headers)

    [2-2] 서비스 내부: Mock 호출
          restTemplate.exchange(url, GET, requestEntity, ...)

    [2-3] Mock: 호출 기록 저장
          Mock 내부 기록: [url, GET, requestEntity, ...]

[3] verify + capture
    verify(restTemplate).exchange(..., entityCaptor.capture(), ...)

    Mock의 기록에서 entityCaptor에 값 복사
    entityCaptor.value = requestEntity (2-1에서 생성된 객체)

[4] getValue()
    HttpEntity captured = entityCaptor.getValue()

    captured = requestEntity (2-1에서 생성된 그 객체!)
```

---

## 실제 사용 예시

### 전체 코드

```java
@Test
public void getArticleTagListFromAms_요청파라미터_검증() {
    // given
    RArticle rArticle = new RArticle();
    rArticle.setArticleId("A2026020513000005239");

    AmsResponseDto<AmsTag> responseDto = buildMockResponse();
    when(restTemplate.exchange(anyString(), any(), any(), any(ParameterizedTypeReference.class), anyMap()))
        .thenReturn(new ResponseEntity<>(responseDto, HttpStatus.OK));

    // when
    amsArticleTagService.getArticleTagListFromAms(rArticle);
    // ↑ 이 메서드 내부에서 restTemplate.exchange()가 호출됨
    // ↑ 그때 전달된 인자들을 나중에 캡처할 것

    // then
    ArgumentCaptor<HttpEntity> entityCaptor = ArgumentCaptor.forClass(HttpEntity.class);
    ArgumentCaptor<Map> paramsCaptor = ArgumentCaptor.forClass(Map.class);

    // verify: Mock이 호출되었는지 확인 + 인자 캡처
    verify(restTemplate).exchange(
        contains("/tag"),
        eq(HttpMethod.GET),
        entityCaptor.capture(),  // ← 실제로 전달된 HttpEntity 캡처
        any(ParameterizedTypeReference.class),
        paramsCaptor.capture()   // ← 실제로 전달된 Map 캡처
    );

    // 캡처된 값 꺼내기
    HttpEntity capturedEntity = entityCaptor.getValue();
    Map<String, String> capturedParams = paramsCaptor.getValue();

    // 검증: 실제로 올바른 값이 전달되었는가?
    HttpHeaders headers = capturedEntity.getHeaders();
    assertEquals("BATCH_SYSTEM", headers.getFirst("X-Batch-User-Id"));
    assertEquals("application/json", headers.getFirst("Content-Type"));
    assertEquals("A2026020513000005239", capturedParams.get("articleId"));
}
```

---

## ArgumentCaptor vs ArgumentMatcher

### ArgumentMatcher (any(), eq(), contains() 등)

```java
verify(restTemplate).exchange(
    contains("/tag"),       // 매칭만 함 (값은 안 가져옴)
    eq(HttpMethod.GET),     // 매칭만 함
    any(),                  // 매칭만 함
    any(),
    anyMap()                // 매칭만 함
);

// "이런 조건으로 호출되었나?"만 확인
// 실제 값은 가져올 수 없음
```

### ArgumentCaptor

```java
ArgumentCaptor<HttpEntity> captor = ArgumentCaptor.forClass(HttpEntity.class);

verify(restTemplate).exchange(
    anyString(),
    any(),
    captor.capture(),  // 매칭 + 캡처!
    any(),
    anyMap()
);

HttpEntity actual = captor.getValue();  // 실제 값 가져옴!
// 실제로 전달된 값을 꺼내서 자세히 검증 가능
```

---

## 언제 사용하나?

### ArgumentMatcher만으로 충분한 경우

```java
verify(restTemplate).exchange(
    contains("/tag"),           // URL에 "/tag"만 포함되면 OK
    eq(HttpMethod.GET),         // GET 메서드면 OK
    any(),                      // HttpEntity는 뭐든 OK
    any(),
    anyMap()                    // Map은 뭐든 OK
);
```

### ArgumentCaptor가 필요한 경우

```java
// Header의 특정 값까지 검증하고 싶을 때
ArgumentCaptor<HttpEntity> captor = ArgumentCaptor.forClass(HttpEntity.class);
verify(restTemplate).exchange(..., captor.capture(), ...);

HttpEntity entity = captor.getValue();
HttpHeaders headers = entity.getHeaders();
assertEquals("BATCH_SYSTEM", headers.getFirst("X-Batch-User-Id"));  // 정확한 값 검증
assertEquals("application/json", headers.getFirst("Content-Type"));

// Map의 각 키-값까지 검증하고 싶을 때
ArgumentCaptor<Map> paramsCaptor = ArgumentCaptor.forClass(Map.class);
verify(restTemplate).exchange(..., paramsCaptor.capture());

Map params = paramsCaptor.getValue();
assertEquals("A2026020513000005239", params.get("articleId"));  // 정확한 값 검증
```

---

## 핵심 요약

**ArgumentCaptor는:**
1. Mock에 전달된 **실제 인자 객체**를 캡처
2. `capture()` - Mock 호출 시점에 인자를 저장
3. `getValue()` - 저장된 인자를 꺼냄
4. 꺼낸 객체로 상세한 검증 가능

**언제 필요한가:**
- ArgumentMatcher로는 검증할 수 없는 **내부 필드 값**을 확인할 때
- Header의 특정 값, Map의 특정 키-값 등을 정확히 검증할 때

**동작 순서:**
```
Captor 생성 → 서비스 실행 → Mock 호출 → verify + capture → getValue → 검증
```
