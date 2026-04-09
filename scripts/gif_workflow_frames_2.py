"""Frame generators for workflow GIFs (Part 2): ai-assistant, export-excel, cost-summary.

Each function returns (frames, durations) for save_gif().
"""

from PIL import Image, ImageDraw
from gif_ui_helpers import (
    COLORS, WIDTH, HEIGHT, FRAME_DURATION,
    hex_to_rgb, get_font, new_frame,
    draw_sidebar, draw_header, draw_button, draw_input_field,
    draw_card, draw_cursor, draw_step_indicator, save_gif,
)


def _base_frame(title: str) -> tuple[Image.Image, ImageDraw.Draw]:
    img = new_frame()
    draw = ImageDraw.Draw(img)
    draw_sidebar(draw)
    draw_header(draw, title)
    return img, draw


def generate_ai_assistant_frames() -> tuple[list, list]:
    """Frames: type question → AI responds with tool call → result shown."""
    frames, durations = [], []
    small = get_font(11)
    font = get_font(12)

    # Frame 1: Empty chat
    img, draw = _base_frame("AI Assistant")
    draw_card(draw, 200, 65, 580, 370)
    draw.text((250, 200), "Ask me anything about your estimate...",
              fill=hex_to_rgb(COLORS["text_muted"]), font=font)
    draw_input_field(draw, 210, 400, 480, 30, "", "")
    draw_button(draw, 700, 400, 70, 30, "Send", "button")
    draw_step_indicator(draw, 0, 5)
    frames.append(img); durations.append(1000)

    # Frame 2: User typing
    img, draw = _base_frame("AI Assistant")
    draw_card(draw, 200, 65, 580, 370)
    draw.text((250, 200), "Ask me anything about your estimate...",
              fill=hex_to_rgb(COLORS["text_muted"]), font=font)
    draw_input_field(draw, 210, 400, 480, 30, "", "Add a DBSQL warehouse, medium size, 8hrs/day")
    draw_button(draw, 700, 400, 70, 30, "Send", "button")
    draw_cursor(draw, 685, 415)
    draw_step_indicator(draw, 1, 5)
    frames.append(img); durations.append(1000)

    # Frame 3: User message sent, AI thinking
    img, draw = _base_frame("AI Assistant")
    draw_card(draw, 200, 65, 580, 370)
    # User bubble
    draw.rounded_rectangle([450, 80, 760, 120], radius=8,
                           fill=hex_to_rgb(COLORS["button"]))
    draw.text((460, 90), "Add a DBSQL warehouse, medium,",
              fill=hex_to_rgb(COLORS["white"]), font=small)
    draw.text((460, 103), "8hrs/day", fill=hex_to_rgb(COLORS["white"]), font=small)
    # AI thinking indicator
    draw.text((220, 140), "Thinking...", fill=hex_to_rgb(COLORS["highlight"]), font=font)
    draw_step_indicator(draw, 2, 5)
    frames.append(img); durations.append(1200)

    # Frame 4: AI tool call shown
    img, draw = _base_frame("AI Assistant")
    draw_card(draw, 200, 65, 580, 370)
    draw.rounded_rectangle([450, 80, 760, 120], radius=8,
                           fill=hex_to_rgb(COLORS["button"]))
    draw.text((460, 90), "Add a DBSQL warehouse, medium,",
              fill=hex_to_rgb(COLORS["white"]), font=small)
    draw.text((460, 103), "8hrs/day", fill=hex_to_rgb(COLORS["white"]), font=small)
    # AI response
    draw.rounded_rectangle([210, 135, 580, 250], radius=8,
                           fill=hex_to_rgb(COLORS["sidebar"]))
    draw.text((220, 145), "I'll add that for you. Creating:",
              fill=hex_to_rgb(COLORS["text"]), font=font)
    draw.text((220, 168), "Tool: add_workload",
              fill=hex_to_rgb(COLORS["highlight"]), font=small)
    draw.text((220, 185), '  type: "DBSQL Warehouse"',
              fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw.text((220, 200), '  size: "Medium"  hours: 160/mo',
              fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw.text((220, 220), 'Est. cost: $1,200/month',
              fill=hex_to_rgb(COLORS["success"]), font=font)
    draw_button(draw, 220, 260, 160, 28, "Apply to Estimate", "accent")
    draw_step_indicator(draw, 3, 5)
    frames.append(img); durations.append(1500)

    # Frame 5: Applied confirmation
    img, draw = _base_frame("AI Assistant")
    draw_card(draw, 200, 65, 580, 370)
    draw.rounded_rectangle([450, 80, 760, 120], radius=8,
                           fill=hex_to_rgb(COLORS["button"]))
    draw.text((460, 90), "Add a DBSQL warehouse, medium,",
              fill=hex_to_rgb(COLORS["white"]), font=small)
    draw.text((460, 103), "8hrs/day", fill=hex_to_rgb(COLORS["white"]), font=small)
    draw.rounded_rectangle([210, 135, 580, 200], radius=8,
                           fill=hex_to_rgb(COLORS["sidebar"]))
    draw.text((220, 145), "Done! DBSQL Warehouse added.",
              fill=hex_to_rgb(COLORS["success"]), font=font)
    draw.text((220, 168), "Your estimate now has 3 workloads",
              fill=hex_to_rgb(COLORS["text"]), font=small)
    draw.text((220, 185), "totaling $4,500/month.",
              fill=hex_to_rgb(COLORS["text"]), font=small)
    draw_step_indicator(draw, 4, 5)
    frames.append(img); durations.append(1500)

    return frames, durations


def generate_export_excel_frames() -> tuple[list, list]:
    """Frames: click Export → download starts → file downloaded."""
    frames, durations = [], []
    small = get_font(11)
    font = get_font(12)

    # Frame 1: Calculator with Export button
    img, draw = _base_frame("Calculator — Demo Corp")
    draw_card(draw, 200, 70, 580, 55, "Demo Corp - AWS Estimate")
    draw.text((215, 100), "3 workloads • $4,500/mo",
              fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw_button(draw, 660, 80, 100, 30, "Export", "button")
    draw_cursor(draw, 710, 95)
    draw_step_indicator(draw, 0, 4)
    frames.append(img); durations.append(1000)

    # Frame 2: Export dropdown
    img, draw = _base_frame("Calculator — Demo Corp")
    draw_card(draw, 200, 70, 580, 55, "Demo Corp - AWS Estimate")
    draw.text((215, 100), "3 workloads • $4,500/mo",
              fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw_button(draw, 660, 80, 100, 30, "Export", "button_hover")
    draw.rounded_rectangle([630, 115, 770, 180], radius=6,
                           fill=hex_to_rgb(COLORS["sidebar"]),
                           outline=hex_to_rgb(COLORS["border"]))
    draw.text((645, 125), "Export to Excel", fill=hex_to_rgb(COLORS["text"]), font=small)
    draw.text((645, 148), "Export to PDF", fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw_cursor(draw, 700, 130)
    draw_step_indicator(draw, 1, 4)
    frames.append(img); durations.append(1000)

    # Frame 3: Downloading indicator
    img, draw = _base_frame("Calculator — Demo Corp")
    draw_card(draw, 200, 70, 580, 55, "Demo Corp - AWS Estimate")
    draw.text((215, 100), "3 workloads • $4,500/mo",
              fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    # Toast notification
    draw.rounded_rectangle([500, 420, 785, 460], radius=8,
                           fill=hex_to_rgb(COLORS["sidebar"]),
                           outline=hex_to_rgb(COLORS["highlight"]))
    draw.text((515, 433), "Generating Excel file...",
              fill=hex_to_rgb(COLORS["highlight"]), font=font)
    draw_step_indicator(draw, 2, 4)
    frames.append(img); durations.append(1000)

    # Frame 4: Download complete toast
    img, draw = _base_frame("Calculator — Demo Corp")
    draw_card(draw, 200, 70, 580, 55, "Demo Corp - AWS Estimate")
    draw.text((215, 100), "3 workloads • $4,500/mo",
              fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw.rounded_rectangle([440, 420, 785, 460], radius=8,
                           fill=hex_to_rgb(COLORS["sidebar"]),
                           outline=hex_to_rgb(COLORS["success"]))
    draw.text((455, 433), "Demo_Corp_AWS_Estimate.xlsx saved",
              fill=hex_to_rgb(COLORS["success"]), font=font)
    draw_step_indicator(draw, 3, 4)
    frames.append(img); durations.append(1500)

    return frames, durations



# generate_cost_summary_frames is in gif_workflow_frames_3.py
