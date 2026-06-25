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
    smooth_move, move_to, click_on, fire_ring_at,
    show_subtitle, hide_subtitle,
    visual_select, visual_searchable_select,
)

APP_URL = "https://lakemeter-oss-335310294452632.aws.databricksapps.com"
VIDEO_DIR = os.path.dirname(__file__)
VOICE = "en-US-GuyNeural"
AUDIO_DIR = os.path.join(VIDEO_DIR, "_audio_clips")
PRICING_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend", "static", "pricing")


def _get_databricks_token() -> str:
    """Get a fresh Databricks OAuth token via CLI profile."""
    import json as _json
    result = subprocess.run(
        ["databricks", "auth", "token", "--profile", "lakemeter"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get Databricks token: {result.stderr}")
    return _json.loads(result.stdout)["access_token"]


def _build_regions_from_bundle() -> dict:
    """Extract regions from the static pricing bundle (no DB needed)."""
    import json as _json
    regions_by_cloud: dict[str, set] = {"aws": set(), "azure": set(), "gcp": set()}
    for fname in ("dbu-rates.json", "instance-dbu-rates.json"):
        path = os.path.join(PRICING_DIR, fname)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            data = _json.load(f)
        for key in data:
            parts = key.split(":")
            if len(parts) >= 2:
                cloud = parts[0].lower()
                region = parts[1]
                if cloud in regions_by_cloud:
                    regions_by_cloud[cloud].add(region)
    result = {}
    for cloud, region_set in regions_by_cloud.items():
        result[cloud] = sorted(
            [{"region_code": r, "sku_region": r} for r in region_set],
            key=lambda x: x["region_code"],
        )
    return result


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
    """Wait until the region select has options with us-east-1 available."""
    for _ in range(40):
        try:
            has_region = await page.locator('select').first.evaluate(
                '(el) => Array.from(el.options).some(o => o.value === "us-east-1")'
            )
            if has_region:
                break
        except:
            pass
        await page.wait_for_timeout(500)
    await page.wait_for_timeout(500)


# ─── Main ───

async def main():
    # ─── Define narrations ───
    narrations = [
        # Scene 1: Landing (compact — one clip)
        ("s1_welcome", "Welcome to Lakemeter, the Databricks pricing calculator. "
                       "Let's create a cost estimate step by step."),
        # Scene 2: Help (compact — one clip)
        ("s2_help", "The help menu provides documentation, guides, and a link to official Databricks pricing."),
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
        ("s4a_formula", "Let's expand the calculation formula to see exactly how the cost is derived."),
        ("s4a_formula_detail", "The D-B-U cost combines driver and worker instance rates, "
                               "multiplied by monthly hours and the per-D-B-U price. "
                               "The V-M cost uses cloud instance hourly rates times total hours. "
                               "Together they give the total workload cost."),
        # Scene 4b: DBSQL
        ("s4b_intro", "Now let's add a Databricks SQL warehouse for analytics queries."),
        ("s4b_type", "Select Databricks SQL as the workload type."),
        ("s4b_size", "Choose a Large warehouse size for high concurrency analytics."),
        ("s4b_usage", "We'll set the average runtime to 5 hours per query session, 22 days per month."),
        ("s4b_save", "Save and view the cost breakdown."),
        ("s4b_compare", "Both workloads show their cost share with percentage bars."),
        # Scene 5: Summary (shorter clips — 3-4s each)
        ("s5_summary", "The total cost breaks down by D-B-U and V-M charges."),
        ("s5_detail", "Each workload shows its share of the total cost."),
        # Scene 6: AI multi-turn conversation
        ("s6_intro", "Let's explore the AI assistant. We'll ask it to propose a workload."),
        ("s6_ask", "We start by asking what type of workload we need."),
        ("s6_pick", "We'll choose document parsing for an A-I Parse workload."),
        ("s6_config", "We specify per-page billing, low complexity, and one million pages."),
        ("s6_response", "The AI generates a full workload configuration with billing mode, "
                       "complexity, and volume. We can review the details before accepting."),
        ("s6_accept", "We click the confirm button to add the workload to the estimate."),
        ("s6_added", "The A-I Parse workload has been added with calculated costs."),
        # Scene 7: Export
        ("s7_export", "Finally, export the estimate to Excel for a full cost breakdown "
                      "with SKU details, token rates, and VM pricing."),
        # Scene 8: Close (short)
        ("s8_close", "That's Lakemeter. Start estimating your Databricks costs today."),
    ]

    print("Generating voiceover clips...")
    await generate_clips(narrations)

    # ─── Record ───
    print("Recording video...")
    rec = SyncRecorder()

    # Get Databricks auth token for deployed app
    print("  Authenticating with Databricks...")
    db_token = _get_databricks_token()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=VIDEO_DIR,
            record_video_size={"width": 1440, "height": 900},
            extra_http_headers={"Authorization": f"Bearer {db_token}"},
        )
        page = await context.new_page()
        rec.start()  # Start timestamp tracking aligned with video recording start
        page.set_default_timeout(10000)  # 10s default timeout to avoid long waits in video
        # Set background + title card immediately to avoid blank white opening frame
        await page.add_init_script("document.documentElement.style.background = '#f8fafc'")
        await page.add_init_script(CURSOR_INJECT)
        await page.add_init_script(SUBTITLE_INJECT)
        # Show branded title card for 2s before navigating
        await page.evaluate("""
          () => {
            document.body.style.cssText = 'display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;background:linear-gradient(135deg, #1e293b 0%, #334155 100%);';
            const h = document.createElement('div');
            h.style.cssText = 'font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:56px;font-weight:700;color:white;letter-spacing:-1px;';
            h.textContent = 'Lakemeter';
            document.body.appendChild(h);
            const sub = document.createElement('div');
            sub.style.cssText = 'font-family:-apple-system,sans-serif;font-size:22px;color:rgba(255,255,255,0.7);margin-top:12px;font-weight:400;';
            sub.textContent = 'Databricks Pricing Calculator';
            document.body.appendChild(sub);
          }
        """)
        await page.wait_for_timeout(2000)  # Hold title card for 2s

        # Seed localStorage with regions from pricing bundle (no DB needed)
        # Uses add_init_script so it runs before React on each navigation
        import json as _json
        regions_map = _build_regions_from_bundle()
        cache_data = {
            "workloadTypes": [], "cloudProviders": [], "dbsqlSizes": [],
            "dltEditions": [], "fmapiProviders": [], "vmPricingTiers": [],
            "vmPaymentOptions": [], "fmapiDatabricksConfig": None,
            "fmapiProprietaryConfig": None, "serverlessModes": [],
            "instanceTypes": [], "modelServingGPUTypes": [],
            "regions": regions_map.get("aws", []),
            "regionsMap": regions_map,
            "photonMultipliers": [], "instanceFamilies": [],
            "dbsqlWarehouseTypes": [], "fmapiDatabricksModels": [],
            "timestamp": int(time.time() * 1000),
        }
        cache_json = _json.dumps(cache_data)
        await page.add_init_script(f"""
          try {{ localStorage.setItem('lakemeter_reference_data_v7', '{cache_json.replace("'", "\\'")}'); }} catch(e) {{}}
        """)

        # ══════════════════════════════════════════
        # Scene 1: Landing
        # ══════════════════════════════════════════
        print("  Scene 1: Landing")
        await page.goto(APP_URL, wait_until="domcontentloaded", timeout=60000)
        # Extra wait for React hydration + Google Fonts
        await page.wait_for_timeout(3000)
        # Wait for app content to render
        try:
            await page.wait_for_selector('text="Pricing Estimates"', timeout=10000)
        except:
            pass
        await page.wait_for_timeout(200)
        await setup_page(page)
        # Show subtitle as soon as page is loaded
        await show_subtitle(page, "Welcome to Lakemeter — Databricks Pricing Calculator", 0)

        # ── s1_welcome (compact — ~7s) ──
        t = time.time()
        rec.mark("s1_welcome")
        # Show subtitle immediately so there's no dead air at start
        await show_subtitle(page, "Welcome to Lakemeter — Databricks Pricing Calculator", 0)
        # Move cursor through the page to show the landing view
        await smooth_move(page, 500, 300)
        await page.wait_for_timeout(300)
        await smooth_move(page, 720, 350)
        await page.wait_for_timeout(300)
        # Hover the Lakemeter logo/header
        try:
            logo = page.locator('text=/Lakemeter|Pricing Estimates/i').first
            await move_to(page, logo, pause=300)
        except:
            pass
        await sync_wait(page, "s1_welcome", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 2: Help & Documentation (very compact — ~12s total)
        # ══════════════════════════════════════════
        print("  Scene 2: Help & Docs")

        # ── s2_help: Click Help, show dropdown briefly, close ──
        t = time.time()
        rec.mark("s2_help")
        await show_subtitle(page, "Help menu: documentation, guides, and official pricing", 0)
        help_btn = page.locator('button:has-text("Help")').first
        try:
            await click_on(page, help_btn, pause=600, timeout=5000)
            # Briefly hover docs link
            doc_link = page.locator('a:has-text("Documentation")').first
            await move_to(page, doc_link, pause=400, timeout=3000)
            # Briefly hover pricing link
            pricing_link = page.locator('a:has-text("Official Pricing"), a[href*="databricks.com/product/pricing"]').first
            await move_to(page, pricing_link, pause=400, timeout=3000)
        except:
            pass
        await sync_wait(page, "s2_help", t)
        await hide_subtitle(page)

        # Close dropdown
        await page.mouse.click(720, 400)
        await page.wait_for_timeout(200)

        # ══════════════════════════════════════════
        # Scene 3: Create Estimate
        # ══════════════════════════════════════════
        print("  Scene 3: Create estimate")

        # ── s3_create ──
        t = time.time()
        rec.mark("s3_create")
        await show_subtitle(page, "Creating a new pricing estimate", 0)
        new_link = page.locator('a:has-text("New Estimate")').first
        await move_to(page, new_link, pause=300)
        await new_link.click()
        await page.wait_for_timeout(2000)
        await setup_page(page)
        try:
            await page.wait_for_selector('select', timeout=8000)
        except:
            pass
        await wait_for_regions(page)
        await sync_wait(page, "s3_create", t)
        await hide_subtitle(page)

        # ── s3_name ──
        t = time.time()
        rec.mark("s3_name")
        await show_subtitle(page, "Naming the estimate", 0)
        name_field = page.locator('input[placeholder="Untitled Estimate"]').first
        await move_to(page, name_field, pause=400)
        await name_field.click(click_count=3)
        await page.wait_for_timeout(200)
        await name_field.press_sequentially("Q4 Data Platform Estimate", delay=75)
        await page.wait_for_timeout(400)
        # Verify name was typed into React state
        typed_val = await name_field.input_value()
        if not typed_val.strip():
            # Fallback: use fill() which reliably triggers React onChange
            await name_field.fill("Q4 Data Platform Estimate")
            await page.wait_for_timeout(200)
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
        # Wait for button to be enabled (all fields filled)
        try:
            await page.wait_for_selector('button:has-text("Create Estimate"):not([disabled])', timeout=5000)
        except:
            print("  [warn] Create Estimate still disabled — checking fields")
            # Debug: print field values
            n = await page.locator('input[placeholder="Untitled Estimate"]').first.input_value()
            r = await page.locator('select').first.input_value()
            print(f"  [debug] name='{n}' region='{r}'")
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

        # Wait for page to be ready — "Add Workload" dashed card appears after estimate creation
        try:
            await page.wait_for_selector('button:has-text("Add Workload")', timeout=20000)
        except:
            pass
        await page.wait_for_timeout(2000)

        # ── s4a_intro ──
        t = time.time()
        rec.mark("s4a_intro")
        await show_subtitle(page, "Adding a Lakeflow Jobs workload for ETL", 0)

        # Click the dashed "Add Workload" card button — with retry
        form_opened = False
        for attempt in range(3):
            add_btn = page.locator('button:has-text("Add Workload")').first
            await click_on(page, add_btn, pause=800)

            # Wait for the form to open — confirmed by the name input with placeholder
            try:
                await page.wait_for_selector('input[placeholder*="ETL Pipeline"]', state="visible", timeout=5000)
                print("    Form opened (name input found)")
                form_opened = True
                break
            except:
                print(f"  [retry {attempt+1}] Form name input not found, retrying click...")
                await page.wait_for_timeout(500)

        if not form_opened:
            print("  [warn] Form never opened after 3 attempts")
        await page.wait_for_timeout(500)

        await sync_wait(page, "s4a_intro", t)
        await hide_subtitle(page)

        # Fill workload name using placeholder selector + page.fill() for React reliability
        name_input = page.locator('input[placeholder*="ETL Pipeline"]')
        try:
            await move_to(page, name_input, pause=300)
            await name_input.click()
            # Use press_sequentially for visible typing effect, then verify with fill() fallback
            await name_input.press_sequentially("ETL Data Pipeline", delay=70)
            await page.wait_for_timeout(300)
            # Verify React state got the value
            typed = await name_input.input_value()
            if not typed.strip():
                print("    [fix] press_sequentially failed, using fill()")
                await name_input.fill("ETL Data Pipeline")
            else:
                print(f"    Name filled: '{typed}'")
        except Exception as e:
            print(f"  [warn] Could not fill workload name: {e}")

        # ── s4a_type: JOBS is the default type ──
        # Setup: find the workload type select before narration
        wl_type_sel = page.locator('select').first
        has_jobs = False
        try:
            opts = await wl_type_sel.evaluate('(el) => Array.from(el.options).map(o => o.value)')
            has_jobs = 'JOBS' in opts
        except Exception as e:
            print(f"  [warn] type select: {e}")

        t = time.time()
        rec.mark("s4a_type")
        await show_subtitle(page, "Selecting Jobs Compute workload type", 0)

        if has_jobs:
            await visual_select(page, wl_type_sel, value="JOBS")

        # Wait for VM config section
        await page.wait_for_timeout(2000)
        try:
            await page.wait_for_selector('text="Select type..."', timeout=10000)
            print("    Driver SearchableSelect ready")
        except:
            print("  [warn] SearchableSelect not found after JOBS selection")

        await sync_wait(page, "s4a_type", t)
        await hide_subtitle(page)

        # ── s4a_driver: Select driver instance type ──
        # Setup: find and scroll to element before narration
        select_trigger = None
        try:
            select_trigger = page.locator('text="Select type..."').first
            await select_trigger.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
        except:
            pass

        t = time.time()
        rec.mark("s4a_driver")
        await show_subtitle(page, "Choosing driver instance type: i3.xlarge", 0)

        try:
            if select_trigger:
                await visual_searchable_select(
                    page, select_trigger, "i3.xlarge",
                    option_text="i3.xlarge", pause=500, load_wait=2000
                )
        except Exception as e:
            print(f"  [skip] driver select: {e}")

        await sync_wait(page, "s4a_driver", t)
        await hide_subtitle(page)

        # ── s4a_worker: Configure workers ──
        # Setup: find worker select before narration
        await page.wait_for_timeout(500)
        worker_trigger = None
        try:
            worker_trigger = page.locator('text="Select type..."').first
            await worker_trigger.scroll_into_view_if_needed()
            await page.wait_for_timeout(300)
        except:
            pass

        t = time.time()
        rec.mark("s4a_worker")
        await show_subtitle(page, "Configuring worker nodes: m5.xlarge × 3", 0)

        try:
            if worker_trigger:
                await visual_searchable_select(
                    page, worker_trigger, "m5.xlarge",
                    option_text="m5.xlarge", pause=500, load_wait=2000
                )
        except Exception as e:
            print(f"  [skip] worker select: {e}")

        # Set worker count to 3 — find the spinbutton with value "2" (default)
        try:
            spinbuttons = page.locator('input[type="number"]')
            sp_count = await spinbuttons.count()
            for i in range(sp_count):
                sp = spinbuttons.nth(i)
                val = await sp.input_value()
                if val == "2":
                    await move_to(page, sp, pause=200)
                    await sp.click(click_count=3)
                    await page.keyboard.type("3", delay=100)
                    await page.wait_for_timeout(200)
                    # Verify React registered the value
                    actual = await sp.input_value()
                    if actual != "3":
                        await sp.fill("3")
                    print(f"    Worker count set to {await sp.input_value()}")
                    break
        except Exception as e:
            print(f"  [skip] worker count: {e}")

        await sync_wait(page, "s4a_worker", t)
        await hide_subtitle(page)

        # ── s4a_usage: Set usage parameters ──
        # Setup: scroll to usage section before narration
        await page.evaluate("window.scrollBy(0, 200)")
        await page.wait_for_timeout(300)

        t = time.time()
        rec.mark("s4a_usage")
        await show_subtitle(page, "Setting usage: 3 runs/day, 45 min each, 22 days/month", 0)

        # Fill runs/day and avg runtime with visible typing
        # Default: Runs/Day=1, Avg Runtime=30, Days/Month=22
        # Target: Runs/Day=3, Avg Runtime=45
        try:
            spinbuttons = page.locator('input[type="number"]')
            sp_count = await spinbuttons.count()
            for i in range(sp_count):
                sp = spinbuttons.nth(i)
                try:
                    val = await sp.input_value()
                    if val == "1":
                        await sp.scroll_into_view_if_needed()
                        await move_to(page, sp, pause=200)
                        await sp.click(click_count=3)
                        await page.keyboard.type("3", delay=100)
                        await page.wait_for_timeout(200)
                        actual = await sp.input_value()
                        if actual != "3":
                            await sp.fill("3")
                        print(f"    Runs/Day set to {await sp.input_value()}")
                    elif val == "30":
                        await sp.scroll_into_view_if_needed()
                        await move_to(page, sp, pause=200)
                        await sp.click(click_count=3)
                        await page.keyboard.type("45", delay=100)
                        await page.wait_for_timeout(200)
                        actual = await sp.input_value()
                        if actual != "45":
                            await sp.fill("45")
                        print(f"    Avg Runtime set to {await sp.input_value()}")
                except:
                    continue
        except Exception as e:
            print(f"  [skip] usage fill: {e}")

        await sync_wait(page, "s4a_usage", t)
        await hide_subtitle(page)

        # ── s4a_save: Save workload ──
        # Setup: scroll to submit button before narration
        await page.evaluate("window.scrollBy(0, 300)")
        await page.wait_for_timeout(300)
        save_btn = page.locator('button[type="submit"]:has-text("Add Workload")')

        t = time.time()
        rec.mark("s4a_save")
        await show_subtitle(page, "Saving the workload", 0)
        try:
            is_disabled = await save_btn.is_disabled()
            print(f"    Submit button disabled={is_disabled}")
            if is_disabled:
                # Name is empty — force fill it
                name_input = page.locator('input[placeholder*="ETL Pipeline"]')
                await name_input.fill("ETL Data Pipeline")
                await page.wait_for_timeout(500)
                is_disabled = await save_btn.is_disabled()
                print(f"    After name fill, disabled={is_disabled}")

            await save_btn.scroll_into_view_if_needed()
            await click_on(page, save_btn, pause=500)
        except Exception as e:
            print(f"  [FAIL] save btn: {e}")

        # Wait for form to close (confirms successful save)
        # Only check if form was actually opened
        if form_opened:
            try:
                await page.wait_for_selector('input[placeholder*="ETL Pipeline"]', state="hidden", timeout=10000)
                print("    Form closed — workload saved successfully!")
            except:
                # Check if workload was actually saved by looking for cost in the page
                wl_count = await page.locator('[aria-roledescription="sortable"]').count()
                if wl_count > 0:
                    print(f"    Form may still be open but {wl_count} workload(s) saved. Continuing.")
                    # Click outside to close form
                    await page.mouse.click(400, 200)
                    await page.wait_for_timeout(500)
                else:
                    print("  [warn] Form did not close and no workloads found — retrying submit")
                    try:
                        save_btn = page.locator('button[type="submit"]:has-text("Add Workload")')
                        await save_btn.click(force=True)
                        await page.wait_for_selector('input[placeholder*="ETL Pipeline"]', state="hidden", timeout=5000)
                        print("    Form closed on retry!")
                    except:
                        print("  [warn] Form still open after retry")

        await page.wait_for_timeout(3000)  # Wait for cost calculation
        await sync_wait(page, "s4a_save", t)
        await hide_subtitle(page)

        # ── s4a_calc: Show calculations ──
        # Setup: scroll to top before narration
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)

        t = time.time()
        rec.mark("s4a_calc")
        await show_subtitle(page, "Cost breakdown: monthly DBU and VM charges", 0)

        # Click on the workload row to expand cost details
        try:
            wl = page.locator('text=ETL Data Pipeline').first
            await click_on(page, wl, pause=1000)
        except Exception as e:
            print(f"  [skip] expand workload: {e}")

        await page.wait_for_timeout(1500)
        await sync_wait(page, "s4a_calc", t)
        await hide_subtitle(page)

        # ── s4a_formula: Expand calculation formula ──
        t = time.time()
        rec.mark("s4a_formula")
        await show_subtitle(page, "Expanding the cost calculation formula", 0)

        # Click "Show Cost Calculation" button in the expanded workload details
        try:
            calc_btn = page.locator('button:has-text("Show Cost Calculation")').first
            await calc_btn.scroll_into_view_if_needed()
            await click_on(page, calc_btn, pause=800)
        except Exception as e:
            # Fallback: try calculator icon button with title
            try:
                calc_btn = page.locator('button[title="Show calculation"]').first
                await click_on(page, calc_btn, pause=800)
            except:
                print(f"  [skip] formula toggle: {e}")

        await page.wait_for_timeout(500)
        await sync_wait(page, "s4a_formula", t)
        await hide_subtitle(page)

        # ── s4a_formula_detail: Hover through DBU, VM, Total formula lines ──
        t = time.time()
        rec.mark("s4a_formula_detail")
        await show_subtitle(page, "DBU + VM cost formula with actual instance rates", 0)

        # Scroll formula into view and hover each line
        try:
            # Hover DBU formula line
            dbu_label = page.locator('span:has-text("DBU:")').first
            await dbu_label.scroll_into_view_if_needed()
            await move_to(page, dbu_label, pause=600)
            # Slowly scan across the DBU formula
            dbu_box = await dbu_label.bounding_box()
            if dbu_box:
                await smooth_move(page, dbu_box["x"] + 200, dbu_box["y"] + dbu_box["height"]/2)
                await page.wait_for_timeout(500)
                await smooth_move(page, dbu_box["x"] + 450, dbu_box["y"] + dbu_box["height"]/2)
                await page.wait_for_timeout(500)
        except Exception as e:
            print(f"  [skip] DBU formula hover: {e}")

        try:
            # Hover VM formula line
            vm_label = page.locator('span:has-text("VM:")').first
            await move_to(page, vm_label, pause=600)
            vm_box = await vm_label.bounding_box()
            if vm_box:
                await smooth_move(page, vm_box["x"] + 200, vm_box["y"] + vm_box["height"]/2)
                await page.wait_for_timeout(500)
                await smooth_move(page, vm_box["x"] + 400, vm_box["y"] + vm_box["height"]/2)
                await page.wait_for_timeout(500)
        except Exception as e:
            print(f"  [skip] VM formula hover: {e}")

        try:
            # Hover Total line
            total_label = page.locator('span:has-text("Total:")').first
            await move_to(page, total_label, pause=800)
        except Exception as e:
            print(f"  [skip] Total formula hover: {e}")

        await sync_wait(page, "s4a_formula_detail", t)
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
        # Setup: scroll to top and find Add button before narration
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)
        add_btn = page.locator('button:has-text("Add Workload")').first

        t = time.time()
        rec.mark("s4b_intro")
        await show_subtitle(page, "Adding a Databricks SQL warehouse for analytics", 0)
        try:
            await click_on(page, add_btn, pause=1000)
        except:
            # Fallback to header "Add" button
            add_btn = page.locator('button:has-text("Add")').first
            await click_on(page, add_btn, pause=1000)

        # Wait for form
        try:
            await page.wait_for_selector('input[placeholder*="ETL Pipeline"]', timeout=10000)
        except:
            pass
        await page.wait_for_timeout(500)
        await sync_wait(page, "s4b_intro", t)
        await hide_subtitle(page)

        # Fill name using placeholder + fill()
        name_input = page.locator('input[placeholder*="ETL Pipeline"]')
        try:
            await move_to(page, name_input, pause=300)
            await name_input.click()
            await name_input.press_sequentially("Analytics SQL Warehouse", delay=70)
            await page.wait_for_timeout(300)
            typed = await name_input.input_value()
            if not typed.strip():
                await name_input.fill("Analytics SQL Warehouse")
            print(f"    DBSQL name: '{await name_input.input_value()}'")
        except Exception as e:
            print(f"  [warn] DBSQL name fill: {e}")

        # ── s4b_type ──
        # Setup: find select before narration
        wl_type_sel = page.locator('select').first
        has_dbsql = False
        try:
            opts = await wl_type_sel.evaluate('(el) => Array.from(el.options).map(o => o.value)')
            has_dbsql = 'DBSQL' in opts
        except Exception as e:
            print(f"  [warn] DBSQL type select: {e}")

        t = time.time()
        rec.mark("s4b_type")
        await show_subtitle(page, "Selecting Databricks SQL workload type", 0)

        if has_dbsql:
            await visual_select(page, wl_type_sel, value="DBSQL")
        await page.wait_for_timeout(1500)
        await sync_wait(page, "s4b_type", t)
        await hide_subtitle(page)

        # ── s4b_size: Select warehouse size ──
        # Setup: scroll and find size select before narration
        await page.evaluate("window.scrollBy(0, 150)")
        await page.wait_for_timeout(300)
        size_sel = None
        try:
            selects = page.locator('select')
            sel_count = await selects.count()
            for i in range(sel_count):
                sel = selects.nth(i)
                opts = await sel.evaluate('(el) => Array.from(el.options).map(o => o.value)')
                if 'Large' in opts or any('Small' in o for o in opts):
                    size_sel = sel
                    break
        except Exception as e:
            print(f"  [skip] size select: {e}")

        t = time.time()
        rec.mark("s4b_size")
        await show_subtitle(page, "Choosing Large warehouse size for analytics", 0)

        if size_sel:
            await visual_select(page, size_sel, value="Large")
            print(f"    Warehouse size set to Large")

        await sync_wait(page, "s4b_size", t)
        await hide_subtitle(page)

        # ── s4b_usage ──
        # Setup: scroll before narration
        await page.evaluate("window.scrollBy(0, 200)")
        await page.wait_for_timeout(300)

        t = time.time()
        rec.mark("s4b_usage")
        await show_subtitle(page, "Setting avg runtime to 300 minutes per session", 0)

        # DBSQL default: Runs/Day=1, Avg Runtime=30, Days/Month=22
        # Change Avg Runtime to 300 → 1×300min×22days = 110 hours/month
        try:
            spinbuttons = page.locator('input[type="number"]')
            sp_count = await spinbuttons.count()
            for i in range(sp_count):
                sp = spinbuttons.nth(i)
                try:
                    val = await sp.input_value()
                    if val == "30":
                        await sp.scroll_into_view_if_needed()
                        await move_to(page, sp, pause=200)
                        await sp.click(click_count=3)
                        await page.keyboard.type("300", delay=100)
                        await page.wait_for_timeout(300)
                        actual = await sp.input_value()
                        if actual != "300":
                            await sp.fill("300")
                        print(f"    Avg Runtime set to {await sp.input_value()}")
                        break
                except:
                    continue
        except Exception as e:
            print(f"  [skip] DBSQL usage fill: {e}")

        await sync_wait(page, "s4b_usage", t)
        await hide_subtitle(page)

        # ── s4b_save ──
        # Setup: scroll and find button before narration
        await page.evaluate("window.scrollBy(0, 300)")
        await page.wait_for_timeout(300)
        save_btn = page.locator('button[type="submit"]:has-text("Add Workload")')

        t = time.time()
        rec.mark("s4b_save")
        await show_subtitle(page, "Saving the SQL warehouse workload", 0)
        try:
            is_disabled = await save_btn.is_disabled()
            print(f"    DBSQL submit disabled={is_disabled}")
            if is_disabled:
                name_input = page.locator('input[placeholder*="ETL Pipeline"]')
                await name_input.fill("Analytics SQL Warehouse")
                await page.wait_for_timeout(500)
            await save_btn.scroll_into_view_if_needed()
            await click_on(page, save_btn, pause=500)
        except Exception as e:
            print(f"  [FAIL] DBSQL save btn: {e}")

        # Wait for form to close (confirms successful save)
        form_closed = False
        try:
            await page.wait_for_selector('input[placeholder*="ETL Pipeline"]', state="hidden", timeout=8000)
            print("    DBSQL form closed — workload saved!")
            form_closed = True
        except:
            print("  [retry] DBSQL form still open, trying submit again")
            try:
                # Scroll to bottom to ensure submit visible
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(500)
                name_input = page.locator('input[placeholder*="ETL Pipeline"]')
                name_val = await name_input.input_value()
                print(f"    Name value: '{name_val}'")
                if not name_val.strip():
                    await name_input.fill("Analytics SQL Warehouse")
                    await page.wait_for_timeout(300)
                save_btn = page.locator('button[type="submit"]:has-text("Add Workload")')
                await save_btn.click(force=True)
                await page.wait_for_timeout(5000)
                try:
                    await page.wait_for_selector('input[placeholder*="ETL Pipeline"]', state="hidden", timeout=5000)
                    print("    DBSQL form closed on retry!")
                    form_closed = True
                except:
                    print("  [warn] DBSQL form still open after retry")
            except Exception as e:
                print(f"  [warn] retry failed: {e}")

        await page.wait_for_timeout(3000)
        await sync_wait(page, "s4b_save", t)
        await hide_subtitle(page)

        # ── s4b_compare ──
        t = time.time()
        rec.mark("s4b_compare")
        await show_subtitle(page, "Both workloads show their cost share with percentage bars", 0)

        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)

        # Actively hover BOTH workload rows + cost summary
        workload_rows = page.locator('[aria-roledescription="sortable"]')
        wl_count = await workload_rows.count()
        for i in range(min(wl_count, 2)):
            row = workload_rows.nth(i)
            await move_to(page, row, pause=300)
        try:
            monthly = page.locator('text=Monthly Estimate').first
            await move_to(page, monthly, pause=300)
        except:
            pass
        await sync_wait(page, "s4b_compare", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 5: Cost Summary (compact)
        # ══════════════════════════════════════════
        print("  Scene 5: Cost summary")

        # ── s5_summary ──
        t = time.time()
        rec.mark("s5_summary")
        await show_subtitle(page, "Total monthly estimate with DBU and VM cost breakdown", 0)

        # Continuously move cursor through cost elements: heading → total → DBU → VM → pie chart
        try:
            summary_heading = page.locator('text=Cost Summary').first
            await move_to(page, summary_heading, pause=300)
        except:
            pass
        try:
            total = page.locator('text=/\\$[\\d,]+\\.\\d{2}/').first
            await move_to(page, total, pause=400)
        except:
            await smooth_move(page, 1100, 300)
        try:
            dbu_label = page.locator('text=/DBU/i').first
            await move_to(page, dbu_label, pause=400)
        except:
            pass
        # Move to VM cost area
        try:
            vm_label = page.locator('text=/VM|Infrastructure/i').first
            await move_to(page, vm_label, pause=400)
        except:
            await smooth_move(page, 1100, 450)
            await page.wait_for_timeout(300)
        # Circle back to total
        try:
            total = page.locator('text=/\\$[\\d,]+\\.\\d{2}/').first
            await move_to(page, total, pause=300)
        except:
            pass

        await sync_wait(page, "s5_summary", t)
        await hide_subtitle(page)

        # ── s5_detail ──
        t = time.time()
        rec.mark("s5_detail")
        await show_subtitle(page, "Each workload's share makes it easy to spot cost drivers", 0)

        # Hover workload rows + their cost columns
        workload_rows = page.locator('[aria-roledescription="sortable"]')
        wl_count = await workload_rows.count()
        for i in range(min(wl_count, 2)):
            row = workload_rows.nth(i)
            box = await move_to(page, row, pause=300)
            # Move to the right side of the row (cost column)
            if box:
                await smooth_move(page, box["x"] + box["width"] - 50, box["y"] + box["height"]/2)
                await page.wait_for_timeout(300)
        # Hover the percentage/bar area
        try:
            pct = page.locator('text=/%/').first
            await move_to(page, pct, pause=300)
        except:
            await smooth_move(page, 900, 400)
        # End on the total cost
        try:
            total = page.locator('text=/\\$[\\d,]+\\.\\d{2}/').first
            await move_to(page, total, pause=300)
        except:
            pass

        await sync_wait(page, "s5_detail", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 6: AI Assistant — multi-turn conversation
        # ══════════════════════════════════════════
        print("  Scene 6: AI Assistant")

        # Setup: scroll to top and find chat area
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)
        initial_workload_count = await page.locator('[aria-roledescription="sortable"]').count()

        # Helper: send a chat message and wait for AI response
        async def send_chat_message(text, typing_delay=30):
            chat_input = page.locator('textarea').last
            await move_to(page, chat_input, pause=200, timeout=5000)
            await chat_input.click()
            await page.keyboard.type(text, delay=typing_delay)
            await page.wait_for_timeout(400)
            await page.keyboard.press("Enter")

        # Helper: wait for AI to finish streaming (spinner disappears or new text stops)
        async def wait_for_ai_response(max_wait=45):
            """Wait for the AI assistant to finish generating a response."""
            prev_text = ""
            stable_ticks = 0
            for i in range(max_wait):
                await page.wait_for_timeout(1000)
                # Check if a loading spinner is visible
                spinner = await page.locator('.animate-spin').count()
                if spinner == 0 and i > 2:
                    # No spinner — check if text is stable
                    try:
                        cur_text = await page.locator('[class*="message"], [class*="chat-message"]').last.inner_text()
                    except:
                        cur_text = ""
                    if cur_text == prev_text and cur_text:
                        stable_ticks += 1
                        if stable_ticks >= 2:
                            print(f"    AI responded after {i+1}s")
                            return True
                    else:
                        stable_ticks = 0
                    prev_text = cur_text
                # Gently move cursor to follow the streaming text
                y_pos = 300 + (i * 25) % 350
                await smooth_move(page, 1200, y_pos)
            print(f"    [WARN] AI response wait timed out after {max_wait}s")
            return False

        # ── s6_intro: Move to chat area ──
        t = time.time()
        rec.mark("s6_intro")
        await show_subtitle(page, "Exploring the AI assistant to propose a workload", 0)
        try:
            chat_area = page.locator('textarea').last
            await move_to(page, chat_area, pause=400, timeout=5000)
        except:
            await smooth_move(page, 1200, 500)
        await sync_wait(page, "s6_intro", t)
        await hide_subtitle(page)

        # ── s6_ask: First message — ask for workload type ──
        t = time.time()
        rec.mark("s6_ask")
        await show_subtitle(page, "Asking the AI to propose a new workload", 0)

        try:
            await send_chat_message(
                "Propose a new workload for my existing estimate. Ask me what type I need.",
                typing_delay=25
            )
        except Exception as e:
            print(f"  [skip] AI msg 1: {e}")

        # Wait for AI to respond with workload type list
        await wait_for_ai_response(max_wait=30)
        await page.wait_for_timeout(1000)
        await sync_wait(page, "s6_ask", t)
        await hide_subtitle(page)

        # ── s6_pick: Second message — choose document parsing ──
        t = time.time()
        rec.mark("s6_pick")
        await show_subtitle(page, "Choosing document parsing for an AI Parse workload", 0)

        try:
            await send_chat_message("document parsing", typing_delay=40)
        except Exception as e:
            print(f"  [skip] AI msg 2: {e}")

        # Wait for AI to respond with follow-up questions
        await wait_for_ai_response(max_wait=30)
        await page.wait_for_timeout(1000)
        await sync_wait(page, "s6_pick", t)
        await hide_subtitle(page)

        # ── s6_config: Third message — specify per-page, low, 1M pages ──
        t = time.time()
        rec.mark("s6_config")
        await show_subtitle(page, "Specifying per-page billing, low complexity, one million pages", 0)

        try:
            await send_chat_message("per page, low, 1 million page", typing_delay=35)
        except Exception as e:
            print(f"  [skip] AI msg 3: {e}")

        await sync_wait(page, "s6_config", t)
        await hide_subtitle(page)

        # ── s6_response: Wait for AI to generate the configuration proposal ──
        t = time.time()
        rec.mark("s6_response")
        await show_subtitle(page, "AI generates a full workload configuration for review", 0)

        # Wait for the proposal card with confirm/reject buttons to appear
        confirm_btn = page.locator('button[title="Confirm & Add"]').first
        proposal_found = False
        for check in range(60):
            await page.wait_for_timeout(1000)
            btn_count = await page.locator('button[title="Confirm & Add"]').count()
            if btn_count > 0:
                print(f"    AI proposal appeared after {check+1}s")
                proposal_found = True
                break
            # Follow streaming text
            y_pos = 300 + (check * 25) % 350
            await smooth_move(page, 1200, y_pos)
        else:
            # Also check for "Accept All" as alternative
            accept_all = await page.locator('button:has-text("Accept All")').count()
            if accept_all > 0:
                proposal_found = True
                print(f"    AI proposal (Accept All) found")
            else:
                print(f"    [WARN] AI proposal not found after 60s")

        # Scroll to make the proposal card fully visible
        await page.wait_for_timeout(1000)
        try:
            proposal_card = page.locator('button[title="Confirm & Add"]').first
            await proposal_card.scroll_into_view_if_needed()
            await page.wait_for_timeout(500)
        except:
            pass

        await sync_wait(page, "s6_response", t)
        await hide_subtitle(page)

        # ── s6_accept: Click the confirm button ──
        t = time.time()
        rec.mark("s6_accept")
        ai_added = False

        if proposal_found:
            await show_subtitle(page, "Confirming the proposed workload configuration", 0)
            try:
                confirm_btn = page.locator('button[title="Confirm & Add"]').first
                await move_to(page, confirm_btn, pause=600)
                await confirm_btn.click()
                print("    Clicked Confirm & Add")
                # Wait for workload to appear in the list
                for check in range(20):
                    await page.wait_for_timeout(1000)
                    new_count = await page.locator('[aria-roledescription="sortable"]').count()
                    if new_count > initial_workload_count:
                        print(f"    Workload added ({initial_workload_count} → {new_count})")
                        ai_added = True
                        break
            except Exception as e:
                print(f"  [skip] confirm click: {e}")
        else:
            await show_subtitle(page, "The AI assistant generates workload configurations from chat", 0)

        await page.wait_for_timeout(1000)
        await sync_wait(page, "s6_accept", t)
        await hide_subtitle(page)

        # ── s6_added: Show the new workload in the list ──
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)

        t = time.time()
        rec.mark("s6_added")

        if ai_added:
            await show_subtitle(page, "AI Parse workload has been added with calculated costs", 0)
            new_count = await page.locator('[aria-roledescription="sortable"]').count()
            if new_count > 0:
                last_wl = page.locator('[aria-roledescription="sortable"]').nth(new_count - 1)
                wl_box = await move_to(page, last_wl, pause=600)
                if wl_box:
                    await fire_ring_at(page, wl_box["x"] + wl_box["width"]/2, wl_box["y"] + wl_box["height"]/2)
                await page.wait_for_timeout(1000)
                try:
                    total = page.locator('text=/\\$[\\d,]+\\.\\d{2}/').first
                    await move_to(page, total, pause=400)
                except:
                    pass
        else:
            await show_subtitle(page, "The AI assistant generates workload configurations from natural language", 0)
            try:
                msgs = page.locator('[class*="message"], [class*="chat"]').last
                await move_to(page, msgs, pause=400, timeout=3000)
            except:
                await smooth_move(page, 1200, 350)
                await page.wait_for_timeout(400)

        await sync_wait(page, "s6_added", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 7: Export
        # ══════════════════════════════════════════
        print("  Scene 7: Export")

        # ── s7_export ──
        # Setup: scroll to top and find button before narration
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)
        excel_btn = page.locator('button:has-text("Excel")').first

        t = time.time()
        rec.mark("s7_export")
        await show_subtitle(page, "Exporting to Excel with full cost breakdown", 0)
        try:
            await click_on(page, excel_btn, pause=2000)
        except:
            # Fallback: try any download/export icon button
            try:
                export_btn = page.locator('button[title*="Export"], button[title*="Download"]').first
                await click_on(page, export_btn, pause=2000)
            except:
                pass

        await sync_wait(page, "s7_export", t)
        await hide_subtitle(page)

        # ══════════════════════════════════════════
        # Scene 8: Closing
        # ══════════════════════════════════════════
        print("  Scene 8: Closing")

        # ── s8_close (compact ~5s) ──
        # Scroll to top for clean final view
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(300)
        t = time.time()
        rec.mark("s8_close")
        await show_subtitle(page, "That's Lakemeter — start estimating your Databricks costs today!", 0)
        # Move cursor to Lakemeter logo for clean ending
        try:
            logo = page.locator('text=/Lakemeter|Pricing/i').first
            await move_to(page, logo, pause=300)
        except:
            await smooth_move(page, 200, 50)
        await sync_wait(page, "s8_close", t)
        await hide_subtitle(page)

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
        "-vf", "scale=1440:900",
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

    # Add trailing silence to match video duration
    if current_pos < video_dur:
        trailing_gap = video_dur - current_pos + 0.5
        trailing_sil = os.path.join(AUDIO_DIR, f"_sil_trailing.mp3")
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
            "-t", str(trailing_gap), "-c:a", "libmp3lame", "-q:a", "9", trailing_sil
        ], capture_output=True)
        concat_entries.append(trailing_sil)

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
