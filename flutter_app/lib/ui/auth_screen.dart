import 'package:material_ui/material_ui.dart';
import '../data/app_controller.dart';
import 'design.dart';

class LedgerLogo extends StatelessWidget {
  const LedgerLogo({super.key, this.compact = false});
  final bool compact;
  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: Palette.amber,
          borderRadius: BorderRadius.circular(14),
        ),
        child: const Icon(Icons.waves_rounded, size: 24, color: Palette.ink),
      ),
      if (!compact) ...[
        const SizedBox(width: 10),
        const Text(
          'PocketLedger',
          style: TextStyle(
            fontSize: 17,
            fontWeight: FontWeight.w700,
            letterSpacing: -.6,
          ),
        ),
      ],
    ],
  );
}

class ErrorNotice extends StatelessWidget {
  const ErrorNotice({super.key, required this.controller});
  final AppController controller;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.fromLTRB(14, 8, 6, 8),
    decoration: BoxDecoration(
      color: const Color(0xffffeeee),
      borderRadius: BorderRadius.circular(16),
    ),
    child: Row(
      children: [
        const Icon(Icons.info_outline, size: 18, color: Color(0xffa43b42)),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            [
              controller.error ?? '',
              ...controller.fieldErrors.entries.map(
                (e) => '${e.key.replaceAll('_', ' ')}: ${e.value.join(' ')}',
              ),
            ].join('\n'),
            style: const TextStyle(fontSize: 12),
          ),
        ),
        if (controller.canRetry)
          TextButton(onPressed: controller.retry, child: const Text('Retry')),
        IconButton(
          tooltip: 'Dismiss error',
          onPressed: controller.clearError,
          icon: const Icon(Icons.close, size: 16),
        ),
      ],
    ),
  );
}

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key, required this.controller});
  final AppController controller;
  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final username = TextEditingController(),
      password = TextEditingController(),
      confirm = TextEditingController(),
      name = TextEditingController();
  final form = GlobalKey<FormState>();
  bool register = false, obscure = true;
  @override
  void dispose() {
    for (final c in [username, password, confirm, name]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> submit() async {
    if (!form.currentState!.validate()) return;
    FocusScope.of(context).unfocus();
    if (register) {
      await widget.controller.register(
        username.text,
        password.text,
        confirm.text,
        firstName: name.text,
      );
    } else {
      await widget.controller.signIn(username.text, password.text);
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    final wide = MediaQuery.sizeOf(context).width > 850;
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1060),
          child: Row(
            children: [
              if (wide)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(right: 70),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const LedgerLogo(),
                        const SizedBox(height: 65),
                        Text(
                          'A calmer way\nto move forward.',
                          style: Theme.of(context).textTheme.headlineLarge
                              ?.copyWith(
                                fontSize: 58,
                                height: 1.05,
                                letterSpacing: -3,
                              ),
                        ),
                        const SizedBox(height: 24),
                        const Text(
                          'A clear view of today.\nA little room for tomorrow.',
                          style: TextStyle(
                            fontSize: 19,
                            height: 1.6,
                            color: Palette.muted,
                          ),
                        ),
                        const SizedBox(height: 45),
                        const Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            TinyTag('Your money'),
                            TinyTag('Your plans', color: Palette.green),
                            TinyTag('Your local AI', color: Palette.ink),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              Expanded(
                child: GlassCard(
                  padding: EdgeInsets.all(wide ? 38 : 24),
                  child: Form(
                    key: form,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        if (!wide) ...[
                          const LedgerLogo(),
                          const SizedBox(height: 32),
                        ],
                        Text(
                          register ? 'A fresh start.' : 'Welcome back.',
                          style: Theme.of(context).textTheme.headlineLarge,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          register
                              ? 'Create your private space for money.'
                              : 'Let’s bring your money into focus.',
                          style: const TextStyle(color: Palette.muted),
                        ),
                        const SizedBox(height: 30),
                        if (c.error != null) ...[
                          ErrorNotice(controller: c),
                          const SizedBox(height: 16),
                        ],
                        if (register) ...[
                          TextFormField(
                            controller: name,
                            decoration: const InputDecoration(
                              labelText: 'First name (optional)',
                            ),
                            textInputAction: TextInputAction.next,
                          ),
                          const SizedBox(height: 16),
                        ],
                        TextFormField(
                          controller: username,
                          autofillHints: const [AutofillHints.username],
                          decoration: const InputDecoration(
                            labelText: 'Username',
                          ),
                          validator: (v) => v == null || v.trim().isEmpty
                              ? 'Enter your username'
                              : null,
                          textInputAction: TextInputAction.next,
                        ),
                        const SizedBox(height: 16),
                        TextFormField(
                          controller: password,
                          autofillHints: [
                            register
                                ? AutofillHints.newPassword
                                : AutofillHints.password,
                          ],
                          obscureText: obscure,
                          decoration: InputDecoration(
                            labelText: 'Password',
                            suffixIcon: IconButton(
                              tooltip: obscure
                                  ? 'Show password'
                                  : 'Hide password',
                              onPressed: () =>
                                  setState(() => obscure = !obscure),
                              icon: Icon(
                                obscure
                                    ? Icons.visibility_outlined
                                    : Icons.visibility_off_outlined,
                                size: 19,
                              ),
                            ),
                          ),
                          validator: (v) => v == null || v.isEmpty
                              ? 'Enter your password'
                              : null,
                          onFieldSubmitted: (_) {
                            if (!register && !c.isLoading) submit();
                          },
                        ),
                        if (register) ...[
                          const SizedBox(height: 16),
                          TextFormField(
                            controller: confirm,
                            obscureText: true,
                            decoration: const InputDecoration(
                              labelText: 'Confirm password',
                            ),
                            validator: (v) => v != password.text
                                ? 'Passwords do not match'
                                : null,
                          ),
                        ],
                        const SizedBox(height: 24),
                        SizedBox(
                          width: double.infinity,
                          child: PillButton(
                            label: c.isLoading
                                ? 'Connecting…'
                                : register
                                ? 'Create account'
                                : 'Step inside',
                            icon: Icons.arrow_forward_rounded,
                            primary: true,
                            onPressed: c.isLoading ? null : submit,
                          ),
                        ),
                        const SizedBox(height: 20),
                        Center(
                          child: TextButton(
                            onPressed: c.isLoading
                                ? null
                                : () => setState(() {
                                    register = !register;
                                    c.clearError();
                                  }),
                            child: Text(
                              register
                                  ? 'Already have an account? Sign in'
                                  : 'New here? Create an account',
                            ),
                          ),
                        ),
                        const SizedBox(height: 10),
                        const Center(
                          child: Text(
                            'A little more clarity. Every day.',
                            style: TextStyle(
                              color: Palette.muted,
                              fontSize: 11,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
