import 'dart:convert';
import 'package:material_ui/material_ui.dart';
import '../data/app_controller.dart';
import 'design.dart';

class AssistantScreen extends StatefulWidget {
  const AssistantScreen({super.key, required this.controller});
  final AppController controller;
  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

class _AssistantScreenState extends State<AssistantScreen> {
  final question = TextEditingController();
  bool share = false;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) widget.controller.loadAssistant();
    });
  }

  @override
  void dispose() {
    question.dispose();
    super.dispose();
  }

  Future<void> ask() async {
    final text = question.text.trim();
    if (text.isEmpty) return;
    setState(() => share = false);
    await widget.controller.askAssistant(text, shareSummary: true);
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.controller;
    final data = c.assistantInfo;
    final status = mapOf(data['status']);
    final summary = mapOf(data['summary']);
    final ready = status['ready'] == true;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'A fresh perspective.',
          style: Theme.of(context).textTheme.headlineLarge,
        ),
        const SizedBox(height: 8),
        const Text(
          'Make sense of your money with a model you control.',
          style: TextStyle(color: Palette.muted),
        ),
        const SizedBox(height: 26),
        GlassCard(
          color: const Color(0xffe8e1fb).withValues(alpha: .7),
          child: Row(
            children: [
              const Icon(
                Icons.auto_awesome_outlined,
                color: Palette.ink,
                size: 30,
              ),
              const SizedBox(width: 18),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Your local companion',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      status['detail']?.toString() ??
                          'Checking your local model…',
                      style: const TextStyle(
                        color: Palette.muted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              TinyTag(
                status['label']?.toString() ?? 'Checking',
                color: ready ? Palette.green : Palette.ink,
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        GlassCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SectionHeading(
                title: 'Start with a question',
                subtitle:
                    'Model: ${data['model'] ?? 'Ollama'} · read-only answers',
              ),
              const SizedBox(height: 18),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  for (final prompt in [
                    'Where is my spending going?',
                    'Explain my next 30 days.',
                    'What should I review this month?',
                  ])
                    ActionChip(
                      label: Text(prompt, style: const TextStyle(fontSize: 11)),
                      onPressed: () => setState(() => question.text = prompt),
                    ),
                ],
              ),
              const SizedBox(height: 20),
              TextField(
                controller: question,
                maxLength: 2000,
                minLines: 3,
                maxLines: 6,
                decoration: const InputDecoration(
                  labelText: 'What’s on your mind?',
                  hintText: 'Ask about your spending or upcoming plans',
                ),
                onChanged: (_) => setState(() {}),
              ),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: share,
                onChanged: c.isLoading
                    ? null
                    : (v) => setState(() => share = v ?? false),
                controlAffinity: ListTileControlAffinity.leading,
                title: const Text(
                  'Share this summary with my configured local model for this question.',
                  style: TextStyle(fontSize: 12),
                ),
              ),
              const Text(
                'Only the summary below and your question are sent. Account names and transaction descriptions are excluded. The model cannot change records.',
                style: TextStyle(color: Palette.muted, fontSize: 11),
              ),
              const SizedBox(height: 18),
              PillButton(
                label: c.isLoading ? 'Working…' : 'Ask my local AI',
                icon: Icons.arrow_upward_rounded,
                primary: true,
                onPressed:
                    ready &&
                        share &&
                        question.text.trim().isNotEmpty &&
                        !c.isLoading
                    ? ask
                    : null,
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        if (c.assistantAnswer != null) ...[
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionHeading(
                  title: 'A little more clarity',
                  trailing: TinyTag('AI response'),
                ),
                const SizedBox(height: 18),
                SelectableText(
                  c.assistantAnswer!,
                  style: const TextStyle(fontSize: 14, height: 1.75),
                ),
                const SizedBox(height: 20),
                const Text(
                  'Check suggestions against your records. AI can make mistakes.',
                  style: TextStyle(fontSize: 11, color: Palette.muted),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],
        if (summary.isNotEmpty)
          GlassCard(
            child: ExpansionTile(
              tilePadding: EdgeInsets.zero,
              childrenPadding: const EdgeInsets.only(bottom: 12),
              title: const Text(
                'Preview the exact summary',
                style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14),
              ),
              subtitle: const Text(
                'You decide when to share it.',
                style: TextStyle(fontSize: 11, color: Palette.muted),
              ),
              children: [
                Align(
                  alignment: Alignment.centerLeft,
                  child: SelectableText(
                    const JsonEncoder.withIndent('  ').convert(summary),
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 12,
                      height: 1.6,
                    ),
                  ),
                ),
              ],
            ),
          ),
        if (!ready) ...[
          const SizedBox(height: 20),
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionHeading(
                  title: 'Connect an open model',
                  subtitle:
                      'Set this up on the computer running your PocketLedger server.',
                ),
                const SizedBox(height: 16),
                const SelectableText(
              '1. Install Ollama and run: ollama pull qwen3:4b\n2. Set the server environment variable OLLAMA_ENABLED=1.\n3. Restart the server, then check the connection.',
                  style: TextStyle(fontSize: 13, height: 1.8),
                ),
                const SizedBox(height: 16),
                PillButton(
                  label: 'Check connection',
                  icon: Icons.refresh_rounded,
                  onPressed: c.isLoading ? null : c.loadAssistant,
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }
}
