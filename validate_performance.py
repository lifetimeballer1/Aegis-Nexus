#!/usr/bin/env python3
"""Static Phase 7 performance/mobile regression gate.

This gate intentionally checks implementation invariants rather than inventing
runtime performance numbers that CI cannot reliably reproduce on GitHub-hosted
runners. It protects the expensive browser paths that matter most on mobile.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def main():
    index = (ROOT / "index.html").read_text(encoding="utf-8")
    qa = (ROOT / "global_pulse_qa.js").read_text(encoding="utf-8")
    perf = (ROOT / "global_pulse_performance.js").read_text(encoding="utf-8")
    layout = (ROOT / "css/layout.css").read_text(encoding="utf-8")
    map_css = (ROOT / "css/map.css").read_text(encoding="utf-8")

    assert 'class="gp-intelweb-frame"' in index
    assert 'loading="lazy"' in index, "Intelligence Web iframe must not eagerly load on mobile"
    eager_patterns = (
        r"loading\s*=\s*['\"]eager['\"]",
        r"\.loading\s*=\s*['\"]eager['\"]",
        r"setAttribute\(\s*['\"]loading['\"]\s*,\s*['\"]eager['\"]",
    )
    assert not any(re.search(pattern, index, re.I) for pattern in eager_patterns), (
        "No below-fold iframe may be switched to eager loading"
    )
    assert "global_pulse_performance.js" in index
    # CSSOM style properties are exposed in JavaScript as camelCase. Accept
    # either spelling so the gate verifies the real implementation instead of
    # rejecting valid browser code because of a text-format mismatch.
    assert "content-visibility" in perf or "contentVisibility" in perf, "below-fold content visibility optimization missing"
    assert "IntersectionObserver" in perf
    assert "requestIdleCallback" in perf
    assert "prefers-reduced-motion" in perf

    # Protect the page from common horizontal-overflow regressions.
    for css, name in ((layout, "layout.css"), (map_css, "map.css")):
        assert "min-width:0" in css.replace(" ", "") or "min-width: 0" in css, f"{name}: missing shrink-safe sizing"

    # The QA observer must be throttled; a full-body observer callback on every
    # marker/card mutation is a mobile battery and rendering regression.
    assert "requestAnimationFrame" in qa
    assert "MutationObserver" in qa
    assert "queueMicrotask" in qa or "requestAnimationFrame" in qa

    # Reject accidental giant inline payloads in the main document.
    inline_scripts = re.findall(r"<script(?![^>]*src=)[^>]*>(.*?)</script>", index, re.S | re.I)
    inline_bytes = sum(len(x.encode("utf-8")) for x in inline_scripts)
    assert inline_bytes < 50000, f"inline JS payload too large: {inline_bytes} bytes"

    print("PASS: Phase 7 mobile/performance gate")
    print(f"inlineScriptBytes={inline_bytes}")
    print("lazyIntelligenceWeb=True")
    print("idlePerformanceObserver=True")
    print("reducedMotion=True")


if __name__ == "__main__":
    main()
