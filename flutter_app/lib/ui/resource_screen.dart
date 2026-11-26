import 'package:material_ui/material_ui.dart';

import '../data/app_controller.dart';
import '../data/api_client.dart';
import 'design.dart';

String _singular(String resource) =>
    const {
      'transactions': 'transaction',
      'accounts': 'account',
      'categories': 'category',
      'budgets': 'budget',
      'goals': 'goal',
      'recurring': 'recurring item',
    }[resource] ??
    'record';

String _date(DateTime value) =>
    '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
int? _id(Object? value) => int.tryParse('$value');

Future<void> showResourceEditor(
  BuildContext context,
  AppController controller,
  String resource, {
  Map<String, dynamic>? item,
}) async {
  controller.clearError();
  await showDialog<void>(
    context: context,
    barrierDismissible: false,
    builder: (_) =>
        _ResourceEditor(controller: controller, resource: resource, item: item),
  );
}

class ResourceScreen extends StatefulWidget {
  const ResourceScreen({
    super.key,
    required this.controller,
    required this.resource,
    required this.title,
    this.embedded = false,
  });
  final AppController controller;
  final String resource;
  final String title;
  final bool embedded;
  @override
  State<ResourceScreen> createState() => _ResourceScreenState();
}

class _ResourceScreenState extends State<ResourceScreen> {
  final _search = TextEditingController();
  String _kind = '';
  String _month = '';
  @override
  void initState() {
    super.initState();
    _readQuery();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _load();
    });
  }

  @override
  void didUpdateWidget(covariant ResourceScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.resource != widget.resource) {
      _readQuery();
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _load();
      });
    }
  }

  void _readQuery() {
    final query = widget.controller.resourceQueries[widget.resource] ?? {};
    _search.text = '${query['q'] ?? ''}';
    _kind = '${query['kind'] ?? ''}';
    _month = '${query['month'] ?? ''}';
  }

  Future<void> _load([int page = 1]) => widget.controller.loadResource(
    widget.resource,
    query: {
      'page': page,
      'page_size': 25,
      if (widget.resource == 'transactions') ...{
        'q': _search.text.trim(),
        'kind': _kind,
      },
      if (widget.resource == 'transactions' || widget.resource == 'budgets')
        'month': _month,
    },
  );
  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _pickMonth() async {
    final now = DateTime.now();
    final selected = await showDatePicker(
      context: context,
      initialDate: DateTime.tryParse('$_month-01') ?? now,
      firstDate: DateTime(1900),
      lastDate: DateTime(2100, 12, 31),
      helpText: 'Choose a date in the month to view',
      initialDatePickerMode: DatePickerMode.year,
    );
    if (selected != null && mounted) {
      setState(() => _month = _date(selected).substring(0, 7));
      await _load();
    }
  }

  Future<void> _delete(Map<String, dynamic> item) async {
    final warning = switch (widget.resource) {
      'accounts' =>
        'This also deletes transactions in this account and transfers into it. This cannot be undone.',
      'categories' =>
        'Its transactions will become uncategorized and its budgets will be deleted. This cannot be undone.',
      'budgets' =>
        'Your recorded transactions will stay. This budget will be permanently deleted.',
      _ => 'This record will be permanently deleted. This cannot be undone.',
    };
    final approved = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text('Delete ${_singular(widget.resource)}?'),
        content: Text(warning),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Keep it'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    final id = _id(item['id']);
    if (approved == true && id != null) {
      await widget.controller.deleteResource(widget.resource, id);
    }
  }

  @override
  Widget build(BuildContext context) => AnimatedBuilder(
    animation: widget.controller,
    builder: (context, _) {
      final c = widget.controller;
      final items = c.records(widget.resource);
      final meta = c.resourceMeta[widget.resource] ?? {};
      final page = _id(meta['page']) ?? 1;
      final pages = _id(meta['pages']) ?? 1;
      final summary = mapOf(meta['summary']);
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _header(context),
          const SizedBox(height: 25),
          if (widget.resource == 'transactions' ||
              widget.resource == 'budgets') ...[
            _filters(context),
            const SizedBox(height: 20),
          ],
          if (summary.isNotEmpty) ...[
            Wrap(
              spacing: 12,
              runSpacing: 12,
              children: [
                _summaryCard('Planned', summary['total_budget']),
                _summaryCard('Spent', summary['total_spent']),
                _summaryCard('Remaining', summary['total_remaining']),
                _summaryCard('Without a budget', summary['unbudgeted_spent']),
              ],
            ),
            const SizedBox(height: 20),
          ],
          if (c.isLoading)
            const Padding(
              padding: EdgeInsets.only(bottom: 18),
              child: LinearProgressIndicator(minHeight: 2),
            ),
          if (c.error != null) ...[
            GlassCard(
              color: const Color(0xfffff1e9),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: Palette.ink),
                  const SizedBox(width: 12),
                  Expanded(child: Text(c.error!)),
                  TextButton(
                    onPressed: c.isLoading ? null : () => _load(page),
                    child: const Text('Refresh'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),
          ],
          if (items.isEmpty && !c.isLoading)
            EmptyPanel(
              title: 'A fresh page',
              message: widget.resource == 'transactions'
                  ? 'No transactions match this view. Add one or adjust your filters.'
                  : 'Add your first ${_singular(widget.resource)} to start shaping your plan.',
            ),
          if (items.isNotEmpty)
            GlassCard(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Column(
                children: [
                  for (var index = 0; index < items.length; index++) ...[
                    if (index > 0) const Divider(height: 1),
                    _record(context, items[index]),
                  ],
                ],
              ),
            ),
          if (items.isNotEmpty || pages > 1) ...[
            const SizedBox(height: 16),
            Row(
              children: [
                Text(
                  '${meta['count'] ?? items.length} records · Page $page of $pages',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const Spacer(),
                IconButton(
                  tooltip: 'Previous page',
                  onPressed: page > 1 && !c.isLoading
                      ? () => _load(page - 1)
                      : null,
                  icon: const Icon(Icons.chevron_left),
                ),
                IconButton(
                  tooltip: 'Next page',
                  onPressed: page < pages && !c.isLoading
                      ? () => _load(page + 1)
                      : null,
                  icon: const Icon(Icons.chevron_right),
                ),
              ],
            ),
          ],
        ],
      );
    },
  );

  Widget _header(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final heading = Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            widget.title,
            style: widget.embedded
                ? Theme.of(context).textTheme.titleLarge
                : Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 6),
          Text(_subtitle, style: Theme.of(context).textTheme.bodySmall),
        ],
      );
      final add = PillButton(
        label: 'Add ${_singular(widget.resource)}',
        icon: Icons.add,
        primary: true,
        onPressed: () =>
            showResourceEditor(context, widget.controller, widget.resource),
      );
      if (constraints.maxWidth < 540) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [heading, const SizedBox(height: 12), add],
        );
      }
      return Row(
        children: [
          Expanded(child: heading),
          const SizedBox(width: 16),
          add,
        ],
      );
    },
  );

  Widget _filters(BuildContext context) => GlassCard(
    padding: const EdgeInsets.all(16),
    child: LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 480;
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            if (widget.resource == 'transactions') ...[
              SizedBox(
                width: compact ? constraints.maxWidth : 250,
                child: TextField(
                  controller: _search,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _load(),
                  decoration: InputDecoration(
                    labelText: 'Search transactions',
                    suffixIcon: IconButton(
                      tooltip: 'Search transactions',
                      onPressed: () => _load(),
                      icon: const Icon(Icons.search),
                    ),
                  ),
                ),
              ),
              SizedBox(
                width: compact ? constraints.maxWidth : 160,
                child: DropdownButtonFormField<String>(
                  initialValue: _kind,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Type'),
                  items: const [
                    DropdownMenuItem(value: '', child: Text('All types')),
                    DropdownMenuItem(value: 'income', child: Text('Income')),
                    DropdownMenuItem(value: 'expense', child: Text('Expense')),
                    DropdownMenuItem(
                      value: 'transfer',
                      child: Text('Transfer'),
                    ),
                  ],
                  onChanged: (value) {
                    setState(() => _kind = value ?? '');
                    _load();
                  },
                ),
              ),
            ],
            PillButton(
              label: _month.isEmpty ? 'All months' : _month,
              icon: Icons.calendar_today_outlined,
              onPressed: _pickMonth,
            ),
            if (_month.isNotEmpty)
              TextButton(
                onPressed: () {
                  setState(() => _month = '');
                  _load();
                },
                child: const Text('Clear month'),
              ),
          ],
        );
      },
    ),
  );

  String get _subtitle => switch (widget.resource) {
    'transactions' => 'The little moments that make up your money story.',
    'accounts' => 'A clear view of every place your money lives.',
    'categories' => 'Give every transaction a little context.',
    'budgets' => 'Thoughtful limits. A little more room to breathe.',
    'goals' => 'Make space for the things that matter to you.',
    _ => 'Plan the income and bills that come around again.',
  };

  Widget _summaryCard(String label, Object? value) => GlassCard(
    padding: const EdgeInsets.all(18),
    child: SizedBox(
      width: 165,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(color: Palette.muted, fontSize: 11),
          ),
          const SizedBox(height: 6),
          Text(
            money(value, widget.controller.currency),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
        ],
      ),
    ),
  );

  Widget _record(BuildContext context, Map<String, dynamic> item) {
    final resource = widget.resource;
    final name = resource == 'transactions'
        ? ('${item['description'] ?? ''}'.isEmpty
              ? '${item['category_name'] ?? item['kind']}'
              : '${item['description']}')
        : '${item[resource == 'budgets' ? 'category_name' : 'name'] ?? ''}';
    final detail = switch (resource) {
      'transactions' =>
        '${item['date']} · ${item['account_name']}${item['kind'] == 'transfer' ? ' → ${item['to_account_name']}' : ' · ${item['category_name'] ?? 'Uncategorized'}'}',
      'accounts' =>
        'Opening balance ${money(item['opening_balance'], widget.controller.currency)}',
      'categories' =>
        item['kind'] == 'income' ? 'Income category' : 'Expense category',
      'budgets' => '${item['month']} · ${item['status_label']}',
      'goals' =>
        'Target ${item['target_date']} · ${money(item['saved_so_far'], widget.controller.currency)} saved',
      _ =>
        '${item['frequency']} · next ${item['next_date']}${item['active'] == true ? '' : ' · Paused'}',
    };
    final amount = switch (resource) {
      'accounts' => item['balance'],
      'goals' => item['target_amount'],
      'categories' => null,
      _ => item['amount'],
    };
    final icon = switch (resource) {
      'accounts' => Icons.account_balance_wallet_outlined,
      'categories' => Icons.category_outlined,
      'budgets' => Icons.donut_large,
      'goals' => Icons.flag_outlined,
      'recurring' => Icons.autorenew,
      _ =>
        item['kind'] == 'income'
            ? Icons.south_west
            : item['kind'] == 'transfer'
            ? Icons.swap_horiz
            : Icons.north_east,
    };
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 17),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: (item['kind'] == 'income' ? Palette.green : Palette.blue)
                  .withValues(alpha: .08),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(icon, size: 19, color: Palette.blue),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(name, style: const TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(
                  detail,
                  style: const TextStyle(fontSize: 11, color: Palette.muted),
                ),
                if (amount != null) ...[
                  const SizedBox(height: 7),
                  Text(
                    '${resource == 'transactions' && item['kind'] == 'expense' ? '−' : ''}${money(amount, widget.controller.currency)}',
                    style: TextStyle(
                      fontWeight: FontWeight.w600,
                      color: item['kind'] == 'income'
                          ? Palette.green
                          : Palette.ink,
                    ),
                  ),
                ],
                if (resource == 'budgets' || resource == 'goals') ...[
                  const SizedBox(height: 10),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(9),
                    child: LinearProgressIndicator(
                      value: (number(item['percent']) / 100).clamp(0, 1),
                      minHeight: 5,
                      color: resource == 'goals'
                          ? Palette.lavender
                          : Palette.blue,
                      backgroundColor: const Color(0xffededf3),
                    ),
                  ),
                  if (resource == 'budgets')
                    Padding(
                      padding: const EdgeInsets.only(top: 5),
                      child: Text(
                        '${money(item['remaining'], widget.controller.currency)} remaining',
                        style: const TextStyle(
                          fontSize: 11,
                          color: Palette.muted,
                        ),
                      ),
                    ),
                ],
              ],
            ),
          ),
          PopupMenuButton<String>(
            tooltip: 'Record actions',
            enabled: !widget.controller.isLoading,
            onSelected: (action) => action == 'edit'
                ? showResourceEditor(
                    context,
                    widget.controller,
                    resource,
                    item: item,
                  )
                : _delete(item),
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'edit', child: Text('Edit')),
              PopupMenuItem(value: 'delete', child: Text('Delete')),
            ],
          ),
        ],
      ),
    );
  }
}

class _ResourceEditor extends StatefulWidget {
  const _ResourceEditor({
    required this.controller,
    required this.resource,
    this.item,
  });
  final AppController controller;
  final String resource;
  final Map<String, dynamic>? item;
  @override
  State<_ResourceEditor> createState() => _ResourceEditorState();
}

class _ResourceEditorState extends State<_ResourceEditor> {
  final _form = GlobalKey<FormState>();
  final _text = <String, TextEditingController>{};
  late Map<String, dynamic> _values;
  List<Map<String, dynamic>> _accounts = [], _categories = [];
  bool _loading = false, _saving = false;
  String? _error;
  @override
  void initState() {
    super.initState();
    final today = _date(DateTime.now());
    _values = {
      'kind': 'expense',
      'frequency': 'monthly',
      'active': true,
      'date': today,
      'next_date': today,
      'target_date': _date(DateTime.now().add(const Duration(days: 180))),
      'month': today.substring(0, 7),
      'opening_balance': '0.00',
      'saved_so_far': '0.00',
      ...?widget.item,
    };
    for (final field in [
      'name',
      'description',
      'amount',
      'opening_balance',
      'target_amount',
      'saved_so_far',
      'date',
      'next_date',
      'end_date',
      'target_date',
      'month',
    ]) {
      _text[field] = TextEditingController(text: '${_values[field] ?? ''}');
    }
    if (widget.resource == 'transactions' || widget.resource == 'budgets') {
      _loadChoices();
    }
  }

  @override
  void dispose() {
    for (final controller in _text.values) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<List<Map<String, dynamic>>> _allChoices(String resource) async {
    final result = <Map<String, dynamic>>[];
    var page = 1;
    while (true) {
      final response = await widget.controller.api.listResource(
        resource,
        query: {'page': page, 'page_size': 200},
      );
      result.addAll(maps(response['results']));
      if (page >= (_id(response['pages']) ?? 1)) return result;
      page++;
    }
  }

  Future<void> _loadChoices() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _allChoices('accounts'),
        _allChoices('categories'),
      ]);
      if (!mounted) return;
      setState(() {
        _accounts = results[0];
        _categories = results[1];
      });
    } catch (error) {
      if (mounted) {
        setState(
          () => _error = error is ApiException
              ? error.message
              : 'Could not load your accounts and categories. Please retry.',
        );
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String? _serverError(String field) =>
      widget.controller.fieldErrors[field]?.join('\n');
  Widget _field(
    String name,
    String label, {
    bool amount = false,
    bool positive = true,
    bool signed = false,
    bool optional = false,
    int maxLength = 100,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: TextFormField(
      controller: _text[name],
      maxLength: amount ? null : maxLength,
      keyboardType: amount
          ? const TextInputType.numberWithOptions(decimal: true, signed: true)
          : TextInputType.text,
      decoration: InputDecoration(
        labelText: label,
        counterText: '',
        errorText: _serverError(name),
      ),
      validator: (raw) {
        final value = (raw ?? '').trim();
        if (optional && value.isEmpty) return null;
        if (value.isEmpty) return 'Enter ${label.toLowerCase()}.';
        if (amount) {
          final expression = signed
              ? r'^-?\d{1,10}(\.\d{1,2})?$'
              : r'^\d{1,10}(\.\d{1,2})?$';
          if (!RegExp(expression).hasMatch(value)) {
            return 'Use a number with up to two decimal places.';
          }
          if (positive && !RegExp(r'[1-9]').hasMatch(value)) {
            return 'Use an amount greater than zero.';
          }
        }
        return null;
      },
    ),
  );

  Widget _select(
    String field,
    String label,
    List<DropdownMenuItem<String>> items, {
    bool optional = false,
  }) {
    final selected = _values[field]?.toString();
    final valid = items.any((item) => item.value == selected) ? selected : null;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: DropdownButtonFormField<String>(
        key: ValueKey('$field:$valid'),
        initialValue: valid,
        isExpanded: true,
        decoration: InputDecoration(
          labelText: label,
          errorText: _serverError(field),
        ),
        items: items,
        validator: (value) => !optional && (value == null || value.isEmpty)
            ? 'Choose ${label.toLowerCase()}.'
            : null,
        onChanged: (value) => setState(() {
          _values[field] = value;
          if (field == 'kind') {
            _values['category'] = null;
            if (value != 'transfer') _values['to_account'] = null;
          }
          if (field == 'account' &&
              value == _values['to_account']?.toString()) {
            _values['to_account'] = null;
          }
        }),
      ),
    );
  }

  Widget _kind({bool transfers = false}) => _select('kind', 'Type', [
    const DropdownMenuItem(value: 'expense', child: Text('Expense')),
    const DropdownMenuItem(value: 'income', child: Text('Income')),
    if (transfers)
      const DropdownMenuItem(value: 'transfer', child: Text('Transfer')),
  ]);
  Widget _account(String field, String label) => _select(
    field,
    label,
    _accounts
        .where(
          (item) =>
              field != 'to_account' ||
              item['id'].toString() != _values['account']?.toString(),
        )
        .map(
          (item) => DropdownMenuItem(
            value: '${item['id']}',
            child: Text('${item['name']}'),
          ),
        )
        .toList(),
  );
  Widget _category({bool budget = false}) => _select('category', 'Category', [
    if (!budget)
      const DropdownMenuItem(value: '', child: Text('Uncategorized')),
    ..._categories
        .where((item) => item['kind'] == (budget ? 'expense' : _values['kind']))
        .map(
          (item) => DropdownMenuItem(
            value: '${item['id']}',
            child: Text('${item['name']}'),
          ),
        ),
  ], optional: !budget);

  Widget _dateField(
    String field,
    String label, {
    bool optional = false,
    bool month = false,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: TextFormField(
      controller: _text[field],
      readOnly: true,
      decoration: InputDecoration(
        labelText: label,
        errorText: _serverError(field),
        suffixIcon: optional
            ? IconButton(
                tooltip: 'Clear date',
                onPressed: () => setState(() => _text[field]!.clear()),
                icon: const Icon(Icons.close, size: 18),
              )
            : const Icon(Icons.calendar_today_outlined, size: 18),
      ),
      validator: (value) => !optional && (value == null || value.isEmpty)
          ? 'Choose a date.'
          : null,
      onTap: () async {
        final now = DateTime.now();
        final last = widget.resource == 'transactions'
            ? now
            : DateTime(2100, 12, 31);
        var initial =
            DateTime.tryParse('${_text[field]!.text}${month ? '-01' : ''}') ??
            now;
        if (initial.isAfter(last)) initial = last;
        if (initial.isBefore(DateTime(1900))) initial = DateTime(1900);
        final result = await showDatePicker(
          context: context,
          initialDate: initial,
          firstDate: DateTime(1900),
          lastDate: last,
          helpText: month ? 'Choose any date in the budget month' : label,
        );
        if (result != null && mounted) {
          setState(
            () => _text[field]!.text = month
                ? _date(result).substring(0, 7)
                : _date(result),
          );
        }
      },
    ),
  );

  List<Widget> _fields() => switch (widget.resource) {
    'accounts' => [
      _field('name', 'Account name'),
      _field(
        'opening_balance',
        'Opening balance',
        amount: true,
        positive: false,
        signed: true,
      ),
    ],
    'categories' => [_field('name', 'Category name', maxLength: 60), _kind()],
    'transactions' => [
      _kind(transfers: true),
      _account('account', 'From account'),
      if (_values['kind'] == 'transfer')
        _account('to_account', 'To account')
      else
        _category(),
      _field('amount', 'Amount', amount: true),
      _dateField('date', 'Transaction date'),
      _field(
        'description',
        'Description (optional)',
        optional: true,
        maxLength: 200,
      ),
      const Text(
        'Record money that has already moved. Use recurring items or the planner for future payments.',
        style: TextStyle(fontSize: 11, color: Palette.muted),
      ),
    ],
    'budgets' => [
      _category(budget: true),
      _dateField('month', 'Budget month', month: true),
      _field('amount', 'Monthly limit', amount: true),
    ],
    'goals' => [
      _field('name', 'Goal name'),
      _field('target_amount', 'Target amount', amount: true),
      _field('saved_so_far', 'Saved so far', amount: true, positive: false),
      _dateField('target_date', 'Target date'),
      const Text(
        'Updating this goal does not move money between accounts.',
        style: TextStyle(fontSize: 11, color: Palette.muted),
      ),
    ],
    'recurring' => [
      _field('name', 'Name'),
      _kind(),
      _field('amount', 'Amount', amount: true),
      _select('frequency', 'Frequency', const [
        DropdownMenuItem(value: 'monthly', child: Text('Monthly')),
        DropdownMenuItem(value: 'weekly', child: Text('Weekly')),
      ]),
      _dateField('next_date', 'Next date'),
      _dateField('end_date', 'End date (optional)', optional: true),
      SwitchListTile(
        contentPadding: EdgeInsets.zero,
        title: const Text('Include in forecast'),
        value: _values['active'] == true,
        onChanged: (value) => setState(() => _values['active'] = value),
      ),
      const Text(
        'This schedule informs your forecast. It does not automatically post transactions.',
        style: TextStyle(fontSize: 11, color: Palette.muted),
      ),
    ],
    _ => [],
  };

  Future<void> _save() async {
    if (_saving || !_form.currentState!.validate()) return;
    final names = switch (widget.resource) {
      'accounts' => ['name', 'opening_balance'],
      'categories' => ['name', 'kind'],
      'transactions' => [
        'kind',
        'account',
        'to_account',
        'category',
        'amount',
        'date',
        'description',
      ],
      'budgets' => ['category', 'month', 'amount'],
      'goals' => ['name', 'target_amount', 'saved_so_far', 'target_date'],
      'recurring' => [
        'name',
        'kind',
        'amount',
        'frequency',
        'next_date',
        'end_date',
        'active',
      ],
      _ => <String>[],
    };
    final payload = <String, dynamic>{
      for (final name in names)
        name: _text.containsKey(name)
            ? _text[name]!.text.trim()
            : _values[name],
    };
    for (final name in ['account', 'to_account', 'category']) {
      if (payload.containsKey(name)) payload[name] = _id(payload[name]);
    }
    if (payload['kind'] == 'transfer') payload['category'] = null;
    if (payload['kind'] != 'transfer' && payload.containsKey('to_account')) {
      payload['to_account'] = null;
    }
    if (payload['end_date'] == '') payload['end_date'] = null;
    setState(() {
      _saving = true;
      _error = null;
    });
    final saved = await widget.controller.saveResource(
      widget.resource,
      payload,
      id: _id(widget.item?['id']),
    );
    if (!mounted) return;
    if (saved) {
      Navigator.pop(context);
    } else {
      setState(() {
        _saving = false;
        _error = widget.controller.error;
      });
    }
  }

  @override
  Widget build(BuildContext context) => PopScope(
    canPop: !_saving,
    child: AlertDialog(
      title: Text(
        '${widget.item == null ? 'Add' : 'Edit'} ${_singular(widget.resource)}',
      ),
      content: SizedBox(
        width: 460,
        child: SingleChildScrollView(
          child: Form(
            key: _form,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_loading)
                  const Padding(
                    padding: EdgeInsets.all(30),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _error!,
                          style: const TextStyle(color: Color(0xffa43b2d)),
                        ),
                        if (widget.controller.fieldErrors['__all__'] != null)
                          Text(
                            widget.controller.fieldErrors['__all__']!.join(
                              '\n',
                            ),
                          ),
                        if (!_loading &&
                            (widget.resource == 'transactions' ||
                                widget.resource == 'budgets') &&
                            _accounts.isEmpty &&
                            _categories.isEmpty)
                          TextButton(
                            onPressed: _loadChoices,
                            child: const Text('Retry loading choices'),
                          ),
                      ],
                    ),
                  ),
                if (!_loading) ..._fields(),
                if (!_loading &&
                    widget.resource == 'transactions' &&
                    _accounts.isEmpty)
                  const Padding(
                    padding: EdgeInsets.only(top: 12),
                    child: Text(
                      'Create an account before recording a transaction.',
                      style: TextStyle(color: Palette.blue),
                    ),
                  ),
                if (!_loading &&
                    widget.resource == 'budgets' &&
                    !_categories.any((item) => item['kind'] == 'expense'))
                  const Padding(
                    padding: EdgeInsets.only(top: 12),
                    child: Text(
                      'Create an expense category before setting a budget.',
                      style: TextStyle(color: Palette.blue),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _loading || _saving ? null : _save,
          child: Text(_saving ? 'Saving…' : 'Save'),
        ),
      ],
    ),
  );
}
