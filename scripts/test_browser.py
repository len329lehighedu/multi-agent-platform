#!/usr/bin/env python3
"""Exercise the live Neural Equation Finder dashboard through a real browser."""

import argparse
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
MODULE = "neural-equation-finder"


def linear_csv(rows=120):
    values = ["x,y,unused"]
    for index in range(rows):
        x = -3 + 6 * index / (rows - 1)
        values.append(f"{x:.17g},{(2*x+1):.17g},note-{index}")
    return "\n".join(values) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--output", type=Path, default=ROOT / "output/browser")
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    fixture = args.output / "linear-upload.csv"
    fixture.write_text(linear_csv())
    evidence = {"base_url": args.base_url, "status": "in-progress", "checks": [], "errors": [], "viewports": []}
    started = time.perf_counter()

    def record(name, details):
        evidence["checks"].append({"name": name, "status": "pass", "details": details})

    def model(page, name, expression):
        return page.evaluate("""([name, expression]) => {
            const item = Bokeh.documents[0].get_model_by_name(name);
            return Function('item', 'return ' + expression)(item);
        }""", [name, expression])

    def ready(page):
        page.goto(args.base_url, wait_until="networkidle")
        page.wait_for_url(f"**/modules/{MODULE}/")
        page.wait_for_function("window.Bokeh && Bokeh.documents.length === 1 && Bokeh.documents[0].get_model_by_name('train')")
        page.get_by_role("button", name="Train", exact=True).wait_for(state="visible")

    def inspect_layout(page, label):
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"Horizontal overflow: {label}"
        assert page.locator("details").count() == 0
        assert page.get_by_text("What you will learn").count() == 0
        assert page.get_by_text("Check your understanding").count() == 0
        page.screenshot(path=str(args.output / f"{label}.png"), full_page=True)
        evidence["viewports"].append({"label": label, **page.viewport_size, "horizontal_overflow": False, "screenshot": f"{label}.png"})

    try:
        with sync_playwright() as playwright:
            options = {"headless": True}
            if args.browser_executable:
                options["executable_path"] = args.browser_executable
            browser = playwright.chromium.launch(**options)
            evidence["browser_version"] = browser.version
            first_context = browser.new_context(viewport={"width": 1366, "height": 1000})
            page = first_context.new_page()
            page.on("pageerror", lambda error: evidence["errors"].append(str(error)))
            page.on("console", lambda message: evidence["errors"].append(message.text) if message.type == "error" else None)
            ready(page)
            assert page.locator("h1").get_by_text("Neural Equation Finder").count() == 1
            assert model(page, "target", "item.value") == "target"
            assert model(page, "features", "Array.from(item.value)") == ["x"]
            assert "300 raw rows" in model(page, "preview", "item.text")
            record("Single dashboard shell", "Root redirected to the sole active module; compact data/model/metric/plot/equation cards loaded without lesson or quiz rails")

            second_context = browser.new_context(viewport={"width": 1366, "height": 1000})
            other = second_context.new_page()
            ready(other)
            page.locator('input[type="file"]').set_input_files(str(fixture))
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('target').value === 'unused'")
            page.locator('select[name="target"]').select_option("y")
            # MultiChoice keeps x selected from the upload default.
            # Bokeh 3.8 propagates model names to Select/NumericInput DOM nodes,
            # while TextInput renders as the sole unnamed text input.
            hidden_input = page.locator('input[type="text"]:not([name])')
            hidden_input.fill("8")
            hidden_input.press("Tab")
            page.locator('select[name="activation"]').select_option("identity")
            page.get_by_role("button", name="Advanced", exact=False).click()
            page.locator('input[name="alpha"]').fill("0")
            page.locator('input[name="alpha"]').press("Tab")
            page.locator('input[name="equation_degree"]').fill("1")
            page.locator('input[name="equation_degree"]').press("Tab")
            page.get_by_role("button", name="Train", exact=True).click()
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('train').disabled === true")
            page.wait_for_function("Bokeh.documents[0].get_model_by_name('status').text.startsWith('Complete')", timeout=120000)
            assert model(page, "observations", "item.data.x.length") == 120
            assert model(page, "residuals", "item.data.residual.length") == 120
            assert model(page, "nn_curve", "item.data.x.length") == 250
            assert "rank" in model(page, "equation", "item.text")
            assert "NN test R" in model(page, "metrics", "item.text")
            assert "2·x1" in model(page, "equation", "item.text") or "2.0" in model(page, "equation", "item.text")
            assert model(other, "target", "item.value") == "target"
            assert "300 raw rows" in model(other, "preview", "item.text")
            assert model(other, "metrics", "item.text") == "Metrics appear after training."
            record("Upload, controls, worker, and isolation", "A visible CSV upload and parameter edits trained the subprocess-backed NN, updated all plot sources/equation/metrics, and a second browser session retained independent sample state")
            inspect_layout(page, "neural-equation-desktop")
            second_context.close()

            narrow_context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1)
            narrow = narrow_context.new_page()
            narrow.on("pageerror", lambda error: evidence["errors"].append(str(error)))
            narrow.on("console", lambda message: evidence["errors"].append(message.text) if message.type == "error" else None)
            ready(narrow)
            inspect_layout(narrow, "neural-equation-mobile")
            assert narrow.get_by_role("button", name="Train", exact=True).is_visible()
            record("Responsive dashboard", "Desktop 1366x1000 and narrow 390x844 screenshots have no page-level horizontal overflow and the primary controls remain visible")
            narrow_context.close()
            first_context.close()
            browser.close()
            assert not evidence["errors"], evidence["errors"]
            record("Browser errors", "No captured JavaScript page errors or primary console errors")
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
