# 소프트웨어 설계 원칙

## 1. SOLID 원칙

객체지향 설계의 5가지 핵심 원칙.

### SRP (Single Responsibility Principle) - 단일 책임 원칙
클래스는 하나의 책임만 가져야 한다.

```java
// 나쁜 예 - 여러 책임이 섞여 있음
class UserService {
    void saveUser(User user) { ... }
    void sendEmail(User user) { ... }  // 이메일 전송은 다른 책임
    String formatUserName(User user) { ... }  // 포맷팅도 다른 책임
}

// 좋은 예
class UserService {
    void saveUser(User user) { ... }
}
class EmailService {
    void sendEmail(User user) { ... }
}
```

### OCP (Open/Closed Principle) - 개방/폐쇄 원칙
확장에는 열려 있고, 수정에는 닫혀 있어야 한다.

```java
// 나쁜 예 - 새 할인 정책 추가 시 기존 코드 수정 필요
class DiscountService {
    double discount(String type, double price) {
        if (type.equals("VIP")) return price * 0.8;
        if (type.equals("MEMBER")) return price * 0.9;
        return price;
    }
}

// 좋은 예 - 새 정책은 구현체만 추가
interface DiscountPolicy {
    double apply(double price);
}
class VipDiscountPolicy implements DiscountPolicy {
    public double apply(double price) { return price * 0.8; }
}
class MemberDiscountPolicy implements DiscountPolicy {
    public double apply(double price) { return price * 0.9; }
}
```

### LSP (Liskov Substitution Principle) - 리스코프 치환 원칙
자식 클래스는 부모 클래스를 대체할 수 있어야 한다.

```java
// 위반 예 - 정사각형은 직사각형을 대체할 수 없음
class Rectangle {
    void setWidth(int w) { this.width = w; }
    void setHeight(int h) { this.height = h; }
}
class Square extends Rectangle {
    void setWidth(int w) { this.width = w; this.height = w; }  // 높이도 바꿔버림
}
```

### ISP (Interface Segregation Principle) - 인터페이스 분리 원칙
클라이언트가 사용하지 않는 메서드에 의존하지 않도록 인터페이스를 분리한다.

```java
// 나쁜 예
interface Animal {
    void eat();
    void fly();  // 모든 동물이 날 수 있는 건 아님
    void swim();
}

// 좋은 예
interface Eatable { void eat(); }
interface Flyable { void fly(); }
interface Swimmable { void swim(); }

class Duck implements Eatable, Flyable, Swimmable { ... }
class Dog implements Eatable, Swimmable { ... }
```

### DIP (Dependency Inversion Principle) - 의존관계 역전 원칙
고수준 모듈이 저수준 모듈에 의존하지 않고, 둘 다 추상화에 의존해야 한다.

```java
// 나쁜 예 - 구체 클래스에 직접 의존
class OrderService {
    private MySQLOrderRepository repository = new MySQLOrderRepository();
}

// 좋은 예 - 인터페이스에 의존
class OrderService {
    private final OrderRepository repository;  // 인터페이스
    public OrderService(OrderRepository repository) {
        this.repository = repository;
    }
}
```

---

## 2. Law of Demeter (디미터 법칙) - 최소 지식 원칙

객체는 직접 아는 객체하고만 대화해야 한다. "낯선 사람과 대화하지 말라."

메서드 체이닝이 길어질수록 위반 가능성이 높다.

```java
// 위반 - 깊은 체이닝으로 내부 구조에 의존
double price = order.getCustomer().getMembership().getDiscount().getRate();

// 준수 - 필요한 정보를 직접 제공
double price = order.getDiscountRate();  // Order가 내부적으로 처리
```

---

## 3. PSA (Portable Service Abstraction) - 일관된 서비스 추상화

Spring의 핵심 개념. 환경이나 기술이 바뀌어도 동일한 방식으로 사용할 수 있도록 추상화 계층을 제공한다.

```java
// @Transactional - 기술(JDBC, JPA, JTA)이 달라도 동일하게 사용
@Transactional
public void transfer(long fromId, long toId, int amount) { ... }

// @Cacheable - Redis, EhCache 등 구현체가 달라도 동일하게 사용
@Cacheable("users")
public User getUser(long id) { ... }
```

---

## 4. DRY (Don't Repeat Yourself)

중복을 제거하라. 같은 지식은 단 한 곳에만 존재해야 한다.

```java
// 나쁜 예
double calcCircleArea(double r) { return 3.14159 * r * r; }
double calcCirclePerimeter(double r) { return 2 * 3.14159 * r; }

// 좋은 예
static final double PI = 3.14159;
double calcCircleArea(double r) { return PI * r * r; }
double calcCirclePerimeter(double r) { return 2 * PI * r; }
```

---

## 5. KISS (Keep It Simple, Stupid)

단순하게 유지하라. 불필요한 복잡성을 피하라.

> 코드는 작성할 때보다 읽힐 때가 훨씬 많다.

---

## 6. YAGNI (You Aren't Gonna Need It)

지금 필요하지 않은 기능은 만들지 마라. 미래를 위한 과도한 설계를 경계한다.

```java
// 나쁜 예 - 아직 필요 없는 기능까지 미리 만듦
class UserService {
    void saveUser() { ... }
    void exportUserToCsv() { ... }       // 아직 요구사항 없음
    void syncUserToLdap() { ... }        // 아직 요구사항 없음
    void generateUserReport() { ... }    // 아직 요구사항 없음
}
```

---

## 7. Tell, Don't Ask

객체에게 상태를 물어보고 외부에서 판단하지 말고, 객체 스스로 판단하게 하라.

```java
// 나쁜 예 - 외부에서 상태를 꺼내 판단
if (user.getAge() >= 18) {
    user.setAdult(true);
}

// 좋은 예 - 객체 스스로 판단
user.checkAdult();  // User 내부에서 나이 판단
```

---

## 요약 비교

| 원칙 | 핵심 질문 |
|---|---|
| SRP | 이 클래스가 바뀌어야 할 이유가 하나뿐인가? |
| OCP | 새 기능 추가 시 기존 코드를 수정하는가? |
| LSP | 자식이 부모를 완전히 대체할 수 있는가? |
| ISP | 구현체가 불필요한 메서드를 강요받는가? |
| DIP | 구체 클래스가 아닌 추상화에 의존하는가? |
| 디미터 | 메서드 체이닝이 과도하게 길지 않은가? |
| PSA | 기술이 바뀌어도 코드가 그대로인가? |
| DRY | 같은 로직이 두 곳 이상에 있지 않은가? |
| YAGNI | 지금 당장 필요한 기능만 만들었는가? |
| Tell, Don't Ask | 객체 상태를 꺼내서 외부에서 판단하지 않는가? |

## 실무 권장사항

- SOLID는 원칙이지 규칙이 아니다. 지나친 추상화는 오히려 복잡성을 높인다.
- YAGNI와 OCP는 충돌한다. 지금 당장 필요 없으면 만들지 말되, 확장 가능한 구조는 유지한다.
- 디미터 법칙은 DTO나 데이터 클래스에는 엄격하게 적용하지 않아도 된다.
- Tell, Don't Ask는 도메인 로직에서 특히 중요하다.
