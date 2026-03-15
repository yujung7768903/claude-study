import java.util.List;

/**
 * 온라인 쇼핑몰 상품 정보를 담는 클래스
 */
public class Product {
    private String name;
    private String category;
    private int price;
    private int stock;
    private List<String> tags;

    public Product(String name, String category, int price, int stock, List<String> tags) {
        this.name = name;
        this.category = category;
        this.price = price;
        this.stock = stock;
        this.tags = tags;
    }

    public String getName()         { return name; }
    public String getCategory()     { return category; }
    public int getPrice()           { return price; }
    public int getStock()           { return stock; }
    public List<String> getTags()   { return tags; }

    @Override
    public String toString() {
        return name + "(" + price + "원)";
    }
}
