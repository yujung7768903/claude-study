# k6 + InfluxDB: 메트릭 타입, 테이블 분류, 그리고 InfluxDB 기본 개념

## 1. k6 메트릭 타입 (4가지)

k6의 모든 메트릭(내장/커스텀)은 반드시 아래 4가지 타입 중 하나에 속한다.

### 1.1 Counter (카운터)

**누적 합계**를 추적하는 메트릭. 값이 계속 더해지기만 한다(단조 증가).

- **End-of-test 출력**: `count` (총합), `rate` (초당 비율)
- **대표 내장 메트릭**: `http_reqs`, `data_received`, `data_sent`, `iterations`, `dropped_iterations`

```javascript
import { Counter } from 'k6/metrics';
const myCounter = new Counter('my_custom_counter');

export default function () {
  myCounter.add(1);  // 1 증가
  myCounter.add(3);  // 3 증가 → 누적 4
}
```

### 1.2 Gauge (게이지)

**마지막 값**(현재 스냅샷)을 저장하는 메트릭. 값이 오르내릴 수 있다.

- **End-of-test 출력**: `value` (마지막 값), `min`, `max`
- **대표 내장 메트릭**: `vus`, `vus_max`

```javascript
import { Gauge } from 'k6/metrics';
const myGauge = new Gauge('my_custom_gauge');

export default function () {
  myGauge.add(42);   // value=42
  myGauge.add(100);  // value=100, min=42, max=100
}
```

### 1.3 Rate (비율)

추가된 값 중 **0이 아닌 값의 비율**(백분율)을 추적하는 메트릭.

- **End-of-test 출력**: `rate` (0.00 ~ 1.00 사이 비율)
- **대표 내장 메트릭**: `http_req_failed`, `checks`

```javascript
import { Rate } from 'k6/metrics';
const failRate = new Rate('custom_fail_rate');

export default function () {
  const res = http.get('https://example.com');
  failRate.add(res.status !== 200);  // true(1) 또는 false(0)
}
```

### 1.4 Trend (트렌드)

모든 값에 대한 **통계 분포**를 계산하는 메트릭. 지연 시간/응답 시간 측정에 핵심.

- **End-of-test 출력**: `min`, `max`, `avg`, `med`(중앙값), `p(90)`, `p(95)`, `p(99)`
- **대표 내장 메트릭**: `http_req_duration`, `http_req_blocked`, `http_req_waiting` 등

```javascript
import { Trend } from 'k6/metrics';
const myTrend = new Trend('custom_response_time');

export default function () {
  const res = http.get('https://example.com');
  myTrend.add(res.timings.duration);
}
```

### 메트릭 타입 비교표

| 타입 | 추적 대상 | End-of-test 출력 | 용도 |
|------|-----------|-------------------|------|
| **Counter** | 누적 합계 | count, rate/s | 이벤트 수 세기 (요청 수, 바이트) |
| **Gauge** | 마지막 값, 최솟값, 최댓값 | value, min, max | 시점 스냅샷 (활성 VU 수) |
| **Rate** | 0이 아닌 값의 비율 | rate (0.00~1.00) | 성공/실패 비율 |
| **Trend** | 전체 분포 통계 | min, max, avg, med, p(90), p(95) | 지연 시간/응답 시간 |

---

## 2. k6 내장 메트릭 전체 목록 (Grafana 공식 문서 기준)

### Standard 내장 메트릭 (프로토콜 무관, 항상 수집)

| 메트릭 이름 | 타입 | 설명 |
|-------------|------|------|
| `checks` | **Rate** | 성공한 check의 비율 |
| `data_received` | **Counter** | 수신된 데이터 양. [개별 URL 추적](https://grafana.com/docs/k6/latest/using-k6/metrics/#tracking-data-for-an-individual-url) 가능 |
| `data_sent` | **Counter** | 전송한 데이터 양. 개별 URL 단위로 추적 가능 |
| `dropped_iterations` | **Counter** | VU 부족(arrival-rate executor) 또는 시간 부족(iteration 기반 executor에서 maxDuration 초과)으로 시작되지 못한 반복 횟수 |
| `iteration_duration` | **Trend** | setup과 teardown을 포함한 1회 전체 반복 소요 시간 |
| `iterations` | **Counter** | VU가 JS 스크립트(default 함수)를 실행한 총 횟수 |
| `vus` | **Gauge** | 현재 활성 가상 사용자 수 |
| `vus_max` | **Gauge** | 최대 가상 사용자 수 (성능에 영향을 주지 않도록 VU 리소스가 미리 할당됨) |

### HTTP 전용 내장 메트릭 (HTTP 요청 시에만 생성)

> **참고**: 모든 `http_req_*` 메트릭의 타임스탬프는 **요청 종료 시점**(응답 본문 수신 완료 또는 타임아웃 시점)에 기록된다.

| 메트릭 이름 | 타입 | 설명 |
|-------------|------|------|
| `http_req_blocked` | **Trend** | 요청 시작 전 차단된 시간 (사용 가능한 TCP 연결 슬롯 대기 시간). float |
| `http_req_connecting` | **Trend** | 원격 호스트와 TCP 연결을 수립하는 데 소요된 시간. float |
| `http_req_duration` | **Trend** | 요청 전체 소요 시간. `http_req_sending + http_req_waiting + http_req_receiving`과 동일 (초기 DNS 조회/연결 시간 제외, 원격 서버의 처리 및 응답 시간). float |
| `http_req_failed` | **Rate** | `setResponseCallback`에 따른 실패 요청 비율 |
| `http_req_receiving` | **Trend** | 원격 호스트로부터 응답 데이터를 수신하는 데 소요된 시간. float |
| `http_req_sending` | **Trend** | 원격 호스트로 데이터를 전송하는 데 소요된 시간. float |
| `http_req_tls_handshaking` | **Trend** | 원격 호스트와 TLS 세션 핸드셰이크에 소요된 시간 |
| `http_req_waiting` | **Trend** | 원격 호스트로부터 응답을 대기하는 시간 (일명 "첫 번째 바이트까지의 시간", TTFB). float |
| `http_reqs` | **Counter** | k6가 생성한 총 HTTP 요청 수 |

**HTTP 타이밍 분해도:**

```
blocked → connecting → tls_handshaking → sending → waiting → receiving
                                         |________duration________|
```

> `duration`은 `sending + waiting + receiving`만 포함하며, `blocked`, `connecting`, `tls_handshaking`은 포함하지 않는다.

---

## 3. k6 → InfluxDB 연동 시 데이터 저장 구조

### 3.1 실행 방법

```bash
# InfluxDB 1.x (k6 내장 지원)
k6 run --out influxdb=http://localhost:8086/k6 script.js

# InfluxDB 2.x (xk6 확장 필요)
K6_INFLUXDB_ORGANIZATION=my-org \
K6_INFLUXDB_BUCKET=k6 \
K6_INFLUXDB_TOKEN=my-token \
./k6 run --out xk6-influxdb=http://localhost:8086 script.js
```

### 3.2 메트릭 → InfluxDB 매핑 규칙

k6의 **각 메트릭 이름이 InfluxDB의 measurement(테이블)**가 된다.

| InfluxDB 요소 | 매핑 대상 |
|---------------|-----------|
| **measurement** | k6 메트릭 이름 (예: `http_req_duration`, `http_reqs`) |
| **field** | `value` 필드에 메트릭 값 저장 |
| **tag** | 메타데이터 (`method`, `status`, `url`, `name`, `scenario` 등) |
| **timestamp** | 샘플 기록 시각 |

### 3.3 메트릭 타입별 InfluxDB 저장 방식과 조회 전략

InfluxDB에는 모든 메트릭이 **동일한 구조**(measurement + tags + `value` 필드 + timestamp)로 저장된다. 차이는 **조회할 때 사용하는 집계 함수**에 있다.

| k6 타입 | InfluxDB에 저장되는 value 예시 | 의미 있는 조회 쿼리 |
|---------|-------------------------------|---------------------|
| **Counter** | `value=1` (요청 1건 발생) | `SUM("value")` → 총합, `SUM("value")/시간` → 초당 비율 |
| **Gauge** | `value=50` (현재 VU 50명) | `LAST("value")` → 현재 값, `MAX("value")` → 최댓값 |
| **Rate** | `value=0` 또는 `value=1` | `MEAN("value")` → 비율 (0.0~1.0) |
| **Trend** | `value=245.3` (밀리초) | `MEAN("value")` → 평균, `PERCENTILE("value", 95)` → p95 |

### 3.4 생성되는 measurement(테이블) 목록

```
Counter 계열:  http_reqs, iterations, data_received, data_sent, dropped_iterations
Gauge 계열:    vus, vus_max
Rate 계열:     http_req_failed, checks
Trend 계열:    http_req_duration, http_req_blocked, http_req_connecting,
               http_req_tls_handshaking, http_req_sending, http_req_waiting,
               http_req_receiving, iteration_duration
```

### 3.5 태그(Tag)와 필드(Field) 구성

**기본 태그** (각 데이터 포인트에 자동 부여):

| 태그 키 | 설명 |
|---------|------|
| `method` | HTTP 메서드 (GET, POST 등) |
| `status` | HTTP 응답 상태 코드 |
| `name` | URL 그룹 이름 |
| `group` | k6 group 이름 |
| `scenario` | 시나리오 이름 |
| `expected_response` | 예상된 응답 여부 (true/false) |
| `error` | 에러 메시지 |
| `error_code` | 에러 코드 |
| `tls_version` | TLS 버전 |
| `proto` | 프로토콜 (HTTP/1.1, HTTP/2) |

**태그→필드 변환 설정** (`K6_INFLUXDB_TAGS_AS_FIELDS`):

기본값은 `vu:int,iter:int,url`로, 높은 카디널리티를 가진 `url` 등을 필드로 변환하여 인덱스 부담을 줄인다.

### 3.6 주요 환경변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `K6_INFLUXDB_ADDR` | InfluxDB 서버 주소 | `http://localhost:8086` |
| `K6_INFLUXDB_DB` | DB 이름 (v1) | `k6` |
| `K6_INFLUXDB_PUSH_INTERVAL` | 데이터 플러시 주기 | `1s` |
| `K6_INFLUXDB_TAGS_AS_FIELDS` | 필드로 변환할 태그 | `vu:int,iter:int,url` |
| `K6_INFLUXDB_BUCKET` | 버킷 이름 (v2) | - |
| `K6_INFLUXDB_ORGANIZATION` | 조직 이름 (v2) | - |
| `K6_INFLUXDB_TOKEN` | 인증 토큰 (v2) | - |

---

## 4. InfluxDB 기본 개념

### 4.1 시계열 데이터베이스(TSDB)란?

**시간 인덱스 기반**으로 데이터를 저장·조회하도록 최적화된 데이터베이스.

- 높은 쓰기 처리량 (초당 수십만~수백만 포인트)
- 시간 범위 조회 최적화 ("최근 1시간 데이터 조회")
- 자동 데이터 다운샘플링 및 보존 정책
- 시간 순서 데이터에 최적화된 압축

### 4.2 핵심 개념

```
┌─────────────────────────────────────────────────────────────────┐
│ Database (v1) / Bucket (v2)                                     │
│                                                                 │
│  ┌─── Measurement: "http_req_duration" ──────────────────────┐  │
│  │                                                           │  │
│  │  Tags (인덱싱됨)          Fields (인덱싱 안됨)              │  │
│  │  ┌──────────────────┐    ┌────────────────────┐           │  │
│  │  │ method = "GET"   │    │ value = 245.3      │           │  │
│  │  │ status = "200"   │    │                    │           │  │
│  │  │ name = "/api"    │    │                    │           │  │
│  │  └──────────────────┘    └────────────────────┘           │  │
│  │                                                           │  │
│  │  Timestamp: 2026-02-14T10:30:00Z                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

| 개념 | 설명 |
|------|------|
| **Measurement** | SQL의 테이블에 해당. 관련 데이터의 컨테이너 (예: `http_req_duration`) |
| **Tag** | 키-값 쌍의 메타데이터. **인덱싱됨** → 빠른 필터링. 문자열만 가능 |
| **Field** | 키-값 쌍의 실제 데이터 값. **인덱싱 안됨**. 문자열/정수/실수/불리언 가능 |
| **Timestamp** | 모든 데이터 포인트의 필수 요소. 내부적으로 나노초 에포크 저장 |
| **Series** | 동일한 measurement + tag set + field key를 공유하는 포인트 집합 |
| **Point** | 하나의 데이터 레코드 = measurement + tag set + field set + timestamp |
| **Retention Policy (v1)** | 데이터 보존 기간 설정 (예: 30일 후 자동 삭제) |
| **Bucket (v2)** | Database + Retention Policy를 하나로 합친 개념 |

### 4.3 Tag vs Field 비교

| 특성 | Tag | Field |
|------|-----|-------|
| **인덱싱** | O (빠른 조회) | X (전체 스캔) |
| **데이터 타입** | 문자열만 | 문자열, 정수, 실수, 불리언 |
| **필수 여부** | 선택 | 필수 (최소 1개) |
| **GROUP BY** | 가능 | 불가 (InfluxQL) |
| **수학 연산** | 불가 | 가능 |
| **적합한 데이터** | 저카디널리티 메타데이터 | 측정값, 고카디널리티 데이터 |

> **핵심 원칙**: 필터링/그룹핑에 자주 쓰이고 고유 값이 적은 데이터 → **Tag**, 수학 연산이 필요하거나 고유 값이 많은 데이터 → **Field**

### 4.4 InfluxDB Line Protocol

InfluxDB에 데이터를 쓸 때 사용하는 텍스트 기반 형식:

```
<measurement>,<tag_key>=<tag_value> <field_key>=<field_value> <timestamp>
```

```
http_req_duration,method=GET,status=200 value=245.3 1705312200000000000
http_reqs,method=POST,status=201 value=1 1705312200000000000
vus value=50 1705312200000000000
```

### 4.5 InfluxDB 1.x vs 2.x 비교

| 항목 | InfluxDB 1.x | InfluxDB 2.x |
|------|-------------|-------------|
| **데이터 구조** | Database + Retention Policy | Organization + Bucket |
| **쿼리 언어** | InfluxQL | Flux (기본) + InfluxQL (하위 호환) |
| **인증** | 아이디/비밀번호 | 토큰 기반 |
| **UI** | Chronograf (별도 설치) | 내장 웹 UI |
| **알림/태스크** | Kapacitor (별도 설치) | 내장 태스크 엔진 |
| **k6 지원** | 내장 (`--out influxdb`) | 확장 필요 (`xk6-output-influxdb`) |

---

## 5. InfluxDB 쿼리

### 5.1 InfluxQL (SQL 유사 — v1 기본, v2 호환)

**기본 조회:**

```sql
-- 전체 조회
SELECT * FROM "http_req_duration" LIMIT 10

-- 특정 필드만
SELECT "value" FROM "http_req_duration"
```

**WHERE 절 (필터링):**

```sql
-- 태그 필터 (태그 값은 작은따옴표)
SELECT "value" FROM "http_req_duration" WHERE "method" = 'GET'
SELECT "value" FROM "http_req_duration" WHERE "status" = '200'

-- 필드 값 필터
SELECT "value" FROM "http_req_duration" WHERE "value" > 500

-- 시간 필터
SELECT "value" FROM "http_req_duration" WHERE time > now() - 1h
SELECT "value" FROM "http_req_duration" WHERE time > '2026-02-14T00:00:00Z'

-- 조합
SELECT "value" FROM "http_req_duration"
  WHERE "method" = 'GET' AND time > now() - 30m
```

**GROUP BY time() (시간 기반 집계):**

```sql
-- 1분 단위 평균 응답 시간
SELECT MEAN("value") FROM "http_req_duration"
  WHERE time > now() - 1h
  GROUP BY time(1m)

-- 5분 단위 평균, HTTP 메서드별 분류
SELECT MEAN("value") FROM "http_req_duration"
  WHERE time > now() - 1h
  GROUP BY time(5m), "method"

-- 10초 단위 요청 수 합계
SELECT SUM("value") FROM "http_reqs"
  WHERE time > now() - 1h
  GROUP BY time(10s)

-- 빈 구간은 0으로 채우기
SELECT MEAN("value") FROM "http_req_duration"
  WHERE time > now() - 1h
  GROUP BY time(1m) fill(0)
```

**집계 함수:**

```sql
SELECT MEAN("value") FROM "http_req_duration"         -- 평균
SELECT SUM("value") FROM "http_reqs"                   -- 총합
SELECT COUNT("value") FROM "http_req_duration"         -- 건수
SELECT PERCENTILE("value", 95) FROM "http_req_duration" -- 95번째 백분위
SELECT PERCENTILE("value", 99) FROM "http_req_duration" -- 99번째 백분위
SELECT MIN("value"), MAX("value") FROM "http_req_duration" -- 최솟값, 최댓값
SELECT MEDIAN("value") FROM "http_req_duration"        -- 중앙값
SELECT LAST("value") FROM "vus"                        -- 마지막 값 (Gauge에 유용)
```

### 5.2 Flux (InfluxDB 2.x 기본 쿼리 언어)

파이프 포워드(`|>`) 연산자로 체이닝하는 함수형 쿼리 언어.

**기본 구조:**

```flux
from(bucket: "k6")
  |> range(start: -1h)                                          // 시간 범위 (필수)
  |> filter(fn: (r) => r._measurement == "http_req_duration")   // 필터링
  |> yield(name: "results")                                     // 결과 출력
```

**필터링:**

```flux
// 태그 필터
from(bucket: "k6")
  |> range(start: -1h)
  |> filter(fn: (r) =>
    r._measurement == "http_req_duration" and r.method == "GET"
  )

// 필드 값 필터
from(bucket: "k6")
  |> range(start: -1h)
  |> filter(fn: (r) =>
    r._measurement == "http_req_duration" and r._value > 500
  )
```

**aggregateWindow() (시간 기반 집계):**

```flux
// 1분 단위 평균 응답 시간
from(bucket: "k6")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "http_req_duration")
  |> aggregateWindow(every: 1m, fn: mean)

// 10초 단위 요청 수 합계
from(bucket: "k6")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "http_reqs")
  |> aggregateWindow(every: 10s, fn: sum)
```

**그룹핑:**

```flux
from(bucket: "k6")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "http_req_duration")
  |> group(columns: ["method"])
  |> mean()
```

**Flux 주요 집계 함수:**

```flux
|> mean()                   // 평균
|> sum()                    // 합계
|> count()                  // 건수
|> quantile(q: 0.95)       // 95번째 백분위
|> quantile(q: 0.99)       // 99번째 백분위
|> min()                    // 최솟값
|> max()                    // 최댓값
|> median()                 // 중앙값
|> last()                   // 마지막 값
|> spread()                 // 최댓값 - 최솟값
```

### 5.3 k6 결과 분석 실전 쿼리

```sql
-- 초당 요청 수 (RPS)
SELECT SUM("value") / 10 FROM "http_reqs"
  WHERE time > now() - 1h GROUP BY time(10s)

-- 평균 응답 시간 추이
SELECT MEAN("value") FROM "http_req_duration"
  WHERE time > now() - 1h GROUP BY time(10s)

-- p95 응답 시간 추이
SELECT PERCENTILE("value", 95) FROM "http_req_duration"
  WHERE time > now() - 1h GROUP BY time(1m)

-- 에러율 추이
SELECT MEAN("value") FROM "http_req_failed"
  WHERE time > now() - 1h GROUP BY time(10s)

-- 활성 VU 수 추이
SELECT LAST("value") FROM "vus"
  WHERE time > now() - 1h GROUP BY time(10s)

-- 엔드포인트별 평균 응답 시간
SELECT MEAN("value") FROM "http_req_duration"
  WHERE time > now() - 1h GROUP BY "name"

-- 데이터 수신 처리량
SELECT SUM("value") FROM "data_received"
  WHERE time > now() - 1h GROUP BY time(10s)

-- Check 통과율
SELECT MEAN("value") FROM "checks"
  WHERE time > now() - 1h GROUP BY time(10s)
```

**Grafana 대시보드에서 사용하는 쿼리 예시:**

```sql
-- Grafana 템플릿 변수 활용 RPS
SELECT sum("value") / ($__interval_ms / 1000)
  FROM "http_reqs"
  WHERE $timeFilter
  GROUP BY time($__interval), "name" fill(null)
```

---

## 6. 실무 권장사항

### k6 + InfluxDB 운영 팁

1. **카디널리티 관리**: `url` 태그는 고유 값이 매우 많으므로 반드시 필드로 변환(`K6_INFLUXDB_TAGS_AS_FIELDS`)하여 인덱스 부하를 줄여야 한다
2. **Retention Policy 설정**: 부하테스트 데이터는 영구 보관할 필요가 없으므로, 적절한 보존 기간(예: 30일)을 설정한다
3. **Grafana 연동**: k6 → InfluxDB → Grafana 파이프라인이 실시간 모니터링의 표준 구성이다. [공식 대시보드 ID: 2587](https://grafana.com/grafana/dashboards/2587-k6-load-testing-results/)을 임포트하면 바로 사용 가능
4. **중복 데이터 주의**: InfluxDB는 measurement + tag set + timestamp 조합이 동일하면 덮어쓴다. 동시 요청이 많으면 `vu`, `iter`를 태그로 유지하여 고유성을 확보할 수 있다
5. **InfluxDB 버전 선택**:
   - v1.x: k6 내장 지원으로 설정이 간단. 소규모/단순 구성에 적합
   - v2.x: Flux 쿼리, 내장 UI, 토큰 인증 등 기능이 풍부하지만 xk6 확장 빌드가 필요

### 쿼리 작성 팁

| 메트릭 타입 | 권장 집계 함수 | 이유 |
|------------|---------------|------|
| Counter | `SUM()` | 누적값이므로 합계가 의미 있음 |
| Gauge | `LAST()`, `MAX()` | 시점 값이므로 마지막/최대가 의미 있음 |
| Rate | `MEAN()` | 0/1 값의 평균 = 비율 |
| Trend | `MEAN()`, `PERCENTILE()` | 분포 통계가 핵심 |
