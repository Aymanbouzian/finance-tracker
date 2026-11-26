import 'dart:math' as math;
import 'package:material_ui/material_ui.dart';
import 'design.dart';

class FlowChart extends StatefulWidget {
  const FlowChart({
    super.key,
    required this.primary,
    required this.secondary,
    required this.labels,
    this.primaryLabel = 'Income',
    this.secondaryLabel = 'Expenses',
    this.height = 230,
  });
  final List<double> primary, secondary;
  final List<String> labels;
  final String primaryLabel, secondaryLabel;
  final double height;
  @override
  State<FlowChart> createState() => _FlowChartState();
}

class _FlowChartState extends State<FlowChart> {
  int? selected;
  @override
  Widget build(BuildContext context) {
    final all = [...widget.primary, ...widget.secondary];
    if (all.isEmpty) {
      return const SizedBox(
        height: 220,
        child: Center(
          child: Text('Your chart will appear as you add records.'),
        ),
      );
    }
    final high = all.reduce(math.max);
    final low = math.min(0.0, all.reduce(math.min));
    final top = high <= 0 ? 1.0 : high * 1.16;
    return Column(
      children: [
        SizedBox(
          height: widget.height,
          child: Row(
            children: [
              SizedBox(
                width: 42,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: List.generate(
                    5,
                    (i) => Text(
                      _axis(top - (top - low) * i / 4),
                      style: const TextStyle(
                        fontSize: 10,
                        color: Palette.muted,
                      ),
                    ),
                  ),
                ),
              ),
              Expanded(
                child: LayoutBuilder(
                  builder: (context, box) => MouseRegion(
                    onExit: (_) => setState(() => selected = null),
                    onHover: (e) => setState(
                      () => selected =
                          ((e.localPosition.dx / box.maxWidth) *
                                  (widget.primary.length - 1))
                              .round()
                              .clamp(0, widget.primary.length - 1),
                    ),
                    child: GestureDetector(
                      onTapDown: (e) => setState(
                        () => selected =
                            ((e.localPosition.dx / box.maxWidth) *
                                    (widget.primary.length - 1))
                                .round()
                                .clamp(0, widget.primary.length - 1),
                      ),
                      child: TweenAnimationBuilder<double>(
                        tween: Tween(begin: 0, end: 1),
                        duration: Duration(
                          milliseconds: MediaQuery.disableAnimationsOf(context)
                              ? 0
                              : 1000,
                        ),
                        curve: Curves.easeOutCubic,
                        builder: (_, v, __) => CustomPaint(
                          size: Size(box.maxWidth, widget.height),
                          painter: _LinePainter(
                            widget.primary,
                            widget.secondary,
                            low,
                            top,
                            v,
                            selected,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 13),
        Padding(
          padding: const EdgeInsets.only(left: 42),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: _labelIndexes(widget.labels.length)
                .map(
                  (i) => Text(
                    widget.labels[i],
                    style: const TextStyle(fontSize: 10, color: Palette.muted),
                  ),
                )
                .toList(),
          ),
        ),
        const SizedBox(height: 20),
        Wrap(
          spacing: 20,
          runSpacing: 8,
          children: [
            _legend(Palette.blue, widget.primaryLabel),
            _legend(Palette.amber, widget.secondaryLabel),
            if (selected != null && selected! < widget.primary.length)
              Text(
                '${widget.labels[selected!]}  ·  ${formatChart(widget.primary[selected!])} / ${formatChart(widget.secondary[selected!])}',
                style: const TextStyle(fontSize: 10, color: Palette.ink),
              ),
          ],
        ),
      ],
    );
  }

  Widget _legend(Color c, String label) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Container(
        width: 7,
        height: 7,
        decoration: BoxDecoration(color: c, shape: BoxShape.circle),
      ),
      const SizedBox(width: 6),
      Text(label, style: const TextStyle(fontSize: 11, color: Palette.muted)),
    ],
  );
  List<int> _labelIndexes(int count) => count <= 6
      ? List.generate(count, (i) => i)
      : List.generate(6, (i) => (i * (count - 1) / 5).round());
  String _axis(double n) => n.abs() >= 1000
      ? '${(n / 1000).toStringAsFixed(1)}k'
      : n.toStringAsFixed(0);
  String formatChart(double n) => n.toStringAsFixed(2);
}

class _LinePainter extends CustomPainter {
  _LinePainter(
    this.a,
    this.b,
    this.low,
    this.high,
    this.progress,
    this.selected,
  );
  final List<double> a, b;
  final double low, high, progress;
  final int? selected;
  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()
      ..color = const Color(0xffefeff3)
      ..strokeWidth = 1;
    for (var i = 0; i < 5; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    Offset point(List<double> data, int i) => Offset(
      data.length <= 1 ? size.width / 2 : i * size.width / (data.length - 1),
      size.height * (1 - (data[i] - low) / (high - low)),
    );
    void plot(List<double> data, Color color, bool fill) {
      if (data.isEmpty) return;
      final p = Path()..moveTo(point(data, 0).dx, point(data, 0).dy);
      for (var i = 1; i < data.length; i++) {
        final prev = point(data, i - 1);
        final next = point(data, i);
        final mid = (prev.dx + next.dx) / 2;
        p.cubicTo(mid, prev.dy, mid, next.dy, next.dx, next.dy);
      }
      canvas.save();
      canvas.clipRect(
        Rect.fromLTWH(0, 0, size.width * progress, size.height + 6),
      );
      if (fill && data.length > 1) {
        final area = Path.from(p)
          ..lineTo(size.width, size.height)
          ..lineTo(0, size.height)
          ..close();
        canvas.drawPath(
          area,
          Paint()
            ..shader = LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                color.withValues(alpha: .14),
                color.withValues(alpha: 0),
              ],
            ).createShader(Offset.zero & size),
        );
      }
      canvas.drawPath(
        p,
        Paint()
          ..color = color
          ..strokeWidth = 2.7
          ..strokeCap = StrokeCap.round
          ..style = PaintingStyle.stroke,
      );
      if (data.length <= 7) {
        for (var i = 0; i < data.length; i++) {
          canvas.drawCircle(point(data, i), 3, Paint()..color = color);
          canvas.drawCircle(point(data, i), 1.4, Paint()..color = Colors.white);
        }
      }
      canvas.restore();
    }

    plot(b, Palette.amber, false);
    plot(a, Palette.blue, true);
    if (selected != null && selected! < a.length) {
      final p = point(a, selected!);
      canvas.drawLine(
        Offset(p.dx, 0),
        Offset(p.dx, size.height),
        Paint()
          ..color = Palette.blue.withValues(alpha: .14)
          ..strokeWidth = 1,
      );
      canvas.drawCircle(
        p,
        7,
        Paint()..color = Palette.blue.withValues(alpha: .15),
      );
      canvas.drawCircle(p, 4, Paint()..color = Palette.blue);
    }
  }

  @override
  bool shouldRepaint(_LinePainter old) => true;
}

class LiquidRing extends StatelessWidget {
  const LiquidRing({
    super.key,
    required this.value,
    required this.label,
    required this.subtitle,
    this.color = Palette.blue,
  });
  final double value;
  final String label, subtitle;
  final Color color;
  @override
  Widget build(BuildContext context) => TweenAnimationBuilder<double>(
    tween: Tween(begin: 0, end: value.clamp(0, 1)),
    duration: Duration(
      milliseconds: MediaQuery.disableAnimationsOf(context) ? 0 : 1100,
    ),
    curve: Curves.easeOutCubic,
    builder: (_, v, __) => SizedBox(
      width: 160,
      height: 160,
      child: CustomPaint(
        painter: _RingPainter(v, color),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                label,
                style: const TextStyle(
                  fontSize: 27,
                  letterSpacing: -1,
                  fontWeight: FontWeight.w600,
                  color: Palette.ink,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                subtitle,
                style: const TextStyle(fontSize: 10, color: Palette.muted),
              ),
            ],
          ),
        ),
      ),
    ),
  );
}

class _RingPainter extends CustomPainter {
  _RingPainter(this.v, this.color);
  final double v;
  final Color color;
  @override
  void paint(Canvas canvas, Size size) {
    final r = Rect.fromLTWH(10, 10, size.width - 20, size.height - 20);
    canvas.drawArc(
      r,
      math.pi * .72,
      math.pi * 1.56,
      false,
      Paint()
        ..color = Colors.white.withValues(alpha: .6)
        ..strokeWidth = 11
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round,
    );
    canvas.drawArc(
      r,
      math.pi * .72,
      math.pi * 1.56 * v,
      false,
      Paint()
        ..shader = SweepGradient(
          colors: [color.withValues(alpha: .3), color],
          startAngle: math.pi * .72,
          endAngle: math.pi * 2.28,
        ).createShader(r)
        ..strokeWidth = 11
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round,
    );
  }

  @override
  bool shouldRepaint(_RingPainter old) => old.v != v || old.color != color;
}
