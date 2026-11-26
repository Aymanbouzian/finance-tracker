import 'package:material_ui/material_ui.dart';
import '../data/app_controller.dart';
import 'design.dart';
import 'charts.dart';
import 'resource_screen.dart';
import 'liquid_controls.dart';

class PlanningScreen extends StatefulWidget {
  const PlanningScreen({
    super.key,
    required this.controller,
    this.initialTab = 'budgets',
  });
  final AppController controller;
  final String initialTab;
  @override
  State<PlanningScreen> createState() => _PlanningScreenState();
}

class _PlanningScreenState extends State<PlanningScreen> {
  static const tabs = ['budgets', 'goals', 'recurring', 'forecast', 'whatif'];
  late String tab = widget.initialTab;
  @override
  void didUpdateWidget(covariant PlanningScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.initialTab != widget.initialTab) tab = widget.initialTab;
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) => Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Make space for what’s next.',
          style: Theme.of(context).textTheme.headlineLarge?.copyWith(
            fontSize: constraints.maxWidth < 600 ? 32 : 44,
            height: 1.12,
            letterSpacing: constraints.maxWidth < 600 ? -1.1 : -1.8,
          ),
        ),
        const SizedBox(height: 8),
        const Text(
          'Small plans. More possibilities.',
          style: TextStyle(color: Palette.muted),
        ),
        const SizedBox(height: 24),
        LiquidSegmentedControl(
          labels: const [
            'Budgets',
            'Savings goals',
            'Recurring',
            'Forecast',
            'What if?',
          ],
          selected: tabs.indexOf(tab),
          onSelected: (index) => setState(() => tab = tabs[index]),
        ),
        const SizedBox(height: 24),
        LiquidPageTransition(
          identity: tab,
          child: ['budgets', 'goals', 'recurring'].contains(tab)
              ? ResourceScreen(
                  key: ValueKey(tab),
                  controller: widget.controller,
                  resource: tab,
                  embedded: true,
                  title: {
                    'budgets': 'Your monthly rhythm',
                    'goals': 'Little by little',
                    'recurring': 'On repeat',
                  }[tab]!,
                )
              : _ForecastPanel(
                  key: ValueKey(tab),
                  controller: widget.controller,
                  scenario: tab == 'whatif',
                ),
        ),
      ],
    ),
  );
}

class _ForecastPanel extends StatefulWidget {
  const _ForecastPanel({
    super.key,
    required this.controller,
    required this.scenario,
  });
  final AppController controller;
  final bool scenario;
  @override
  State<_ForecastPanel> createState() => _ForecastPanelState();
}

class _ForecastPanelState extends State<_ForecastPanel> {
  int days = 90;
  final daily = TextEditingController(),
      purchase = TextEditingController(),
      income = TextEditingController(),
      cut = TextEditingController();
  DateTime date = DateTime.now();
  @override
  void initState() {
    super.initState();
    if (!widget.scenario) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) widget.controller.loadForecast();
      });
    }
  }

  @override
  void dispose() {
    for (final c in [daily, purchase, income, cut]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> run() async {
    if (widget.scenario) {
      await widget.controller.runWhatIf({
        'days': days,
        'purchase_amount': purchase.text,
        'purchase_date': date.toIso8601String().split('T').first,
        'monthly_income_change': income.text,
        'monthly_expense_cut': cut.text,
      });
    } else {
      await widget.controller.loadForecast(
        days: days,
        dailySpend: daily.text.trim().isEmpty ? null : daily.text,
      );
    }
  }

  Widget input(TextEditingController c, String label) => SizedBox(
    width: 240,
    child: TextField(
      controller: c,
      keyboardType: const TextInputType.numberWithOptions(
        decimal: true,
        signed: true,
      ),
      decoration: InputDecoration(labelText: label),
    ),
  );
  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    final data = widget.scenario ? c.whatIfResult : c.forecast;
    final labels = (data['dates'] as List? ?? [])
        .map((v) => v.toString().substring(5))
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeading(
                title: widget.scenario
                    ? 'Try a possibility'
                    : 'A view down the road',
                subtitle: widget.scenario
                    ? 'Explore a change before making it. Your records stay as they are.'
                    : 'Based on your balance, recurring items and recent variable spending.',
              ),
              const SizedBox(height: 22),
              LiquidSegmentedControl(
                labels: const [
                  '30 days',
                  '60 days',
                  '90 days',
                  '180 days',
                  '365 days',
                ],
                selected: const [30, 60, 90, 180, 365].indexOf(days),
                onSelected: (index) =>
                    setState(() => days = const [30, 60, 90, 180, 365][index]),
              ),
              const SizedBox(height: 20),
              Wrap(
                spacing: 14,
                runSpacing: 14,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: widget.scenario
                    ? [
                        input(purchase, 'One-off purchase (${c.currency})'),
                        input(income, 'Monthly income change'),
                        input(cut, 'Monthly spending reduction'),
                        PillButton(
                          label:
                              'Purchase: ${date.toIso8601String().split('T').first}',
                          icon: Icons.calendar_today_outlined,
                          onPressed: () async {
                            final d = await showDatePicker(
                              context: context,
                              initialDate: date,
                              firstDate: DateTime.now().subtract(
                                const Duration(days: 1),
                              ),
                              lastDate: DateTime.now().add(
                                const Duration(days: 3650),
                              ),
                            );
                            if (d != null) setState(() => date = d);
                          },
                        ),
                      ]
                    : [
                        input(daily, 'Daily spending override (${c.currency})'),
                        const SizedBox(
                          width: 240,
                          child: Text(
                            'Leave blank to use the estimate from your past 90 days.',
                            style: TextStyle(
                              color: Palette.muted,
                              fontSize: 12,
                            ),
                          ),
                        ),
                      ],
              ),
              const SizedBox(height: 22),
              PillButton(
                label: widget.scenario
                    ? 'Explore this scenario'
                    : 'Update forecast',
                icon: Icons.auto_graph_rounded,
                primary: true,
                onPressed: c.isLoading ? null : run,
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        if (data.isNotEmpty)
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SectionHeading(
                  title: widget.scenario
                      ? 'Your possible path'
                      : 'Expected balance',
                  subtitle:
                      '${money(data[widget.scenario ? 'scenario_end' : 'end_expected'], c.currency)} at the end of this projection',
                  trailing: const TinyTag('Estimate'),
                ),
                const SizedBox(height: 26),
                FlowChart(
                  primary:
                      (data[widget.scenario ? 'scenario' : 'expected']
                                  as List? ??
                              [])
                          .map(number)
                          .toList(),
                  secondary:
                      (data[widget.scenario ? 'baseline' : 'low'] as List? ??
                              [])
                          .map(number)
                          .toList(),
                  labels: labels,
                  primaryLabel: widget.scenario ? 'Scenario' : 'Expected',
                  secondaryLabel: widget.scenario ? 'Today’s plan' : 'Cautious',
                  height: 260,
                ),
                const SizedBox(height: 22),
                Wrap(
                  spacing: 24,
                  runSpacing: 12,
                  children: [
                    if (widget.scenario)
                      Text(
                        'Difference: ${money(data['difference'], c.currency)}',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      )
                    else
                      Text(
                        'Daily spending: ${money(data['daily_spend'], c.currency)}',
                      ),
                    Text(
                      'Cautious ending: ${money(data[widget.scenario ? 'scenario_end_low' : 'end_low'], c.currency)}',
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  widget.scenario
                      ? 'Income changes begin next month; spending reductions lower the daily estimate. Purchases apply on the selected date.'
                      : 'Cautious projection assumes 25% more variable spending. Recurring entries are plans and do not post transactions.',
                  style: const TextStyle(fontSize: 12, color: Palette.muted),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Estimates exclude unrecorded bills and changes in income. Review your upcoming commitments before making a decision.',
                  style: TextStyle(fontSize: 11, color: Palette.muted),
                ),
              ],
            ),
          )
        else if (!c.isLoading)
          const EmptyPanel(
            title: 'What would you like to change?',
            message:
                'Enter a purchase, income change or spending reduction to compare it with your current plan.',
          ),
      ],
    );
  }
}
