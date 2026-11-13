# Accessibility checks

Four Playwright scripts that check the built site in docs/. Serve it first, then run them with page names:

    python -m http.server 8765 --directory docs &
    npm i axe-core playwright
    node tools/website/a11y/axe.js index.html maps.html map-snow.html      # WCAG 2.2 A/AA rules (axe-core)
    node tools/website/a11y/contrast.js index.html maps.html               # text contrast on solid backgrounds
    node tools/website/a11y/focus.js index.html devlog.html                # every Tab stop shows a focus ring
    node tools/website/a11y/motion.js                                      # nothing animates with reduced motion

Result on 13 Nov 2026 (25 pages): no axe violations, no text below 4.5:1 (3:1 for large text) apart from
decorative outline lettering, a visible focus ring on every Tab stop, and no running animation when the
visitor's system asks for reduced motion. style.css also follows Windows high-contrast mode
(forced-colors) and "more contrast" (prefers-contrast).
