"""Record all 6 GIFs using Playwright with visible cursor and smooth mouse movement."""
import asyncio
import subprocess
import sys
import os
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from cursor import CURSOR_INJECT, inject_cursor, smooth_move, move_to, click_on, visual_select

APP_URL = "http://localhost:8000"
ESTIMATE_URL = f"{APP_URL}/calculator/2fc50a70-060d-49e2-b845-eb8c055f4aeb"
GIF_DIR = os.path.join(os.path.dirname(__file__), "..", "img", "gifs")
VIDEO_TMP = os.path.dirname(__file__)


def webm_to_gif(webm_path, gif_path, fps=10, width=800):
    """Convert WebM to optimized GIF (smaller fps + fewer colors = smaller file)."""
    subprocess.run([
        "ffmpeg", "-y", "-i", webm_path,
        "-vf", f"fps={fps},scale={width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=96[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5",
        gif_path
    ], capture_output=True)
    size = os.path.getsize(gif_path) / 1024
    print(f"  → {os.path.basename(gif_path)} ({size:.0f}KB)")


async def new_context(p):
    browser = await p.chromium.launch(headless=True)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 800},
        record_video_dir=VIDEO_TMP,
        record_video_size={"width": 1280, "height": 800},
    )
    page = await context.new_page()
    await page.add_init_script(CURSOR_INJECT)
    return browser, context, page


async def go_to_estimate(page):
    """Navigate directly to the estimate with workloads and wait for full load."""
    await page.goto(ESTIMATE_URL, wait_until="load", timeout=60000)
    try:
        await page.wait_for_selector('text="Monthly Estimate"', timeout=15000)
    except:
        pass
    await page.wait_for_timeout(3000)
    await inject_cursor(page)
    await page.wait_for_timeout(300)
    await page.mouse.move(0, 400)
    await page.wait_for_timeout(200)


async def finish(page, context, browser, gif_name):
    video_path = await page.video.path()
    await context.close()
    await browser.close()
    webm_to_gif(video_path, os.path.join(GIF_DIR, gif_name))


# ─── GIF 1: Creating an estimate ───
async def record_creating_estimate(p):
    print("Recording: creating-estimate...")
    browser, context, page = await new_context(p)
    await page.goto(f"{APP_URL}/calculator", wait_until="load", timeout=60000)
    try:
        await page.wait_for_selector('select', timeout=15000)
    except:
        pass
    # Wait for regions to load asynchronously
    for _ in range(30):
        opt_count = await page.locator('select').first.evaluate('(el) => el.options.length')
        if opt_count > 5:
            break
        await page.wait_for_timeout(500)
    await page.wait_for_timeout(1000)
    await inject_cursor(page)
    await page.mouse.move(0, 400)
    await page.wait_for_timeout(300)

    # Move to estimate name field and type
    name_field = page.get_by_role("textbox").first
    await move_to(page, name_field, pause=500)
    await name_field.click(click_count=3)
    await page.keyboard.type("Q4 Data Platform Estimate", delay=45)
    await page.wait_for_timeout(600)

    # Select region — with visible dropdown overlay
    region_select = page.locator('select').first
    await visual_select(page, region_select, value="us-east-1")

    # Select tier — with visible dropdown overlay
    tier_select = page.locator('select').nth(1)
    await visual_select(page, tier_select, value="premium")

    # Move to Create Estimate button and click
    create_btn = page.locator('button:has-text("Create Estimate")').first
    await click_on(page, create_btn, pause=1500)

    await finish(page, context, browser, "creating-estimate.gif")


# ─── GIF 2: Adding a workload ───
async def record_adding_workload(p):
    print("Recording: adding-workload...")
    browser, context, page = await new_context(p)
    await go_to_estimate(page)

    # Click "Add Workload"
    add_btn = page.locator('button:has-text("Add Workload")').first
    await click_on(page, add_btn, pause=1000)

    # Fill workload name
    await page.wait_for_timeout(500)
    all_inputs = page.locator('input[type="text"]')
    count = await all_inputs.count()
    for i in range(count):
        try:
            inp = all_inputs.nth(i)
            box = await inp.bounding_box(timeout=1000)
            if box and box["y"] > 100:
                await move_to(page, inp, pause=300)
                await inp.click()
                await inp.fill("")
                await page.keyboard.type("ML Training Pipeline", delay=45)
                await page.wait_for_timeout(500)
                break
        except:
            continue

    # Select workload type with visible dropdown overlay
    selects = page.locator('select')
    sel_count = await selects.count()
    if sel_count > 0:
        for i in range(sel_count):
            try:
                sel = selects.nth(i)
                box = await sel.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    await visual_select(page, sel, value="JOBS")
                    break
            except:
                continue

    await page.wait_for_timeout(1000)
    await finish(page, context, browser, "adding-workload.gif")


# ─── GIF 3: Cost summary ───
async def record_cost_summary(p):
    print("Recording: cost-summary...")
    browser, context, page = await new_context(p)
    await go_to_estimate(page)

    # Move to cost summary area (right side)
    await smooth_move(page, 950, 200)
    await page.wait_for_timeout(400)

    # Hover Monthly Estimate
    await move_to(page, page.locator('text=Monthly Estimate').first, pause=600)

    # Hover DBU COST
    await move_to(page, page.locator('text=DBU COST').first, pause=600)

    # Hover VM COST
    await move_to(page, page.locator('text=VM COST').first, pause=600)

    # Move to workload breakdown
    try:
        await move_to(page, page.locator('text=Click to view').first, pause=400)
    except:
        pass

    # Click on a workload in breakdown
    bi_wl = page.locator('button:has-text("BI Analytics")').last
    await click_on(page, bi_wl, pause=1000)

    await page.wait_for_timeout(500)
    await finish(page, context, browser, "cost-summary.gif")


# ─── GIF 4: Drag and drop ───
async def record_drag_and_drop(p):
    print("Recording: drag-and-drop...")
    browser, context, page = await new_context(p)
    await go_to_estimate(page)

    # Find first sortable workload row (attribute is aria-roledescription)
    first_wl = page.locator('[aria-roledescription="sortable"]').first
    box = await first_wl.bounding_box(timeout=10000)
    if box:
        handle_x = box["x"] + 20
        handle_y = box["y"] + box["height"] / 2
        await smooth_move(page, handle_x, handle_y)
        await page.wait_for_timeout(500)

        # Mouse down to grab
        await page.mouse.down()
        await page.wait_for_timeout(400)

        # Drag down slowly
        for i in range(40):
            await page.mouse.move(handle_x, handle_y + (i * 2.5), steps=1)
            await page.wait_for_timeout(25)
        await page.wait_for_timeout(400)

        # Drop
        await page.mouse.up()
        await page.wait_for_timeout(1000)

    await finish(page, context, browser, "drag-and-drop.gif")


# ─── GIF 5: Export to Excel ───
async def record_export_excel(p):
    print("Recording: export-excel...")
    browser, context, page = await new_context(p)
    await go_to_estimate(page)

    # Move around workload list first
    wl1 = page.locator('text=Daily ETL Pipeline').first
    await move_to(page, wl1, pause=500)
    wl2 = page.locator('text=BI Analytics').first
    await move_to(page, wl2, pause=500)

    # Move to Excel button and click
    excel_btn = page.locator('button:has-text("Excel")').first
    await move_to(page, excel_btn, pause=600)
    await excel_btn.click()
    await page.wait_for_timeout(2000)

    await finish(page, context, browser, "export-excel.gif")


# ─── GIF 6: AI Assistant ───
async def record_ai_assistant(p):
    print("Recording: ai-assistant...")
    browser, context, page = await new_context(p)
    await go_to_estimate(page)

    # Click the Optimize quick action to show AI capability
    optimize_btn = page.locator('button:has-text("Optimize")').first
    try:
        await click_on(page, optimize_btn, pause=500, timeout=5000)
    except:
        pass

    # Wait for AI response to appear
    await page.wait_for_timeout(4000)

    # Now type a custom message
    chat_input = page.locator('textarea').last
    try:
        await move_to(page, chat_input, pause=500, timeout=5000)
        await chat_input.click()
        await page.keyboard.type("What is the total monthly cost?", delay=50)
        await page.wait_for_timeout(600)
        await page.keyboard.press("Enter")
    except Exception as e:
        print(f"  [skip] AI chat: {e}")

    # Wait for response
    await page.wait_for_timeout(5000)

    await finish(page, context, browser, "ai-assistant.gif")


async def main():
    os.makedirs(GIF_DIR, exist_ok=True)
    async with async_playwright() as p:
        for fn in [record_creating_estimate, record_adding_workload, record_cost_summary,
                   record_drag_and_drop, record_export_excel, record_ai_assistant]:
            try:
                await fn(p)
            except Exception as e:
                print(f"  ✗ {fn.__name__} failed: {e}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
