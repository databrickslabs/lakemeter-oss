"""Record getting-started tutorial video (~4-5 min) with timestamp-synced AI voiceover.

Key design:
  - Track wall-clock timestamps during recording for each narration point
  - In post-processing, place audio clips at exact recorded timestamps
  - This ensures perfect voice-to-action synchronization

Scene order:
  1. Landing page — browse estimates
  2. Help & Documentation
  3. Create new estimate (visible dropdowns)
  4a. Add JOBS workload — full config: driver, worker, usage, save, show calculations
  4b. Add DBSQL workload — full config: size, usage, save, show calculations + percentages
  5. Cost summary
  6. AI Assistant — add workload, show it appearing in UI
  7. Export to Excel
  8. Closing
"""
import asyncio
import subprocess
import sys
import os
import time
import edge_tts
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(__file__))
from cursor import (
    CURSOR_INJECT, SUBTITLE_INJECT,
    inject_cursor, inject_subtitle,
    smooth_move, move_to, click_on,
    show_subtitle, hide_subtitle,
    visual_select, visual_searchable_select,
)

APP_URL = "http://localhost:8000"
VIDEO_DIR = os.path.dirname(__file__)
VOICE = "en-US-GuyNeural"
AUDIO_DIR = os.path.join(VIDEO_DIR, "_audio_clips")


# ─── Timestamp-synced audio ───

class SyncRecorder:
    """Track wall-clock timestamps during video recording for audio sync."""

    def __init__(self):
        self.t0 = None
        self.marks = []  # [(offset_seconds, clip_id)]

    def start(self):
        self.t0 = time.time()

    def mark(self, clip_id):
        """Record the current video timestamp for an audio clip."""
        offset = time.time() - self.t0
        self.marks.append((offset, clip_id))
        return offset


async def generate_clips(narrations: list[tuple[str, str]]):
    """Pre-generate all voiceover clips using edge-tts."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    for clip_id, text in narrations:
        path = os.path.join(AUDIO_DIR, f"{clip_id}.mp3")
        if not os.path.exists(path):
            communicate = edge_tts.Communicate(text, VOICE, rate="-5%")
            await communicate.save(path)
            print(f"    [tts] {clip_id}")


def clip_duration(clip_id: str) -> float:
    """Get clip duration in seconds."""
    path = os.path.join(AUDIO_DIR, f"{clip_id}.mp3")
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def clip_duration_ms(clip_id: str) -> int:
    """Get clip duration in ms with buffer."""
    return int(clip_duration(clip_id) * 1000) + 400


async def sync_wait(page, clip_id, section_start):
    """Wait enough time so the video segment covers the audio clip duration."""
    elapsed = time.time() - section_start
    needed = clip_duration(clip_id) + 0.5  # 500ms buffer after voice ends
    remaining = needed - elapsed
    if remaining > 0:
        await page.wait_for_timeout(int(remaining * 1000))


# ─── Helpers ───

async def setup_page(page):
    await inject_cursor(page)
    await inject_subtitle(page)
    await page.mouse.move(0, 400)
    await page.wait_for_timeout(300)


async def wait_for_regions(page):
    for _ in range(30):
        opt_count = await page.locator('select').first.evaluate('(el) => el.options.length')
        if opt_count > 5:
            break
        await page.wait_for_timeout(500)
    await page.wait_for_timeout(500)


# ─── Main ───

async def main():
    # ─── Define narrations ───
    narrations = [
        # Scene 1: Landing
        ("s1_welcome", "Welcome to Lakemeter, the Databricks pricing calculator. "
                       "This tool helps you estimate costs for any Databricks workload."),
        ("s1_estimates", "The home page shows all your saved estimates. "
                         "You can search, filter by cloud, and drag to reorder."),
        # Scene 2: Help
        ("s2_help", "Before creating an estimate, let's explore the help options."),
        ("s2_docs", "The documentation site covers every feature, from workload setup to the AI assistant."),
        ("s2_pricing", "You can also jump directly to official Databricks pricing."),
        # Scene 3: Create
        ("s3_create", "Now let's create a new pricing estimate."),
        ("s3_name", "We'll name it Q4 Data Platform Estimate."),
        ("s3_region", "Select the AWS US East 1 region. Pricing varies by region."),
        ("s3_tier", "Choose the Premium pricing tier for access to all features."),
        ("s3_done", "The estimate is created. Let's add some workloads."),
        # Scene 4a: JOBS
        ("s4a_intro", "First, a Lakeflow Jobs cluster for our ETL pipeline."),
        ("s4a_type", "Select Jobs Compute as the workload type."),
        ("s4a_driver", "Choose the driver instance type. We'll search for i3 x-large."),
        ("s4a_worker", "For workers, let's use i3 x-large with 3 nodes."),
        ("s4a_usage", "Set usage to 3 runs per day, 45 minutes each, 22 days per month."),
        ("s4a_save", "Save the workload to see the calculated cost."),
        ("s4a_calc", "The cost breakdown shows monthly D-B-U and V-M charges."),
        # Scene 4b: DBSQL
        ("s4b_intro", "Now let's add a Databricks SQL warehouse for analytics queries."),
        ("s4b_type", "Select Databricks SQL as the workload type."),
        ("s4b_size", "Choose a Large warehouse size for high concurrency analytics."),
        ("s4b_usage", "We'll set the average runtime to 5 hours per query session, 22 days per month."),
        ("s4b_save", "Save and view the cost breakdown."),
        ("s4b_compare", "Both workloads now display their share of the total cost with percentage bars."),
        # Scene 5: Summary
        ("s5_summary", "The cost summary panel shows the total monthly estimate, "
                       "broken down by D-B-U cost and V-M cost."),
        ("s5_detail", "Each workload's contribution is displayed as a percentage, "
                      "making it easy to spot cost drivers."),
        # Scene 6: AI
        ("s6_intro", "Let's use the AI assistant to add another workload through conversation."),
        ("s6_ask", "We'll ask it to set up a Foundation Model API workload using Claude Opus."),
        ("s6_response", "The AI configures and adds the workload directly to our estimate."),
        ("s6_added", "The new workload now appears in the list with its calculated cost."),
        # Scene 7: Export
        ("s7_export", "Finally, export the estimate to Excel for a full cost breakdown "
                      "with SKU details, token rates, and VM pricing."),
        # Scene 8: Close
        ("s8_close", "That's Lakemeter. Start estimating your Databricks costs today. "
                     "Check the documentation for detailed guides on every feature."),
    ]

    print("Generating voiceover clips...")
    await generate_clips(narrations)

    # ─── Record ───
    print("Recording video...")
    rec = SyncRecorder()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        await page.add_init_script(CURSOR_INJECT)
        await page.add_init_script(SUBTITLE_INJECT)

        # ══════════════════════════════════════════
        # Scene 1: Landing
        # ══════════════════════════════════════════
        print("  Scene 1: Landing")
        await page.goto(APP_URL, wait_until="load", timeout=60000)
        await page.wait_for_timeout(3000)
        await setup_page(page)
        rec.start()

        # ── s1_welcome ──
        t = time.time()
        rec.mark("s1_welcome")
        await show_subtitle(page, "Welcome to Lakemeter — Databricks Pricing Calculator", 0)
        await smooth_move(page, 640, 300)
        await page.wait_for_timeout(1000)
        await smooth_move(page, 640, 500)
        await sync_wait(page, "s1_welcome", t)
        await hide_subtitle(page)

        # ── s1_estimates ──
        t = time.time()
        rec.mark("s1_estimates")
        await show_subtitle(page, "Browse and manage all your pricing estimates", 0)
        try:
            est_link = page.locator('a:has-text("Estimates")').first
            await move_to(page, est_link, pause=800)
        except:
            pass
        await smooth_move(page, 400, 400)
        await page.wait_for_timeout(500)
        await sync_wait(page, "s1_estimates", t)
        await hide_subtitle(page)
        await page.wait_for_timeout(300)

        # ══════════════════════════════════════════
        # Scene 2: Help & Documentation
        # ══════════════════════════════════════════
        print("  Scene 2: Help & Docs")

        # ── s2_help ──
        t = time.time()
        rec.mark("s2_help")
        await show_subtitle(page, "Exploring help and documentation", 0)
        help_btn = page.locator('button[title="Help & Feedback"], button:has-text("Help")').first
        try:
            await click_on(page, help_btn, pause=800, timeout=5000)
        except:
            pass
        await sync_wait(page, "s2_help", t)
        await hide_subtitle(page)

        # ── s2_docs ──
        t = time.time()
        rec.mark("s2_docs")
        await show_subtitle(page, "Documentation covers every feature and workflow", 0)
        try:
            doc_link = page.locator('a[href="/docs/"]').first
            await move_to(page, doc_link, pause=1200, timeout=3000)
        except:
            pass
        await sync_wait(page, "s2_docs", t)
        await hide_subtitle(page)

        # ── s2_pricing ──
        t = time.time()
        rec.mark("s2_pricing")
        await show_subtitle(page, "Access official Databricks pricing", 0)
        try:
            pricing_link = page.locator('a[href*="databricks.com/product/pricing"]').first
            await move_to(page, pricing_link, pause=1200, timeout=3000)
        except:
            pass
        await sync_wait(page, "s2_pricing", t)
        await hide_subtitle(page)

        # Close help dropdown
        await page.mouse.click(640, 400)
        await page.wait_for_timeout(500)

        # ══════════════════════════════════════════
        # Scene 3: Create Estimate
        # ══════════════════════════════════════════
        print("  Scene 3: Create estimate")

        # ── s3_create ──
        t = time.time()
        rec.mark("s3_create")
        await show_subtitle(page, "Creating a new pricing estimate", 0)
        new_link = page.locator('a:has-text("New Estimate")').first
        await move_to(page, new_link, pause=500)
        await new_link.click()
        await page.wait_for_timeout(3000)
        await setup_page(page)
        try:
            await page.wait_for_selector('select', timeout=10000)
        except:
            pass
        await wait_for_regions(page)
        await sync_wait(page, "s3_create", t)
        await hide_subtitle(page)

        # ── s3_name ──
        t = time.time()
        rec.mark("s3_name")
        await show_subtitle(page, "Naming the estimate", 0)
        name_field = page.get_by_role("textbox").first
        await move_to(page, name_field, pause=400)
        await name_field.click(click_count=3)
        await page.keyboard.type("Q4 Data Platform Estimate", delay=55)
        await sync_wait(page, "s3_name", t)
        await hide_subtitle(page)

        # ── s3_region ──
        t = time.time()
        rec.mark("s3_region")
        await show_subtitle(page, "Selecting AWS US East 1 region", 0)
        region_select = page.locator('select').first
        await visual_select(page, region_select, value="us-east-1")
        await sync_wait(page, "s3_region", t)
        await hide_subtitle(page)

        # ── s3_tier ──
        t = time.time()
        rec.mark("s3_tier")
        await show_subtitle(page, "Choosing Premium pricing tier", 0)
        tier_select = page.locator('select').nth(1)
        await visual_select(page, tier_select, value="premium")
        await sync_wait(page, "s3_tier", t)
        await hide_subtitle(page)

        # ── s3_done ──
        t = time.time()
        rec.mark("s3_done")
        await show_subtitle(page, "Estimate created! Now let's add workloads", 0)
        create_btn = page.locator('button:has-text("Create Estimate")').first
        await click_on(page, create_btn, pause=500)
        await page.wait_for_timeout(3000)
        await setup_page(page)
        await sync_wait(page, "s3_done", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 4a: Add JOBS Workload
        # ══════════════════════════════════════════
        print("  Scene 4a: JOBS workload")

        # Wait for page to be ready — look for the "Add Workload" button OR dashed card
        try:
            await page.wait_for_selector('button:has-text("Add Workload"), button:has-text("Add")', timeout=20000)
        except:
            pass
        await page.wait_for_timeout(2000)

        # ── s4a_intro ──
        t = time.time()
        rec.mark("s4a_intro")
        await show_subtitle(page, "Adding a Lakeflow Jobs workload for ETL", 0)

        # Click the dashed "Add Workload" button (empty state) or "Add" button (header)
        add_btn = page.locator('button:has-text("Add Workload")').first
        try:
            await click_on(page, add_btn, pause=500)
        except:
            add_btn = page.locator('button:has-text("Add")').first
            await click_on(page, add_btn, pause=500)

        # Wait for the form heading to appear — this confirms the form opened
        try:
            await page.wait_for_selector('text="Add New Workload"', timeout=10000)
        except:
            print("  [warn] Form heading not found")
        await page.wait_for_timeout(1000)

        await sync_wait(page, "s4a_intro", t)
        await hide_subtitle(page)

        # Fill workload name — find first empty text input in the form
        name_filled = False
        try:
            all_inputs = page.locator('input[type="text"]')
            count = await all_inputs.count()
            for i in range(count):
                inp = all_inputs.nth(i)
                box = await inp.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    await move_to(page, inp, pause=300)
                    await inp.click()
                    await inp.fill("")
                    await page.keyboard.type("ETL Data Pipeline", delay=50)
                    await page.wait_for_timeout(400)
                    name_filled = True
                    break
        except:
            pass
        if not name_filled:
            print("  [warn] Could not fill workload name")

        # ── s4a_type: JOBS is the default type ──
        # The form defaults to "Lakeflow Jobs" so we just need to confirm it's selected
        # and wait for the VM config to render
        t = time.time()
        rec.mark("s4a_type")
        await show_subtitle(page, "Selecting Jobs Compute workload type", 0)

        # JOBS should already be selected as default. Visual-select it for the video.
        selects = page.locator('select')
        sel_count = await selects.count()
        for i in range(sel_count):
            try:
                sel = selects.nth(i)
                box = await sel.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    opts = await sel.evaluate('(el) => Array.from(el.options).map(o => o.value)')
                    if 'JOBS' in opts:
                        await visual_select(page, sel, value="JOBS")
                        break
            except:
                continue

        # Wait for VM config section to fully render
        await page.wait_for_timeout(3000)

        # Wait for "Select type..." to appear (confirms VM config rendered)
        try:
            await page.wait_for_selector('text="Select type..."', timeout=10000)
            print("    Driver SearchableSelect ready")
        except:
            print("  [warn] SearchableSelect not found after JOBS selection")

        await sync_wait(page, "s4a_type", t)
        await hide_subtitle(page)

        # ── s4a_driver: Select driver instance type ──
        t = time.time()
        rec.mark("s4a_driver")
        await show_subtitle(page, "Choosing driver instance type: i3.xlarge", 0)

        # Use visual_searchable_select for the driver instance
        try:
            select_trigger = page.locator('text="Select type..."').first
            await select_trigger.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await visual_searchable_select(
                page, select_trigger, "i3.xlarge",
                option_text="i3.xlarge", pause=500, load_wait=3000
            )
        except Exception as e:
            print(f"  [skip] driver select: {e}")

        await sync_wait(page, "s4a_driver", t)
        await hide_subtitle(page)

        # ── s4a_worker: Configure workers ──
        t = time.time()
        rec.mark("s4a_worker")
        await show_subtitle(page, "Configuring worker nodes: m5.xlarge × 3", 0)

        # Worker SearchableSelect — "Select type..." should be the second one
        await page.wait_for_timeout(500)
        try:
            select_trigger = page.locator('text="Select type..."').first
            await select_trigger.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
            await visual_searchable_select(
                page, select_trigger, "m5.xlarge",
                option_text="m5.xlarge", pause=500, load_wait=3000
            )
        except Exception as e:
            print(f"  [skip] worker select: {e}")

        # Set worker count to 3
        try:
            count_input = page.locator('input[type="number"]').first
            # Find the count spinbutton (labeled "Count", after worker section)
            spinbuttons = page.locator('input[type="number"]')
            sp_count = await spinbuttons.count()
            for i in range(sp_count):
                sp = spinbuttons.nth(i)
                val = await sp.input_value()
                if val == "2":  # Default worker count
                    await move_to(page, sp, pause=200)
                    await sp.click(click_count=3)
                    await page.keyboard.type("3", delay=80)
                    await page.wait_for_timeout(300)
                    break
        except:
            pass

        await sync_wait(page, "s4a_worker", t)
        await hide_subtitle(page)

        # ── s4a_usage: Set usage parameters ──
        t = time.time()
        rec.mark("s4a_usage")
        await show_subtitle(page, "Setting usage: 3 runs/day, 45 min each, 22 days/month", 0)

        # Scroll to usage section
        await page.evaluate("window.scrollBy(0, 200)")
        await page.wait_for_timeout(500)

        # Fill runs/day and avg runtime using label-based targeting
        # JOBS default: Runs/Day=1, Avg Runtime=30, Days/Month=22
        # Target: Runs/Day=3, Avg Runtime=45 → 3×45×22 = 49.5 hours/month
        usage_fields = [
            ("Runs/Day", "3"),
            ("Avg Runtime (min)", "45"),
        ]
        try:
            for label_text, new_val in usage_fields:
                label = page.locator(f'label:has-text("{label_text}")').last
                container = label.locator('xpath=ancestor::div[1]')
                inp = container.locator('input[type="number"]')
                if await inp.count() > 0:
                    await inp.first.scroll_into_view_if_needed()
                    await page.wait_for_timeout(200)
                    await move_to(page, inp.first, pause=200)
                    await inp.first.click(click_count=3)
                    await page.keyboard.type(new_val, delay=80)
                    await page.wait_for_timeout(300)
                else:
                    print(f"  [warn] Could not find input for '{label_text}'")
        except Exception as e:
            print(f"  [skip] usage fill: {e}")

        await sync_wait(page, "s4a_usage", t)
        await hide_subtitle(page)

        # ── s4a_save: Save workload ──
        t = time.time()
        rec.mark("s4a_save")
        await show_subtitle(page, "Saving the workload", 0)

        # Scroll to bottom to find the submit button
        await page.evaluate("window.scrollBy(0, 300)")
        await page.wait_for_timeout(300)

        # The submit button is "Add Workload" (type=submit, disabled if name empty)
        save_btn = page.locator('button[type="submit"]:has-text("Add Workload")').last
        try:
            await save_btn.wait_for(state="visible", timeout=5000)
            await click_on(page, save_btn, pause=500)
        except Exception as e:
            print(f"  [skip] save btn: {e}")
            # Try clicking any visible submit button
            save_btn = page.locator('button[type="submit"]').last
            try:
                await click_on(page, save_btn, pause=500)
            except:
                pass

        await page.wait_for_timeout(3000)  # Wait for save + cost calculation
        await sync_wait(page, "s4a_save", t)
        await hide_subtitle(page)

        # ── s4a_calc: Show calculations ──
        t = time.time()
        rec.mark("s4a_calc")
        await show_subtitle(page, "Cost breakdown: monthly DBU and VM charges", 0)

        # Scroll to top to see the workload with its cost
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        # Click on the workload to expand and show calculation details
        try:
            wl = page.locator('text=ETL Data Pipeline').first
            await click_on(page, wl, pause=1000)
        except:
            pass

        await page.wait_for_timeout(1500)
        await sync_wait(page, "s4a_calc", t)
        await hide_subtitle(page)

        # Collapse workload before adding next
        try:
            wl = page.locator('text=ETL Data Pipeline').first
            await click_on(page, wl, pause=500)
        except:
            pass

        # ══════════════════════════════════════════
        # Scene 4b: Add DBSQL Workload
        # ══════════════════════════════════════════
        print("  Scene 4b: DBSQL workload")

        # ── s4b_intro ──
        t = time.time()
        rec.mark("s4b_intro")
        await show_subtitle(page, "Adding a Databricks SQL warehouse for analytics", 0)

        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
        add_btn = page.locator('button:has-text("Add Workload")').first
        await click_on(page, add_btn, pause=1500)
        await sync_wait(page, "s4b_intro", t)
        await hide_subtitle(page)

        # Fill name
        await page.wait_for_timeout(500)
        all_inputs = page.locator('input[type="text"]')
        count = await all_inputs.count()
        for i in range(count):
            try:
                inp = all_inputs.nth(i)
                box = await inp.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    val = await inp.input_value()
                    if not val:
                        await move_to(page, inp, pause=300)
                        await inp.click()
                        await page.keyboard.type("Analytics SQL Warehouse", delay=50)
                        await page.wait_for_timeout(400)
                        break
            except:
                continue

        # ── s4b_type ──
        t = time.time()
        rec.mark("s4b_type")
        await show_subtitle(page, "Selecting Databricks SQL workload type", 0)
        selects = page.locator('select')
        sel_count = await selects.count()
        for i in range(sel_count):
            try:
                sel = selects.nth(i)
                box = await sel.bounding_box(timeout=1000)
                if box and box["y"] > 100:
                    opts = await sel.evaluate('(el) => Array.from(el.options).map(o => o.value)')
                    if 'DBSQL' in opts:
                        await visual_select(page, sel, value="DBSQL")
                        break
            except:
                continue
        await page.wait_for_timeout(1500)
        await sync_wait(page, "s4b_type", t)
        await hide_subtitle(page)

        # ── s4b_size: Select warehouse size ──
        t = time.time()
        rec.mark("s4b_size")
        await show_subtitle(page, "Choosing Large warehouse size for analytics", 0)

        await page.evaluate("window.scrollBy(0, 150)")
        await page.wait_for_timeout(500)

        # Find the warehouse size select (a native <select> with size options)
        try:
            selects = page.locator('select')
            sel_count = await selects.count()
            for i in range(sel_count):
                sel = selects.nth(i)
                box = await sel.bounding_box(timeout=500)
                if box and box["y"] > 200:
                    opts = await sel.evaluate('(el) => Array.from(el.options).map(o => o.value)')
                    if any("Small" in o or "Medium" in o or "Large" in o for o in opts):
                        await visual_select(page, sel, value="Large")
                        break
        except Exception as e:
            print(f"  [skip] size select: {e}")

        await sync_wait(page, "s4b_size", t)
        await hide_subtitle(page)

        # ── s4b_usage ──
        t = time.time()
        rec.mark("s4b_usage")
        await show_subtitle(page, "Setting avg runtime to 300 minutes per session", 0)

        await page.evaluate("window.scrollBy(0, 200)")
        await page.wait_for_timeout(500)

        # Use Run-Based mode (default) — change Avg Runtime from 30 to 300 min
        # This gives 1 run × 300 min × 22 days = 110 hours/month at Large (40 DBU/hr)
        # Use JS to find the input near the "Avg Runtime" label
        try:
            await page.evaluate("""
                (() => {
                    // Find all labels/spans containing "Avg Runtime"
                    const labels = [...document.querySelectorAll('label, span')].filter(
                        el => el.textContent.includes('Avg Runtime')
                    );
                    for (const lbl of labels) {
                        // Find the nearest number input
                        const container = lbl.closest('div');
                        if (container) {
                            const inp = container.querySelector('input[type="number"]');
                            if (inp) {
                                inp.scrollIntoView({ block: 'center' });
                                return;
                            }
                        }
                    }
                })()
            """)
            await page.wait_for_timeout(500)

            # Now find and fill the Avg Runtime input by its label
            runtime_label = page.locator('label:has-text("Avg Runtime")').last
            runtime_container = runtime_label.locator('xpath=ancestor::div[1]')
            runtime_input = runtime_container.locator('input[type="number"]')
            found = False
            if await runtime_input.count() > 0:
                await move_to(page, runtime_input.first, pause=200)
                await runtime_input.first.click(click_count=3)
                await page.keyboard.type("300", delay=80)
                await page.wait_for_timeout(300)
                found = True

            if not found:
                # Fallback: brute-force search all number inputs
                num_inputs = page.locator('input[type="number"]')
                num_count = await num_inputs.count()
                for i in range(num_count):
                    inp = num_inputs.nth(i)
                    try:
                        val = await inp.input_value()
                        if val == "30":
                            await move_to(page, inp, pause=200)
                            await inp.click(click_count=3)
                            await page.keyboard.type("300", delay=80)
                            await page.wait_for_timeout(300)
                            break
                    except:
                        continue
        except Exception as e:
            print(f"  [skip] DBSQL usage fill: {e}")

        await sync_wait(page, "s4b_usage", t)
        await hide_subtitle(page)

        # ── s4b_save ──
        t = time.time()
        rec.mark("s4b_save")
        await show_subtitle(page, "Saving the SQL warehouse workload", 0)

        await page.evaluate("window.scrollBy(0, 300)")
        await page.wait_for_timeout(300)
        save_btn = page.locator('button[type="submit"]:has-text("Add Workload")').last
        try:
            await save_btn.wait_for(state="visible", timeout=5000)
            await click_on(page, save_btn, pause=500)
        except Exception as e:
            print(f"  [skip] DBSQL save btn: {e}")
            save_btn = page.locator('button[type="submit"]').last
            try:
                await click_on(page, save_btn, pause=500)
            except:
                pass
        await page.wait_for_timeout(3000)
        await sync_wait(page, "s4b_save", t)
        await hide_subtitle(page)

        # ── s4b_compare ──
        t = time.time()
        rec.mark("s4b_compare")
        await show_subtitle(page, "Both workloads show their cost contribution with percentages", 0)

        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        # Hover the cost summary area to show percentages
        try:
            monthly = page.locator('text=Monthly Estimate').first
            await move_to(page, monthly, pause=800)
        except:
            pass

        await page.wait_for_timeout(1500)
        await sync_wait(page, "s4b_compare", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 5: Cost Summary
        # ══════════════════════════════════════════
        print("  Scene 5: Cost summary")

        # ── s5_summary ──
        t = time.time()
        rec.mark("s5_summary")
        await show_subtitle(page, "Total monthly estimate with DBU and VM cost breakdown", 0)

        try:
            dbu = page.locator('text=DBU Cost').first
            await move_to(page, dbu, pause=800)
        except:
            pass
        try:
            vm = page.locator('text=VM Cost').first
            await move_to(page, vm, pause=800)
        except:
            pass

        await sync_wait(page, "s5_summary", t)
        await hide_subtitle(page)

        # ── s5_detail ──
        t = time.time()
        rec.mark("s5_detail")
        await show_subtitle(page, "Each workload's share makes it easy to spot cost drivers", 0)

        # Scroll down slightly to show workload cost bars
        await page.evaluate("window.scrollBy(0, 100)")
        await page.wait_for_timeout(1000)

        await sync_wait(page, "s5_detail", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 6: AI Assistant
        # ══════════════════════════════════════════
        print("  Scene 6: AI Assistant")

        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        # ── s6_intro ──
        t = time.time()
        rec.mark("s6_intro")
        await show_subtitle(page, "Using the AI assistant to add a workload", 0)
        await page.wait_for_timeout(1000)
        await sync_wait(page, "s6_intro", t)
        await hide_subtitle(page)

        # ── s6_ask ──
        t = time.time()
        rec.mark("s6_ask")
        await show_subtitle(page, "Asking AI to configure a Foundation Model API workload", 0)

        # Count current workloads to detect when new one is added
        initial_workload_count = await page.locator('[aria-roledescription="sortable"]').count()

        chat_input = page.locator('textarea').last
        try:
            await move_to(page, chat_input, pause=500, timeout=5000)
            await chat_input.click()
            await page.keyboard.type(
                "Add a Foundation Model Proprietary workload using Claude Opus 4.6 "
                "with 5 million input tokens per month",
                delay=30
            )
            await page.wait_for_timeout(600)
            await page.keyboard.press("Enter")
        except Exception as e:
            print(f"  [skip] AI type: {e}")

        await sync_wait(page, "s6_ask", t)
        await hide_subtitle(page)

        # ── s6_response: Wait for AI to respond and add workload ──
        t = time.time()
        rec.mark("s6_response")
        await show_subtitle(page, "AI configures and adds the workload to the estimate", 0)

        # Poll for workload count to increase (AI adds it), max 30 seconds
        for check in range(30):
            await page.wait_for_timeout(1000)
            new_count = await page.locator('[aria-roledescription="sortable"]').count()
            if new_count > initial_workload_count:
                print(f"    AI added workload after {check+1}s ({initial_workload_count} → {new_count})")
                await page.wait_for_timeout(2000)  # Extra pause to show streaming finish
                break
        else:
            print(f"    Workload count unchanged after 30s ({new_count})")

        await sync_wait(page, "s6_response", t)
        await hide_subtitle(page)

        # ── s6_added: Show the new workload in the list ──
        t = time.time()
        rec.mark("s6_added")
        await show_subtitle(page, "New workload appears in the list with calculated cost", 0)

        # Scroll to workload list to show the new workload
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)

        # Hover over the workload list to highlight the new entry
        new_count = await page.locator('[aria-roledescription="sortable"]').count()
        if new_count > 0:
            last_wl = page.locator('[aria-roledescription="sortable"]').nth(new_count - 1)
            await move_to(page, last_wl, pause=1000)

        await page.wait_for_timeout(1000)
        await sync_wait(page, "s6_added", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 7: Export
        # ══════════════════════════════════════════
        print("  Scene 7: Export")

        # ── s7_export ──
        t = time.time()
        rec.mark("s7_export")
        await show_subtitle(page, "Exporting to Excel with full cost breakdown", 0)

        excel_btn = page.locator('button:has-text("Excel")').first
        try:
            await move_to(page, excel_btn, pause=600)
            await excel_btn.click()
            await page.wait_for_timeout(2000)
        except:
            pass

        await sync_wait(page, "s7_export", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 8: Closing
        # ══════════════════════════════════════════
        print("  Scene 8: Closing")

        # ── s8_close ──
        t = time.time()
        rec.mark("s8_close")
        await show_subtitle(page, "That's Lakemeter — start estimating your Databricks costs today!", 0)
        await sync_wait(page, "s8_close", t)
        await hide_subtitle(page)
        await page.wait_for_timeout(2000)

        # ─── Finish recording ───
        video_path = await page.video.path()
        await context.close()
        await browser.close()

    # ═══════════════════════════════════════════════
    # Post-processing: build timestamp-synced audio
    # ═══════════════════════════════════════════════
    print("Post-processing...")

    # Step 1: Convert WebM → silent MP4
    silent_mp4 = os.path.join(VIDEO_DIR, "_silent.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-vf", "scale=1280:800",
        "-movflags", "+faststart", "-an",
        silent_mp4
    ], capture_output=True)

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", silent_mp4],
        capture_output=True, text=True
    )
    video_dur = float(r.stdout.strip())
    print(f"  Video: {video_dur:.1f}s")

    # Step 2: Build synced audio — place each clip at its recorded timestamp
    concat_entries = []
    current_pos = 0.0  # current position in the audio track (seconds)

    for timestamp, clip_id in rec.marks:
        clip_path = os.path.join(AUDIO_DIR, f"{clip_id}.mp3")
        if not os.path.exists(clip_path):
            continue

        gap = timestamp - current_pos
        if gap > 0.05:
            # Generate silence file for this gap
            sil_path = os.path.join(AUDIO_DIR, f"_sil_{len(concat_entries)}.mp3")
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
                "-t", str(gap), "-c:a", "libmp3lame", "-q:a", "9", sil_path
            ], capture_output=True)
            concat_entries.append(sil_path)

        concat_entries.append(clip_path)
        current_pos = timestamp + clip_duration(clip_id)

    concat_file = os.path.join(AUDIO_DIR, "sync_concat.txt")
    with open(concat_file, "w") as f:
        for entry in concat_entries:
            f.write(f"file '{entry}'\n")

    combined = os.path.join(AUDIO_DIR, "synced_combined.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_file, "-c:a", "libmp3lame", "-q:a", "2",
        combined
    ], capture_output=True)

    audio_dur = 0
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", combined],
            capture_output=True, text=True
        )
        audio_dur = float(r.stdout.strip())
    except:
        pass
    print(f"  Audio: {audio_dur:.1f}s (synced to video timestamps)")

    # Step 3: Merge video + synced audio
    final_mp4 = os.path.join(VIDEO_DIR, "getting-started-tutorial.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", silent_mp4, "-i", combined,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        final_mp4
    ], capture_output=True)

    size = os.path.getsize(final_mp4) / (1024 * 1024)
    print(f"  → getting-started-tutorial.mp4 ({size:.1f}MB)")

    # Step 4: WebM version
    webm_path = os.path.join(VIDEO_DIR, "getting-started-tutorial.webm")
    subprocess.run([
        "ffmpeg", "-y", "-i", final_mp4,
        "-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0",
        "-c:a", "libopus", "-b:a", "96k",
        webm_path
    ], capture_output=True)
    size = os.path.getsize(webm_path) / (1024 * 1024)
    print(f"  → getting-started-tutorial.webm ({size:.1f}MB)")

    # Cleanup
    for f in [silent_mp4, video_path]:
        if os.path.exists(f) and f != final_mp4:
            try:
                os.remove(f)
            except:
                pass
    # Clean temp silence files
    for f in concat_entries:
        if "_sil_" in f and os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass

    # Print sync report
    print("\nSync report:")
    for ts, cid in rec.marks:
        print(f"  {ts:6.1f}s  {cid} ({clip_duration(cid):.1f}s)")
    print(f"\nDone! Video: {video_dur:.1f}s, Audio: {audio_dur:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
