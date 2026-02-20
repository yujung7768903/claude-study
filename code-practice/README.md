# 코드 연습 문제

학습한 내용을 실제로 구현해보는 연습 공간입니다.

## 사용 방법

### 1. 문제 출제
채팅에서 "코드 연습 문제 내줘" 또는 구체적인 주제를 요청하세요.
예: "Mockito 테스트 작성 문제 내줘", "AtomicInteger 사용하는 문제 내줘"

### 2. 문제 풀기
- 각 문제 폴더에는 `Problem.md` (문제 설명)와 템플릿 코드가 있습니다.
- `TODO` 주석이 있는 부분을 구현하세요.
- 테스트 코드나 main() 메서드로 실행해서 확인하세요.

### 3. 정답 확인
채팅에서 "코드 검증해줘: {파일명}" 또는 "{파일명} 이거 맞는지 확인해줘"를 요청하세요.
- 코드 리뷰와 개선점 제안
- 정답 코드 제시
- 추가 학습 포인트 안내

## 문제 목록

| 번호 | 제목 | 난이도 | 주제 |
|------|------|--------|------|
| 01 | 멀티스레드 카운터 | 하 | AtomicInteger, CAS |
| 02 | UserService 테스트 작성 | 중 | Mockito, @Mock, @InjectMocks, verify, ArgumentCaptor |

## 폴더 구조

```
code-practice/
├── README.md
├── problem-01-atomic-counter/
│   ├── Problem.md          (문제 설명)
│   ├── Counter.java        (구현할 파일)
│   └── CounterTest.java    (테스트 코드)
├── problem-02-mock-test/
│   ├── Problem.md
│   ├── ApiService.java
│   └── ApiServiceTest.java
└── ...
```

## 팁

- 먼저 테스트를 실행해서 실패하는 것을 확인하세요 (Red)
- TODO 부분을 구현하세요 (Green)
- 코드를 개선하세요 (Refactor)
- 막히면 학습 자료를 다시 읽어보거나 AI에게 힌트를 요청하세요
