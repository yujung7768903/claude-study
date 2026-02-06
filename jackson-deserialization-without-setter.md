# Jackson 역직렬화: Setter 없이도 가능한 이유

## 질문: @Getter와 @NoArgsConstructor만 있는데 어떻게 JSON이 파싱되나?

```java
@Getter  // Setter 없음!
@NoArgsConstructor
public class AmsTag {
    private String tagId;
    private String tag;
}
```

**답: Jackson이 Setter 없이도 필드에 직접 접근할 수 있기 때문입니다.**

---

## Jackson의 역직렬화(Deserialization) 과정

### 1. 기본 생성자로 객체 생성

```java
@NoArgsConstructor  // 기본 생성자 제공 (필수!)
public class AmsTag {
    private String tagId;
}
```

**Jackson이 하는 일:**
```java
AmsTag obj = new AmsTag();  // 기본 생성자 호출
```

---

### 2. 필드에 값 주입 (3가지 방법 시도)

Jackson은 다음 순서로 값을 주입합니다:

#### 방법 A: Setter 메서드 (우선순위 1)

```java
public class AmsTag {
    private String tagId;

    public void setTagId(String tagId) {  // Setter가 있으면 사용
        this.tagId = tagId;
    }
}
```

Jackson: `obj.setTagId("TAG001")`

---

#### 방법 B: 필드 직접 접근 (우선순위 2) ⭐

```java
@Getter  // Setter 없음!
@NoArgsConstructor
public class AmsTag {
    private String tagId;  // private 필드
}
```

**Jackson이 하는 일 (리플렉션):**
```java
Field field = AmsTag.class.getDeclaredField("tagId");
field.setAccessible(true);  // private 무시!
field.set(obj, "TAG001");   // 직접 값 주입
```

이게 가능한 이유:
- Java Reflection API는 private 필드에도 접근 가능
- `setAccessible(true)`로 접근 제한 우회
- Setter가 없어도 필드에 값을 넣을 수 있음

---

#### 방법 C: Creator 메서드 (우선순위 3)

```java
@JsonCreator
public AmsTag(@JsonProperty("tagId") String tagId) {
    this.tagId = tagId;
}
```

---

## 실제 동작 확인

### JSON 입력

```json
{
  "tagId": "TAG001",
  "tag": "경제"
}
```

### Java 클래스

```java
@Getter  // Setter 없음!
@NoArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class AmsTag {
    private String tagId;
    private String tag;
}
```

### Jackson의 역직렬화 과정

```java
// 1. 기본 생성자로 객체 생성
AmsTag obj = new AmsTag();

// 2. 리플렉션으로 필드에 직접 접근
Field tagIdField = AmsTag.class.getDeclaredField("tagId");
tagIdField.setAccessible(true);
tagIdField.set(obj, "TAG001");  // obj.tagId = "TAG001"

Field tagField = AmsTag.class.getDeclaredField("tag");
tagField.setAccessible(true);
tagField.set(obj, "경제");  // obj.tag = "경제"

// 3. 완성!
// obj.getTagId() → "TAG001"
// obj.getTag() → "경제"
```

---

## ObjectMapper 설정에 따른 동작

### 기본 설정 (Spring Boot 기본값)

```java
ObjectMapper mapper = new ObjectMapper();
// 기본적으로 필드 직접 접근 가능
```

**동작:**
- ✅ Setter 없어도 역직렬화 가능
- ✅ private 필드에 리플렉션으로 접근
- ✅ @NoArgsConstructor만 있으면 됨

---

### 필드 접근 비활성화 (거의 안 씀)

```java
ObjectMapper mapper = new ObjectMapper();
mapper.setVisibility(PropertyAccessor.FIELD, JsonAutoDetect.Visibility.NONE);
mapper.setVisibility(PropertyAccessor.SETTER, JsonAutoDetect.Visibility.PUBLIC_ONLY);
```

**동작:**
- ❌ Setter 없으면 역직렬화 실패
- ❌ 필드 직접 접근 불가

이 경우에만 @Setter가 필요합니다 (특수한 경우).

---

## 정리

### Setter 없이 역직렬화가 되는 이유

| 조건 | 설명 |
|------|------|
| ✅ @NoArgsConstructor | 기본 생성자 필수 |
| ✅ Jackson Reflection | private 필드에도 접근 가능 |
| ✅ Spring Boot 기본 설정 | 필드 접근 허용 |

### 각 어노테이션의 역할

```java
@Getter  // 역직렬화: 불필요, 읽기용
@Setter  // 역직렬화: 선택사항 (있으면 우선 사용)
@NoArgsConstructor  // 역직렬화: 필수!
@JsonIgnoreProperties(ignoreUnknown = true)  // JSON에 추가 필드 있어도 무시
```

---

## 실무 패턴

### 패턴 1: DTO (불변 객체)

```java
@Getter  // 읽기만 가능
@NoArgsConstructor  // Jackson용
@JsonIgnoreProperties(ignoreUnknown = true)
public class ResponseDto {
    private String id;
    private String name;
}
```

**장점:**
- 불변성 유지 (Setter 없음)
- Jackson이 리플렉션으로 값 주입
- 외부에서 값 변경 불가

---

### 패턴 2: Entity (JPA)

```java
@Entity
@Getter
@Setter  // JPA도 리플렉션 사용하지만, 편의상 Setter 추가
@NoArgsConstructor
public class User {
    @Id
    private Long id;
    private String name;
}
```

**이유:**
- JPA도 리플렉션으로 필드 접근 가능
- 하지만 코드에서 값 변경이 필요할 때를 위해 Setter 추가

---

## 디버깅 팁

역직렬화가 안 될 때 체크할 것:

1. **기본 생성자 있나?** (@NoArgsConstructor)
   ```
   No suitable constructor found for type
   ```

2. **필드명이 JSON 키와 일치하나?**
   ```json
   {"tagId": "TAG001"}  // JSON
   private String tagId;  // Java (대소문자까지 일치해야 함)
   ```

3. **ObjectMapper 설정이 기본값인가?**
   ```java
   // 커스텀 설정이 있는지 확인
   @Bean
   public ObjectMapper objectMapper() { ... }
   ```

4. **중첩 클래스인 경우 static인가?**
   ```java
   public static class TagItem { ... }  // static 필요!
   ```

---

## 핵심 요약

**@Getter만 있고 @Setter가 없어도 Jackson 역직렬화가 되는 이유:**

1. Jackson이 리플렉션으로 private 필드에 직접 접근
2. @NoArgsConstructor로 기본 생성자 제공
3. Spring Boot의 기본 ObjectMapper 설정이 필드 접근 허용
4. Setter는 선택사항 (있으면 우선 사용, 없으면 필드 직접 접근)

**필수 조건:**
- ✅ @NoArgsConstructor (또는 기본 생성자)
- ✅ 필드명 = JSON 키명 (대소문자 일치)
- ✅ 중첩 클래스는 static

**선택 사항:**
- @Setter (있으면 사용, 없으면 리플렉션)
- @JsonProperty (필드명과 JSON 키가 다를 때)
