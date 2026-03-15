import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * 상품 데이터를 Stream API로 분석하는 인터페이스.
 * StreamAnalyzerImpl에서 구현하세요.
 */
public interface StreamAnalyzer {

    /**
     * minPrice 이상인 상품을 가격 내림차순으로 반환합니다.
     *
     * @param minPrice 최소 가격 (이상)
     * @return 조건을 만족하는 상품 목록
     */
    List<Product> getExpensiveProducts(int minPrice);

    /**
     * 특정 카테고리에 속한 상품명을 이름 오름차순으로 반환합니다.
     *
     * @param category 카테고리명
     * @return 상품명 목록
     */
    List<String> getProductNamesByCategory(String category);

    /**
     * 카테고리별 재고 수량 합계를 반환합니다.
     *
     * @return 카테고리 → 총 재고 수량
     */
    Map<String, Integer> getTotalStockByCategory();

    /**
     * 카테고리별 평균 가격을 반환합니다.
     *
     * @return 카테고리 → 평균 가격 (소수점 버림)
     */
    Map<String, Integer> getAveragePriceByCategory();

    /**
     * 가장 비싼 상품을 반환합니다. 상품이 없으면 empty Optional.
     *
     * @return 가장 비싼 상품 (Optional)
     */
    Optional<Product> getMostExpensiveProduct();

    /**
     * 카테고리별 상품 수를 반환합니다.
     *
     * @return 카테고리 → 상품 수
     */
    Map<String, Long> getProductCountByCategory();

    /**
     * 전체 상품에 등록된 모든 태그를 중복 제거 후 알파벳/가나다 오름차순으로 반환합니다.
     *
     * @return 정렬된 태그 목록 (중복 없음)
     */
    List<String> getAllTags();

    /**
     * 가격 기준 상위 n개 상품의 이름을 반환합니다.
     *
     * @param n 가져올 상품 수
     * @return 가격 내림차순 상위 n개 상품명
     */
    List<String> getTopNByPrice(int n);

    /**
     * 재고가 0인 상품이 하나라도 있으면 true를 반환합니다.
     *
     * @return 품절 상품 존재 여부
     */
    boolean hasOutOfStockProduct();

    /**
     * 모든 상품의 (가격 × 재고)를 합산한 총 판매 가능 금액을 반환합니다.
     *
     * @return 전체 판매 가능 금액
     */
    long getTotalRevenuePotential();
}
