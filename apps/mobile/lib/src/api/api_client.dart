import 'dart:async';
import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../models/models.dart';

class ApiException implements Exception {
  const ApiException(this.message, this.statusCode);

  final String message;
  final int statusCode;

  @override
  String toString() => message;
}

abstract interface class TokenStorage {
  Future<String?> readAccessToken();
  Future<String?> readRefreshToken();
  Future<void> saveTokens(String accessToken, String refreshToken);
  Future<void> clear();
}

class SecureTokenStorage implements TokenStorage {
  const SecureTokenStorage();

  static const _storage = FlutterSecureStorage();
  static const _accessTokenKey = 'ker-manager-access-token';
  static const _refreshTokenKey = 'ker-manager-refresh-token';

  @override
  Future<String?> readAccessToken() => _storage.read(key: _accessTokenKey);

  @override
  Future<String?> readRefreshToken() => _storage.read(key: _refreshTokenKey);

  @override
  Future<void> saveTokens(String accessToken, String refreshToken) async {
    await _storage.write(key: _accessTokenKey, value: accessToken);
    await _storage.write(key: _refreshTokenKey, value: refreshToken);
  }

  @override
  Future<void> clear() => _storage.deleteAll();
}

class ApiClient {
  ApiClient({
    http.Client? httpClient,
    TokenStorage tokenStorage = const SecureTokenStorage(),
    String? baseUrl,
  }) : _httpClient = httpClient ?? http.Client(),
       _tokenStorage = tokenStorage,
       _baseUrl = (baseUrl ?? _configuredBaseUrl).replaceFirst(
         RegExp(r'/$'),
         '',
       );

  static const _configuredBaseUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'http://127.0.0.1:8000',
  );
  static const _prefix = '/api/v1';

  final http.Client _httpClient;
  final TokenStorage _tokenStorage;
  final String _baseUrl;
  Future<bool>? _refreshing;

  Future<bool> hasSession() async =>
      await _tokenStorage.readAccessToken() != null;

  Future<void> clearSession() => _tokenStorage.clear();

  Future<void> login({
    required String organizationSlug,
    required String email,
    required String password,
  }) async {
    await _tokenStorage.clear();
    final response = await _send(
      'POST',
      '/auth/login',
      body: {
        'organization_slug': organizationSlug,
        'email': email,
        'password': password,
      },
      authenticated: false,
      retry: false,
    );
    final payload = _decodeObject(response);
    await _tokenStorage.saveTokens(
      payload['access_token'] as String,
      payload['refresh_token'] as String,
    );
  }

  Future<DashboardSnapshot> loadDashboard() async {
    final user = CurrentUser.fromJson(
      _decodeObject(await _send('GET', '/auth/me')),
    );
    final stores = await _allPages('/stores', Store.fromJson);
    final results = await Future.wait<dynamic>([
      _allPages('/catalog/products', Product.fromJson),
      _allPages('/inventory/alerts?open_only=true', StockAlert.fromJson),
      _allPages('/sales', Sale.fromJson),
      Future.wait(
        stores.map(
          (store) => _allPages(
            '/inventory/stores/${store.id}/balances',
            InventoryBalance.fromJson,
          ),
        ),
      ),
    ]);
    return DashboardSnapshot(
      user: user,
      stores: stores,
      products: results[0] as List<Product>,
      alerts: results[1] as List<StockAlert>,
      sales: results[2] as List<Sale>,
      balances: (results[3] as List<List<InventoryBalance>>)
          .expand((items) => items)
          .toList(),
    );
  }

  Future<void> logout() async {
    try {
      await _send('POST', '/auth/logout-all', retry: false);
    } finally {
      await _tokenStorage.clear();
    }
  }

  Future<List<T>> _allPages<T>(
    String path,
    T Function(JsonMap json) fromJson,
  ) async {
    final items = <T>[];
    var page = 1;
    var total = 0;
    do {
      final uri = Uri.parse(path);
      final query = Map<String, String>.from(uri.queryParameters)
        ..['page'] = '$page'
        ..['page_size'] = '100';
      final pagedPath = uri.replace(queryParameters: query).toString();
      final payload = _decodeObject(await _send('GET', pagedPath));
      final pageItems = (payload['items'] as List<dynamic>)
          .map((item) => fromJson(item as JsonMap))
          .toList();
      items.addAll(pageItems);
      total = payload['total'] as int;
      page += 1;
      if (pageItems.isEmpty) break;
    } while (items.length < total);
    return items;
  }

  Future<http.Response> _send(
    String method,
    String path, {
    JsonMap? body,
    bool authenticated = true,
    bool retry = true,
  }) async {
    final headers = <String, String>{'Accept': 'application/json'};
    if (body != null) headers['Content-Type'] = 'application/json';
    if (authenticated) {
      final accessToken = await _tokenStorage.readAccessToken();
      if (accessToken != null) headers['Authorization'] = 'Bearer $accessToken';
    }

    http.Response response;
    try {
      final uri = Uri.parse('$_baseUrl$_prefix$path');
      response = switch (method) {
        'GET' => await _httpClient.get(uri, headers: headers),
        'POST' => await _httpClient.post(
          uri,
          headers: headers,
          body: body == null ? null : jsonEncode(body),
        ),
        _ => throw ArgumentError.value(
          method,
          'method',
          'Méthode HTTP non prise en charge',
        ),
      };
    } on ApiException {
      rethrow;
    } catch (_) {
      throw const ApiException('Impossible de joindre le serveur.', 0);
    }

    if (response.statusCode == 401 &&
        authenticated &&
        retry &&
        path != '/auth/refresh') {
      _refreshing ??= _refreshSession().whenComplete(() => _refreshing = null);
      if (await _refreshing!) {
        return _send(
          method,
          path,
          body: body,
          authenticated: authenticated,
          retry: false,
        );
      }
      await _tokenStorage.clear();
    }

    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw ApiException(_errorMessage(response), response.statusCode);
    }
    return response;
  }

  Future<bool> _refreshSession() async {
    final refreshToken = await _tokenStorage.readRefreshToken();
    if (refreshToken == null) return false;
    try {
      final response = await _send(
        'POST',
        '/auth/refresh',
        body: {'refresh_token': refreshToken},
        authenticated: false,
        retry: false,
      );
      final payload = _decodeObject(response);
      await _tokenStorage.saveTokens(
        payload['access_token'] as String,
        payload['refresh_token'] as String,
      );
      return true;
    } catch (_) {
      return false;
    }
  }

  JsonMap _decodeObject(http.Response response) {
    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    if (decoded is! JsonMap) {
      throw ApiException('Réponse inattendue du serveur.', response.statusCode);
    }
    return decoded;
  }

  String _errorMessage(http.Response response) {
    try {
      final payload = _decodeObject(response);
      final detail = payload['detail'];
      if (detail is String) return detail;
      if (detail is JsonMap && detail['message'] is String) {
        return detail['message'] as String;
      }
    } catch (_) {
      // The fallback below also covers non-JSON error responses.
    }
    return 'Erreur HTTP ${response.statusCode}';
  }
}
