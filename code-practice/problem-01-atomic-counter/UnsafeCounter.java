/**
 * Thread-unsafe한 카운터 (비교용)
 * 멀티스레드 환경에서 race condition이 발생합니다.
 */
public class UnsafeCounter implements Counter {

    // TODO: int 필드 선언


    @Override
    public void increment() {
        // TODO: count를 1 증가

    }

    @Override
    public int getCount() {
        // TODO: 현재 count 값 반환
        return 0;
    }

    @Override
    public void reset() {
        // TODO: count를 0으로 초기화

    }
}
