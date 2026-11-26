import 'dart:math' as math;
import 'package:material_ui/material_ui.dart';
import '../data/money.dart';

abstract final class Palette {
  static const ink = Color(0xff252733);
  static const muted = Color(0xff85868d);
  static const blue = Color(0xff3473e8);
  static const amber = Color(0xffffc54d);
  static const lavender = Color(0xffb9a7eb);
  static const green = Color(0xff3f957d);
  static const orange = Color(0xffe8832a);
  static const canvas = Color(0xffe9e9ea);
}

String money(Object? value, [String currency = 'MAD']) =>
    formatMoney(value, currency: currency);
double number(Object? value) => double.tryParse('$value') ?? 0;
List<Map<String, dynamic>> maps(Object? value) => value is List
    ? value.whereType<Map>().map((v) => Map<String, dynamic>.from(v)).toList()
    : [];
Map<String, dynamic> mapOf(Object? value) =>
    value is Map ? Map<String, dynamic>.from(value) : {};

ThemeData appTheme() => ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: Colors.transparent,
  colorScheme: ColorScheme.fromSeed(
    seedColor: Palette.blue,
    surface: Colors.white,
  ),
  fontFamily: 'Arial',
  textTheme: const TextTheme(
    headlineLarge: TextStyle(
      fontSize: 54,
      height: 1.04,
      fontWeight: FontWeight.w700,
      letterSpacing: -2.4,
      color: Palette.ink,
    ),
    headlineMedium: TextStyle(
      fontSize: 38,
      height: 1.08,
      fontWeight: FontWeight.w700,
      letterSpacing: -1.6,
      color: Palette.ink,
    ),
    titleLarge: TextStyle(
      fontSize: 20,
      fontWeight: FontWeight.w600,
      letterSpacing: -.6,
      color: Palette.ink,
    ),
    titleMedium: TextStyle(
      fontSize: 15,
      fontWeight: FontWeight.w600,
      color: Palette.ink,
    ),
    bodyMedium: TextStyle(fontSize: 13, height: 1.5, color: Palette.ink),
    bodySmall: TextStyle(fontSize: 11, height: 1.5, color: Palette.muted),
  ),
  inputDecorationTheme: InputDecorationTheme(
    filled: true,
    fillColor: const Color(0xfff7f7f9),
    border: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: BorderSide.none,
    ),
    focusedBorder: OutlineInputBorder(
      borderRadius: BorderRadius.circular(16),
      borderSide: const BorderSide(color: Palette.blue),
    ),
    contentPadding: const EdgeInsets.symmetric(horizontal: 17, vertical: 18),
    labelStyle: const TextStyle(color: Palette.muted, fontSize: 13),
  ),
  dialogTheme: const DialogThemeData(
    backgroundColor: Color(0xfffcfcfe),
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.all(Radius.circular(28)),
    ),
  ),
  dividerColor: const Color(0xffededf1),
);

class GlassCard extends StatelessWidget {
  const GlassCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(24),
    this.color,
    this.gradient,
    this.radius = 34,
  });
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? color;

  /// When set, paints this gradient instead of a flat colour (hero tiles).
  final Gradient? gradient;
  final double radius;

  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
    // Continuous ("squircle") corners flow into the straight edges like the
    // reference widgets, instead of the basic circular-arc rounded rectangle.
    clipBehavior: Clip.antiAlias,
    decoration: ShapeDecoration(
      color: gradient == null
          ? (color ?? Colors.white.withValues(alpha: .92))
          : null,
      gradient: gradient,
      shape: ContinuousRectangleBorder(
        borderRadius: BorderRadius.circular(radius * 1.7),
        side: BorderSide(
          color: Colors.white.withValues(alpha: .7),
          width: 1.2,
        ),
      ),
      shadows: [
        BoxShadow(
          color: const Color(0xff7a5a2a).withValues(alpha: .10),
          blurRadius: 36,
          offset: const Offset(0, 14),
        ),
      ],
    ),
    child: Material(type: MaterialType.transparency, child: child),
  );
}

class SectionHeading extends StatelessWidget {
  const SectionHeading({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
  });
  final String title;
  final String? subtitle;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) => Row(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Expanded(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: Theme.of(context).textTheme.titleMedium),
            if (subtitle != null) ...[
              const SizedBox(height: 5),
              Text(subtitle!, style: Theme.of(context).textTheme.bodySmall),
            ],
          ],
        ),
      ),
      if (trailing != null) ...[const SizedBox(width: 12), trailing!],
    ],
  );
}

class PillButton extends StatelessWidget {
  const PillButton({
    super.key,
    required this.label,
    this.icon,
    this.onPressed,
    this.primary = false,
  });
  final String label;
  final IconData? icon;
  final VoidCallback? onPressed;
  final bool primary;
  @override
  Widget build(BuildContext context) => FilledButton(
    onPressed: onPressed,
    style: FilledButton.styleFrom(
      backgroundColor: primary
          ? Palette.ink
          : Colors.white.withValues(alpha: .85),
      foregroundColor: primary ? Colors.white : Palette.ink,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      shape: const StadiumBorder(),
      elevation: 0,
    ),
    child: Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (icon != null) ...[Icon(icon, size: 17), const SizedBox(width: 9)],
        Flexible(
          child: Text(
            label,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
          ),
        ),
      ],
    ),
  );
}

class TinyTag extends StatelessWidget {
  const TinyTag(this.label, {super.key, this.color = Palette.blue});
  final String label;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
    decoration: BoxDecoration(
      color: color.withValues(alpha: .1),
      borderRadius: BorderRadius.circular(30),
    ),
    child: Text(
      label,
      style: TextStyle(fontSize: 10, color: color, fontWeight: FontWeight.w600),
    ),
  );
}

class HoverLift extends StatefulWidget {
  const HoverLift({super.key, required this.child});
  final Widget child;
  @override
  State<HoverLift> createState() => _HoverLiftState();
}

class _HoverLiftState extends State<HoverLift> {
  bool hover = false;
  @override
  Widget build(BuildContext context) => MouseRegion(
    onEnter: (_) => setState(() => hover = true),
    onExit: (_) => setState(() => hover = false),
    child: AnimatedScale(
      scale: hover && !MediaQuery.disableAnimationsOf(context) ? 1.015 : 1,
      duration: const Duration(milliseconds: 380),
      curve: Curves.easeOutBack,
      child: AnimatedSlide(
        offset: Offset(
          0,
          hover && !MediaQuery.disableAnimationsOf(context) ? -.016 : 0,
        ),
        duration: const Duration(milliseconds: 380),
        curve: Curves.easeOutBack,
        child: widget.child,
      ),
    ),
  );
}

class LiquidBackdrop extends StatefulWidget {
  const LiquidBackdrop({super.key, required this.child, required this.motion});
  final Widget child;
  final bool motion;
  @override
  State<LiquidBackdrop> createState() => _LiquidBackdropState();
}

class _LiquidBackdropState extends State<LiquidBackdrop>
    with SingleTickerProviderStateMixin {
  late final AnimationController flow = AnimationController(
    vsync: this,
    duration: const Duration(seconds: 24),
  );
  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _sync();
  }

  @override
  void didUpdateWidget(covariant LiquidBackdrop old) {
    super.didUpdateWidget(old);
    _sync();
  }

  void _sync() {
    if (widget.motion && !MediaQuery.disableAnimationsOf(context)) {
      flow.repeat();
    } else {
      flow.stop();
    }
  }

  @override
  void dispose() {
    flow.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Stack(
    children: [
      Positioned.fill(
        child: RepaintBoundary(
          child: AnimatedBuilder(
            animation: flow,
            builder: (_, child) =>
                CustomPaint(painter: _WaterPainter(flow.value)),
          ),
        ),
      ),
      widget.child,
    ],
  );
}

class _WaterPainter extends CustomPainter {
  _WaterPainter(this.t);
  final double t;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.drawRect(Offset.zero & size, Paint()..color = Palette.canvas);
    // Whole-number speed multipliers keep the 24 s loop seamless.
    final phase = t * math.pi * 2;
    final unit = math.max(size.width, size.height);

    void blob({
      required double x,
      required double y,
      required double driftX,
      required double driftY,
      required int speedX,
      required int speedY,
      required double shift,
      required double radius,
      required Color color,
      required double alpha,
    }) {
      final at = Offset(
        size.width * x + math.sin(phase * speedX + shift) * unit * driftX,
        size.height * y + math.cos(phase * speedY + shift) * unit * driftY,
      );
      final r = unit * radius;
      canvas.drawCircle(
        at,
        r,
        Paint()
          ..shader = RadialGradient(
            colors: [color.withValues(alpha: alpha), color.withValues(alpha: 0)],
          ).createShader(Rect.fromCircle(center: at, radius: r)),
      );
    }

    // Soft, liquid colour fields: yellow glow, orange body, amber, cool teal.
    blob(
      x: .05, y: .10, driftX: .05, driftY: .04, speedX: 1, speedY: 2,
      shift: 0, radius: .30, color: const Color(0xfff7d7a8), alpha: .7,
    );
    blob(
      x: .50, y: .06, driftX: .08, driftY: .05, speedX: 1, speedY: 1,
      shift: 1.2, radius: .40, color: const Color(0xfff0df5a), alpha: .75,
    );
    blob(
      x: .22, y: .64, driftX: .09, driftY: .06, speedX: 2, speedY: 1,
      shift: 2.4, radius: .38, color: const Color(0xffee8f2b), alpha: .85,
    );
    blob(
      x: .80, y: .40, driftX: .07, driftY: .08, speedX: 1, speedY: 3,
      shift: 3.6, radius: .34, color: const Color(0xfff6b43c), alpha: .75,
    );
    blob(
      x: .95, y: .92, driftX: .08, driftY: .05, speedX: 3, speedY: 1,
      shift: 4.8, radius: .38, color: const Color(0xff9ec4d6), alpha: .75,
    );
  }

  @override
  bool shouldRepaint(_WaterPainter old) => old.t != t;
}

class Reveal extends StatelessWidget {
  const Reveal({super.key, required this.child, this.delay = Duration.zero});
  final Widget child;

  /// Wait this long before easing in; use small steps (60-90 ms) to stagger
  /// a list of cards so they flow in one after another.
  final Duration delay;
  @override
  Widget build(BuildContext context) {
    final still = MediaQuery.disableAnimationsOf(context);
    final total = 700 + delay.inMilliseconds;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: still ? 0 : total),
      curve: Interval(
        delay.inMilliseconds / total,
        1,
        curve: Curves.easeOutQuart,
      ),
      // Slide only: no per-frame opacity layer over the whole page.
      builder: (_, v, child) =>
          Transform.translate(offset: Offset(0, 22 * (1 - v)), child: child),
      child: child,
    );
  }
}

class EmptyPanel extends StatelessWidget {
  const EmptyPanel({
    super.key,
    required this.title,
    required this.message,
    this.action,
  });
  final String title, message;
  final Widget? action;
  @override
  Widget build(BuildContext context) => GlassCard(
    child: Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 30),
        child: Column(
          children: [
            const Icon(
              Icons.water_drop_outlined,
              color: Palette.amber,
              size: 40,
            ),
            const SizedBox(height: 16),
            Text(title, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (action != null) ...[const SizedBox(height: 22), action!],
          ],
        ),
      ),
    ),
  );
}
