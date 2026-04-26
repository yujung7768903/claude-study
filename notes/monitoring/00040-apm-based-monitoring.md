# APM 기반 모니터링 (Application Performance Monitoring)

## APM이란?

**APM(Application Performance Monitoring)**은 애플리케이션의 내부 동작을 실시간으로 추적해 성능 문제를 탐지하고 분석하는 모니터링 방식이다.

CPU·메모리 같은 인프라 지표를 보는 일반 모니터링과 달리, APM은 **애플리케이션 레벨**에서 무슨 일이 일어나는지를 본다.

---

## 일반 모니터링 vs APM

| 구분 | 일반 인프라 모니터링 | APM |
|------|------------------|-----|
| 관심 대상 | 서버 자원 (CPU, 메모리, 디스크) | 애플리케이션 동작 (트랜잭션, DB, 에러) |
| 답하는 질문 | "서버가 살아있나?" | "이 API가 왜 느린가?" |
| 대표 도구 | CloudWatch, Prometheus | Datadog APM, New Relic, Pinpoint |
| 가시성 수준 | 인프라 레벨 | 코드/쿼리 레벨 |

---

## APM이 추적하는 것들

### 1. 트랜잭션 추적 (Transaction Tracing)
각 API 요청의 응답 시간, 처리량, 성공/실패를 추적한다.

```
GET /api/orders/123
  └── 총 응답시간: 850ms
        ├── UserService.getUser()      : 12ms
        ├── OrderRepository.findById() : 720ms  ← 병목!
        └── 직렬화                     : 18ms
```

### 2. 분산 추적 (Distributed Tracing)
마이크로서비스 환경에서 요청이 여러 서비스를 거치는 흐름을 하나의 Trace로 시각화한다.

```
[API Gateway] → [Order Service] → [Payment Service] → [Notification Service]
    10ms              200ms              450ms               30ms
                                          ↑
                                       여기서 지연 발생
```

각 서비스에 **Trace ID** 를 전파해서 전체 호출 체인을 연결한다.

### 3. 에러 추적 (Error Tracking)
어느 코드 라인에서 예외가 발생했는지 스택 트레이스와 함께 수집한다.

```
NullPointerException at OrderService.java:87
  발생 횟수: 23회/분  ← 급증 감지
  영향받은 사용자: 15명
```

### 4. DB 쿼리 성능
느린 쿼리를 자동으로 탐지하고 실행 계획까지 연결해 보여준다.

```sql
-- 평균 실행시간 1.2s로 탐지된 슬로우 쿼리
SELECT * FROM orders WHERE user_id = ? AND status = 'PENDING'
-- 인덱스 미사용 경고
```

### 5. 외부 API / 의존성 호출 추적
내 서비스가 호출하는 외부 API, 캐시, 메시지 큐의 응답 시간도 측정한다.

---

## 대표 APM 도구

| 도구 | 특징 |
|------|------|
| **Datadog APM** | 분산 추적 + 서비스 맵 + 로그 연동, SaaS |
| **New Relic** | 코드 레벨 분석, AI 이상 탐지 |
| **Dynatrace** | AI 기반 자동 루트 코즈 분석 |
| **Elastic APM** | ELK 스택과 통합, 오픈소스 |
| **Pinpoint** | 네이버 오픈소스, Java/PHP 특화, 무료 |
| **Scouter** | LG CNS 오픈소스, Pinpoint와 유사 |
| **AWS X-Ray** | AWS 환경 분산 추적, Lambda·ECS 연동 |
| **Jaeger** | CNCF 오픈소스 분산 추적 |

---

## Spring Boot + Pinpoint 연동 예시

Pinpoint는 Java Agent 방식으로 코드 수정 없이 자동 계측한다.

```bash
# JVM 옵션에 Pinpoint Agent 추가만 하면 됨 (코드 변경 없음)
java -javaagent:/pinpoint/pinpoint-bootstrap.jar \
     -Dpinpoint.agentId=order-service-1 \
     -Dpinpoint.applicationName=order-service \
     -jar app.jar
```

실행 후 Pinpoint UI에서 트랜잭션 흐름, 응답 시간 분포, DB 쿼리 추적이 자동으로 수집된다.

---

## CloudWatch는 APM인가?

**CloudWatch 단독으로는 APM이 아니다.**

CloudWatch는 기본적으로 **인프라 모니터링** 도구다.

| 기능 | CloudWatch | APM |
|------|-----------|-----|
| CPU/메모리 메트릭 | ✅ | 보통 함께 제공 |
| 로그 수집·검색 | ✅ | ✅ |
| 트랜잭션 추적 | ❌ | ✅ |
| 분산 추적 | ❌ (X-Ray가 담당) | ✅ |
| DB 슬로우 쿼리 탐지 | ❌ | ✅ |
| 코드 레벨 프로파일링 | ❌ | ✅ |
| 에러 스택 트레이스 | 로그에서 수동 확인 | 자동 수집·분류 |

### CloudWatch를 APM에 가깝게 쓰려면

AWS가 제공하는 APM 관련 서비스를 조합해야 한다.

```
[애플리케이션]
    ├── CloudWatch Logs       : 로그 수집
    ├── CloudWatch Metrics    : 커스텀 메트릭
    ├── AWS X-Ray             : 분산 추적 (APM 핵심 기능)
    └── CloudWatch ServiceLens: X-Ray + CloudWatch 통합 뷰
```

**결론**: `CloudWatch + X-Ray + ServiceLens` 조합이 AWS 환경에서 APM에 해당한다. CloudWatch 단독은 인프라 모니터링이다.

---

## 실무 권장사항

- **소규모 서비스 (무료 우선)**: Pinpoint 또는 Scouter 자체 호스팅
- **AWS 기반 서비스**: X-Ray + CloudWatch ServiceLens로 시작, 부족하면 Datadog 도입
- **마이크로서비스**: 분산 추적이 필수 — Jaeger(오픈소스) 또는 Datadog APM 검토
- **에이전트 방식 선택**: Pinpoint처럼 코드 무수정 Java Agent 방식이 도입 비용이 가장 낮음
- APM 도입 시 **Trace ID를 로그에 함께 출력**하면 로그와 트레이스를 연결해 디버깅 효율이 크게 높아진다

```java
// MDC로 Trace ID를 로그에 자동 포함하는 패턴
@Component
public class TraceIdFilter implements Filter {
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain) {
        MDC.put("traceId", UUID.randomUUID().toString());
        chain.doFilter(req, res);
        MDC.clear();
    }
}
```
