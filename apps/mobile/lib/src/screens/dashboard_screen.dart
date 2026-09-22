import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../api/api_client.dart';
import '../models/models.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({
    super.key,
    required this.initialSnapshot,
    required this.apiClient,
    required this.onLogout,
  });

  final DashboardSnapshot initialSnapshot;
  final ApiClient apiClient;
  final Future<void> Function() onLogout;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late DashboardSnapshot _snapshot = widget.initialSnapshot;
  String? _selectedStoreId;
  int _pageIndex = 0;
  bool _refreshing = false;

  static final _money = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: 'F CFA',
    decimalDigits: 0,
  );
  static final _number = NumberFormat.decimalPattern('fr_FR');
  static final _date = DateFormat('dd/MM, HH:mm');

  bool _matchesStore(String storeId) =>
      _selectedStoreId == null || storeId == _selectedStoreId;

  Future<void> _refresh() async {
    if (_refreshing) return;
    setState(() => _refreshing = true);
    try {
      final snapshot = await widget.apiClient.loadDashboard();
      if (mounted) {
        setState(() {
          _snapshot = snapshot;
          if (_selectedStoreId != null &&
              !snapshot.stores.any((store) => store.id == _selectedStoreId)) {
            _selectedStoreId = null;
          }
        });
      }
    } on ApiException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(error.message)));
      }
    } finally {
      if (mounted) setState(() => _refreshing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final balances = _snapshot.balances
        .where((balance) => _matchesStore(balance.storeId))
        .toList();
    final alerts = _snapshot.alerts
        .where((alert) => _matchesStore(alert.storeId))
        .toList();
    final sales = _snapshot.sales
        .where((sale) => _matchesStore(sale.storeId))
        .toList();
    final stores = _snapshot.stores
        .where((store) => _matchesStore(store.id))
        .toList();
    final pages = [
      _OverviewPage(
        snapshot: _snapshot,
        stores: stores,
        balances: balances,
        alerts: alerts,
        sales: sales,
        money: _money,
        number: _number,
      ),
      _StockPage(snapshot: _snapshot, balances: balances, number: _number),
      _AlertsPage(
        snapshot: _snapshot,
        alerts: alerts,
        number: _number,
        date: _date,
      ),
      _SalesPage(
        snapshot: _snapshot,
        sales: sales,
        money: _money,
        number: _number,
        date: _date,
      ),
    ];

    return Scaffold(
      appBar: AppBar(
        titleSpacing: 18,
        title: const Row(
          children: [
            Icon(
              Icons.shopping_bag_outlined,
              color: Color(0xff63d3a4),
              size: 23,
            ),
            SizedBox(width: 9),
            Text('KërManager'),
          ],
        ),
        actions: [
          IconButton(
            onPressed: _refreshing ? null : _refresh,
            tooltip: 'Actualiser',
            icon: _refreshing
                ? const SizedBox.square(
                    dimension: 19,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Color(0xff63d3a4),
                    ),
                  )
                : const Icon(Icons.refresh),
          ),
          IconButton(
            onPressed: widget.onLogout,
            tooltip: 'Se déconnecter',
            icon: const Icon(Icons.logout),
          ),
          const SizedBox(width: 6),
        ],
      ),
      body: Column(
        children: [
          _StoreFilter(
            stores: _snapshot.stores,
            selectedStoreId: _selectedStoreId,
            onChanged: (value) => setState(() => _selectedStoreId = value),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _refresh,
              child: KeyedSubtree(
                key: ValueKey('$_pageIndex-$_selectedStoreId'),
                child: pages[_pageIndex],
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _pageIndex,
        onDestinationSelected: (index) => setState(() => _pageIndex = index),
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.space_dashboard_outlined),
            selectedIcon: Icon(Icons.space_dashboard),
            label: 'Synthèse',
          ),
          NavigationDestination(
            icon: Icon(Icons.inventory_2_outlined),
            selectedIcon: Icon(Icons.inventory_2),
            label: 'Stock',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_none),
            selectedIcon: Icon(Icons.notifications),
            label: 'Alertes',
          ),
          NavigationDestination(
            icon: Icon(Icons.receipt_long_outlined),
            selectedIcon: Icon(Icons.receipt_long),
            label: 'Ventes',
          ),
        ],
      ),
    );
  }
}

class _StoreFilter extends StatelessWidget {
  const _StoreFilter({
    required this.stores,
    required this.selectedStoreId,
    required this.onChanged,
  });

  final List<Store> stores;
  final String? selectedStoreId;
  final ValueChanged<String?> onChanged;

  @override
  Widget build(BuildContext context) => Container(
    color: Colors.white,
    padding: const EdgeInsets.fromLTRB(16, 12, 16, 13),
    child: DropdownButtonFormField<String?>(
      value: selectedStoreId,
      isExpanded: true,
      decoration: const InputDecoration(
        labelText: 'Boutique affichée',
        prefixIcon: Icon(Icons.storefront_outlined),
        isDense: true,
      ),
      items: [
        const DropdownMenuItem<String?>(
          value: null,
          child: Text('Toutes mes boutiques'),
        ),
        ...stores.map(
          (store) => DropdownMenuItem<String?>(
            value: store.id,
            child: Text(store.name),
          ),
        ),
      ],
      onChanged: onChanged,
    ),
  );
}

class _OverviewPage extends StatelessWidget {
  const _OverviewPage({
    required this.snapshot,
    required this.stores,
    required this.balances,
    required this.alerts,
    required this.sales,
    required this.money,
    required this.number,
  });

  final DashboardSnapshot snapshot;
  final List<Store> stores;
  final List<InventoryBalance> balances;
  final List<StockAlert> alerts;
  final List<Sale> sales;
  final NumberFormat money;
  final NumberFormat number;

  @override
  Widget build(BuildContext context) {
    final totalStock = balances.fold<double>(
      0,
      (sum, balance) => sum + balance.quantity,
    );
    final revenue = sales.fold<double>(
      0,
      (sum, sale) => sum + sale.totalAmount,
    );
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 22, 16, 28),
      children: [
        Text(
          'Bonjour ${snapshot.user.fullName.split(' ').first},',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.w800,
            color: const Color(0xff16352f),
          ),
        ),
        const SizedBox(height: 5),
        Text(
          'Voici la situation de vos boutiques.',
          style: Theme.of(
            context,
          ).textTheme.bodySmall?.copyWith(color: const Color(0xff71807c)),
        ),
        const SizedBox(height: 22),
        GridView.count(
          crossAxisCount: 2,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisSpacing: 10,
          mainAxisSpacing: 10,
          childAspectRatio: 1.18,
          children: [
            _MetricTile(
              label: 'Boutiques',
              value: '${stores.where((store) => store.isActive).length}',
              icon: Icons.storefront_outlined,
              tone: const Color(0xff178565),
            ),
            _MetricTile(
              label: 'Unités en stock',
              value: number.format(totalStock),
              icon: Icons.inventory_2_outlined,
              tone: const Color(0xff39738d),
            ),
            _MetricTile(
              label: 'Alertes ouvertes',
              value: '${alerts.length}',
              icon: Icons.notifications_active_outlined,
              tone: const Color(0xffb0781f),
            ),
            _MetricTile(
              label: 'Chiffre d’affaires',
              value: money.format(revenue),
              icon: Icons.payments_outlined,
              tone: const Color(0xff536661),
            ),
          ],
        ),
        const SizedBox(height: 24),
        const _SectionTitle(
          title: 'Mes boutiques',
          subtitle: 'Accès et état opérationnel',
        ),
        const SizedBox(height: 10),
        if (stores.isEmpty)
          const _EmptyState(
            icon: Icons.storefront_outlined,
            message: 'Aucune boutique ne vous est encore attribuée.',
          )
        else
          ...stores.map((store) {
            final stock = balances
                .where((balance) => balance.storeId == store.id)
                .fold<double>(0, (sum, balance) => sum + balance.quantity);
            final alertCount = alerts
                .where((alert) => alert.storeId == store.id)
                .length;
            final initials = store.code.length > 2
                ? store.code.substring(0, 2)
                : store.code;
            return Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: const Color(0xffe4f3ee),
                    foregroundColor: const Color(0xff178565),
                    child: Text(initials),
                  ),
                  title: Text(
                    store.name,
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    '${number.format(stock)} unités · $alertCount alerte${alertCount > 1 ? 's' : ''}',
                  ),
                  trailing: _StatusChip(active: store.isActive),
                ),
              ),
            );
          }),
      ],
    );
  }
}

class _StockPage extends StatelessWidget {
  const _StockPage({
    required this.snapshot,
    required this.balances,
    required this.number,
  });

  final DashboardSnapshot snapshot;
  final List<InventoryBalance> balances;
  final NumberFormat number;

  @override
  Widget build(BuildContext context) {
    final products = {
      for (final product in snapshot.products) product.id: product,
    };
    final stores = {for (final store in snapshot.stores) store.id: store};
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 22, 16, 28),
      children: [
        const _SectionTitle(
          title: 'Stock disponible',
          subtitle: 'Soldes actuels par produit et boutique',
        ),
        const SizedBox(height: 14),
        if (balances.isEmpty)
          const _EmptyState(
            icon: Icons.inventory_2_outlined,
            message: 'Aucun solde de stock dans cette vue.',
          )
        else
          ...balances.map((balance) {
            final product = products[balance.productId];
            return Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Card(
                child: ListTile(
                  leading: const CircleAvatar(
                    backgroundColor: Color(0xffe7f0f5),
                    foregroundColor: Color(0xff39738d),
                    child: Icon(Icons.inventory_2_outlined),
                  ),
                  title: Text(
                    product?.name ?? 'Produit inconnu',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    '${stores[balance.storeId]?.name ?? 'Boutique'} · ${product?.sku ?? ''}',
                  ),
                  trailing: Text(
                    number.format(balance.quantity),
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w800,
                      color: const Color(0xff183b34),
                    ),
                  ),
                ),
              ),
            );
          }),
      ],
    );
  }
}

class _AlertsPage extends StatelessWidget {
  const _AlertsPage({
    required this.snapshot,
    required this.alerts,
    required this.number,
    required this.date,
  });

  final DashboardSnapshot snapshot;
  final List<StockAlert> alerts;
  final NumberFormat number;
  final DateFormat date;

  @override
  Widget build(BuildContext context) {
    final products = {
      for (final product in snapshot.products) product.id: product,
    };
    final stores = {for (final store in snapshot.stores) store.id: store};
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 22, 16, 28),
      children: [
        const _SectionTitle(
          title: 'Alertes ouvertes',
          subtitle: 'Produits qui demandent votre attention',
        ),
        const SizedBox(height: 14),
        if (alerts.isEmpty)
          const _EmptyState(
            icon: Icons.check_circle_outline,
            message: 'Aucune alerte ouverte dans cette vue.',
          )
        else
          ...alerts.map((alert) {
            final critical = alert.alertType == 'out_of_stock';
            return Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Card(
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: critical
                        ? const Color(0xfffae8e6)
                        : const Color(0xfffbf0dc),
                    foregroundColor: critical
                        ? const Color(0xffb34840)
                        : const Color(0xffa56c1c),
                    child: Icon(
                      critical ? Icons.error_outline : Icons.warning_amber,
                    ),
                  ),
                  title: Text(
                    products[alert.productId]?.name ?? 'Produit inconnu',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    '${stores[alert.storeId]?.name ?? 'Boutique'} · ${date.format(alert.createdAt.toLocal())}',
                  ),
                  trailing: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text(
                        critical ? 'Rupture' : 'Stock faible',
                        style: TextStyle(
                          fontWeight: FontWeight.w800,
                          color: critical
                              ? const Color(0xffb34840)
                              : const Color(0xff9a6a1e),
                        ),
                      ),
                      Text(
                        '${number.format(alert.observedQuantity)} / ${number.format(alert.threshold)}',
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ],
                  ),
                ),
              ),
            );
          }),
      ],
    );
  }
}

class _SalesPage extends StatelessWidget {
  const _SalesPage({
    required this.snapshot,
    required this.sales,
    required this.money,
    required this.number,
    required this.date,
  });

  final DashboardSnapshot snapshot;
  final List<Sale> sales;
  final NumberFormat money;
  final NumberFormat number;
  final DateFormat date;

  @override
  Widget build(BuildContext context) {
    final stores = {for (final store in snapshot.stores) store.id: store};
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.fromLTRB(16, 22, 16, 28),
      children: [
        const _SectionTitle(
          title: 'Ventes récentes',
          subtitle: 'Transactions de vos boutiques accessibles',
        ),
        const SizedBox(height: 14),
        if (sales.isEmpty)
          const _EmptyState(
            icon: Icons.receipt_long_outlined,
            message: 'Aucune vente dans cette vue.',
          )
        else
          ...sales.map((sale) {
            final quantity = sale.lines.fold<double>(
              0,
              (sum, line) => sum + line.quantity,
            );
            return Padding(
              padding: const EdgeInsets.only(bottom: 9),
              child: Card(
                child: ListTile(
                  leading: const CircleAvatar(
                    backgroundColor: Color(0xffe4f3ee),
                    foregroundColor: Color(0xff178565),
                    child: Icon(Icons.receipt_long_outlined),
                  ),
                  title: Text(
                    '#${sale.id.substring(0, 8).toUpperCase()}',
                    style: const TextStyle(fontWeight: FontWeight.w700),
                  ),
                  subtitle: Text(
                    '${stores[sale.storeId]?.name ?? 'Boutique'} · ${date.format(sale.createdAt.toLocal())}\n${number.format(quantity)} article${quantity > 1 ? 's' : ''}',
                  ),
                  isThreeLine: true,
                  trailing: Text(
                    money.format(sale.totalAmount),
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      color: Color(0xff183b34),
                    ),
                  ),
                ),
              ),
            );
          }),
      ],
    );
  }
}

class _MetricTile extends StatelessWidget {
  const _MetricTile({
    required this.label,
    required this.value,
    required this.icon,
    required this.tone,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color tone;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(15),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: tone, size: 23),
          const Spacer(),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              value,
              maxLines: 1,
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.w800,
                color: const Color(0xff183b34),
              ),
            ),
          ),
          const SizedBox(height: 3),
          Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(
              context,
            ).textTheme.labelSmall?.copyWith(color: const Color(0xff687974)),
          ),
        ],
      ),
    ),
  );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.title, required this.subtitle});

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(
        title,
        style: Theme.of(context).textTheme.titleMedium?.copyWith(
          fontWeight: FontWeight.w800,
          color: const Color(0xff203c36),
        ),
      ),
      const SizedBox(height: 3),
      Text(
        subtitle,
        style: Theme.of(
          context,
        ).textTheme.bodySmall?.copyWith(color: const Color(0xff82918d)),
      ),
    ],
  );
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({required this.active});

  final bool active;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
    decoration: BoxDecoration(
      color: active ? const Color(0xffe5f5ef) : const Color(0xffedf1ef),
      borderRadius: BorderRadius.circular(4),
    ),
    child: Text(
      active ? 'Active' : 'Suspendue',
      style: TextStyle(
        fontSize: 10,
        fontWeight: FontWeight.w800,
        color: active ? const Color(0xff237b60) : const Color(0xff687974),
      ),
    ),
  );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 42),
      child: Center(
        child: Column(
          children: [
            Icon(icon, size: 30, color: const Color(0xff91a09c)),
            const SizedBox(height: 10),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: const Color(0xff71807c)),
            ),
          ],
        ),
      ),
    ),
  );
}
