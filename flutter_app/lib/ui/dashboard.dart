import 'package:material_ui/material_ui.dart';
import '../data/app_controller.dart';
import 'design.dart';
import 'charts.dart';

class Dashboard extends StatelessWidget {
  const Dashboard({
    super.key,
    required this.controller,
    required this.onNavigate,
    required this.onAdd,
  });
  final AppController controller;
  final void Function(String) onNavigate;
  final VoidCallback onAdd;
  @override
  Widget build(BuildContext context) {
    final d = controller.overview;
    final c = controller.currency;
    final forecast = mapOf(d['forecast']);
    final history = maps(d['history']);
    final budgets = mapOf(d['budgets']);
    final goals = maps(d['goals']);
    return LayoutBuilder(
      builder: (context, box) {
        final wide = box.maxWidth > 900;
        final compact = box.maxWidth < 580;
        final chart = GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeading(
                title: 'Your financial pulse',
                subtitle: 'A little perspective on money in and out.',
                trailing: const TinyTag('6 months'),
              ),
              const SizedBox(height: 28),
              FlowChart(
                primary: history.map((r) => number(r['income'])).toList(),
                secondary: history.map((r) => number(r['expense'])).toList(),
                labels: history
                    .map((r) => '${r['label']}'.split(' ').first)
                    .toList(),
                height: compact ? 180 : 220,
              ),
            ],
          ),
        );
        final budgetCard = GlassCard(
          color: const Color(0xfffff1cf).withValues(alpha: .85),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeading(
                title: 'Room to breathe',
                subtitle: 'Your category budgets this month',
                trailing: IconButton(
                  tooltip: 'Manage budgets',
                  onPressed: () => onNavigate('budgets'),
                  icon: const Icon(Icons.north_east, size: 18),
                ),
              ),
              Center(
                child: LiquidRing(
                  value: number(budgets['total_budget']) > 0
                      ? (number(budgets['total_remaining']) /
                                number(budgets['total_budget']))
                            .clamp(0, 1)
                      : 0,
                  label: number(budgets['total_budget']) > 0
                      ? '${((number(budgets['total_remaining']) / number(budgets['total_budget'])).clamp(0, 1) * 100).round()}%'
                      : '—',
                  subtitle: 'OF BUDGET LEFT',
                  color: const Color(0xffc99b35),
                ),
              ),
              const SizedBox(height: 8),
              Center(
                child: Text(
                  money(budgets['total_remaining'] ?? '0', c),
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              const SizedBox(height: 6),
              Center(
                child: Text(
                  number(budgets['total_budget']) > 0
                      ? 'Across your planned categories'
                      : 'Set your first budget to get started',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
              const SizedBox(height: 10),
            ],
          ),
        );
        return Reveal(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 22,
                runSpacing: 20,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 1100),
                        child: Text.rich(
                          const TextSpan(
                            children: [
                              TextSpan(text: 'Your money,\n'),
                              TextSpan(
                                text: 'finally clear.',
                                style: TextStyle(color: Palette.orange),
                              ),
                            ],
                          ),
                          style: Theme.of(context).textTheme.headlineLarge
                              ?.copyWith(
                                fontSize: compact ? 52 : (wide ? 112 : 84),
                                height: .98,
                                fontWeight: FontWeight.w800,
                                letterSpacing: compact ? -2.4 : -5,
                              ),
                        ),
                      ),
                    ],
                  ),
                  PillButton(
                    label: 'Add transaction',
                    icon: Icons.add,
                    onPressed: onAdd,
                    primary: true,
                  ),
                ],
              ),
              const SizedBox(height: 28),
              if (d.isEmpty) ...[
                const EmptyPanel(
                  title: 'Let’s find your flow',
                  message:
                      'Connect to your server to see your accounts and plans.',
                ),
                const SizedBox(height: 24),
              ] else ...[
                LayoutBuilder(
                  builder: (context, metrics) {
                    final columns = metrics.maxWidth > 820 ? 4 : 2;
                    return Wrap(
                      spacing: 16,
                      runSpacing: 16,
                      children: [
                        _metric(
                          context,
                          width:
                              (metrics.maxWidth - 16 * (columns - 1)) / columns,
                          title: 'Total balance',
                          value: d['balance'],
                          foot: 'Across ${maps(d['accounts']).length} accounts',
                          icon: Icons.account_balance_wallet_outlined,
                          featured: true,
                        ),
                        _metric(
                          context,
                          width:
                              (metrics.maxWidth - 16 * (columns - 1)) / columns,
                          title: 'Money in',
                          value: d['income'],
                          foot: 'Received this month',
                          icon: Icons.south_west_rounded,
                        ),
                        _metric(
                          context,
                          width:
                              (metrics.maxWidth - 16 * (columns - 1)) / columns,
                          title: 'Money out',
                          value: d['expense'],
                          foot: 'Spent this month',
                          icon: Icons.north_east_rounded,
                          amber: true,
                        ),
                        _metric(
                          context,
                          width:
                              (metrics.maxWidth - 16 * (columns - 1)) / columns,
                          title: '30-day outlook',
                          value: forecast['end_expected'],
                          foot: 'An estimate, not a guarantee',
                          icon: Icons.waves_rounded,
                        ),
                      ],
                    );
                  },
                ),
                const SizedBox(height: 24),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 7, child: chart),
                      const SizedBox(width: 20),
                      Expanded(flex: 3, child: budgetCard),
                    ],
                  )
                else ...[
                  chart,
                  const SizedBox(height: 18),
                  budgetCard,
                ],
                const SizedBox(height: 20),
                GlassCard(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 22,
                    vertical: 16,
                  ),
                  color: const Color(0xffe9eefb).withValues(alpha: .8),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: const BoxDecoration(
                          color: Colors.white,
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.auto_awesome_outlined,
                          color: Palette.blue,
                          size: 20,
                        ),
                      ),
                      const SizedBox(width: 15),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              forecast['shortfall_low'] != null
                                  ? 'A moment to look ahead'
                                  : 'A clearer tomorrow starts today',
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                                fontSize: 13,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              forecast['shortfall_low'] != null
                                  ? 'Your cautious forecast may run short on ${forecast['shortfall_low']}. Review your plan.'
                                  : 'Your forecast allows ${money(forecast['daily_spend'], c)} a day for everyday spending.',
                              style: const TextStyle(
                                fontSize: 11,
                                color: Palette.muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        tooltip: 'Open planner',
                        onPressed: () => onNavigate('planning'),
                        icon: const Icon(
                          Icons.arrow_forward_rounded,
                          color: Palette.blue,
                          size: 20,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 20),
                if (wide)
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        flex: 7,
                        child: _activity(context, maps(d['recent'])),
                      ),
                      const SizedBox(width: 20),
                      Expanded(flex: 3, child: _plans(context, budgets, goals)),
                    ],
                  )
                else ...[
                  _activity(context, maps(d['recent'])),
                  const SizedBox(height: 20),
                  _plans(context, budgets, goals),
                ],
                const SizedBox(height: 20),
                _accounts(context, maps(d['accounts'])),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _metric(
    BuildContext context, {
    required double width,
    required String title,
    required Object? value,
    required String foot,
    required IconData icon,
    bool featured = false,
    bool amber = false,
  }) {
    final dark = amber;
    final fg = dark ? Colors.white : Palette.ink;
    final soft = dark ? Colors.white : const Color(0xff4b5b65);
    final small = width < 180;
    return SizedBox(
      width: width,
      child: HoverLift(
        child: GlassCard(
          padding: EdgeInsets.all(small ? 18 : 24),
          gradient: featured
              ? const LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xfffbfeff),
                    Color(0xffdfedf3),
                    Color(0xffc0dce5),
                  ],
                )
              : null,
          color: amber ? const Color(0xffa9691f).withValues(alpha: .88) : null,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 38,
                    height: 38,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(color: fg.withValues(alpha: .3)),
                    ),
                    child: Icon(icon, size: 17, color: fg),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13,
                        height: 1.25,
                        fontWeight: FontWeight.w500,
                        color: fg,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 28),
              FittedBox(
                fit: BoxFit.scaleDown,
                alignment: Alignment.centerLeft,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic,
                  children: [
                    Text(
                      money(value, ''),
                      style: TextStyle(
                        fontSize: small ? 30 : 38,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -1.4,
                        color: fg,
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      controller.currency,
                      style: TextStyle(fontSize: 12, color: soft),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Text(foot, style: TextStyle(fontSize: 10, color: soft)),
            ],
          ),
        ),
      ),
    );
  }

  Widget _activity(BuildContext context, List<Map<String, dynamic>> rows) =>
      GlassCard(
        child: Column(
          children: [
            SectionHeading(
              title: 'Recent activity',
              subtitle: 'The small things that add up.',
              trailing: TextButton(
                onPressed: () => onNavigate('transactions'),
                child: const Text('View all →', style: TextStyle(fontSize: 11)),
              ),
            ),
            const SizedBox(height: 17),
            if (rows.isEmpty)
              const Padding(
                padding: EdgeInsets.all(30),
                child: Text('Add your first transaction to start your story.'),
              ),
            ...rows.take(5).map((r) {
              final income = r['kind'] == 'income';
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 12),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: income
                            ? const Color(0xffe8f3ed)
                            : const Color(0xfff5f0e7),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Icon(
                        income ? Icons.south_west : Icons.north_east,
                        size: 18,
                        color: income ? Palette.green : const Color(0xffc0a16a),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${r['description']}'.isEmpty
                                ? '${r['category_name'] ?? r['kind']}'
                                : '${r['description']}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${r['date']} · ${r['account_name']}',
                            style: const TextStyle(
                              fontSize: 10,
                              color: Palette.muted,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      '${income
                          ? '+'
                          : r['kind'] == 'expense'
                          ? '−'
                          : ''}${money(r['amount'], '')}',
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: income ? Palette.green : Palette.ink,
                      ),
                    ),
                  ],
                ),
              );
            }),
          ],
        ),
      );
  Widget _plans(
    BuildContext context,
    Map<String, dynamic> summary,
    List<Map<String, dynamic>> goals,
  ) => GlassCard(
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeading(
          title: 'Little plans. Big possibilities.',
          trailing: IconButton(
            tooltip: 'Manage plans',
            onPressed: () => onNavigate('budgets'),
            icon: const Icon(Icons.more_horiz, size: 19),
          ),
        ),
        ...maps(summary['rows'])
            .take(3)
            .map(
              (r) => Padding(
                padding: const EdgeInsets.only(top: 20),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            '${r['category_name']}',
                            style: const TextStyle(fontSize: 12),
                          ),
                        ),
                        Text(
                          '${number(r['percent']).round()}%',
                          style: const TextStyle(
                            fontSize: 11,
                            color: Palette.muted,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    TweenAnimationBuilder<double>(
                      tween: Tween(
                        begin: 0,
                        end: (number(r['percent']) / 100).clamp(0, 1),
                      ),
                      duration: Duration(
                        milliseconds: MediaQuery.disableAnimationsOf(context)
                            ? 0
                            : 700,
                      ),
                      builder: (_, v, __) => LinearProgressIndicator(
                        value: v,
                        minHeight: 6,
                        borderRadius: BorderRadius.circular(10),
                        backgroundColor: const Color(0xfff0eff4),
                        color: r['status'] == 'over'
                            ? const Color(0xffde8a7f)
                            : Palette.lavender,
                      ),
                    ),
                    const SizedBox(height: 7),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            '${r['status_label']}',
                            style: const TextStyle(
                              fontSize: 10,
                              color: Palette.muted,
                            ),
                          ),
                        ),
                        Text(
                          money(r['amount'], ''),
                          style: const TextStyle(
                            fontSize: 10,
                            color: Palette.muted,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
        if (maps(summary['rows']).isEmpty)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 18),
            child: PillButton(
              label: 'Set a budget',
              icon: Icons.add,
              onPressed: () => onNavigate('budgets'),
            ),
          ),
        if (goals.isNotEmpty) ...[
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 18),
            child: Divider(),
          ),
          Row(
            children: [
              const Icon(Icons.flag_outlined, color: Palette.blue, size: 20),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '${goals.first['name']}',
                  style: const TextStyle(fontSize: 12),
                ),
              ),
              Text(
                '${goals.first['percent']}%',
                style: const TextStyle(fontSize: 11, color: Palette.blue),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '${money(goals.first['saved_so_far'], controller.currency)} saved for what’s next.',
            style: const TextStyle(fontSize: 10, color: Palette.muted),
          ),
        ],
      ],
    ),
  );
  Widget _accounts(BuildContext context, List<Map<String, dynamic>> rows) =>
      GlassCard(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SectionHeading(
              title: 'Your pockets',
              subtitle: 'Everything in its own place.',
              trailing: TextButton(
                onPressed: () => onNavigate('accounts'),
                child: const Text('Manage →', style: TextStyle(fontSize: 11)),
              ),
            ),
            const SizedBox(height: 20),
            Wrap(
              spacing: 14,
              runSpacing: 14,
              children: rows
                  .map(
                    (r) => Container(
                      width: 230,
                      padding: const EdgeInsets.all(20),
                      decoration: BoxDecoration(
                        color: const Color(0xfff4f5fa),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              const Icon(
                                Icons.account_balance_outlined,
                                size: 18,
                                color: Palette.blue,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  '${r['name']}',
                                  style: const TextStyle(fontSize: 12),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 16),
                          Text(
                            money(r['balance'], controller.currency),
                            style: const TextStyle(
                              fontSize: 20,
                              letterSpacing: -.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                  .toList(),
            ),
            if (rows.isEmpty)
              PillButton(
                label: 'Add your first account',
                onPressed: () => onNavigate('accounts'),
              ),
          ],
        ),
      );
}
