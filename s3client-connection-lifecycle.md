# S3Client 커넥션 라이프사이클 상세 분석

## 목차
1. [S3Client 아키텍처 개요](#1-s3client-아키텍처-개요)
2. [커넥션 획득 (Connection Acquisition)](#2-커넥션-획득-connection-acquisition)
3. [커넥션 반환 (Connection Release)](#3-커넥션-반환-connection-release)
4. [유휴 커넥션 정리 (Idle Connection Reaper)](#4-유휴-커넥션-정리-idle-connection-reaper)
5. [실전 사용 패턴](#5-실전-사용-패턴)
6. [트러블슈팅](#6-트러블슈팅)

---

## 1. S3Client 아키텍처 개요

### 1.1 S3Client 구조

```
┌────────────────────────────────────────────────────┐
│              S3ClientProvider (Singleton)          │
│  ┌──────────────────────────────────────────────┐ │
│  │         S3Client (1개, 애플리케이션당)        │ │
│  │  ┌────────────────────────────────────────┐  │ │
│  │  │  ApacheHttpClient (SdkHttpClient)      │  │ │
│  │  │  ┌──────────────────────────────────┐  │  │ │
│  │  │  │ PoolingHttpClientConnectionManager│ │  │ │
│  │  │  │  ┌────────────────────────────┐  │  │  │ │
│  │  │  │  │   Connection Pool (200개)  │  │  │  │ │
│  │  │  │  │  - available: List<Entry>  │  │  │  │ │
│  │  │  │  │  - leased: Set<Entry>      │  │  │  │ │
│  │  │  │  │  - totalConnections: 200   │  │  │  │ │
│  │  │  │  └────────────────────────────┘  │  │  │ │
│  │  │  └──────────────────────────────────┘  │  │ │
│  │  │  ┌──────────────────────────────────┐  │  │ │
│  │  │  │ IdleConnectionReaper (Thread)    │  │  │ │
│  │  │  │  - 30초마다 유휴 커넥션 정리      │  │  │ │
│  │  │  └──────────────────────────────────┘  │  │ │
│  │  └────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────┘
```

### 1.2 실제 코드

```java
@Component
public class S3ClientProvider {
    private final S3Client s3Client;  // ← 애플리케이션당 1개 (싱글톤)

    public S3ClientProvider() {
        // HTTP Client 설정 (Connection Pool 포함)
        SdkHttpClient httpClient = ApacheHttpClient.builder()
                .maxConnections(200)  // Connection Pool 최대 크기
                .connectionAcquisitionTimeout(Duration.ofSeconds(30))  // Pool에서 대기
                .socketTimeout(Duration.ofSeconds(60))  // 응답 대기
                .build();

        // S3Client 생성 (싱글톤)
        this.s3Client = S3Client.builder()
                .httpClient(httpClient)
                .region(Region.AP_NORTHEAST_2)
                .build();
    }

    public S3Client getClient() {
        return s3Client;  // 항상 같은 인스턴스 반환
    }

    @PreDestroy
    public void shutdown() {
        s3Client.close();  // 애플리케이션 종료 시 모든 커넥션 닫기
    }
}
```

### 1.3 핵심 개념

**중요한 구분:**
- **S3Client 인스턴스**: 1개 (싱글톤, 애플리케이션 생명주기)
- **HTTP Connection**: 200개 (풀에서 재사용)

**커넥션 사용 시점:**
- ✅ **S3 API 호출당 1개 커넥션** (getObject, putObject, deleteObject 등)
- ❌ HTTP 요청당 1개 커넥션 (X)

```java
// 예시: HTTP 요청 1개에서 S3 API 3번 호출
public String uploadImage(MultipartFile file) {
    S3Client s3 = s3ClientProvider.getClient();  // ← 싱글톤 가져오기 (커넥션 사용 X)

    s3.putObject(...);    // ← 커넥션 #1 사용
    s3.putObject(...);    // ← 커넥션 #2 사용
    s3.headObject(...);   // ← 커넥션 #3 사용

    return "성공";
} // → HTTP 요청 1개, S3 커넥션 3개 사용!
```

---

## 2. 커넥션 획득 (Connection Acquisition)

### 2.1 전체 흐름

```
s3Client.getObject(request)
    ↓
ApacheHttpClient.execute()
    ↓
PoolingHttpClientConnectionManager.requestConnection()
    ↓
CPool.lease(route, state, timeout, timeUnit)
    ↓
┌─────────────────────────────────────────┐
│ 1. available 리스트에서 찾기             │
│    ├─ 있으면: 즉시 반환                  │
│    └─ 없으면: ↓                         │
│                                         │
│ 2. 새로 생성 가능?                       │
│    (totalConnections < maxTotal)        │
│    ├─ YES: 새 커넥션 생성                │
│    └─ NO: ↓                             │
│                                         │
│ 3. pending 큐에 추가 후 대기             │
│    (connectionAcquisitionTimeout)       │
│    ├─ timeout 내 반환되면: 획득          │
│    └─ timeout 초과: 예외 발생            │
└─────────────────────────────────────────┘
```

### 2.2 ApacheHttpClient.execute() 상세

실제 AWS SDK 코드에서 커넥션 획득이 어디서 일어나는지 살펴봅시다.

#### 사용자가 보는 코드

```java
// AWS SDK v2: software.amazon.awssdk.http.apache.internal.ApacheHttpClient
private HttpExecuteResponse execute(HttpRequestBase apacheRequest, MetricCollector metricCollector) throws IOException {
    HttpClientContext localRequestContext = ApacheUtils.newClientContext(this.requestConfig.proxyConfiguration());
    ClientConnectionRequestFactory.THREAD_LOCAL_REQUEST_METRIC_COLLECTOR.set(metricCollector);

    HttpExecuteResponse var5;
    try {
        // ⭐ 바로 여기서 커넥션 획득이 일어납니다!
        HttpResponse httpResponse = this.httpClient.execute(apacheRequest, localRequestContext);
        var5 = this.createResponse(httpResponse, apacheRequest);
    } finally {
        ClientConnectionRequestFactory.THREAD_LOCAL_REQUEST_METRIC_COLLECTOR.remove();
    }

    return var5;
}
```

**핵심:** `this.httpClient.execute()` 호출 시점에 내부적으로 커넥션 획득이 시작됩니다.

#### Apache HttpClient 내부 동작

```java
// Apache HttpClient 내부 (간략화)
public class InternalHttpClient {

    public HttpResponse execute(HttpRequest request, HttpContext context) throws IOException {
        // ──────────────────────────────────────
        // 1단계: Route 결정 (어느 호스트로 연결할지)
        // ──────────────────────────────────────
        HttpRoute route = determineRoute(request);
        logger.debug("Determined route: {}", route);

        // ──────────────────────────────────────
        // 2단계: ⭐ 커넥션 획득 요청
        // ──────────────────────────────────────
        ConnectionRequest connRequest = connManager.requestConnection(
            route,
            null,  // state
            connectionRequestTimeout,
            TimeUnit.MILLISECONDS
        );
        logger.debug("Connection request created for route: {}", route);

        // ──────────────────────────────────────
        // 3단계: 커넥션 획득 대기 (블로킹)
        // 이 시점에서 CPool.lease()가 호출됨
        // ──────────────────────────────────────
        HttpClientConnection conn = connRequest.get(
            connectionRequestTimeout,
            TimeUnit.MILLISECONDS
        );
        logger.debug("Connection acquired: {}", conn);

        try {
            // ──────────────────────────────────────
            // 4단계: 커넥션을 사용하여 요청 전송
            // ──────────────────────────────────────
            requestExecutor.execute(request, conn, context);
            logger.debug("Request sent via connection: {}", conn);

            // ──────────────────────────────────────
            // 5단계: 응답 받기
            // ──────────────────────────────────────
            HttpResponse response = responseFactory.newHttpResponse(...);
            logger.debug("Response received: {} {}",
                response.getStatusLine().getStatusCode(),
                response.getStatusLine().getReasonPhrase());

            return response;

        } catch (Exception e) {
            // ──────────────────────────────────────
            // 에러 시 커넥션 즉시 해제
            // ──────────────────────────────────────
            logger.error("Error during request execution, closing connection", e);
            conn.close();
            throw e;
        }
        // 정상 흐름: 커넥션은 InputStream.close() 시점에 반환됨
    }
}
```

#### 상세 흐름도

```
사용자 코드: s3.getObject(request)
    ↓
ApacheHttpClient.execute(apacheRequest, context)
    ↓
┌─────────────────────────────────────────────────┐
│ InternalHttpClient.execute()                    │
│                                                 │
│ 1. determineRoute()                             │
│    → route = s3.ap-northeast-2.amazonaws.com    │
│                                                 │
│ 2. connManager.requestConnection(route)         │
│    → ConnectionRequest 객체 생성                 │
│                                                 │
│ 3. connRequest.get(timeout) ⏳ (블로킹)          │
│    ↓                                            │
│    PoolingHttpClientConnectionManager           │
│        ↓                                        │
│    CPool.lease() ← 2.3절 참조                    │
│        ↓                                        │
│    ┌─ available에서 찾기                         │
│    ├─ 없으면 새로 생성                           │
│    └─ 불가능하면 pending 대기                    │
│        ↓                                        │
│    커넥션 획득 완료! ✅                           │
│                                                 │
│ 4. requestExecutor.execute(request, conn)       │
│    → TCP 소켓으로 HTTP 요청 전송                 │
│                                                 │
│ 5. response 수신                                │
│    → HttpResponse 객체 반환                      │
└─────────────────────────────────────────────────┘
    ↓
ApacheHttpClient.createResponse(httpResponse)
    ↓
사용자에게 ResponseInputStream 반환
```

#### 핵심 포인트

1. **`httpClient.execute()` 한 줄 안에 숨겨진 과정:**
   - 커넥션 획득 요청
   - Pool에서 대기 (필요 시 블로킹)
   - 커넥션 획득
   - HTTP 요청 전송
   - 응답 수신

2. **블로킹 지점:**
   ```java
   HttpClientConnection conn = connRequest.get(timeout, TimeUnit.MILLISECONDS);
   ```
   - Pool에 available 커넥션이 없으면 여기서 대기
   - `connectionAcquisitionTimeout` 동안 블로킹
   - 시간 내에 커넥션 못 얻으면 `ConnectionPoolTimeoutException` 발생

3. **커넥션 획득 시점:**
   - ❌ `s3.getObject()` 호출 시 (X)
   - ❌ `ApacheHttpClient.execute()` 시작 시 (X)
   - ✅ `connRequest.get()` 호출 시 (O)

### 2.3 CPool.lease() 상세 코드

```java
// Apache HttpComponents: org.apache.http.pool.AbstractConnPool
public class AbstractConnPool<T, E extends PoolEntry<T>> {
    private final LinkedList<E> available;  // 사용 가능한 커넥션 리스트
    private final Set<E> leased;           // 대여 중인 커넥션 셋
    private final LinkedList<FutureCallback<E>> pending;  // 대기 큐
    private final AtomicInteger totalConnections;  // 전체 커넥션 수
    private final int maxTotal;  // 최대 커넥션 수

    public Future<E> lease(
            final T route,
            final Object state,
            final long timeout,
            final TimeUnit timeUnit) {

        synchronized (this.lock) {
            // ──────────────────────────────────────
            // 1단계: available 리스트에서 찾기
            // ──────────────────────────────────────
            E entry = getAvailableEntry(route);

            if (entry != null) {
                // 찾았으면 즉시 반환
                available.remove(entry);
                leased.add(entry);
                logger.debug("Reusing connection from pool: {}", entry);
                return new BasicFuture<>(entry);
            }

            // ──────────────────────────────────────
            // 2단계: 새 커넥션 생성 가능 여부 확인
            // ──────────────────────────────────────
            int current = totalConnections.get();
            if (current < maxTotal) {
                // Pool에 여유가 있으면 새로 생성
                E newEntry = createNewEntry(route);
                totalConnections.incrementAndGet();
                leased.add(newEntry);
                logger.debug("Created new connection: {} (total: {})",
                    newEntry, totalConnections.get());
                return new BasicFuture<>(newEntry);
            }

            // ──────────────────────────────────────
            // 3단계: Pool이 꽉 찼으면 대기
            // ──────────────────────────────────────
            logger.debug("Pool exhausted (max: {}), waiting...", maxTotal);
            final FutureCallback<E> callback = new FutureCallback<E>();
            this.pending.add(callback);

            // 다른 스레드가 커넥션 반환할 때까지 대기
            // (connectionAcquisitionTimeout 동안)
            return callback;
        }
    }

    private E getAvailableEntry(T route) {
        Iterator<E> it = available.iterator();
        while (it.hasNext()) {
            E entry = it.next();
            // 같은 route(호스트)이고, stale 상태가 아니면 재사용
            if (entry.getRoute().equals(route) && !entry.isStale()) {
                return entry;
            }
        }
        return null;
    }
}
```

### 2.4 실제 시나리오

#### 시나리오 1: Pool에 여유가 있을 때
```
초기 상태:
- available: [conn1, conn2, conn3]
- leased: []
- totalConnections: 3 / maxTotal: 200

요청: s3.getObject()
    ↓
1. available에서 conn1 찾기 ✅
2. available → leased로 이동
    ↓
결과 상태:
- available: [conn2, conn3]
- leased: [conn1]
- 소요 시간: ~1ms (즉시)
```

#### 시나리오 2: Pool이 꽉 찼을 때
```
현재 상태:
- available: []
- leased: [conn1, conn2, ..., conn200]  ← 200개 모두 사용 중
- totalConnections: 200 / maxTotal: 200

요청: s3.getObject()
    ↓
1. available에서 찾기 ❌ (비어있음)
2. 새로 생성? ❌ (200 == maxTotal)
3. pending 큐에 추가, 대기...
    ↓
30초 후:
- 다른 스레드가 conn1 반환
- pending 큐에서 대기 중인 요청에게 conn1 전달 ✅
    ↓
결과: 커넥션 획득 (소요 시간: 30초)

만약 30초 내에 반환 안되면:
    ↓
TimeoutException: "Timeout waiting for connection from pool"
```

---

## 3. 커넥션 반환 (Connection Release)

### 3.1 핵심 포인트

**중요:** 커넥션은 **InputStream을 닫을 때** 반환됩니다!

```java
// ❌ 잘못된 코드 - 커넥션 누수!
ResponseInputStream<GetObjectResponse> response = s3.getObject(request);
byte[] data = response.readAllBytes();
// response를 닫지 않음 → 커넥션이 leased에 계속 남아있음
// → Pool 고갈 → "Timeout waiting for connection from pool"

// ✅ 올바른 코드
try (ResponseInputStream<GetObjectResponse> response = s3.getObject(request)) {
    byte[] data = response.readAllBytes();
} // finally 블록에서 자동으로 close() 호출
  // → 커넥션 반환
```

### 3.2 반환 흐름

```
InputStream.close()
    ↓
ApacheHttpResponse.close()
    ↓
PoolingHttpClientConnectionManager.releaseConnection()
    ↓
┌─────────────────────────────────────────┐
│ 1. leased 셋에서 제거                    │
│                                         │
│ 2. 커넥션 상태 확인                      │
│    ├─ 정상 (open && !stale)             │
│    │   ├─ available 리스트에 추가         │
│    │   └─ pending 큐 알림 (있다면)        │
│    │                                     │
│    └─ 비정상 (closed || stale)          │
│        ├─ 커넥션 닫기                    │
│        └─ totalConnections--            │
└─────────────────────────────────────────┘
```

### 3.3 releaseConnection() 상세 코드

```java
public class PoolingHttpClientConnectionManager {

    public void releaseConnection(
            final HttpClientConnection managedConn,
            final Object state,
            final long keepalive,
            final TimeUnit timeUnit) {

        synchronized (this.lock) {
            // ──────────────────────────────────────
            // 1단계: leased에서 제거
            // ──────────────────────────────────────
            E entry = this.leased.remove(managedConn);

            if (entry == null) {
                throw new IllegalStateException(
                    "Connection not leased from this pool: " + managedConn
                );
            }

            logger.debug("Releasing connection: {}", entry);

            // ──────────────────────────────────────
            // 2단계: 커넥션 상태 확인
            // ──────────────────────────────────────
            boolean isReusable = managedConn.isOpen()
                              && !managedConn.isStale()
                              && entry.isValid();

            if (isReusable) {
                // ──────────────────────────────────────
                // 3-A: 재사용 가능하면 available에 추가
                // ──────────────────────────────────────
                entry.updateExpiry(keepalive, timeUnit);
                this.available.add(entry);
                logger.debug("Connection returned to pool: {} (available: {})",
                    entry, available.size());

                // ──────────────────────────────────────
                // 4단계: 대기 중인 요청 알림
                // ──────────────────────────────────────
                if (!this.pending.isEmpty()) {
                    FutureCallback<E> callback = this.pending.poll();
                    if (callback != null) {
                        // 대기 중인 요청에게 커넥션 전달
                        this.available.remove(entry);
                        this.leased.add(entry);
                        callback.completed(entry);
                        logger.debug("Waking up pending request with connection: {}", entry);
                    }
                }
            } else {
                // ──────────────────────────────────────
                // 3-B: 재사용 불가능하면 폐기
                // ──────────────────────────────────────
                logger.debug("Connection not reusable, closing: {}", entry);
                entry.close();
                totalConnections.decrementAndGet();
                logger.debug("Total connections after close: {}", totalConnections.get());
            }
        }
    }
}
```

### 3.4 실제 시나리오

#### 정상 반환 시나리오
```
사용 중 상태:
- available: [conn2, conn3]
- leased: [conn1]  ← conn1 사용 중

작업 완료: response.close()
    ↓
1. leased에서 conn1 제거
2. conn1 상태 확인: open=true, stale=false ✅
3. available에 conn1 추가
    ↓
결과 상태:
- available: [conn2, conn3, conn1]
- leased: []
```

#### Pool 고갈 + 대기 중인 요청 시나리오
```
고갈 상태:
- available: []
- leased: [conn1, ..., conn200]  ← 200개 모두 사용 중
- pending: [req1, req2]  ← 2개 요청 대기 중

커넥션 반환: conn1.close()
    ↓
1. leased에서 conn1 제거
2. conn1 상태 확인: 정상 ✅
3. available에 추가하려 했지만...
4. pending 큐에 req1이 있음!
    ↓
5. available에 추가하지 않고 즉시 req1에게 전달
    ↓
결과 상태:
- available: []
- leased: [conn1, conn2, ..., conn200]  ← conn1이 req1에게
- pending: [req2]  ← req1이 깨어남
```

---

## 4. 유휴 커넥션 정리 (Idle Connection Reaper)

### 4.1 IdleConnectionReaper 구조

```java
// AWS SDK v2: software.amazon.awssdk.http.apache.internal.IdleConnectionReaper
final class IdleConnectionReaper extends Thread {
    private final PoolingHttpClientConnectionManager connectionManager;
    private volatile boolean shuttingDown;

    // 30초마다 실행
    private static final long SLEEP_INTERVAL_MS = 30_000;

    private IdleConnectionReaper(PoolingHttpClientConnectionManager manager) {
        super("idle-connection-reaper");
        this.connectionManager = manager;
        this.setDaemon(true);  // 데몬 스레드 (애플리케이션 종료 시 자동 종료)
    }

    @Override
    public void run() {
        logger.info("IdleConnectionReaper started");

        while (!shuttingDown) {
            try {
                Thread.sleep(SLEEP_INTERVAL_MS);

                // ──────────────────────────────────────
                // 1. 만료된 커넥션 닫기 (maxLifetime 초과)
                // ──────────────────────────────────────
                connectionManager.closeExpiredConnections();

                // ──────────────────────────────────────
                // 2. 유휴 시간 초과 커넥션 닫기
                // ──────────────────────────────────────
                connectionManager.closeIdleConnections(
                    idleConnectionTime,
                    TimeUnit.MILLISECONDS
                );

            } catch (InterruptedException e) {
                logger.info("IdleConnectionReaper interrupted, shutting down");
                Thread.currentThread().interrupt();
            } catch (Exception e) {
                logger.error("Error in IdleConnectionReaper", e);
            }
        }

        logger.info("IdleConnectionReaper stopped");
    }

    public void shutdown() {
        shuttingDown = true;
        interrupt();
    }
}
```

### 4.2 closeExpiredConnections() 상세

```java
public class PoolingHttpClientConnectionManager {

    public void closeExpiredConnections() {
        synchronized (this.lock) {
            long now = System.currentTimeMillis();
            int closed = 0;

            Iterator<E> it = available.iterator();
            while (it.hasNext()) {
                E entry = it.next();

                // maxLifetime (connectionTimeToLive) 초과 확인
                if (entry.getExpiry() <= now) {
                    it.remove();
                    entry.close();
                    totalConnections.decrementAndGet();
                    closed++;
                    logger.debug("Closed expired connection: {} (expiry: {})",
                        entry, new Date(entry.getExpiry()));
                }
            }

            if (closed > 0) {
                logger.info("Closed {} expired connections (total: {})",
                    closed, totalConnections.get());
            }
        }
    }
}
```

### 4.3 closeIdleConnections() 상세

```java
public class PoolingHttpClientConnectionManager {

    public void closeIdleConnections(long idleTimeout, TimeUnit timeUnit) {
        synchronized (this.lock) {
            long deadline = System.currentTimeMillis() - timeUnit.toMillis(idleTimeout);
            int closed = 0;

            Iterator<E> it = available.iterator();
            while (it.hasNext()) {
                E entry = it.next();

                // 마지막 사용 시간이 deadline보다 오래된 커넥션 제거
                if (entry.getLastUsed() <= deadline) {
                    it.remove();
                    entry.close();
                    totalConnections.decrementAndGet();
                    closed++;
                    logger.debug("Closed idle connection: {} (idle: {}ms)",
                        entry, System.currentTimeMillis() - entry.getLastUsed());
                }
            }

            if (closed > 0) {
                logger.info("Closed {} idle connections (total: {})",
                    closed, totalConnections.get());
            }
        }
    }
}
```

### 4.4 실제 동작 예시

```
시간 0초:
- available: [conn1(사용: 0초 전), conn2(사용: 65초 전), conn3(사용: 5분 전)]
- totalConnections: 3

시간 30초 (Reaper 실행):
    ↓
1. closeExpiredConnections()
   - conn1: 생성 30초 → 유지 (maxLifetime: 5분)
   - conn2: 생성 1분 35초 → 유지
   - conn3: 생성 5분 30초 → ❌ 제거 (maxLifetime 초과)
    ↓
2. closeIdleConnections(idleTimeout: 1분)
   - conn1: 30초 전 사용 → 유지 (idleTimeout: 1분 이내)
   - conn2: 95초 전 사용 → ❌ 제거 (idleTimeout 초과)
    ↓
결과:
- available: [conn1]
- totalConnections: 1
- 로그: "Closed 1 expired connections, 1 idle connections"
```

---

## 5. 실전 사용 패턴

### 5.1 올바른 패턴 (try-with-resources)

```java
public byte[] downloadFile(String key) {
    S3Client s3 = s3ClientProvider.getClient();

    GetObjectRequest request = GetObjectRequest.builder()
        .bucket(bucketName)
        .key(key)
        .build();

    // ✅ try-with-resources 사용
    try (ResponseInputStream<GetObjectResponse> response = s3.getObject(request)) {
        return response.readAllBytes();
    } catch (IOException e) {
        logger.error("Failed to download file: {}", key, e);
        throw new RuntimeException("S3 download failed", e);
    }
    // close() 자동 호출 → 커넥션 반환
}
```

### 5.2 잘못된 패턴 (커넥션 누수)

```java
// ❌ 잘못된 코드 1: InputStream 닫지 않음
public byte[] downloadFileBad1(String key) {
    S3Client s3 = s3ClientProvider.getClient();

    ResponseInputStream<GetObjectResponse> response = s3.getObject(request);
    byte[] data = response.readAllBytes();

    return data;
    // response를 닫지 않음 → 커넥션 누수!
}

// ❌ 잘못된 코드 2: 예외 발생 시 닫지 않음
public byte[] downloadFileBad2(String key) {
    S3Client s3 = s3ClientProvider.getClient();
    ResponseInputStream<GetObjectResponse> response = null;

    try {
        response = s3.getObject(request);
        return response.readAllBytes();
    } catch (Exception e) {
        logger.error("Error", e);
        return null;
        // 예외 발생 시 response가 닫히지 않음 → 커넥션 누수!
    } finally {
        // finally 블록도 없음!
    }
}

// ✅ 수동으로 닫는다면 이렇게
public byte[] downloadFileManual(String key) {
    S3Client s3 = s3ClientProvider.getClient();
    ResponseInputStream<GetObjectResponse> response = null;

    try {
        response = s3.getObject(request);
        return response.readAllBytes();
    } finally {
        if (response != null) {
            try {
                response.close();  // 반드시 닫기
            } catch (IOException e) {
                logger.warn("Failed to close response stream", e);
            }
        }
    }
}
```

### 5.3 대량 작업 시 배치 처리

```java
// ❌ 잘못된 방법: 동시에 1000개 처리
public void processManyFilesBad(List<String> keys) {
    // 1000개 파일 동시 다운로드 → Pool 고갈!
    keys.parallelStream().forEach(key -> {
        downloadFile(key);  // 커넥션 1000개 필요 (Pool: 200개)
    });
}

// ✅ 올바른 방법: 배치로 나눠서 처리
public void processManyFilesGood(List<String> keys) {
    int batchSize = 50;  // Pool 크기(200)의 25%

    for (int i = 0; i < keys.size(); i += batchSize) {
        List<String> batch = keys.subList(
            i,
            Math.min(i + batchSize, keys.size())
        );

        // 50개씩 병렬 처리
        batch.parallelStream().forEach(key -> {
            downloadFile(key);
        });

        logger.info("Processed batch {}/{}", i / batchSize + 1,
            (keys.size() + batchSize - 1) / batchSize);
    }
}
```

---

## 6. 트러블슈팅

### 6.1 "Timeout waiting for connection from pool"

**증상:**
```
Exception: software.amazon.awssdk.core.exception.SdkClientException:
Unable to execute HTTP request: Timeout waiting for connection from pool
```

**원인 분석:**
1. **커넥션 누수**: InputStream을 닫지 않음
2. **Pool 크기 부족**: 동시 요청이 너무 많음
3. **느린 응답**: S3 응답이 느려서 커넥션 점유 시간이 김

**해결 방법:**

```java
// 1. try-with-resources 사용 확인
try (ResponseInputStream<GetObjectResponse> response = s3.getObject(request)) {
    // 처리
}

// 2. Pool 크기 증가
SdkHttpClient httpClient = ApacheHttpClient.builder()
    .maxConnections(400)  // 200 → 400
    .build();

// 3. Timeout 조정
SdkHttpClient httpClient = ApacheHttpClient.builder()
    .connectionAcquisitionTimeout(Duration.ofSeconds(60))  // 30초 → 60초
    .socketTimeout(Duration.ofSeconds(120))  // 큰 파일 다운로드 대응
    .build();

// 4. 커넥션 누수 감지
@Scheduled(fixedRate = 60000)  // 1분마다
public void monitorConnectionPool() {
    PoolStats stats = connectionManager.getTotalStats();
    logger.info("S3 Connection Pool - Available: {}, Leased: {}, Max: {}",
        stats.getAvailable(),
        stats.getLeased(),
        stats.getMax());

    if (stats.getLeased() > stats.getMax() * 0.8) {
        logger.warn("S3 Connection Pool usage high: {}%",
            (stats.getLeased() * 100.0 / stats.getMax()));
    }
}
```

### 6.2 커넥션 누수 찾기

```java
// 의심되는 코드에 로그 추가
public byte[] downloadFile(String key) {
    logger.debug("Acquiring S3 connection for key: {}", key);

    try (ResponseInputStream<GetObjectResponse> response = s3.getObject(request)) {
        logger.debug("S3 connection acquired for key: {}", key);
        byte[] data = response.readAllBytes();
        logger.debug("S3 connection will be released for key: {}", key);
        return data;
    } catch (IOException e) {
        logger.error("S3 connection released (error) for key: {}", key);
        throw new RuntimeException("S3 download failed", e);
    }
    // close() 호출 → 로그에 "released" 나와야 함
}

// 모든 "acquired"에 대응하는 "released"가 있는지 확인
```

### 6.3 성능 모니터링

```java
@Component
public class S3ConnectionPoolMonitor {

    @Autowired
    private S3ClientProvider s3ClientProvider;

    @Scheduled(fixedRate = 30000)  // 30초마다
    public void logPoolStats() {
        // 실제로는 httpClient에 접근해야 하므로
        // S3ClientProvider에서 노출 필요
        PoolStats stats = getPoolStats();

        logger.info("S3 Pool Stats - " +
            "Available: {}, " +
            "Leased: {}, " +
            "Pending: {}, " +
            "Max: {}, " +
            "Usage: {}%",
            stats.getAvailable(),
            stats.getLeased(),
            stats.getPending(),
            stats.getMax(),
            String.format("%.2f", stats.getLeased() * 100.0 / stats.getMax())
        );
    }
}
```

---

## 7. 요약

### 7.1 핵심 포인트

1. **S3Client는 싱글톤, 커넥션은 풀에서 재사용**
   - S3Client 인스턴스: 애플리케이션당 1개
   - HTTP Connection: Pool에서 200개 관리

2. **S3 API 호출당 커넥션 1개**
   - HTTP 요청과는 무관
   - getObject(), putObject() 등 각각 커넥션 사용

3. **반드시 InputStream을 닫아야 커넥션 반환**
   - try-with-resources 필수
   - 안 닫으면 leased에 계속 남아있음 → Pool 고갈

4. **IdleConnectionReaper가 백그라운드에서 정리**
   - 30초마다 실행
   - maxLifetime, idleTimeout 초과 커넥션 제거

5. **대량 작업 시 배치 처리**
   - Pool 크기(200)의 25% 단위로 나눠서 처리
   - 동시 50개씩 권장

### 7.2 체크리스트

- [ ] S3ClientProvider를 싱글톤(@Component)으로 관리
- [ ] maxConnections 적절히 설정 (200 권장)
- [ ] 모든 S3 API 호출에 try-with-resources 사용
- [ ] 대량 작업 시 배치 처리 적용
- [ ] 커넥션 풀 사용률 모니터링 (80% 이하 유지)
- [ ] @PreDestroy에서 s3Client.close() 호출
