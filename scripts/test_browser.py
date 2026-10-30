#!/usr/bin/env python3
"""Exercise visible controls and server-backed Bokeh state in both pilot lessons."""

import argparse
import json
from pathlib import Path
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, default=ROOT / "output/browser")
    parser.add_argument("--browser-executable", help="Optional existing Chrome/Chromium executable")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    evidence = {"base_url": args.base_url, "status": "in-progress", "checks": [], "errors": [], "viewports": []}
    started = time.perf_counter()

    def record(name, details):
        evidence["checks"].append({"name": name, "status": "pass", "details": details})

    def model(page, name, expression):
        return page.evaluate("""([name, expression]) => {
            const item = Bokeh.documents[0].get_model_by_name(name);
            return Function('item', 'return ' + expression)(item);
        }""", [name, expression])

    def ready(page, module):
        page.goto(args.base_url.rstrip("/") + f"/modules/{module}/", wait_until="networkidle")
        page.wait_for_function("window.Bokeh && Bokeh.documents.length === 1 && Bokeh.documents[0].get_model_by_name('metrics')")
        page.locator("canvas").first.wait_for(state="visible")

    def inspect_layout(page, label):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Horizontal overflow: {label}"
        width = page.viewport_size["width"]
        for canvas in page.locator("canvas").all():
            box = canvas.bounding_box()
            if box:
                assert box["x"] >= -1 and box["x"] + box["width"] <= width + 1, f"Plot clipped: {label}: {box}"
        assert page.locator("details").count() >= 3
        page.locator("summary").first.click()
        assert page.locator("details").first.get_attribute("open") is not None
        page.screenshot(path=str(args.output / f"{label}.png"), full_page=True)
        evidence["viewports"].append({"label": label, **page.viewport_size, "horizontal_overflow": False, "screenshot": f"{label}.png"})

    try:
        with sync_playwright() as playwright:
            options = {"headless": True}
            if args.browser_executable:
                options["executable_path"] = args.browser_executable
            browser = playwright.chromium.launch(**options)
            evidence["browser_version"] = browser.version
            context = browser.new_context(viewport={"width": 1366, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: evidence["errors"].append(str(error)))
            page.on("console", lambda message: evidence["errors"].append(message.text) if message.type == "error" else None)
            page.goto(args.base_url, wait_until="networkidle")
            assert page.locator(".module-card").count() >= 2
            record("Gallery", "Both pilot links rendered through Flask")

            ready(page, "projectile")
            other_context = browser.new_context(viewport={"width": 1366, "height": 1000})
            other = other_context.new_page()
            ready(other, "projectile")
            initial_other = model(other, "trajectory", "Array.from(item.data.x)")
            sliders = page.get_by_role("slider")
            assert sliders.count() == 2
            sliders.nth(0).press("End")
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('speed').value === 50 && Bokeh.documents[0].get_model_by_name('metrics').text.includes('254.842')")
            sliders.nth(1).press("Home")
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('status').text.includes('Zero-duration')")
            assert all(value == 0 for value in model(page, "trajectory", "Array.from(item.data.y)"))
            sliders.nth(1).press("End")
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('angle').value === 90 && Bokeh.documents[0].get_model_by_name('metrics').text.includes('127.421')")
            assert all(value == 0 for value in model(page, "trajectory", "Array.from(item.data.x)"))
            assert model(other, "speed", "item.value") == 20
            assert model(other, "angle", "item.value") == 45
            assert model(other, "trajectory", "Array.from(item.data.x)") == initial_other
            record("Projectile controls and isolation", "Visible keyboard-operated sliders drove server results; zero/horizontal/vertical cases checked; a second browser context stayed unchanged")
            sliders.nth(0).press("Home")
            for _ in range(20):
                sliders.nth(0).press("ArrowRight")
            sliders.nth(1).press("Home")
            for _ in range(30):
                sliders.nth(1).press("ArrowRight")
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('metrics').text.includes('35.312')")
            inspect_layout(page, "projectile-desktop")
            other_context.close()

            ready(page, "linear-regression")
            other_context = browser.new_context(viewport={"width": 1366, "height": 1000})
            other = other_context.new_page()
            ready(other, "linear-regression")
            initial_other = model(other, "observations", "Array.from(item.data.y)")
            sliders = page.get_by_role("slider")
            sliders.nth(0).press("Home")
            sliders.nth(1).press("Home")
            page.locator('input[name="seed"]').fill("123")
            page.locator('input[name="seed"]').press("Tab")
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('status').text.includes('Pending')")
            assert len(model(page, "observations", "Array.from(item.data.x)")) == 100
            page.get_by_role("button", name="Generate and fit", exact=True).click()
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('observations').data.x.length === 20 && Bokeh.documents[0].get_model_by_name('metrics').text.includes('seed = 123')")
            assert max(abs(value) for value in model(page, "residuals", "Array.from(item.data.residual)")) < 1e-10
            assert model(page, "fit_line", "Array.from(item.data.y)") == model(page, "true_line", "Array.from(item.data.y)") or all(abs(a-b) < 1e-10 for a,b in zip(model(page,"fit_line","Array.from(item.data.y)"), [1.,21.]))
            sliders.nth(0).press("End")
            sliders.nth(1).press("End")
            page.get_by_role("button", name="Generate and fit", exact=True).click()
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('observations').data.x.length === 300 && Bokeh.documents[0].get_model_by_name('metrics').text.includes('σ = 5')")
            assert len(model(page, "residuals", "Array.from(item.data.x)")) == 300
            assert model(page, "observations", "Array.from(new Set(item.data.split)).sort()") == ["test", "train"]
            assert model(other, "observations", "Array.from(item.data.y)") == initial_other
            assert model(other, "sample_count", "item.value") == 100
            record("Regression controls and isolation", "Visible sliders/numeric seed/button updated all server results; pending inputs preserved prior results; zero-noise recovery and second-context isolation verified")
            inspect_layout(page, "regression-desktop")
            other_context.close()

            narrow = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            narrow_page = narrow.new_page()
            narrow_page.on("pageerror", lambda error: evidence["errors"].append(str(error)))
            for module, label in (("projectile", "projectile-mobile"), ("linear-regression", "regression-mobile")):
                ready(narrow_page, module)
                narrow_page.get_by_role("slider").first.press("ArrowRight")
                if module == "linear-regression":
                    narrow_page.get_by_role("button", name="Generate and fit", exact=True).click()
                inspect_layout(narrow_page, label)
            record("Responsive layouts and assessment", "Visible controls exercised at 390×844; desktop 1366×1000 and narrow screenshots; no horizontal overflow/clipped canvases; feedback reveal works")
            narrow.close()
            context.close()
            browser.close()
            assert not evidence["errors"], evidence["errors"]
            record("Browser errors", "No captured JavaScript page errors or primary-page console errors")
        evidence["status"] = "pass"
    except Exception as error:
        evidence["status"] = "fail"
        evidence["failure"] = repr(error)
        raise
    finally:
        evidence["suite_wall_seconds"] = time.perf_counter() - started
        (args.output / "results.json").write_text(json.dumps(evidence, indent=2) + "\n")
        print(json.dumps(evidence, indent=2))


if __name__ == "__main__":
    main()
