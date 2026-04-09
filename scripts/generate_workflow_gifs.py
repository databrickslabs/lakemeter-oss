"""Generate 6 workflow GIF animations for Lakemeter documentation.

Creates realistic UI mockup GIFs demonstrating key workflows:
1. creating-estimate.gif — New Estimate flow
2. adding-workload.gif — Add Workload flow
3. drag-and-drop.gif — Workload reordering
4. ai-assistant.gif — AI chat interaction
5. export-excel.gif — Export download
6. cost-summary.gif — Expand/collapse costs + tooltips
"""

import sys
from pathlib import Path

from gif_ui_helpers import (
    COLORS, WIDTH, HEIGHT, FRAME_DURATION,
    hex_to_rgb, get_font, new_frame,
    draw_sidebar, draw_header, draw_button, draw_input_field,
    draw_card, draw_cursor, draw_step_indicator, save_gif,
)
from gif_workflow_frames import (
    generate_creating_estimate_frames,
    generate_adding_workload_frames,
    generate_drag_and_drop_frames,
)
from gif_workflow_frames_2 import (
    generate_ai_assistant_frames,
    generate_export_excel_frames,
)
from gif_workflow_frames_3 import generate_cost_summary_frames

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "docs-site" / "static" / "img" / "gifs"


def main() -> None:
    """Generate all 6 workflow GIFs."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    generators = {
        "creating-estimate.gif": generate_creating_estimate_frames,
        "adding-workload.gif": generate_adding_workload_frames,
        "drag-and-drop.gif": generate_drag_and_drop_frames,
        "ai-assistant.gif": generate_ai_assistant_frames,
        "export-excel.gif": generate_export_excel_frames,
        "cost-summary.gif": generate_cost_summary_frames,
    }

    for filename, gen_func in generators.items():
        path = OUTPUT_DIR / filename
        frames, durations = gen_func()
        save_gif(frames, str(path), durations)
        size_kb = path.stat().st_size / 1024
        print(f"  {filename}: {len(frames)} frames, {size_kb:.0f}KB")

    print(f"\nAll 6 GIFs written to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
