# 실행 방법

## 1. 컴파일 및 실행

### Windows (현재 환경)
```bash
cd C:\Users\D4006124\claude-study\code-practice\problem-01-atomic-counter

# 컴파일
javac *.java

# 실행
java CounterTest
```

### Linux/Mac
```bash
cd ~/claude-study/code-practice/problem-01-atomic-counter

# 컴파일
javac *.java

# 실행
java CounterTest
```

## 2. 작업 순서

1. **문제 읽기**: `Problem.md` 파일 읽기
2. **구현하기**: TODO 주석이 있는 부분 구현
   - `UnsafeCounter.java`
   - `SynchronizedCounter.java`
   - `AtomicCounter.java`
3. **테스트**: `CounterTest.java` 실행
4. **확인**: 모든 테스트 통과 확인

## 3. 테스트 결과 보는 법

### 성공 예시
```
=== 1. 단일 스레드 테스트 (각 1000번 증가) ===

UnsafeCounter: 1000 ✅
SynchronizedCounter: 1000 ✅
AtomicCounter: 1000 ✅

=== 2. 멀티스레드 테스트 (10개 스레드, 각 1000번 증가) ===

예상 결과: 10000

UnsafeCounter: 8742 ❌  ← race condition으로 일부 유실 (정상)
SynchronizedCounter: 10000 ✅
AtomicCounter: 10000 ✅
```

### UnsafeCounter가 10000이 안 나오는 이유
- 이건 **정상**입니다!
- Thread-unsafe하므로 race condition이 발생합니다
- 실행할 때마다 다른 값이 나올 수 있습니다 (8000~9900 정도)

## 4. 막혔을 때

### 컴파일 에러가 나면
- import 문 확인 (`import java.util.concurrent.atomic.AtomicInteger;`)
- 메서드 시그니처 확인 (Counter 인터페이스와 일치해야 함)
- 세미콜론, 중괄호 확인

### 로직을 모르겠으면
1. `~/claude-study/atomic-integer.md` 학습 자료 다시 읽기
2. `_Solution.md` 파일의 힌트 부분만 보기
3. AI에게 질문하기: "AtomicInteger의 incrementAndGet() 메서드가 뭐야?"

### 정답을 보고 싶으면
- `_Solution.md` 파일 열기 (하지만 먼저 스스로 풀어보세요!)

## 5. 코드 검증 요청

완성했다면 AI에게 검증을 요청하세요:

```
내 코드 확인해줘: AtomicCounter.java
```

또는

```
problem-01 풀었는데 코드 리뷰해줘
```

AI가 다음을 확인해줍니다:
- ✅ 정답 여부
- ✅ 코드 품질
- ✅ 개선 가능한 부분
- ✅ 추가 학습 포인트

## 6. IDE 사용하는 경우

### IntelliJ IDEA
1. 폴더를 프로젝트로 열기
2. CounterTest.java 우클릭 → Run 'CounterTest.main()'

### VS Code
1. Java Extension Pack 설치
2. CounterTest.java 열기
3. Run 버튼 클릭

### Eclipse
1. File → New → Java Project
2. 소스 파일 복사
3. CounterTest.java 우클릭 → Run As → Java Application
