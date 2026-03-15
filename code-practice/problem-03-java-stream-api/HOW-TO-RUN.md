# 실행 방법

## 작업 순서

1. `StreamAnalyzerImpl.java`를 열어 `// TODO:` 주석을 찾습니다.
2. 각 메서드를 Stream API로 구현합니다.
3. 컴파일 후 테스트를 실행하여 결과를 확인합니다.

---

## 컴파일 & 실행

### Linux / macOS

```bash
# 이 디렉토리로 이동
cd ~/claude-study/code-practice/problem-03-java-stream-api

# 전체 컴파일
javac Product.java StreamAnalyzer.java StreamAnalyzerImpl.java StreamAnalyzerTest.java

# 테스트 실행
java StreamAnalyzerTest
```

### Windows

```cmd
cd %USERPROFILE%\claude-study\code-practice\problem-03-java-stream-api

javac Product.java StreamAnalyzer.java StreamAnalyzerImpl.java StreamAnalyzerTest.java

java StreamAnalyzerTest
```

---

## 테스트 결과 보는 법

```
✅ 전자제품 상품 수       ← 통과
❌ 의류 평균가격 (실패)   ← 실패 → 해당 메서드 로직 재확인
```

마지막 줄에서 몇 개 통과했는지 요약됩니다:

```
========================================
결과: 27개 통과 / 0개 실패
✅ 모든 테스트 통과!
```

---

## 막혔을 때

- `Problem.md`의 **힌트** 섹션을 참고하세요.
- 정답을 보려면 `_Solution.md`를 열어보세요.
- Java Stream API 공식 문서: `java.util.stream.Collectors` / `java.util.stream.Stream`

---

## IDE 사용법

### IntelliJ IDEA
1. `File → Open` → 이 디렉토리 선택
2. `StreamAnalyzerImpl.java` 열기
3. `StreamAnalyzerTest.java` 열고 `main` 메서드 왼쪽 ▶ 클릭

### VS Code
1. Extension: "Extension Pack for Java" 설치
2. 폴더 열기 후 `StreamAnalyzerTest.java`에서 `Run` 클릭

### Eclipse
1. `File → New → Java Project` 생성
2. `src` 폴더에 파일들을 붙여넣기
3. `StreamAnalyzerTest.java` 우클릭 → `Run As → Java Application`
