"""Frame generators (Part 1): creating-estimate, adding-workload, drag-and-drop."""
from PIL import Image, ImageDraw
from gif_ui_helpers import (
    COLORS, hex_to_rgb, get_font, new_frame, draw_sidebar, draw_header,
    draw_button, draw_input_field, draw_card, draw_cursor, draw_step_indicator,
)


def _base_frame(title):
    img = new_frame()
    draw = ImageDraw.Draw(img)
    draw_sidebar(draw)
    draw_header(draw, title)
    return img, draw


def generate_creating_estimate_frames() -> tuple[list, list]:
    """Frames: click New Estimate -> fill form -> submit -> land on calculator."""
    frames, durations = [], []
    # Frame 1: Estimates list with New Estimate button
    img, draw = _base_frame("Estimates")
    draw_card(draw, 200, 70, 580, 40, "Demo Corp - AWS Estimate")
    draw_card(draw, 200, 120, 580, 40, "QA Test Account - Eval")
    draw_button(draw, 640, 15, 140, 30, "+ New Estimate", "accent")
    draw_cursor(draw, 710, 30)
    draw_step_indicator(draw, 0, 5)
    frames.append(img); durations.append(1000)

    # Frame 2: Button highlighted
    img, draw = _base_frame("Estimates")
    draw_card(draw, 200, 70, 580, 40, "Demo Corp - AWS Estimate")
    draw_card(draw, 200, 120, 580, 40, "QA Test Account - Eval")
    draw_button(draw, 640, 15, 140, 30, "+ New Estimate", "accent_hover")
    draw_cursor(draw, 710, 30)
    draw_step_indicator(draw, 1, 5)
    frames.append(img); durations.append(600)

    # Frame 3: Form dialog open
    img, draw = _base_frame("New Estimate")
    draw_card(draw, 220, 70, 540, 350)
    font = get_font(14)
    draw.text((240, 85), "Create New Estimate", fill=hex_to_rgb(COLORS["text"]), font=font)
    draw_input_field(draw, 240, 130, 500, 30, "Estimate Name", "Acme Industries - Production")
    draw_input_field(draw, 240, 195, 240, 30, "Cloud", "AWS")
    draw_input_field(draw, 500, 195, 240, 30, "Region", "us-east-1")
    draw_input_field(draw, 240, 260, 240, 30, "Tier", "Premium")
    draw_button(draw, 590, 370, 150, 35, "Create Estimate", "accent")
    draw_step_indicator(draw, 2, 5)
    frames.append(img); durations.append(1200)

    # Frame 4: Cursor on Create button
    img, draw = _base_frame("New Estimate")
    draw_card(draw, 220, 70, 540, 350)
    draw.text((240, 85), "Create New Estimate", fill=hex_to_rgb(COLORS["text"]), font=font)
    draw_input_field(draw, 240, 130, 500, 30, "Estimate Name", "Acme Industries - Production")
    draw_input_field(draw, 240, 195, 240, 30, "Cloud", "AWS")
    draw_input_field(draw, 500, 195, 240, 30, "Region", "us-east-1")
    draw_input_field(draw, 240, 260, 240, 30, "Tier", "Premium")
    draw_button(draw, 590, 370, 150, 35, "Create Estimate", "accent_hover")
    draw_cursor(draw, 665, 388)
    draw_step_indicator(draw, 3, 5)
    frames.append(img); durations.append(800)

    # Frame 5: Calculator page
    img, draw = _base_frame("Calculator — Acme Industries")
    draw_card(draw, 200, 70, 580, 60, "Acme Industries - Production")
    small = get_font(11)
    draw.text((215, 100), "AWS • us-east-1 • Premium", fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw_button(draw, 200, 150, 130, 30, "+ Add Workload", "button")
    draw.text((215, 200), "No workloads yet. Click Add Workload to get started.", fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw_step_indicator(draw, 4, 5)
    frames.append(img); durations.append(1500)

    return frames, durations


def generate_adding_workload_frames() -> tuple[list, list]:
    """Frames: click Add Workload → select type → configure → save."""
    frames, durations = [], []

    # Frame 1: Calculator with Add Workload button
    img, draw = _base_frame("Calculator — Demo Corp")
    draw_button(draw, 200, 70, 130, 30, "+ Add Workload", "button")
    draw_cursor(draw, 265, 85)
    draw_step_indicator(draw, 0, 5)
    frames.append(img); durations.append(1000)

    # Frame 2: Workload type selector
    img, draw = _base_frame("Select Workload Type")
    types = ["Jobs Compute", "DBSQL Warehouse", "DLT Pipeline", "Model Serving", "Vector Search", "FMAPI"]
    for i, wtype in enumerate(types):
        row, col = divmod(i, 3)
        x, y = 210 + col * 190, 80 + row * 100
        draw_card(draw, x, y, 175, 80, wtype)
    draw_cursor(draw, 300, 120)
    draw_step_indicator(draw, 1, 5)
    frames.append(img); durations.append(1000)

    # Frame 3: Jobs Compute selected — config form
    img, draw = _base_frame("Configure: Jobs Compute")
    draw_card(draw, 200, 65, 580, 370)
    draw_input_field(draw, 220, 100, 250, 28, "Workload Name", "ETL Daily Pipeline")
    draw_input_field(draw, 490, 100, 270, 28, "Compute Type", "Classic")
    draw_input_field(draw, 220, 165, 250, 28, "Instance Type", "i3.xlarge")
    draw_input_field(draw, 490, 165, 130, 28, "Workers", "4")
    draw_input_field(draw, 640, 165, 120, 28, "Hours/Month", "160")
    draw_step_indicator(draw, 2, 5)
    frames.append(img); durations.append(1200)

    # Frame 4: Cursor on Save
    img, draw = _base_frame("Configure: Jobs Compute")
    draw_card(draw, 200, 65, 580, 370)
    draw_input_field(draw, 220, 100, 250, 28, "Workload Name", "ETL Daily Pipeline")
    draw_input_field(draw, 490, 100, 270, 28, "Compute Type", "Classic")
    draw_input_field(draw, 220, 165, 250, 28, "Instance Type", "i3.xlarge")
    draw_input_field(draw, 490, 165, 130, 28, "Workers", "4")
    draw_input_field(draw, 640, 165, 120, 28, "Hours/Month", "160")
    draw_button(draw, 620, 390, 140, 32, "Save Workload", "accent_hover")
    draw_cursor(draw, 690, 406)
    draw_step_indicator(draw, 3, 5)
    frames.append(img); durations.append(800)

    # Frame 5: Workload added to list
    img, draw = _base_frame("Calculator — Demo Corp")
    draw_card(draw, 200, 70, 580, 60, "ETL Daily Pipeline")
    small = get_font(11)
    draw.text((215, 100), "Jobs Compute • Classic • 4x i3.xlarge • $2,340/mo", fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw_button(draw, 200, 150, 130, 30, "+ Add Workload", "button")
    font = get_font(12)
    draw.text((215, 200), "Total: $2,340.00 / month", fill=hex_to_rgb(COLORS["success"]), font=font)
    draw_step_indicator(draw, 4, 5)
    frames.append(img); durations.append(1500)

    return frames, durations


def generate_drag_and_drop_frames() -> tuple[list, list]:
    """Frames: grab workload -> drag to new position -> drop."""
    frames, durations = [], []
    small, font13 = get_font(11), get_font(13)
    wl = [("ETL Daily Pipeline", "Jobs • $2,340/mo"), ("Analytics Warehouse", "DBSQL • $1,800/mo"),
          ("ML Serving Endpoint", "Model Serving • $960/mo")]
    muted, txt = hex_to_rgb(COLORS["text_muted"]), hex_to_rgb(COLORS["text"])

    # Frame 1: Initial order
    img, draw = _base_frame("Calculator — Demo Corp")
    for i, (name, desc) in enumerate(wl):
        y = 75 + i * 65
        draw_card(draw, 200, y, 580, 55, name)
        draw.text((215, y + 30), desc, fill=muted, font=small)
        draw.text((205, y + 15), "⋮⋮", fill=muted, font=get_font(14))
    draw_step_indicator(draw, 0, 4)
    frames.append(img); durations.append(1000)

    # Frame 2: Grabbed ML Serving (highlighted)
    img, draw = _base_frame("Calculator — Demo Corp")
    for i, (name, desc) in enumerate(wl):
        y = 75 + i * 65
        if i == 2:
            draw.rounded_rectangle([198, y - 2, 782, y + 57], radius=8,
                                   fill=hex_to_rgb(COLORS["drag_bg"]),
                                   outline=hex_to_rgb(COLORS["accent"]), width=2)
        else:
            draw_card(draw, 200, y, 580, 55, name)
        draw.text((215, y + 10), name, fill=txt, font=font13)
        draw.text((215, y + 30), desc, fill=muted, font=small)
    draw_cursor(draw, 210, 215)
    draw_step_indicator(draw, 1, 4)
    frames.append(img); durations.append(800)

    # Frame 3: Dragging up
    img, draw = _base_frame("Calculator — Demo Corp")
    draw_card(draw, 200, 75, 580, 55, wl[0][0])
    draw.text((215, 105), wl[0][1], fill=muted, font=small)
    draw.rectangle([200, 138, 780, 140], fill=hex_to_rgb(COLORS["accent"]))
    draw_card(draw, 200, 145, 580, 55, wl[1][0])
    draw.text((215, 175), wl[1][1], fill=muted, font=small)
    draw.rounded_rectangle([210, 115, 770, 165], radius=8,
                           fill=hex_to_rgb(COLORS["drag_bg"]),
                           outline=hex_to_rgb(COLORS["accent"]), width=2)
    draw.text((225, 125), wl[2][0], fill=txt, font=font13)
    draw.text((225, 143), wl[2][1], fill=muted, font=small)
    draw_cursor(draw, 220, 140)
    draw_step_indicator(draw, 2, 4)
    frames.append(img); durations.append(800)

    # Frame 4: Dropped — new order
    reordered = [wl[0], wl[2], wl[1]]
    img, draw = _base_frame("Calculator — Demo Corp")
    for i, (name, desc) in enumerate(reordered):
        y = 75 + i * 65
        draw_card(draw, 200, y, 580, 55, name)
        if i == 1:
            draw.rounded_rectangle([198, y - 2, 782, y + 57], radius=8,
                                   outline=hex_to_rgb(COLORS["success"]), width=2)
        draw.text((215, y + 30), desc, fill=muted, font=small)
    draw_step_indicator(draw, 3, 4)
    frames.append(img); durations.append(1500)

    return frames, durations
