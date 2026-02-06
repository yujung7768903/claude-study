/**
 * synchronized를 사용한 thread-safe 카운터
 */
public class SynchronizedCounter implements Counter {

    // TODO: int 필드 선언


    @Override
    public void increment() {
        // TODO: synchronized로 동기화하여 count를 1 증가

    }

    @Override
    public int getCount() {
        // TODO: synchronized로 동기화하여 현재 count 값 반환
        return 0;
    }

    @Override
    public void reset() {
        // TODO: synchronized로 동기화하여 count를 0으로 초기화

    }
}
