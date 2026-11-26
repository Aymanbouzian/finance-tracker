import 'package:material_ui/material_ui.dart';
import 'package:flutter/foundation.dart';
import 'data/app_controller.dart';
import 'ui/design.dart';
import 'ui/dashboard.dart';
import 'ui/resource_screen.dart';
import 'ui/planning_screen.dart';
import 'ui/assistant_screen.dart';
import 'ui/auth_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  if (kIsWeb) WidgetsBinding.instance.ensureSemantics();
  runApp(const PocketLedgerApp());
}

class PocketLedgerApp extends StatefulWidget {
  const PocketLedgerApp({super.key, this.controller});
  final AppController? controller;
  @override
  State<PocketLedgerApp> createState() => _PocketLedgerAppState();
}

class _PocketLedgerAppState extends State<PocketLedgerApp> {
  late final AppController controller = widget.controller ?? AppController();
  bool motion = true;
  @override
  void initState() {
    super.initState();
    controller.initialize();
  }

  @override
  void dispose() {
    if (widget.controller == null) controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'PocketLedger',
    debugShowCheckedModeBanner: false,
    theme: appTheme(),
    builder: (context, child) => MediaQuery(
      data: MediaQuery.of(context).copyWith(
        disableAnimations:
            !motion ||
            MediaQuery.disableAnimationsOf(context) ||
            MediaQuery.reduceMotionOf(context),
      ),
      child: child!,
    ),
    home: AnimatedBuilder(
      animation: controller,
      builder: (context, _) => LiquidBackdrop(
        motion: motion,
        child: Scaffold(
          body: SafeArea(
            child: !controller.initialized
                ? const Center(child: CircularProgressIndicator())
                : controller.authenticated
                ? _Shell(
                    controller: controller,
                    motion: motion,
                    toggleMotion: () => setState(() => motion = !motion),
                  )
                : AuthScreen(controller: controller),
          ),
        ),
      ),
    ),
  );
}

class _Shell extends StatefulWidget {
  const _Shell({
    required this.controller,
    required this.motion,
    required this.toggleMotion,
  });
  final AppController controller;
  final bool motion;
  final VoidCallback toggleMotion;
  @override
  State<_Shell> createState() => _ShellState();
}

class _ShellState extends State<_Shell> {
  String section = 'overview', planningTab = 'budgets';
  static const destinations = [
    'overview',
    'transactions',
    'planning',
    'accounts',
    'assistant',
  ];
  static const labels = [
    'Overview',
    'Activity',
    'Plan ahead',
    'Accounts',
    'Local AI',
  ];
  static const icons = [
    Icons.space_dashboard_outlined,
    Icons.swap_horiz_rounded,
    Icons.donut_large_rounded,
    Icons.account_balance_wallet_outlined,
    Icons.auto_awesome_outlined,
  ];
  void navigate(String target) {
    setState(() {
      if (['budgets', 'goals', 'recurring', 'forecast'].contains(target)) {
        planningTab = target;
        section = 'planning';
      } else {
        section = target;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    final wide = MediaQuery.sizeOf(context).width >= 900;
    final index = destinations.indexOf(section);
    Widget content = switch (section) {
      'transactions' => ResourceScreen(
        controller: c,
        resource: 'transactions',
        title: 'Your activity',
      ),
      'accounts' => _AccountsSection(controller: c),
      'planning' => PlanningScreen(
        key: ValueKey(planningTab),
        controller: c,
        initialTab: planningTab,
      ),
      'assistant' => AssistantScreen(controller: c),
      _ => Dashboard(
        controller: c,
        onNavigate: navigate,
        onAdd: () => showResourceEditor(context, c, 'transactions'),
      ),
    };
    return Row(
      children: [
        if (wide)
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 20, 0, 20),
            child: GlassCard(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 18),
              radius: 30,
              child: Column(
                children: [
                  const LedgerLogo(compact: true),
                  const SizedBox(height: 42),
                  for (var i = 0; i < destinations.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 15),
                      child: Tooltip(
                        message: labels[i],
                        child: IconButton.filledTonal(
                          onPressed: () => navigate(destinations[i]),
                          style: IconButton.styleFrom(
                            backgroundColor: index == i
                                ? Palette.blue
                                : Colors.transparent,
                            foregroundColor: index == i
                                ? Colors.white
                                : Palette.muted,
                            minimumSize: const Size(48, 48),
                          ),
                          icon: Icon(icons[i], size: 22),
                        ),
                      ),
                    ),
                  const Spacer(),
                  const RotatedBox(
                    quarterTurns: 3,
                    child: Text(
                      'A little more clarity.',
                      style: TextStyle(color: Palette.muted, fontSize: 10),
                    ),
                  ),
                  const SizedBox(height: 20),
                ],
              ),
            ),
          ),
        Expanded(
          child: Column(
            children: [
              Padding(
                padding: EdgeInsets.fromLTRB(
                  wide ? 32 : 20,
                  18,
                  wide ? 32 : 12,
                  12,
                ),
                child: Row(
                  children: [
                    const Flexible(
                      child: FittedBox(
                        alignment: Alignment.centerLeft,
                        child: LedgerLogo(),
                      ),
                    ),
                    const Spacer(),
                    if (wide)
                      Text(
                        c.overview['month_label']?.toString() ?? '',
                        style: const TextStyle(
                          color: Palette.muted,
                          fontSize: 12,
                        ),
                      ),
                    const SizedBox(width: 12),
                    IconButton(
                      tooltip: widget.motion ? 'Pause motion' : 'Enable motion',
                      onPressed: widget.toggleMotion,
                      icon: Icon(
                        widget.motion
                            ? Icons.motion_photos_on_outlined
                            : Icons.motion_photos_off_outlined,
                        size: 20,
                      ),
                    ),
                    IconButton(
                      tooltip: 'Refresh overview',
                      onPressed: c.isLoading ? null : c.refreshOverview,
                      icon: const Icon(Icons.refresh_rounded, size: 20),
                    ),
                    PopupMenuButton<String>(
                      tooltip: 'Profile',
                      icon: CircleAvatar(
                        radius: 16,
                        backgroundColor: Palette.lavender.withValues(alpha: .3),
                        child: Text(
                          (c.user?['username']?.toString() ?? 'P')
                              .substring(0, 1)
                              .toUpperCase(),
                          style: const TextStyle(
                            fontSize: 12,
                            color: Palette.ink,
                          ),
                        ),
                      ),
                      onSelected: (_) => c.signOut(),
                      itemBuilder: (_) => [
                        PopupMenuItem(
                          value: 'logout',
                          child: Text('Sign out · ${c.user?['username']}'),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (c.isLoading)
                const LinearProgressIndicator(
                  minHeight: 2,
                  backgroundColor: Colors.transparent,
                ),
              if (c.error != null)
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 4,
                  ),
                  child: ErrorNotice(controller: c),
                ),
              Expanded(
                child: SingleChildScrollView(
                  key: PageStorageKey(section),
                  padding: EdgeInsets.fromLTRB(
                    wide ? 32 : 18,
                    12,
                    wide ? 32 : 18,
                    24,
                  ),
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 1440),
                      child: AnimatedSwitcher(
                        duration: Duration(
                          milliseconds: MediaQuery.disableAnimationsOf(context)
                              ? 0
                              : 560,
                        ),
                        // Old page fades out first, then the new one glides in,
                        // so two heavy pages are never fully drawn together.
                        switchInCurve: const Interval(
                          .3,
                          1,
                          curve: Curves.easeOutCubic,
                        ),
                        switchOutCurve: const Interval(
                          .55,
                          1,
                          curve: Curves.easeOutCubic,
                        ),
                        transitionBuilder: (child, animation) => FadeTransition(
                          opacity: animation,
                          child: SlideTransition(
                            position: Tween<Offset>(
                              begin: const Offset(0, .035),
                              end: Offset.zero,
                            ).animate(animation),
                            child: child,
                          ),
                        ),
                        child: RepaintBoundary(
                          key: ValueKey(section),
                          child: content,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
              if (!wide)
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                  child: GlassCard(
                    padding: const EdgeInsets.all(5),
                    radius: 28,
                    child: Row(
                      children: [
                        for (var i = 0; i < destinations.length; i++)
                          Expanded(
                            child: Semantics(
                              selected: index == i,
                              child: InkWell(
                                borderRadius: BorderRadius.circular(22),
                                onTap: () => navigate(destinations[i]),
                                child: AnimatedContainer(
                                  duration: const Duration(milliseconds: 220),
                                  padding: const EdgeInsets.symmetric(
                                    vertical: 11,
                                  ),
                                  decoration: BoxDecoration(
                                    color: index == i
                                        ? Palette.blue
                                        : Colors.transparent,
                                    borderRadius: BorderRadius.circular(22),
                                  ),
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        icons[i],
                                        size: 21,
                                        color: index == i
                                            ? Colors.white
                                            : Palette.muted,
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        [
                                          'Home',
                                          'Activity',
                                          'Plan',
                                          'Accounts',
                                          'AI',
                                        ][i],
                                        style: TextStyle(
                                          fontSize: 9,
                                          color: index == i
                                              ? Colors.white
                                              : Palette.muted,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

class _AccountsSection extends StatefulWidget {
  const _AccountsSection({required this.controller});
  final AppController controller;
  @override
  State<_AccountsSection> createState() => _AccountsSectionState();
}

class _AccountsSectionState extends State<_AccountsSection> {
  bool categories = false;
  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Wrap(
        spacing: 8,
        children: [
          ChoiceChip(
            label: const Text('Accounts'),
            selected: !categories,
            onSelected: (_) => setState(() => categories = false),
          ),
          ChoiceChip(
            label: const Text('Categories'),
            selected: categories,
            onSelected: (_) => setState(() => categories = true),
          ),
        ],
      ),
      const SizedBox(height: 20),
      ResourceScreen(
        key: ValueKey(categories),
        controller: widget.controller,
        resource: categories ? 'categories' : 'accounts',
        title: categories ? 'Make it your own' : 'Your money, together',
      ),
    ],
  );
}
