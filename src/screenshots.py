"""生成済みHTMLからカレンダーのPNGスクリーンショットを生成する。"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


# モバイル幅で撮るとカレンダーがコンパクトになる
# Retina相当の解像度（device_scale_factor=2）で鮮明に
VIEWPORT_WIDTH = 800
DEVICE_SCALE = 2

PAGES = ["share", "private", "share-this", "share-next", "private-this", "private-next"]


def generate_png_screenshots(output_dir: Path) -> list[Path]:
    """output/ 配下の HTML を PNG にスクリーンショット保存して、保存先パスを返す。"""
    saved: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name in PAGES:
            html_file = output_dir / f"{name}.html"
            png_file = output_dir / f"{name}.png"
            if not html_file.exists():
                continue
            context = browser.new_context(
                viewport={"width": VIEWPORT_WIDTH, "height": 800},
                device_scale_factor=DEVICE_SCALE,
            )
            page = context.new_page()
            page.goto(f"file://{html_file.resolve()}")
            page.wait_for_load_state("networkidle")
            # フォント・レイアウト確定待ち
            page.wait_for_timeout(800)
            # ボディの実サイズに合わせて full-page スクリーンショット
            page.screenshot(path=str(png_file), full_page=True, omit_background=False)
            saved.append(png_file)
            context.close()
        browser.close()
    return saved


if __name__ == "__main__":
    import sys
    out = Path(__file__).resolve().parent.parent / "output"
    files = generate_png_screenshots(out)
    for f in files:
        print(f"  → {f} ({f.stat().st_size:,} bytes)")
