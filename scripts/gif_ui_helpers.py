"""Shared UI drawing helpers for Lakemeter GIF generation (Pillow-based)."""

from PIL import Image, ImageDraw, ImageFont

# Lakemeter color palette
COLORS = {
    "bg": "#1a1a2e",
    "sidebar": "#16213e",
    "card": "#0f3460",
    "accent": "#e94560",
    "accent_hover": "#ff6b81",
    "text": "#eaeaea",
    "text_muted": "#a0a0b0",
    "success": "#2ecc71",
    "border": "#2a2a4a",
    "input_bg": "#0d1b2a",
    "button": "#3498db",
    "button_hover": "#5dade2",
    "white": "#ffffff",
    "highlight": "#f39c12",
    "drag_bg": "#1e3a5f",
}

WIDTH = 800
HEIGHT = 600
FRAME_DURATION = 800  # ms per frame


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def get_font(size: int = 14) -> ImageFont.FreeTypeFont:
    """Get a monospace font, falling back to default."""
    try:
        return ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", size)
    except (OSError, IOError):
        try:
            return ImageFont.truetype(
                "/System/Library/Fonts/SFNSMono.ttf", size
            )
        except (OSError, IOError):
            return ImageFont.load_default()


def new_frame() -> Image.Image:
    """Create a frame with a subtle gradient background."""
    img = Image.new("RGB", (WIDTH, HEIGHT), hex_to_rgb(COLORS["bg"]))
    draw = ImageDraw.Draw(img)
    bg = hex_to_rgb(COLORS["bg"])
    for y in range(0, HEIGHT, 4):
        shift = y * 3 // HEIGHT
        draw.rectangle([0, y, WIDTH, y + 4], fill=(bg[0] + shift, bg[1] + shift, bg[2] + shift + 2))
    return img


def draw_sidebar(draw: ImageDraw.Draw, active: str = "") -> None:
    """Draw the app sidebar with navigation items."""
    draw.rectangle([0, 0, 180, HEIGHT], fill=hex_to_rgb(COLORS["sidebar"]))
    draw.rectangle(
        [180, 0, 181, HEIGHT], fill=hex_to_rgb(COLORS["border"])
    )
    font = get_font(16)
    draw.text((20, 20), "Lakemeter", fill=hex_to_rgb(COLORS["accent"]), font=font)
    small_font = get_font(10)
    draw.text((20, 42), "Cost Estimation Tool", fill=hex_to_rgb(COLORS["text_muted"]), font=small_font)
    draw.rectangle([15, 60, 165, 61], fill=hex_to_rgb(COLORS["border"]))
    nav = get_font(12)
    items = ["Estimates", "Calculator", "AI Assistant", "Export", "Settings"]
    icons = ["📋", "🧮", "🤖", "📥", "⚙️"]
    for i, (item, icon) in enumerate(zip(items, icons)):
        y = 75 + i * 35
        if item == active:
            draw.rounded_rectangle([8, y - 4, 172, y + 24], radius=4,
                                   fill=hex_to_rgb(COLORS["card"]))
            draw.text((25, y), item, fill=hex_to_rgb(COLORS["accent"]), font=nav)
        else:
            draw.text((25, y), item, fill=hex_to_rgb(COLORS["text_muted"]), font=nav)
    # Footer
    tiny = get_font(9)
    draw.rectangle([15, HEIGHT - 45, 165, HEIGHT - 44], fill=hex_to_rgb(COLORS["border"]))
    draw.text((20, HEIGHT - 35), "v2.4.0 • Databricks", fill=hex_to_rgb(COLORS["text_muted"]), font=tiny)


def draw_header(draw: ImageDraw.Draw, title: str) -> None:
    """Draw a page header bar."""
    draw.rectangle([181, 0, WIDTH, 50], fill=hex_to_rgb(COLORS["sidebar"]))
    draw.rectangle(
        [181, 50, WIDTH, 51], fill=hex_to_rgb(COLORS["border"])
    )
    font = get_font(16)
    draw.text((200, 15), title, fill=hex_to_rgb(COLORS["text"]), font=font)


def draw_button(
    draw: ImageDraw.Draw,
    x: int, y: int, w: int, h: int,
    label: str,
    color: str = "button",
    text_color: str = "white",
) -> None:
    """Draw a rounded button."""
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=6,
        fill=hex_to_rgb(COLORS[color]),
    )
    font = get_font(12)
    bbox = font.getbbox(label)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        (x + (w - tw) // 2, y + (h - th) // 2),
        label,
        fill=hex_to_rgb(COLORS[text_color]),
        font=font,
    )


def draw_input_field(
    draw: ImageDraw.Draw,
    x: int, y: int, w: int, h: int,
    label: str, value: str = "",
) -> None:
    """Draw a labeled input field."""
    small = get_font(11)
    draw.text((x, y - 16), label, fill=hex_to_rgb(COLORS["text_muted"]), font=small)
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=4,
        fill=hex_to_rgb(COLORS["input_bg"]),
        outline=hex_to_rgb(COLORS["border"]),
    )
    if value:
        font = get_font(12)
        draw.text((x + 8, y + 6), value, fill=hex_to_rgb(COLORS["text"]), font=font)


def draw_card(
    draw: ImageDraw.Draw,
    x: int, y: int, w: int, h: int,
    title: str = "",
) -> None:
    """Draw a card container with optional title."""
    draw.rounded_rectangle(
        [x, y, x + w, y + h],
        radius=8,
        fill=hex_to_rgb(COLORS["card"]),
        outline=hex_to_rgb(COLORS["border"]),
    )
    if title:
        font = get_font(13)
        draw.text(
            (x + 12, y + 10), title,
            fill=hex_to_rgb(COLORS["text"]), font=font,
        )


def draw_cursor(draw: ImageDraw.Draw, x: int, y: int) -> None:
    """Draw a mouse cursor indicator."""
    points = [(x, y), (x, y + 18), (x + 6, y + 14), (x + 12, y + 18), (x + 14, y + 14), (x + 8, y + 10), (x + 14, y + 8)]
    draw.polygon(points, fill=hex_to_rgb(COLORS["white"]))


def draw_step_indicator(
    draw: ImageDraw.Draw, step: int, total: int
) -> None:
    """Draw step dots at the bottom of the frame."""
    dot_size = 8
    gap = 20
    start_x = WIDTH // 2 - (total * gap) // 2
    y = HEIGHT - 25
    for i in range(total):
        x = start_x + i * gap
        color = COLORS["accent"] if i == step else COLORS["border"]
        draw.ellipse(
            [x, y, x + dot_size, y + dot_size],
            fill=hex_to_rgb(color),
        )


def save_gif(
    frames: list[Image.Image], path: str, durations: list[int] | None = None
) -> None:
    """Save frames as an animated GIF."""
    if durations is None:
        durations = [FRAME_DURATION] * len(frames)
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )
