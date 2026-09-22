import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'api/api_client.dart';
import 'models/models.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';

class KerManagerApp extends StatefulWidget {
  const KerManagerApp({super.key});

  @override
  State<KerManagerApp> createState() => _KerManagerAppState();
}

class _KerManagerAppState extends State<KerManagerApp> {
  final ApiClient _apiClient = ApiClient();
  DashboardSnapshot? _snapshot;
  bool _checkingSession = true;

  @override
  void initState() {
    super.initState();
    _restoreSession();
  }

  Future<void> _restoreSession() async {
    try {
      if (await _apiClient.hasSession()) {
        _snapshot = await _apiClient.loadDashboard();
      }
    } catch (_) {
      await _apiClient.clearSession();
    } finally {
      if (mounted) setState(() => _checkingSession = false);
    }
  }

  Future<void> _login(
    String organization,
    String email,
    String password,
  ) async {
    await _apiClient.login(
      organizationSlug: organization,
      email: email,
      password: password,
    );
    final snapshot = await _apiClient.loadDashboard();
    if (mounted) setState(() => _snapshot = snapshot);
  }

  Future<void> _logout() async {
    await _apiClient.logout();
    if (mounted) setState(() => _snapshot = null);
  }

  @override
  Widget build(BuildContext context) {
    const primary = Color(0xff178565);
    final textTheme = GoogleFonts.manropeTextTheme();
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      title: 'KërManager',
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: primary,
          primary: primary,
          surface: const Color(0xfff7f9f8),
          error: const Color(0xffb34840),
        ),
        scaffoldBackgroundColor: const Color(0xfff7f9f8),
        textTheme: textTheme,
        appBarTheme: AppBarTheme(
          backgroundColor: const Color(0xff102d2a),
          foregroundColor: Colors.white,
          titleTextStyle: textTheme.titleMedium?.copyWith(
            color: Colors.white,
            fontWeight: FontWeight.w800,
          ),
        ),
        cardTheme: const CardThemeData(
          color: Colors.white,
          elevation: 0,
          margin: EdgeInsets.zero,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.all(Radius.circular(8)),
            side: BorderSide(color: Color(0xffe1e8e5)),
          ),
        ),
        inputDecorationTheme: const InputDecorationTheme(
          filled: true,
          fillColor: Colors.white,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.all(Radius.circular(7)),
            borderSide: BorderSide(color: Color(0xffd8e1dd)),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.all(Radius.circular(7)),
            borderSide: BorderSide(color: Color(0xffd8e1dd)),
          ),
        ),
      ),
      home: _checkingSession
          ? const _BootScreen()
          : _snapshot == null
          ? LoginScreen(onLogin: _login)
          : DashboardScreen(
              initialSnapshot: _snapshot!,
              apiClient: _apiClient,
              onLogout: _logout,
            ),
    );
  }
}

class _BootScreen extends StatelessWidget {
  const _BootScreen();

  @override
  Widget build(BuildContext context) => const Scaffold(
    backgroundColor: Color(0xff102d2a),
    body: Center(child: CircularProgressIndicator(color: Color(0xff63d3a4))),
  );
}
