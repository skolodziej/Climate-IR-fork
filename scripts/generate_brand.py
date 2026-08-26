#!/usr/bin/env python3
"""Generate the brand assets.

The mark is an emitter with three expanding arcs -- the usual reading for a
transmitted signal -- paired with the wordmark. Keeping the generator in the
repository means the assets can be regenerated instead of being opaque
binaries nobody can edit.

Usage: python3 scripts/generate_brand.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).resolve().parents[1] / "custom_components" / "climate_ir" / "brand"

LIGHT = {"mark": (13, 148, 136, 255), "accent": (45, 212, 191, 255),
         "text": (17, 24, 39, 255)}
DARK = {"mark": (94, 234, 212, 255), "accent": (45, 212, 191, 255),
        "text": (243, 244, 246, 255)}

FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNS.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def _font(size: int):
    """Return the first usable system font, or the bitmap fallback."""

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            try:
                return ImageFont.truetype(candidate, size)
            except OSError:
                continue

    return ImageFont.load_default()


def draw_mark(draw: ImageDraw.ImageDraw, box: tuple, palette: dict) -> None:
    """Draw the emitter and its three arcs inside a square box."""

    left, top, size = box
    unit = size / 100

    # The emitter sits low and left; the arcs open up and to the right.
    origin_x = left + 26 * unit
    origin_y = top + 74 * unit
    radius = 9 * unit
    draw.ellipse(
        [origin_x - radius, origin_y - radius, origin_x + radius, origin_y + radius],
        fill=palette["mark"],
    )

    width = max(1, int(7 * unit))
    for index, distance in enumerate((30, 52, 74)):
        span = distance * unit
        colour = palette["mark"] if index < 2 else palette["accent"]
        draw.arc(
            [origin_x - span, origin_y - span, origin_x + span, origin_y + span],
            start=270,
            end=360,
            fill=colour,
            width=width,
        )


def render_icon(path: Path, size: int, palette: dict) -> None:
    """Render the square icon."""

    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw_mark(draw, (size * 0.06, size * 0.06, size * 0.88), palette)
    image.save(path)


def render_logo(path: Path, width: int, height: int, palette: dict) -> None:
    """Render the wide logo: mark plus wordmark."""

    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    mark_size = height * 0.82
    draw_mark(draw, (height * 0.09, height * 0.09, mark_size), palette)

    font = _font(int(height * 0.42))
    text_x = height * 1.08
    draw.text((text_x, height * 0.5), "Climate", font=font, fill=palette["text"],
              anchor="lm")
    offset = draw.textlength("Climate ", font=font)
    draw.text((text_x + offset, height * 0.5), "IR", font=font,
              fill=palette["mark"], anchor="lm")

    image.save(path)


def main() -> None:
    """Write every asset."""

    OUTPUT.mkdir(parents=True, exist_ok=True)
    for prefix, palette in (("", LIGHT), ("dark_", DARK)):
        render_icon(OUTPUT / f"{prefix}icon.png", 256, palette)
        render_icon(OUTPUT / f"{prefix}icon@2x.png", 512, palette)
        render_logo(OUTPUT / f"{prefix}logo.png", 640, 160, palette)
        render_logo(OUTPUT / f"{prefix}logo@2x.png", 1280, 320, palette)

    print(f"wrote 8 assets to {OUTPUT}")


if __name__ == "__main__":
    main()
