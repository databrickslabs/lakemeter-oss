"""Re-capture all documentation screenshots with Playwright."""
import asyncio
import os
from playwright.async_api import async_playwright

APP_URL = "http://localhost:8000"
ESTIMATE_URL = f"{APP_URL}/calculator/2fc50a70-060d-49e2-b845-eb8c055f4aeb"
IMG_DIR = os.path.join(os.path.dirname(__file__), "..", "img")
GUIDES_DIR = os.path.join(IMG_DIR, "guides")


async def capture_all():
    os.makedirs(GUIDES_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})

        # ─── Main screenshots ───

        # 1. Home page (estimates list)
        print("Capturing: home-page.png")
        await page.goto(APP_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=os.path.join(IMG_DIR, "home-page.png"))

        # 2. Estimates list
        print("Capturing: estimates-list.png")
        await page.screenshot(path=os.path.join(IMG_DIR, "estimates-list.png"))

        # 3. Calculator overview (estimate with workloads, workload form open)
        print("Capturing: calculator-overview.png")
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        # Click on a workload to expand it
        try:
            wl = page.locator('text=Vector Search').first
            await wl.click(timeout=5000)
            await page.wait_for_timeout(2000)
        except:
            pass
        await page.screenshot(path=os.path.join(IMG_DIR, "calculator-overview.png"))

        # 4. Estimate with workloads (collapsed view)
        print("Capturing: estimate-with-workloads.png")
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=os.path.join(IMG_DIR, "estimate-with-workloads.png"))

        # 5. Workload expanded config
        print("Capturing: workload-expanded-config.png")
        try:
            wl = page.locator('text=Vector Search').first
            await wl.click(timeout=5000)
            await page.wait_for_timeout(2000)
        except:
            pass
        await page.screenshot(path=os.path.join(IMG_DIR, "workload-expanded-config.png"))

        # 6. Workload calculation detail (same view, scrolled or different workload)
        print("Capturing: workload-calculation-detail.png")
        await page.screenshot(path=os.path.join(IMG_DIR, "workload-calculation-detail.png"))

        # 7. All workloads overview
        print("Capturing: all-workloads-overview.png")
        await page.goto(f"{APP_URL}/workloads", wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=os.path.join(IMG_DIR, "all-workloads-overview.png"))

        # 8. Login page
        print("Capturing: login-page.png")
        # Login page is at /login or the auth flow - skip if not accessible
        # Keep existing login-page.png as it's a static auth page

        # ─── Guide screenshots ───
        # These show various pages of the app for the docs guides
        # Re-capture the main ones that could show cost values

        # Calculator page for various guide screenshots
        print("Capturing guide screenshots...")
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)

        # Guide: getting-started
        await page.screenshot(path=os.path.join(GUIDES_DIR, "getting-started-page.png"))

        # Guide: overview page
        await page.goto(APP_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=os.path.join(GUIDES_DIR, "overview-page.png"))

        # Guide: workloads overview
        await page.goto(f"{APP_URL}/workloads", wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await page.screenshot(path=os.path.join(GUIDES_DIR, "workloads-overview-page.png"))

        # Guide: export guide (estimate page)
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=os.path.join(GUIDES_DIR, "export-guide.png"))

        # Guide: AI assistant (with chat panel visible)
        await page.screenshot(path=os.path.join(GUIDES_DIR, "ai-assistant-guide.png"))

        # Guide: calculation reference
        try:
            wl = page.locator('text=JOBS Classic').first
            await wl.click(timeout=5000)
            await page.wait_for_timeout(2000)
        except:
            pass
        await page.screenshot(path=os.path.join(GUIDES_DIR, "calculation-reference-guide.png"))

        # Guide: calculation worked example
        await page.screenshot(path=os.path.join(GUIDES_DIR, "calculation-worked-example.png"))

        # Guide workload-specific screenshots - navigate to estimate and expand different workloads
        workload_guides = [
            ("DBSQL", "dbsql-warehouses-guide.png", "dbsql-worked-example.png"),
            ("FMAPI", "fmapi-databricks-guide.png", "fmapi-databricks-worked-example.png"),
            ("Lakebase", "lakebase-guide.png", "lakebase-worked-example.png"),
            ("Model Serving", "model-serving-guide.png", "model-serving-worked-example.png"),
            ("Vector Search", "vector-search-guide.png", "vector-search-worked-example.png"),
        ]

        for wl_name, guide_file, example_file in workload_guides:
            print(f"  Capturing: {guide_file}")
            await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
            await page.wait_for_timeout(4000)
            try:
                wl = page.locator(f'text={wl_name}').first
                await wl.click(timeout=5000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"    [skip] Could not find workload '{wl_name}': {e}")
            await page.screenshot(path=os.path.join(GUIDES_DIR, guide_file))
            await page.screenshot(path=os.path.join(GUIDES_DIR, example_file))

        # Guide: FAQ
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=os.path.join(GUIDES_DIR, "faq-guide.png"))
        await page.screenshot(path=os.path.join(GUIDES_DIR, "faq-workload-table.png"))

        # Guide: FMAPI proprietary
        print("  Capturing: fmapi-proprietary screenshots")
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(4000)
        try:
            wl = page.locator('text=FMAPI').first
            await wl.click(timeout=5000)
            await page.wait_for_timeout(2000)
        except:
            pass
        await page.screenshot(path=os.path.join(GUIDES_DIR, "fmapi-proprietary-guide.png"))
        await page.screenshot(path=os.path.join(GUIDES_DIR, "fmapi-proprietary-worked-example.png"))

        # Guide: Excel export structure
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=os.path.join(GUIDES_DIR, "export-excel-structure.png"))

        # Admin guide screenshots - these are docs/architecture pages
        # Re-capture from the docs site pages if running, otherwise from app
        admin_pages = [
            "admin-api-reference-guide.png",
            "admin-architecture-guide.png",
            "admin-configuration-guide.png",
            "admin-database-guide.png",
            "admin-database-schema.png",
            "admin-deployment-guide.png",
            "admin-permissions-guide.png",
            "admin-troubleshooting-guide.png",
        ]
        # Admin screenshots are typically of the docs site itself, not the app
        # They don't show cost values so they won't have overflow issues
        # Keep existing ones

        # AI assistant tools screenshot
        await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path=os.path.join(GUIDES_DIR, "ai-assistant-tools.png"))

        await browser.close()
        print("\nAll screenshots captured!")


if __name__ == "__main__":
    asyncio.run(capture_all())
