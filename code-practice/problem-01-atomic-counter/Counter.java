public interface Counter {
    /**
     * 카운터를 1 증가시킵니다.
     */
    void increment();

    /**
     * 현재 카운터 값을 반환합니다.
     * @return 현재 카운터 값
     */
    int getCount();

    /**
     * 카운터를 0으로 초기화합니다.
     */
    void reset();
}
