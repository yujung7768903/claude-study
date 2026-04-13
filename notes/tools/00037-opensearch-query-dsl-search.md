# OpenSearch Query DSL - 검색 쿼리 사용법

## 개요

OpenSearch(Elasticsearch)의 Full-text 검색은 Query DSL(Domain Specific Language)을 사용한다.
검색 쿼리는 크게 **Full-text query**와 **Term-level query**로 나뉜다.

---

## match 쿼리

단일 필드에 대해 텍스트를 분석(analyzer)하여 검색한다. 가장 기본적인 Full-text 검색 쿼리.

```json
GET /my-index/_search
{
  "query": {
    "match": {
      "title": "quick brown fox"
    }
  }
}
```

### 옵션 포함 (full syntax)

```json
GET /my-index/_search
{
  "query": {
    "match": {
      "title": {
        "query": "quick brown fox",
        "operator": "or",
        "analyzer": "standard",
        "fuzziness": "AUTO",
        "zero_terms_query": "none",
        "boost": 1.5
      }
    }
  }
}
```

---

## operator / mode

`operator`는 여러 토큰이 나왔을 때 AND/OR 조건을 결정한다.

| operator | 동작 |
|----------|------|
| `or` (기본값) | 토큰 중 하나라도 매칭되면 결과 반환 |
| `and` | 모든 토큰이 매칭되어야 결과 반환 |

```json
"match": {
  "title": {
    "query": "quick brown fox",
    "operator": "and"
  }
}
```

### minimum_should_match

`or` 조건에서 최소 몇 개의 토큰이 매칭되어야 하는지 지정한다.

```json
"match": {
  "title": {
    "query": "quick brown fox",
    "minimum_should_match": 2
  }
}
```

- `2`: 최소 2개 토큰 매칭
- `"75%"`: 토큰 중 75% 이상 매칭

---

## match_phrase 쿼리

**단어 순서와 위치**를 고려한 검색. "brown fox"를 검색하면 이 단어들이 순서대로 인접해 있어야 매칭된다.

```json
GET /my-index/_search
{
  "query": {
    "match_phrase": {
      "title": {
        "query": "quick brown fox",
        "analyzer": "standard",
        "slop": 0,
        "boost": 1.0,
        "zero_terms_query": "none"
      }
    }
  }
}
```

### match vs match_phrase 비교

| 항목 | match | match_phrase |
|------|-------|--------------|
| 토큰 순서 | 무관 | 순서 중요 |
| 기본 operator | OR | AND (모두 포함) |
| slop 지원 | X | O |
| "quick fox" 검색 시 "quick brown fox" 매칭 | O | X (slop=0) → O (slop=1) |

---

## slop

`match_phrase`에서 단어 사이에 허용할 **추가 단어 수**를 지정한다.

```json
"match_phrase": {
  "title": {
    "query": "quick fox",
    "slop": 1
  }
}
```

| slop | 매칭 예시 |
|------|-----------|
| 0 | "quick fox"만 매칭 |
| 1 | "quick brown fox" 매칭 (중간에 1개 단어 허용) |
| 2 | "quick big brown fox" 매칭 |

---

## analyzer

인덱싱과 검색 시 텍스트를 어떻게 분석할지 지정한다.
쿼리 시점에 `analyzer`를 명시하면 인덱스 기본 analyzer를 오버라이드한다.

```json
"match": {
  "title": {
    "query": "Quick Brown Fox",
    "analyzer": "english"
  }
}
```

### 주요 built-in analyzer

| analyzer | 특징 |
|----------|------|
| `standard` | 유니코드 기준 토크나이징, 소문자화 |
| `english` | 영어 형태소 분석 (stems: running → run) |
| `whitespace` | 공백 기준으로만 분리 (소문자화 없음) |
| `keyword` | 전체 필드를 단일 토큰으로 취급 |
| `simple` | 알파벳 아닌 문자로 분리, 소문자화 |

> 한국어는 `nori` 플러그인 필요

---

## zero_terms_query

analyzer가 모든 토큰을 제거했을 때(stop word만 입력한 경우 등) 어떻게 처리할지 결정한다.

```json
"match": {
  "title": {
    "query": "to be or not to be",
    "analyzer": "english",
    "zero_terms_query": "all"
  }
}
```

| 값 | 동작 |
|----|------|
| `none` (기본값) | 토큰이 없으면 아무 문서도 반환하지 않음 |
| `all` | 토큰이 없으면 모든 문서를 반환 (match_all처럼 동작) |

---

## boost

쿼리의 **관련성 점수(relevance score)** 가중치를 조정한다. 기본값은 `1.0`.

```json
GET /my-index/_search
{
  "query": {
    "bool": {
      "should": [
        {
          "match": {
            "title": {
              "query": "opensearch",
              "boost": 3.0
            }
          }
        },
        {
          "match": {
            "body": {
              "query": "opensearch",
              "boost": 1.0
            }
          }
        }
      ]
    }
  }
}
```

- `boost > 1.0`: 해당 쿼리의 점수를 높임
- `boost < 1.0`: 해당 쿼리의 점수를 낮춤
- 절대 점수가 아닌 **상대적 가중치**이므로 다른 쿼리와 비교하여 의미를 가짐

---

## multi_match 쿼리

여러 필드에 동시에 match 검색을 수행한다.

```json
GET /my-index/_search
{
  "query": {
    "multi_match": {
      "query": "quick brown fox",
      "fields": ["title^3", "body", "tags^2"],
      "type": "best_fields",
      "operator": "and",
      "analyzer": "standard"
    }
  }
}
```

- `title^3`: title 필드에 boost 3 적용

### multi_match type

| type | 동작 |
|------|------|
| `best_fields` (기본) | 가장 점수 높은 필드의 점수 사용 |
| `most_fields` | 매칭된 필드 점수 합산 |
| `cross_fields` | 여러 필드를 하나의 큰 필드처럼 취급 |
| `phrase` | match_phrase 방식으로 검색 |
| `phrase_prefix` | match_phrase_prefix 방식으로 검색 |

---

## bool 쿼리와 조합

```json
GET /my-index/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "status": "published" } }
      ],
      "should": [
        {
          "match_phrase": {
            "title": {
              "query": "quick fox",
              "slop": 1,
              "boost": 2.0
            }
          }
        },
        {
          "match": {
            "tags": {
              "query": "search engine",
              "operator": "or"
            }
          }
        }
      ],
      "minimum_should_match": 1,
      "filter": [
        { "range": { "date": { "gte": "2024-01-01" } } }
      ]
    }
  }
}
```

| 절 | 특징 |
|----|------|
| `must` | AND 조건, 점수에 영향 |
| `should` | OR 조건, 점수에 영향 |
| `must_not` | NOT 조건, 점수에 영향 없음 |
| `filter` | AND 조건, 점수에 영향 없음 (캐싱 가능) |

---

## 실무 권장사항

1. **analyzer 일치**: 인덱싱 시 사용한 analyzer와 검색 시 사용하는 analyzer를 맞춰야 예상대로 동작한다.
2. **match_phrase + slop**: 순서가 중요한 검색(제목, 고유명사)에 활용. slop은 0~2 수준으로 제한하는 것이 좋다.
3. **boost 남용 주의**: boost는 상대적 가중치이므로 과도하게 사용하면 점수 해석이 어려워진다. 중요 필드에만 의미 있는 값을 부여한다.
4. **zero_terms_query**: 사용자가 stop word만 입력할 가능성이 있는 검색 UI에서는 `all`로 설정해 빈 결과 방지를 고려한다.
5. **filter vs query**: 정확한 필터링(날짜 범위, 카테고리 등)은 `filter` 절 사용. 점수를 계산하지 않아 성능이 좋고 캐싱된다.
6. **multi_match + boost**: `fields: ["title^3", "body"]` 형태로 필드별 가중치를 지정하면 간단하게 랭킹을 조정할 수 있다.

---

# OpenSearch REST API 엔드포인트 정리

OpenSearch는 HTTP REST API를 통해 인덱스 관리, 검색, 분석, 클러스터 운영 등을 수행한다.
URL 패턴은 `/{index}/{endpoint}` 또는 `/{endpoint}` 형태이다.

---

## 핵심 API 엔드포인트 요약

| 엔드포인트 | 역할 |
|-----------|------|
| `_search` | 문서 검색 (Query DSL) |
| `_mapping` | 필드 타입/매핑 정보 조회 및 설정 |
| `_analyze` | 텍스트 분석 과정 디버깅 (토크나이징 결과 확인) |
| `_bulk` | 대량 문서 색인/수정/삭제 |
| `_count` | 조건에 맞는 문서 수 반환 |
| `_explain` | 특정 문서의 점수 계산 이유 설명 |
| `_cat` | 클러스터/인덱스 상태를 사람이 읽기 쉬운 형태로 출력 |
| `_cluster` | 클러스터 상태, 설정, 통계 조회 |
| `_nodes` | 노드 정보 및 상태 조회 |
| `_aliases` | 인덱스 별칭 관리 |
| `_settings` | 인덱스 설정 조회/변경 |
| `_reindex` | 인덱스 간 문서 복사 및 재색인 |
| `_update_by_query` | 조건에 맞는 문서 일괄 업데이트 |
| `_delete_by_query` | 조건에 맞는 문서 일괄 삭제 |
| `_scroll` | 대량 검색 결과를 페이지 단위로 순회 |
| `_msearch` | 여러 검색 쿼리를 한 번에 요청 |
| `_field_caps` | 인덱스 전체에서 필드 정보 조회 |

---

## `_search` — 문서 검색

가장 핵심 API. Query DSL을 통해 인덱스에서 문서를 검색한다.

```http
GET /my-index/_search          # 특정 인덱스 검색
GET /_search                   # 전체 인덱스 검색
GET /my-index,other-index/_search  # 다중 인덱스 검색
GET /my-*/_search              # 와일드카드 패턴
```

```json
GET /my-index/_search
{
  "query": { "match": { "title": "opensearch" } },
  "from": 0,
  "size": 10,
  "sort": [{ "date": "desc" }],
  "_source": ["title", "date"]
}
```

| 파라미터 | 설명 |
|---------|------|
| `from` | 결과 시작 오프셋 (기본값 0) |
| `size` | 반환할 문서 수 (기본값 10) |
| `sort` | 정렬 기준 필드 |
| `_source` | 반환할 필드 목록 (생략 시 전체 반환) |
| `explain` | `true`로 설정하면 각 문서의 점수 계산 이유 포함 |

---

## `_mapping` — 매핑 조회 및 설정

필드의 데이터 타입, analyzer 등 **인덱스 스키마(매핑)** 를 조회하거나 추가한다.

```http
GET /my-index/_mapping           # 전체 매핑 조회
GET /my-index/_mapping/field/title  # 특정 필드 매핑 조회
PUT /my-index/_mapping           # 새 필드 매핑 추가 (기존 필드 타입 변경 불가)
```

```json
GET /my-index/_mapping
```

응답 예시:
```json
{
  "my-index": {
    "mappings": {
      "properties": {
        "title": {
          "type": "text",
          "analyzer": "standard"
        },
        "date": {
          "type": "date"
        },
        "status": {
          "type": "keyword"
        }
      }
    }
  }
}
```

새 필드 추가:
```json
PUT /my-index/_mapping
{
  "properties": {
    "new_field": {
      "type": "keyword"
    }
  }
}
```

> **주의**: 기존 필드의 타입은 변경 불가. 타입 변경이 필요하면 `_reindex`로 새 인덱스로 복사해야 한다.

### 주요 필드 타입

| 타입 | 용도 |
|------|------|
| `text` | Full-text 검색 대상 (analyzer 적용됨) |
| `keyword` | 정확한 값 매칭, 집계, 정렬 용도 |
| `integer`, `long`, `float` | 숫자 |
| `date` | 날짜/시간 |
| `boolean` | true/false |
| `nested` | 배열 내 객체를 독립적으로 쿼리할 때 |
| `object` | 중첩 객체 (nested와 달리 독립 쿼리 불가) |

---

## `_analyze` — 텍스트 분석 디버깅

텍스트가 **어떻게 토크나이징되는지 직접 확인**하는 디버깅 도구.
인덱싱 전/후 analyzer 동작을 검증할 때 유용하다.

```http
GET /_analyze                    # analyzer 직접 지정
GET /my-index/_analyze           # 인덱스에 설정된 analyzer 사용
```

#### analyzer 직접 지정

```json
GET /_analyze
{
  "analyzer": "standard",
  "text": "Quick Brown Fox Jumps"
}
```

응답:
```json
{
  "tokens": [
    { "token": "quick", "start_offset": 0, "end_offset": 5, "type": "<ALPHANUM>", "position": 0 },
    { "token": "brown", "start_offset": 6, "end_offset": 11, "type": "<ALPHANUM>", "position": 1 },
    { "token": "fox",   "start_offset": 12, "end_offset": 15, "type": "<ALPHANUM>", "position": 2 },
    { "token": "jumps", "start_offset": 16, "end_offset": 21, "type": "<ALPHANUM>", "position": 3 }
  ]
}
```

#### 인덱스의 특정 필드 analyzer 사용

```json
GET /my-index/_analyze
{
  "field": "title",
  "text": "Running Faster"
}
```

#### tokenizer + filter 조합으로 직접 구성

```json
GET /_analyze
{
  "tokenizer": "standard",
  "filter": ["lowercase", "stop"],
  "text": "The Quick Brown Fox"
}
```

> `_analyze`는 **"왜 검색이 안 되지?"** 를 디버깅할 때 가장 먼저 확인하는 API.
> 인덱싱 시 토큰과 검색 시 토큰이 다르면 매칭이 안 된다.

---

## `_bulk` — 대량 작업

여러 색인/수정/삭제 작업을 **한 번의 요청**으로 처리. 성능상 단건 API를 반복 호출하는 것보다 훨씬 유리하다.

```http
POST /_bulk
POST /my-index/_bulk
```

요청 형식: action 줄 + document 줄이 한 쌍 (NDJSON):
```json
{ "index": { "_index": "my-index", "_id": "1" } }
{ "title": "First Doc", "status": "published" }
{ "update": { "_index": "my-index", "_id": "1" } }
{ "doc": { "status": "draft" } }
{ "delete": { "_index": "my-index", "_id": "2" } }
```

| action | 설명 |
|--------|------|
| `index` | 문서 생성 또는 전체 교체 |
| `create` | 문서 생성 (이미 존재하면 실패) |
| `update` | 문서 부분 업데이트 |
| `delete` | 문서 삭제 (document 줄 불필요) |

---

## `_count` — 문서 수 조회

검색 조건에 맞는 문서 수만 반환. `_search`보다 가볍다.

```json
GET /my-index/_count
{
  "query": {
    "term": { "status": "published" }
  }
}
```

---

## `_explain` — 점수 계산 이유 확인

특정 문서가 왜 그 점수를 받았는지 **BM25 계산 과정**을 상세히 설명한다.

```json
GET /my-index/_explain/1
{
  "query": {
    "match": { "title": "quick fox" }
  }
}
```

> 검색 랭킹 튜닝 시 `_explain`으로 점수 요인을 파악하고 `boost`를 조정한다.

---

## `_cat` — 운영 상태 텍스트 출력

클러스터/인덱스/샤드 상태를 **사람이 읽기 쉬운 텍스트** 형태로 출력한다. 주로 운영/모니터링 용도.

```http
GET /_cat/indices?v             # 인덱스 목록 + 문서 수, 크기
GET /_cat/health?v              # 클러스터 상태 (green/yellow/red)
GET /_cat/nodes?v               # 노드 목록 및 리소스 사용량
GET /_cat/shards?v              # 샤드 분배 현황
GET /_cat/aliases?v             # 별칭 목록
GET /_cat/indices?v&s=docs.count:desc  # 정렬 가능
```

응답 예시 (`_cat/indices`):
```
health status index      pri rep docs.count store.size
green  open   my-index     1   1       1024       5mb
```

---

## `_settings` — 인덱스 설정

인덱스의 샤드 수, replica 수, analyzer 설정 등을 조회/변경한다.

```http
GET /my-index/_settings         # 설정 조회
PUT /my-index/_settings         # 동적 설정 변경
```

```json
PUT /my-index/_settings
{
  "index": {
    "number_of_replicas": 2,
    "refresh_interval": "30s"
  }
}
```

> `number_of_shards`는 인덱스 생성 후 변경 불가. `number_of_replicas`와 `refresh_interval`은 동적으로 변경 가능.

---

## `_reindex` — 인덱스 재색인

기존 인덱스의 문서를 **새 인덱스로 복사**한다. 매핑 변경이나 인덱스 재구성 시 사용.

```json
POST /_reindex
{
  "source": {
    "index": "old-index",
    "query": { "term": { "status": "published" } }
  },
  "dest": {
    "index": "new-index"
  }
}
```

---

## `_aliases` — 인덱스 별칭 관리

하나 이상의 인덱스에 **별칭(alias)** 을 부여한다. 인덱스를 교체해도 애플리케이션 코드를 변경하지 않아도 된다.

```json
POST /_aliases
{
  "actions": [
    { "add":    { "index": "my-index-v2", "alias": "my-index" } },
    { "remove": { "index": "my-index-v1", "alias": "my-index" } }
  ]
}
```

> **무중단 인덱스 교체** 패턴: alias를 외부에 노출하고, 내부에서 인덱스를 swap한다.

---

## `_cluster` / `_nodes` — 클러스터/노드 상태

```http
GET /_cluster/health            # 클러스터 전체 상태 (green/yellow/red)
GET /_cluster/stats             # 클러스터 통계
GET /_cluster/settings          # 클러스터 설정
GET /_nodes                     # 전체 노드 정보
GET /_nodes/stats               # 노드별 JVM, 메모리, 색인 통계
```

---

## `_delete_by_query` / `_update_by_query` — 조건부 대량 처리

```json
POST /my-index/_delete_by_query
{
  "query": { "term": { "status": "deleted" } }
}

POST /my-index/_update_by_query
{
  "query": { "term": { "status": "draft" } },
  "script": {
    "source": "ctx._source.status = 'archived'"
  }
}
```

---

## API 선택 가이드

| 목적 | 사용 API |
|------|---------|
| 문서 검색 | `_search` |
| 토크나이저 동작 확인 | `_analyze` |
| 필드 타입/스키마 확인 | `_mapping` |
| 검색 점수 이유 확인 | `_explain` |
| 대량 색인/삭제 | `_bulk` |
| 인덱스 스키마 재설계 | `_reindex` + `_mapping` |
| 무중단 인덱스 교체 | `_aliases` |
| 인덱스 현황 파악 | `_cat/indices` |
| 클러스터 이상 탐지 | `_cluster/health`, `_cat/health` |
| 조건부 대량 수정/삭제 | `_update_by_query`, `_delete_by_query` |
