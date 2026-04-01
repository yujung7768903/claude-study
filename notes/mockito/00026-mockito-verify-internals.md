# Mockito verify() 동작 원리와 에러 메시지 분석

## 개념 설명

### verify()가 하는 일

`verify()`는 테스트 실행 중 mock 객체에 기록된 **호출 이력(invocation log)** 을 조회하여,
지정한 조건과 맞는지 검사합니다.

```
실제 코드 실행 → mock 객체가 호출 이력 기록 → verify()가 이력 조회 → 조건 불일치 시 AssertionError
```

---

## verify() 검증 로직

### 내부 동작 순서

```
1. mock 객체 생성 시 → Mockito가 내부적으로 invocation list 준비
2. 실제 코드 실행 중 → mock 메서드가 호출될 때마다 invocation 기록
3. verify() 호출 시 → 기록된 invocation list에서 조건에 맞는 호출 검색
4. VerificationMode 조건 검사 → times(1)이면 정확히 1개 있어야 함
5. 조건 불일치 → WantedButNotInvoked 또는 관련 예외 발생
```

### 기록되는 정보

Mockito는 각 호출마다 다음 정보를 기록합니다:

- 어떤 mock 객체인지
- 어떤 메서드인지
- 전달된 인자(arguments)
- 호출 순서(call sequence number)

---

## 에러 유형별 분석

### 1. WantedButNotInvoked — 한 번도 호출 안 됨

```java
verify(emailService).sendWelcomeEmail(anyString(), anyString());
```

```
Wanted but not invoked:
→ emailService.sendWelcomeEmail(<any string>, <any string>);

However, there were other interactions with this mock:
→ emailService.sendWelcomeEmail("john@example.com", "john");
```

**발생 원인**: 메서드 자체가 호출되지 않았거나, argument matcher가 실제 인자와 불일치

---

### 2. TooManyActualInvocations — 너무 많이 호출됨

```java
verify(userRepository, times(1)).save(any(User.class));
// 실제로는 2번 호출된 경우
```

```
org.mockito.exceptions.verification.TooManyActualInvocations:
userRepository.save(<any>);
Wanted 1 time:
→ at UserServiceTest.사용자_생성_성공_테스트(UserServiceTest.java:42)
But was 2 times:
→ at UserService.createUser(UserService.java:16)
→ at UserService.createUser(UserService.java:22)
```

---

### 3. TooLittleActualInvocations — 너무 적게 호출됨

```java
verify(emailService, times(3)).sendWelcomeEmail(anyString(), anyString());
// 실제로는 1번만 호출된 경우
```

```
org.mockito.exceptions.verification.TooLittleActualInvocations:
emailService.sendWelcomeEmail(<any string>, <any string>);
Wanted 3 times:
→ at UserServiceTest...
But was 1 time:
→ at UserService.createUser(UserService.java:18)
```

---

### 4. NeverWantedButInvoked — never()인데 호출됨

```java
verify(eventPublisher, never()).publish(any());
// 실제로는 호출된 경우
```

```
org.mockito.exceptions.verification.NeverWantedButInvoked:
eventPublisher.publish(<any>);
Never wanted here:
→ at UserServiceTest...
But invoked here:
→ at UserService.createUser(UserService.java:19)
```

---

### 5. NoInteractionsWanted — 예상치 못한 호출

```java
verifyNoInteractions(emailService);
// 실제로는 호출된 경우
```

```
org.mockito.exceptions.verification.NoInteractionsWanted:
No interactions wanted here:
→ at UserServiceTest...
But found these interactions on mock 'emailService':
1. → emailService.sendWelcomeEmail("john@example.com", "john");
```

---

## 에러 메시지 비교표

| 상황 | 예외 클래스 | 핵심 메시지 |
|------|------------|------------|
| 한 번도 호출 안 됨 | `WantedButNotInvoked` | `Wanted but not invoked` |
| 기대보다 많이 호출 | `TooManyActualInvocations` | `Wanted N times: / But was M times:` |
| 기대보다 적게 호출 | `TooLittleActualInvocations` | `Wanted N times: / But was M times:` |
| never()인데 호출됨 | `NeverWantedButInvoked` | `Never wanted here: / But invoked here:` |
| 불필요한 호출 감지 | `NoInteractionsWanted` | `No interactions wanted here:` |
| 호출 순서 불일치 | `VerificationInOrderFailure` | `Verification in order failure` |

모든 예외는 `org.mockito.exceptions.verification` 패키지 하위에 있으며,
`AssertionError`의 하위 클래스입니다. → JUnit이 테스트 실패로 처리

---

## 에러 메시지 읽는 법

```
Wanted but not invoked:              ← 무엇을 기대했는지
→ emailService.sendWelcomeEmail(     ← 기대한 메서드
    <any string>,                    ← 기대한 인자 (Matcher)
    <any string>
);
→ at UserServiceTest.테스트명(UserServiceTest.java:58)  ← verify() 위치

However, there were other interactions with this mock:  ← 실제 발생한 일
→ emailService.send("hi");           ← 실제로 호출된 내용
```

---

## WantedButNotInvoked vs argument mismatch

verify()는 **메서드명 + 인자** 를 함께 비교합니다.
인자만 다른 경우도 `WantedButNotInvoked`가 발생하며, 실제 호출 내역을 함께 보여줍니다.

```java
// 실제 코드: emailService.sendWelcomeEmail("a@b.com", "john")
// 검증 코드:
verify(emailService).sendWelcomeEmail(eq("wrong@email.com"), anyString());
```

```
Wanted but not invoked:
→ emailService.sendWelcomeEmail("wrong@email.com", <any string>);

However, there were other interactions with this mock:
→ emailService.sendWelcomeEmail("a@b.com", "john");
   ↑ 실제로 이렇게 불렸다는 힌트를 줌
```

---

## 실무 권장사항

- 에러 메시지의 **"Wanted"와 "But was/invoked"** 를 비교하면 원인을 빠르게 파악 가능
- `WantedButNotInvoked`에서 `However, there were other interactions` 힌트를 꼭 확인할 것 — argument mismatch일 가능성이 높음
- `verifyNoMoreInteractions(mock)` 으로 예상치 못한 추가 호출을 방지할 수 있음
- `InOrder`를 사용하면 호출 순서까지 검증 가능 (`VerificationInOrderFailure` 발생)

```java
InOrder inOrder = inOrder(userRepository, emailService, eventPublisher);
inOrder.verify(userRepository).save(any(User.class));
inOrder.verify(emailService).sendWelcomeEmail(anyString(), anyString());
inOrder.verify(eventPublisher).publish(any(UserCreatedEvent.class));
```
