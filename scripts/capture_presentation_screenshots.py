"""Capture public CloudMLOps pages for presentation (no credentials stored)."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "docs" / "presentation_assets"
PAGES = [
    ("01_aws_app.png", "https://asqmhsdwfs.us-east-2.awsapprunner.com/", 1400, 900),
    ("03_swagger_docs.png", "https://p3jivcdmbf.us-east-2.awsapprunner.com/docs", 1400, 900),
    ("04_github_repo.png", "https://github.com/nitya200/CloudMlOps", 1400, 900),
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        for name, url, w, h in PAGES:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(url, wait_until="networkidle", timeout=120_000)
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / name), full_page=False)
            print("saved", OUT / name)
        browser.close()


if __name__ == "__main__":
    main()
