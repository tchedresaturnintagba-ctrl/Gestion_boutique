import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ker_manager_mobile/src/screens/login_screen.dart';

void main() {
  testWidgets('le formulaire transmet les identifiants valides', (
    tester,
  ) async {
    String? organization;
    String? email;
    String? password;
    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          onLogin:
              (submittedOrganization, submittedEmail, submittedPassword) async {
                organization = submittedOrganization;
                email = submittedEmail;
                password = submittedPassword;
              },
        ),
      ),
    );

    await tester.enterText(find.byType(TextFormField).at(0), ' demo ');
    await tester.enterText(
      find.byType(TextFormField).at(1),
      ' owner@example.com ',
    );
    await tester.enterText(
      find.byType(TextFormField).at(2),
      'Secret-Test-2026!',
    );
    await tester.ensureVisible(find.text('Se connecter'));
    await tester.tap(find.text('Se connecter'));
    await tester.pump();

    expect(organization, 'demo');
    expect(email, 'owner@example.com');
    expect(password, 'Secret-Test-2026!');
  });
}
