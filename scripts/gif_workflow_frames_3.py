"""Frame generator for cost-summary workflow GIF.

Returns (frames, durations) for save_gif().
"""

from PIL import ImageDraw
from gif_ui_helpers import (
    COLORS, hex_to_rgb, get_font, new_frame,
    draw_sidebar, draw_header, draw_card, draw_cursor, draw_step_indicator,
)


def _base_frame(title: str):
    img = new_frame()
    draw = ImageDraw.Draw(img)
    draw_sidebar(draw)
    draw_header(draw, title)
    return img, draw


WORKLOADS = [
    ("ETL Daily Pipeline", "$2,340.00", "Jobs"),
    ("Analytics Warehouse", "$1,200.00", "DBSQL"),
    ("ML Serving Endpoint", "$960.00", "Serving"),
]

DETAILS = [
    ("DBU Cost:", "$1,920.00"), ("VM Cost:", "$420.00"),
    ("DBU Rate:", "0.15 DBU/hr"), ("Hours:", "160/mo"),
]


def _draw_summary_header(draw: ImageDraw.Draw) -> None:
    """Draw the cost summary card header (total cost)."""
    bold = get_font(14)
    draw_card(draw, 200, 65, 580, 400)
    draw.text((220, 80), "Total Monthly Cost", fill=hex_to_rgb(COLORS["text"]), font=bold)
    draw.text((220, 105), "$4,500.00", fill=hex_to_rgb(COLORS["success"]), font=get_font(20))
    draw.rectangle([220, 140, 760, 141], fill=hex_to_rgb(COLORS["border"]))


def _draw_workload_rows(draw: ImageDraw.Draw, expanded: int = -1) -> None:
    """Draw the workload cost rows, optionally expanding one."""
    small = get_font(11)
    font = get_font(12)
    for i, (name, cost, wtype) in enumerate(WORKLOADS):
        y = 155 + i * 45
        prefix = "▾ " if i == expanded else "▸ "
        if i == expanded:
            draw.rounded_rectangle([215, y - 5, 765, y + 35], radius=4,
                                   fill=hex_to_rgb(COLORS["drag_bg"]))
        draw.text((220, y), prefix + name, fill=hex_to_rgb(COLORS["text"]), font=font)
        draw.text((680, y), cost, fill=hex_to_rgb(COLORS["text"]), font=font)
        draw.text((220, y + 18), wtype, fill=hex_to_rgb(COLORS["text_muted"]), font=small)


def generate_cost_summary_frames() -> tuple[list, list]:
    """Frames: cost summary panel -> expand workload -> hover tooltip."""
    frames, durations = [], []
    small = get_font(11)
    font = get_font(12)

    # Frame 1: Cost summary collapsed
    img, draw = _base_frame("Cost Summary")
    _draw_summary_header(draw)
    _draw_workload_rows(draw)
    draw_step_indicator(draw, 0, 4)
    frames.append(img); durations.append(1200)

    # Frame 2: Cursor on first workload
    img, draw = _base_frame("Cost Summary")
    _draw_summary_header(draw)
    _draw_workload_rows(draw, expanded=0)
    draw_cursor(draw, 300, 165)
    draw_step_indicator(draw, 1, 4)
    frames.append(img); durations.append(800)

    # Frame 3: First workload expanded with details
    img, draw = _base_frame("Cost Summary")
    _draw_summary_header(draw)
    draw.rounded_rectangle([215, 150, 765, 290], radius=4,
                           fill=hex_to_rgb(COLORS["drag_bg"]))
    draw.text((220, 155), "▾ ETL Daily Pipeline", fill=hex_to_rgb(COLORS["text"]), font=font)
    draw.text((680, 155), "$2,340.00", fill=hex_to_rgb(COLORS["text"]), font=font)
    for j, (label, val) in enumerate(DETAILS):
        dy = 180 + j * 22
        draw.text((240, dy), label, fill=hex_to_rgb(COLORS["text_muted"]), font=small)
        draw.text((380, dy), val, fill=hex_to_rgb(COLORS["text"]), font=small)
    for i in range(1, 3):
        y = 300 + (i - 1) * 45
        draw.text((220, y), "▸ " + WORKLOADS[i][0], fill=hex_to_rgb(COLORS["text"]), font=font)
        draw.text((680, y), WORKLOADS[i][1], fill=hex_to_rgb(COLORS["text"]), font=font)
    draw_step_indicator(draw, 2, 4)
    frames.append(img); durations.append(1200)

    # Frame 4: Tooltip on DBU Cost
    img, draw = _base_frame("Cost Summary")
    _draw_summary_header(draw)
    draw.rounded_rectangle([215, 150, 765, 290], radius=4,
                           fill=hex_to_rgb(COLORS["drag_bg"]))
    draw.text((220, 155), "▾ ETL Daily Pipeline", fill=hex_to_rgb(COLORS["text"]), font=font)
    draw.text((680, 155), "$2,340.00", fill=hex_to_rgb(COLORS["text"]), font=font)
    for j, (label, val) in enumerate(DETAILS):
        dy = 180 + j * 22
        draw.text((240, dy), label, fill=hex_to_rgb(COLORS["text_muted"]), font=small)
        draw.text((380, dy), val, fill=hex_to_rgb(COLORS["text"]), font=small)
    draw.rounded_rectangle([410, 170, 700, 210], radius=6,
                           fill=hex_to_rgb("#2c3e50"),
                           outline=hex_to_rgb(COLORS["highlight"]))
    draw.text((420, 178), "DBU cost = rate x workers x hours",
              fill=hex_to_rgb(COLORS["highlight"]), font=small)
    draw.text((420, 193), "0.15 x 4 x 160 x $0.07 = $1,920",
              fill=hex_to_rgb(COLORS["text"]), font=small)
    draw_cursor(draw, 350, 185)
    for i in range(1, 3):
        y = 300 + (i - 1) * 45
        draw.text((220, y), "▸ " + WORKLOADS[i][0], fill=hex_to_rgb(COLORS["text"]), font=font)
        draw.text((680, y), WORKLOADS[i][1], fill=hex_to_rgb(COLORS["text"]), font=font)
    draw_step_indicator(draw, 3, 4)
    frames.append(img); durations.append(1500)

    return frames, durations
