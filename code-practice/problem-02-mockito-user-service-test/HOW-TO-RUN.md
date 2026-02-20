# 실행 방법

## 1. 컴파일 및 실행

### Windows (현재 환경)

#### 준비사항
먼저 JUnit 4와 Mockito 라이브러리가 필요합니다:
- junit-4.13.2.jar
- mockito-core-4.0.0.jar (hamcrest, byte-buddy 등 의존성 포함)

```bash
cd C:\Users\D4006124\claude-study\code-practice\problem-02-mockito-user-service-test

# 컴파일
javac -cp ".;junit-4.13.2.jar;mockito-core-4.0.0.jar" *.java

# 실행
java -cp ".;junit-4.13.2.jar;mockito-core-4.0.0.jar;hamcrest-core-1.3.jar;byte-buddy-1.12.0.jar" org.junit.runner.JUnitCore UserServiceTest
```

### Linux/Mac
```bash
cd ~/claude-study/code-practice/problem-02-mockito-user-service-test

# 컴파일
javac -cp ".:junit-4.13.2.jar:mockito-core-4.0.0.jar" *.java

# 실행
java -cp ".:junit-4.13.2.jar:mockito-core-4.0.0.jar:hamcrest-core-1.3.jar:byte-buddy-1.12.0.jar" org.junit.runner.JUnitCore UserServiceTest
```

## 2. Maven 사용 (권장)

프로젝트 루트에 `pom.xml` 생성:

```xml
<dependencies>
    <dependency>
        <groupId>junit</groupId>
        <artifactId>junit</artifactId>
        <version>4.13.2</version>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.mockito</groupId>
        <artifactId>mockito-core</artifactId>
        <version>4.0.0</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

실행:
```bash
mvn test -Dtest=UserServiceTest
```

## 3. Gradle 사용

`build.gradle`:

```groovy
dependencies {
    testImplementation 'junit:junit:4.13.2'
    testImplementation 'org.mockito:mockito-core:4.0.0'
}
```

실행:
```bash
gradle test --tests UserServiceTest
```

## 4. 작업 순서

1. **문제 읽기**: `Problem.md` 파일 읽기
2. **TODO 확인**: `UserServiceTest.java`의 TODO 주석 부분 확인
3. **구현하기**:
   - `@Mock`, `@InjectMocks` 어노테이션 추가
   - `사용자_생성_성공_테스트()` 메서드 구현
   - `사용자_생성시_올바른_이메일_파라미터_전달_확인()` 메서드 구현
   - `사용자_생성시_이벤트에_올바른_사용자_정보_포함_확인()` 메서드 구현
4. **테스트 실행**: 위 명령어로 테스트 실행
5. **확인**: 모든 테스트가 통과하는지 확인

## 5. 테스트 결과 보는 법

### 성공 예시
```
JUnit version 4.13.2
...
Time: 0.123

OK (3 tests)
```

### 실패 예시
```
There was 1 failure:
1) 사용자_생성_성공_테스트(UserServiceTest)
org.mockito.exceptions.verification.WantedButNotInvoked:
Wanted but not invoked:
userRepository.save(
    <any>
);
```

## 6. 막혔을 때

### ArgumentCaptor를 모르겠으면
- `~/claude-study/20260205-mockito-argument-captor.md` 학습 자료 참고
- `ArgumentCaptor<String> captor = ArgumentCaptor.forClass(String.class);`
- `verify(service).method(captor.capture());`
- `String value = captor.getValue();`

### Matcher 혼용 에러가 나면
```
Invalid use of argument matchers!
```
- 모든 파라미터를 Matcher로 감싸거나, 모두 Raw Value로 사용
- Raw Value를 Matcher와 함께 쓰려면 `eq(value)` 사용
- `~/claude-study/20260210-mockito-unit-testing-guide.md` 참고

### import 에러가 나면
```java
import org.junit.Test;
import org.junit.runner.RunWith;
import org.mockito.Mock;
import org.mockito.InjectMocks;
import org.mockito.ArgumentCaptor;
import org.mockito.junit.MockitoJUnitRunner;
import static org.mockito.Mockito.*;
import static org.mockito.ArgumentMatchers.*;
import static org.junit.Assert.*;
```

### 정답을 보고 싶으면
- `_Solution.md` 파일 열기
- 하지만 먼저 30분은 스스로 고민해보세요!

## 7. 코드 검증 요청

완성했다면 AI에게 검증을 요청하세요:

```
내 코드 확인해줘: UserServiceTest.java
```

또는

```
problem-02 풀었는데 코드 리뷰해줘
```

AI가 다음을 확인해줍니다:
- ✅ 정답 여부
- ✅ 코드 품질
- ✅ Mockito 사용법이 올바른지
- ✅ 개선 가능한 부분
- ✅ 추가 학습 포인트

## 8. IDE 사용하는 경우

### IntelliJ IDEA
1. 폴더를 프로젝트로 열기
2. File → Project Structure → Libraries에서 JUnit, Mockito 추가
3. UserServiceTest.java 우클릭 → Run 'UserServiceTest'

### VS Code
1. Java Extension Pack 설치
2. Maven for Java 또는 Gradle for Java 설치
3. `pom.xml` 또는 `build.gradle` 생성
4. Test 아이콘 클릭하여 실행

### Eclipse
1. File → New → Java Project
2. 소스 파일 복사
3. Build Path에서 JUnit 4, Mockito 라이브러리 추가
4. UserServiceTest.java 우클릭 → Run As → JUnit Test

## 9. 자주 발생하는 에러

### 1. "Wanted but not invoked"
```
Wanted but not invoked:
userRepository.save(<any>);
```
→ `userService.createUser()`를 호출했는지 확인

### 2. "Invalid use of argument matchers"
```
Invalid use of argument matchers!
3 matchers expected, 2 recorded.
```
→ 모든 파라미터를 Matcher로 감싸거나, `eq()` 사용

### 3. "NullPointerException"
```
java.lang.NullPointerException
    at UserService.createUser
```
→ `@Mock`과 `@InjectMocks`가 제대로 설정되었는지 확인
→ `@RunWith(MockitoJUnitRunner.class)` 있는지 확인

### 4. "No tests found"
```
No tests found matching...
```
→ 메서드에 `@Test` 어노테이션 붙였는지 확인
→ 메서드가 `public`인지 확인
