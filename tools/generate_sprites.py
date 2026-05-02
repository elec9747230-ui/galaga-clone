"""Generate placeholder pixel-art PNG sprites with Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw

import settings

OUT_DIR = Path(settings.ASSETS_SPRITES_DIR)


def _make_image(size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _save(img: Image.Image, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(OUT_DIR / f"{name}.png")


def generate_player() -> None:
    img, d = _make_image((32, 24))
    white = (255, 255, 255, 255)
    red = (220, 40, 40, 255)
    blue = (60, 120, 240, 255)
    # ship body (triangle-ish)
    d.rectangle((14, 4, 17, 20), fill=white)
    d.rectangle((10, 8, 21, 20), fill=white)
    d.rectangle((6, 12, 25, 20), fill=white)
    d.rectangle((2, 18, 29, 22), fill=white)
    # red trim
    d.rectangle((13, 16, 18, 19), fill=red)
    # blue cockpit
    d.rectangle((15, 6, 16, 8), fill=blue)
    _save(img, "player")


def generate_bee() -> None:
    img, d = _make_image((28, 22))
    yellow = (240, 220, 60, 255)
    blue = (60, 120, 240, 255)
    d.rectangle((10, 4, 17, 18), fill=yellow)  # body
    d.rectangle((4, 6, 9, 14), fill=blue)  # left wing
    d.rectangle((18, 6, 23, 14), fill=blue)  # right wing
    d.rectangle((12, 0, 15, 3), fill=yellow)  # antenna stub
    _save(img, "enemy_bee")


def generate_butterfly() -> None:
    img, d = _make_image((28, 22))
    red = (220, 40, 40, 255)
    blue = (60, 120, 240, 255)
    yellow = (240, 220, 60, 255)
    d.rectangle((10, 4, 17, 18), fill=red)
    d.rectangle((2, 4, 9, 16), fill=blue)
    d.rectangle((18, 4, 25, 16), fill=blue)
    d.rectangle((4, 6, 7, 9), fill=yellow)
    d.rectangle((20, 6, 23, 9), fill=yellow)
    _save(img, "enemy_butterfly")


def generate_boss() -> None:
    img, d = _make_image((32, 26))
    green = (80, 220, 80, 255)
    cyan = (80, 220, 220, 255)
    d.rectangle((10, 4, 21, 20), fill=green)
    d.rectangle((4, 8, 9, 18), fill=cyan)
    d.rectangle((22, 8, 27, 18), fill=cyan)
    d.rectangle((12, 0, 19, 3), fill=green)
    d.rectangle((14, 8, 17, 11), fill=(0, 0, 0, 255))  # eye
    _save(img, "enemy_boss")


def generate_player_bullet() -> None:
    img, d = _make_image((4, 12))
    d.rectangle((1, 0, 2, 11), fill=(255, 255, 255, 255))
    _save(img, "player_bullet")


def generate_enemy_bullet() -> None:
    img, d = _make_image((4, 12))
    d.rectangle((1, 0, 2, 11), fill=(220, 80, 220, 255))
    _save(img, "enemy_bullet")


def generate_explosion_frames() -> None:
    """4-frame expanding explosion."""
    palette = [
        (255, 240, 80, 255),
        (255, 160, 40, 255),
        (220, 60, 40, 255),
        (120, 30, 30, 255),
    ]
    for i in range(4):
        img, d = _make_image((24, 24))
        radius = 4 + i * 4
        c = palette[i]
        # crude pixel circle
        cx, cy = 12, 12
        for y in range(24):
            for x in range(24):
                if (x - cx) ** 2 + (y - cy) ** 2 < radius * radius:
                    img.putpixel((x, y), c)
        _save(img, f"explosion_{i}")


def generate_logo() -> None:
    """Simple text-style 'GALAGA' logo placeholder."""
    img, d = _make_image((220, 60))
    yellow = (240, 220, 60, 255)
    # 6 letter blocks; very rough "GALAGA" without true font shapes
    d.rectangle((4, 12, 200, 48), outline=yellow, width=3)
    d.text((48, 22), "GALAGA", fill=yellow)
    _save(img, "logo")


def main() -> None:
    generate_player()
    generate_bee()
    generate_butterfly()
    generate_boss()
    generate_player_bullet()
    generate_enemy_bullet()
    generate_explosion_frames()
    generate_logo()
    print(f"Sprites written to {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
