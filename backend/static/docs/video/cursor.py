"""Shared cursor injection and mouse movement utilities for Playwright recordings.

Includes:
  - Custom cursor overlay (arrow + click ring)
  - Subtitle bar (bottom of viewport)
  - Visual <select> dropdown simulation (shows options overlay for headless recording)
"""

# Custom cursor: large arrow with drop shadow, plus click ring animation
CURSOR_INJECT = """
(() => {
  if (document.getElementById('pw-cursor')) return;

  // Cursor container
  const cursor = document.createElement('div');
  cursor.id = 'pw-cursor';
  cursor.style.cssText = 'position:fixed;top:0;left:0;z-index:999999;pointer-events:none;will-change:transform;filter:drop-shadow(1px 2px 2px rgba(0,0,0,0.3));';

  // Highlight dot behind cursor + Arrow SVG (40x40) + click ring
  cursor.innerHTML = `
    <div style="position:absolute;top:4px;left:4px;width:28px;height:28px;border-radius:50%;background:rgba(59,130,246,0.25);filter:blur(4px);"></div>
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 5L32 20L20 22L15 33L8 5Z" fill="white" stroke="black" stroke-width="2.5" stroke-linejoin="round"/>
    </svg>
    <div id="pw-click-ring" style="position:absolute;top:-16px;left:-16px;width:72px;height:72px;border-radius:50%;border:3px solid rgba(239,68,68,0.9);background:rgba(239,68,68,0.2);opacity:0;transform:scale(0.3);pointer-events:none;"></div>
  `;
  document.body.appendChild(cursor);

  // Follow mouse
  let curX = 0, curY = 0;
  document.addEventListener('mousemove', e => {
    curX = e.clientX; curY = e.clientY;
    cursor.style.transform = `translate(${curX}px, ${curY}px)`;
  });

  // Click animation
  document.addEventListener('mousedown', () => {
    const ring = document.getElementById('pw-click-ring');
    if (!ring) return;
    ring.style.transition = 'none';
    ring.style.opacity = '1';
    ring.style.transform = 'scale(0.3)';
    requestAnimationFrame(() => {
      ring.style.transition = 'all 0.4s ease-out';
      ring.style.opacity = '0';
      ring.style.transform = 'scale(1.2)';
    });
  });
})();
"""


async def inject_cursor(page):
    """Inject cursor overlay into the page."""
    await page.evaluate(CURSOR_INJECT)


async def smooth_move(page, x, y, steps=30):
    """Move mouse smoothly to (x, y)."""
    await page.mouse.move(x, y, steps=steps)
    await page.wait_for_timeout(30)


async def move_to(page, locator, pause=400, timeout=5000):
    """Move mouse smoothly to center of element, return bounding box."""
    try:
        await locator.wait_for(state="visible", timeout=timeout)
        box = await locator.bounding_box(timeout=timeout)
        if box:
            await smooth_move(page, box["x"] + box["width"]/2, box["y"] + box["height"]/2)
            await page.wait_for_timeout(pause)
        return box
    except Exception as e:
        print(f"  [skip] move_to failed: {e}")
        return None


async def click_on(page, locator, pause=500, timeout=5000):
    """Move to element, then click it."""
    box = await move_to(page, locator, pause=200, timeout=timeout)
    if box:
        await locator.click(timeout=timeout)
        await page.wait_for_timeout(pause)
    return box


# ─── Subtitle overlay system ───

SUBTITLE_INJECT = """
(() => {
  if (document.getElementById('pw-subtitle')) return;
  const bar = document.createElement('div');
  bar.id = 'pw-subtitle';
  bar.style.cssText = `
    position: fixed; bottom: 0; left: 0; right: 0; z-index: 999998;
    height: 52px; display: flex; align-items: center; justify-content: center;
    background: rgba(0,0,0,0.78); backdrop-filter: blur(8px);
    opacity: 0; transition: opacity 0.3s ease;
    pointer-events: none;
  `;
  const text = document.createElement('span');
  text.id = 'pw-subtitle-text';
  text.style.cssText = `
    color: #fff; font-size: 18px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    font-weight: 500; letter-spacing: 0.3px; text-shadow: 0 1px 3px rgba(0,0,0,0.5);
  `;
  bar.appendChild(text);
  document.body.appendChild(bar);
})();
"""


async def inject_subtitle(page):
    """Inject subtitle overlay into the page."""
    await page.evaluate(SUBTITLE_INJECT)


async def show_subtitle(page, text, pause=2000):
    """Show subtitle text with fade-in, wait for `pause` ms."""
    await page.evaluate(f"""
      (() => {{
        let bar = document.getElementById('pw-subtitle');
        if (!bar) {{ {SUBTITLE_INJECT}; bar = document.getElementById('pw-subtitle'); }}
        const span = document.getElementById('pw-subtitle-text');
        if (span) span.textContent = {repr(text)};
        if (bar) bar.style.opacity = '1';
      }})()
    """)
    await page.wait_for_timeout(pause)


async def hide_subtitle(page, pause=300):
    """Hide subtitle with fade-out."""
    await page.evaluate("""
      (() => {
        const bar = document.getElementById('pw-subtitle');
        if (bar) bar.style.opacity = '0';
      })()
    """)
    await page.wait_for_timeout(pause)


# ─── Visual <select> dropdown simulation ───

async def visual_select(page, select_locator, *, label=None, value=None, index=None,
                        show_ms=1200, highlight_ms=800):
    """Select an option with a visible dropdown overlay for video recording.

    Native <select> dropdowns are invisible in headless Chromium. This function:
      1. Reads all <option> elements from the <select>
      2. Creates a floating dropdown overlay positioned below the <select>
      3. Highlights the target option
      4. Removes the overlay and calls select_option()
    """
    # Move cursor to the <select> element
    await move_to(page, select_locator, pause=300)

    # Build and display the visual overlay
    await page.evaluate("""
      (args) => {
        const {selectSelector, targetValue, targetLabel, targetIndex} = args;
        const sel = document.querySelector(selectSelector) || document.activeElement;
        if (!sel || sel.tagName !== 'SELECT') return;

        const rect = sel.getBoundingClientRect();
        const opts = Array.from(sel.options);

        // Create dropdown overlay
        const overlay = document.createElement('div');
        overlay.id = 'pw-select-overlay';
        overlay.style.cssText = `
          position: fixed; z-index: 999997;
          left: ${rect.left}px; top: ${rect.bottom + 2}px;
          width: ${Math.max(rect.width, 220)}px;
          max-height: 260px; overflow-y: auto;
          background: white; border: 1px solid #d1d5db;
          border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.15);
          padding: 4px 0; opacity: 0;
          transition: opacity 0.15s ease;
        `;

        // Determine which option to highlight
        let highlightIdx = -1;
        if (targetValue !== null) highlightIdx = opts.findIndex(o => o.value === targetValue);
        else if (targetLabel !== null) highlightIdx = opts.findIndex(o => o.textContent.trim() === targetLabel);
        else if (targetIndex !== null) highlightIdx = targetIndex;

        opts.forEach((opt, i) => {
          if (opt.value === '' && opt.textContent.includes('Select')) return; // skip placeholder
          const row = document.createElement('div');
          row.style.cssText = `
            padding: 6px 12px; font-size: 13px; cursor: default;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            color: #1f2937; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            ${i === highlightIdx ? 'background: #3b82f6; color: white; border-radius: 4px; margin: 0 4px; padding: 6px 8px;' : ''}
          `;
          row.textContent = opt.textContent;
          overlay.appendChild(row);
        });

        document.body.appendChild(overlay);
        // Trigger fade-in
        requestAnimationFrame(() => { overlay.style.opacity = '1'; });
      }
    """, {
        "selectSelector": await select_locator.evaluate("el => { const id = el.id; const name = el.name; if (id) return '#'+id; if (name) return 'select[name=\"'+name+'\"]'; return 'select'; }"),
        "targetValue": value,
        "targetLabel": label,
        "targetIndex": index,
    })

    await page.wait_for_timeout(show_ms)

    # Highlight the target option briefly
    await page.wait_for_timeout(highlight_ms)

    # Remove overlay with fade-out
    await page.evaluate("""
      (() => {
        const ol = document.getElementById('pw-select-overlay');
        if (ol) {
          ol.style.opacity = '0';
          setTimeout(() => ol.remove(), 200);
        }
      })()
    """)
    await page.wait_for_timeout(300)

    # Actually select the option
    if label:
        await select_locator.select_option(label=label)
    elif value:
        await select_locator.select_option(value=value)
    elif index is not None:
        await select_locator.select_option(index=index)

    await page.wait_for_timeout(400)


# ─── Custom SearchableSelect interaction ───

async def visual_searchable_select(page, trigger_locator, search_text,
                                    option_text=None, pause=500, load_wait=2000):
    """Interact with a custom SearchableSelect React component for video recording.

    Custom dropdowns ARE visible in headless Chrome (unlike native <select>).
    This function provides smooth mouse movements for clean video capture.

    Args:
        trigger_locator: Playwright locator for the SearchableSelect container/trigger
        search_text: Text to type into the search field
        option_text: Text of the option to click (defaults to search_text)
        pause: ms to wait after selection
        load_wait: ms to wait for options to load after opening
    """
    await move_to(page, trigger_locator, pause=300)
    await trigger_locator.click()
    await page.wait_for_timeout(load_wait)

    # Type search text with visible typing
    await page.keyboard.type(search_text, delay=60)
    await page.wait_for_timeout(800)

    # Find and click matching option in the dropdown overlay
    # The SearchableSelect dropdown has classes: absolute z-50 w-full overflow-auto
    # (Distinguish from tooltips which have w-64 and invisible)
    target = option_text or search_text
    dropdown = page.locator('[class*="absolute"][class*="z-50"][class*="overflow-auto"]').last
    try:
        await dropdown.wait_for(state="visible", timeout=5000)
        # Find the option div that contains the target text
        option = dropdown.locator(f'div >> text=/{target}/i').first
        await move_to(page, option, pause=300)
        await option.click()
    except Exception as e:
        print(f"  [searchable_select] Could not find option '{target}': {e}")

    await page.wait_for_timeout(pause)
