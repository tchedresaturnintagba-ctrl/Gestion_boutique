typedef JsonMap = Map<String, dynamic>;

class CurrentUser {
  const CurrentUser({
    required this.id,
    required this.organizationId,
    required this.email,
    required this.fullName,
    required this.role,
  });

  factory CurrentUser.fromJson(JsonMap json) => CurrentUser(
    id: json['id'] as String,
    organizationId: json['organization_id'] as String,
    email: json['email'] as String,
    fullName: json['full_name'] as String,
    role: json['role'] as String,
  );

  final String id;
  final String organizationId;
  final String email;
  final String fullName;
  final String role;
}

class Store {
  const Store({
    required this.id,
    required this.name,
    required this.code,
    required this.address,
    required this.isActive,
  });

  factory Store.fromJson(JsonMap json) => Store(
    id: json['id'] as String,
    name: json['name'] as String,
    code: json['code'] as String,
    address: json['address'] as String?,
    isActive: json['is_active'] as bool,
  );

  final String id;
  final String name;
  final String code;
  final String? address;
  final bool isActive;
}

class Product {
  const Product({
    required this.id,
    required this.name,
    required this.sku,
    required this.unit,
  });

  factory Product.fromJson(JsonMap json) => Product(
    id: json['id'] as String,
    name: json['name'] as String,
    sku: json['sku'] as String,
    unit: json['unit'] as String,
  );

  final String id;
  final String name;
  final String sku;
  final String unit;
}

class InventoryBalance {
  const InventoryBalance({
    required this.storeId,
    required this.productId,
    required this.quantity,
  });

  factory InventoryBalance.fromJson(JsonMap json) => InventoryBalance(
    storeId: json['store_id'] as String,
    productId: json['product_id'] as String,
    quantity: double.parse(json['quantity'].toString()),
  );

  final String storeId;
  final String productId;
  final double quantity;
}

class StockAlert {
  const StockAlert({
    required this.id,
    required this.storeId,
    required this.productId,
    required this.alertType,
    required this.observedQuantity,
    required this.threshold,
    required this.createdAt,
  });

  factory StockAlert.fromJson(JsonMap json) => StockAlert(
    id: json['id'] as String,
    storeId: json['store_id'] as String,
    productId: json['product_id'] as String,
    alertType: json['alert_type'] as String,
    observedQuantity: double.parse(json['observed_quantity'].toString()),
    threshold: double.parse(json['threshold'].toString()),
    createdAt: DateTime.parse(json['created_at'] as String),
  );

  final String id;
  final String storeId;
  final String productId;
  final String alertType;
  final double observedQuantity;
  final double threshold;
  final DateTime createdAt;
}

class SaleLine {
  const SaleLine({required this.quantity});

  factory SaleLine.fromJson(JsonMap json) =>
      SaleLine(quantity: double.parse(json['quantity'].toString()));

  final double quantity;
}

class Sale {
  const Sale({
    required this.id,
    required this.storeId,
    required this.totalAmount,
    required this.createdAt,
    required this.lines,
  });

  factory Sale.fromJson(JsonMap json) => Sale(
    id: json['id'] as String,
    storeId: json['store_id'] as String,
    totalAmount: double.parse(json['total_amount'].toString()),
    createdAt: DateTime.parse(json['created_at'] as String),
    lines: (json['lines'] as List<dynamic>)
        .map((item) => SaleLine.fromJson(item as JsonMap))
        .toList(),
  );

  final String id;
  final String storeId;
  final double totalAmount;
  final DateTime createdAt;
  final List<SaleLine> lines;
}

class DashboardSnapshot {
  const DashboardSnapshot({
    required this.user,
    required this.stores,
    required this.products,
    required this.balances,
    required this.alerts,
    required this.sales,
  });

  final CurrentUser user;
  final List<Store> stores;
  final List<Product> products;
  final List<InventoryBalance> balances;
  final List<StockAlert> alerts;
  final List<Sale> sales;
}
