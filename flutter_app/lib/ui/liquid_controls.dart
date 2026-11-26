import 'dart:math' as math;

import 'package:material_ui/material_ui.dart';

import 'design.dart';

class LiquidSegmentedControl extends StatelessWidget {
  const LiquidSegmentedControl({
    super.key,
    required this.labels,
    required this.selected,
    required this.onSelected,
  });

  final List<String> labels;
  final int selected;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final reducedMotion = MediaQuery.disableAnimationsOf(context);
    final textScale = MediaQuery.textScalerOf(context).scale(14) / 14;
    return LayoutBuilder(
      builder: (context, constraints) {
        final segmentWidth = math.max(
          110.0 * textScale,
          (constraints.maxWidth - 8) / labels.length,
        );
        final height = math.max(48.0, 30 * textScale);
        return SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: const Color(0xffe9eef3),
              borderRadius: BorderRadius.circular(32),
            ),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: SizedBox(
                width: segmentWidth * labels.length,
                height: height,
                child: Stack(
                  children: [
                    TweenAnimationBuilder<double>(
                      tween: Tween(end: selected.toDouble()),
                      duration: reducedMotion
                          ? Duration.zero
                          : const Duration(milliseconds: 460),
                      curve: Curves.easeOutCubic,
                      builder: (context, position, child) {
                        final stretch =
                            math.sin(
                              math.pi * (position - position.round()).abs(),
                            ) *
                            0.12;
                        return PositionedDirectional(
                          start: (position - stretch / 2) * segmentWidth,
                          top: 1,
                          bottom: 1,
                          width: segmentWidth * (1 + stretch),
                          child: child!,
                        );
                      },
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(28),
                          gradient: const LinearGradient(
                            begin: Alignment.topCenter,
                            end: Alignment.bottomCenter,
                            colors: [Colors.white, Color(0xffd8eaf1)],
                          ),
                          border: Border.all(color: Colors.white),
                        ),
                      ),
                    ),
                    Row(
                      children: [
                        for (var index = 0; index < labels.length; index++)
                          Expanded(
                            child: Semantics(
                              selected: selected == index,
                              child: TextButton(
                                onPressed: () => onSelected(index),
                                style: TextButton.styleFrom(
                                  minimumSize: Size(0, height),
                                  foregroundColor: Palette.ink,
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 4,
                                  ),
                                ),
                                child: Text(labels[index]),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class LiquidPageTransition extends StatelessWidget {
  const LiquidPageTransition({
    super.key,
    required this.identity,
    required this.child,
  });

  final String identity;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.disableAnimationsOf(context)) return child;
    return TweenAnimationBuilder<double>(
      key: ValueKey(identity),
      tween: Tween(begin: 0, end: 1),
      duration: const Duration(milliseconds: 380),
      curve: Curves.easeOutCubic,
      builder: (context, progress, child) => Opacity(
        opacity: progress,
        child: Transform.translate(
          offset: Offset(0, 12 * (1 - progress)),
          child: child,
        ),
      ),
      child: child,
    );
  }
}
