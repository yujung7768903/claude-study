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
