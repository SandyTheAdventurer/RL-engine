#!/usr/bin/env python3
"""Generate ASCII-art placeholder sprite sheets for RL-engine.

Writes every PNG the engine's asset loader (src/Engine.cpp) expects:
  assets/Base_Character/base_<suffix>.png
  assets/Weapons/<weapon>_<suffix>.png
  assets/Armor/<Tier>/<Tier>_<slot>_<suffix>.png
  assets/Projectiles/bullet_projectile.png

Sheet geometry (24 cols x 8 rows of 128x128 tiles) mirrors
src/Structures.h (Spritesheet::TILE_SIZE/COLS/ROWS) and
src/Constants.h (sprite_frame_count, sprite_direction_count, dirIndex).
Direction row order matches the dirIndex map in Constants.h exactly.

Usage:
    python3 tools/generate_placeholder_textures.py
    python3 tools/generate_placeholder_textures.py --only weapons
    python3 tools/generate_placeholder_textures.py --only icons
    python3 tools/generate_placeholder_textures.py --no-labels
    python3 tools/generate_placeholder_textures.py --jobs 1   # disable multiprocessing
"""

import argparse
import math
import os
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

# --- Geometry (must match src/Structures.h + src/Constants.h) -------------

TILE = 128
COLS = 24  # sprite_frame_count
ROWS = 8   # sprite_direction_count
SHEET_W = TILE * COLS
SHEET_H = TILE * ROWS

# Row order == dirIndex in src/Constants.h:131-139 (dx, dy, label)
DIRECTIONS = [
    (1, -1, "NE"),
    (0, -1, "N"),
    (-1, -1, "NW"),
    (-1, 0, "W"),
    (-1, 1, "SW"),
    (0, 1, "S"),
    (1, 1, "SE"),
    (1, 0, "E"),
]
DIRECTION_ANGLES = [math.degrees(math.atan2(dy, dx)) for dx, dy, _ in DIRECTIONS]

ANIMATION_SUFFIXES = [
    "idle", "walk", "run", "cast_shoot",
    "melee_1", "melee_2", "melee_spin", "hurt",
]

WEAPON_NAMES = ["katana", "short_sword", "daggers", "great_sword", "shield", "staff"]
ARMOR_TIERS = ["Cloth", "LightLeather", "MediumChain", "HeavyPlate", "UltraHeavy"]
ARMOR_SLOTS = ["head", "chest", "legs"]

BASE_DIR = "assets/Base_Character"
WEAPON_DIR = "assets/Weapons"
ARMOR_DIR = "assets/Armor"
ICON_DIR = "assets/Icons"
PROJECTILE_PATH = "assets/Projectiles/bullet_projectile.png"
ICON_SIZE = 128

# --- Palette ----------------------------------------------------------------

BASE_SKIN = (222, 196, 160, 255)
BASE_OUTLINE = (60, 45, 30, 255)
HURT_TINT = (220, 30, 30)

WEAPON_SPECS = {
    "katana":      {"text": "==={>",  "color": (215, 230, 255, 255), "reach": 48},
    "short_sword": {"text": "--{>",   "color": (200, 200, 215, 255), "reach": 34},
    "daggers":     {"text": ">-<",    "color": (175, 175, 185, 255), "reach": 24},
    "great_sword": {"text": "[==={>", "color": (185, 195, 210, 255), "reach": 58},
    "shield":      {"text": "[#]",    "color": (205, 150, 80, 255),  "reach": 18},
    "staff":       {"text": "|-*",    "color": (175, 120, 225, 255), "reach": 42},
}

ARMOR_SPECS = {
    "Cloth":        {"char": ".", "color": (222, 184, 135, 255)},
    "LightLeather": {"char": ":", "color": (139, 90, 43, 255)},
    "MediumChain":  {"char": "+", "color": (176, 180, 190, 255)},
    "HeavyPlate":   {"char": "#", "color": (86, 120, 160, 255)},
    "UltraHeavy":   {"char": "@", "color": (70, 20, 20, 255)},
}

# --- Fonts --------------------------------------------------------------

def _find_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


MONO_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    "/System/Library/Fonts/Menlo.ttc",
    "/System/Library/Fonts/Supplemental/Andale Mono.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
]

_FONT_CACHE = {}


def font(size):
    if size not in _FONT_CACHE:
        _FONT_CACHE[size] = _find_font(MONO_CANDIDATES, size)
    return _FONT_CACHE[size]


# --- Glyph atoms: rendered once, ASCII text on transparent RGBA ------------

def render_ascii(text, size, color, spacing=2):
    f = font(size)
    dummy = Image.new("RGBA", (4, 4))
    d = ImageDraw.Draw(dummy)
    bbox = d.multiline_textbbox((0, 0), text, font=f, spacing=spacing, align="center")
    w = max(1, int(bbox[2] - bbox[0]))
    h = max(1, int(bbox[3] - bbox[1]))
    img = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.multiline_text((2 - bbox[0], 2 - bbox[1]), text, font=f, fill=color,
                      spacing=spacing, align="center")
    return img


def vertical_bar(char, color, length_px, thickness_size=16):
    rows = max(2, length_px // (thickness_size - 4))
    return render_ascii("\n".join([char] * rows), thickness_size, color, spacing=0)


@lru_cache(maxsize=None)
def head_glyph():
    return render_ascii("@", 26, BASE_SKIN)


@lru_cache(maxsize=None)
def torso_glyph():
    return render_ascii("/#\\\n|#|\n\\#/", 13, BASE_SKIN, spacing=0)


@lru_cache(maxsize=None)
def limb_glyph(char, length):
    return vertical_bar(char, BASE_SKIN, length)


@lru_cache(maxsize=None)
def weapon_glyph(weapon, scale=1.0):
    spec = WEAPON_SPECS[weapon]
    return render_ascii(spec["text"], round(18 * scale), spec["color"])


@lru_cache(maxsize=None)
def armor_glyph(tier, slot, scale=1.0):
    spec = ARMOR_SPECS[tier]
    ch = spec["char"]
    if slot == "head":
        text = f"[{ch}]"
        size = 14
    elif slot == "chest":
        text = f"[{ch}{ch}]\n[{ch}{ch}]"
        size = 12
    else:  # legs
        text = f"{ch}   {ch}\n{ch}   {ch}\n{ch}   {ch}"
        size = 12
    return render_ascii(text, round(size * scale), spec["color"], spacing=max(1, round(scale)))


# --- Rotation about an arbitrary pivot ------------------------------------

_ROTATE_CACHE = {}


def rotate_about_pivot(img_key, img, pivot, angle_deg, canvas_size):
    key = (img_key, round(angle_deg), canvas_size)
    cached = _ROTATE_CACHE.get(key)
    if cached is not None:
        return cached
    cx = cy = canvas_size / 2
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    canvas.alpha_composite(img, (int(cx - pivot[0]), int(cy - pivot[1])))
    rotated = canvas.rotate(-angle_deg, resample=Image.BICUBIC, center=(cx, cy))
    _ROTATE_CACHE[key] = rotated
    return rotated


def paste_at_pivot(tile, rotated_canvas, target_xy):
    c = rotated_canvas.size[0] / 2
    tile.alpha_composite(rotated_canvas, (int(target_xy[0] - c), int(target_xy[1] - c)))


def apply_tint(img, color, strength):
    if strength <= 0:
        return img
    strength = min(1.0, strength)
    r, g, b, a = img.split()
    tint_alpha = a.point(lambda v: int(v * strength))
    tint_layer = Image.merge(
        "RGBA",
        (Image.new("L", img.size, color[0]),
         Image.new("L", img.size, color[1]),
         Image.new("L", img.size, color[2]),
         tint_alpha),
    )
    return Image.alpha_composite(img, tint_layer)


# --- Pose model -------------------------------------------------------------
# frame in [0, COLS); returns dict of pose parameters for that animation/frame.

def pose_for(anim, frame):
    loop_phase = (frame / COLS) * 2 * math.pi
    progress = frame / (COLS - 1)

    gait_amp = {"idle": 3, "walk": 16, "run": 28}.get(anim, 0)
    bob_amp = {"idle": 1.5, "walk": 3, "run": 5}.get(anim, 0)
    weapon_sway = {"idle": 6, "walk": 15, "run": 24}.get(anim, 0)

    leg_swing = 0.0
    bob = 0.0
    weapon_offset = 0.0
    recoil = 0.0
    flash = 0.0
    glow = 0.0

    if anim in ("idle", "walk", "run"):
        leg_swing = math.sin(loop_phase) * gait_amp
        bob = abs(math.sin(loop_phase)) * bob_amp
        weapon_offset = math.sin(loop_phase) * weapon_sway
    elif anim == "cast_shoot":
        raise_amt = min(progress * 3.0, 1.0)
        weapon_offset = -35 * (1 - raise_amt)
        glow = max(0.0, progress - 0.35) / 0.65
    elif anim == "melee_1":
        weapon_offset = -70 + 140 * progress
    elif anim == "melee_2":
        weapon_offset = 70 - 140 * progress
    elif anim == "melee_spin":
        weapon_offset = progress * 360
    elif anim == "hurt":
        recoil = math.sin(min(progress * 2.2, 1.0) * math.pi) * 9
        flash = max(0.0, 1.0 - progress * 1.6)
        weapon_offset = 18

    return {
        "leg_swing": leg_swing,
        "bob": bob,
        "weapon_offset": weapon_offset,
        "recoil": recoil,
        "flash": flash,
        "glow": glow,
    }


# --- Tile composition -------------------------------------------------------

CENTER_X = 64
HEAD_Y = 32
TORSO_Y = 62
HIP_Y = 88
SHOULDER_Y = 54
LEG_LEN = 32
ARM_LEN = 24


def draw_label(tile, lines, corner_tag=None):
    f = font(11)
    text = "\n".join(lines)
    d = ImageDraw.Draw(tile)
    bbox = d.multiline_textbbox((0, 0), text, font=f, align="center", spacing=1)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (tile.width - w) / 2 - bbox[0]
    y = tile.height - h - 6 - bbox[1]
    d.rectangle([2, tile.height - h - 12, tile.width - 2, tile.height - 2], fill=(0, 0, 0, 150))
    d.multiline_text((x, y), text, font=f, fill=(255, 255, 255, 255), align="center", spacing=1)

    if corner_tag:
        tf = font(8)
        d.text((3, 2), corner_tag, font=tf, fill=(255, 255, 0, 220))


def compose_character(tile, angle_deg, pose, tint_strength):
    dx = math.cos(math.radians(angle_deg))
    dy = math.sin(math.radians(angle_deg))
    bob = -pose["bob"]
    recoil_x = -dx * pose["recoil"]
    recoil_y = -dy * pose["recoil"]

    cx = CENTER_X + recoil_x
    swing = pose["leg_swing"]

    for side, sign in (("L", -1), ("R", 1)):
        leg_img = limb_glyph("|", LEG_LEN)
        leg_img = apply_tint(leg_img, HURT_TINT, tint_strength)
        pivot = (leg_img.width / 2, 2)
        canvas_size = max(leg_img.size) + 8
        rotated = rotate_about_pivot(("leg", side, LEG_LEN, tint_strength > 0), leg_img,
                                      pivot, sign * swing * 0.6, canvas_size)
        paste_at_pivot(tile, rotated, (cx + sign * 9, HIP_Y + bob))

    torso = apply_tint(torso_glyph(), HURT_TINT, tint_strength)
    tile.alpha_composite(torso, (int(cx - torso.width / 2), int(TORSO_Y + bob - torso.height / 2)))

    off_arm = limb_glyph("\\", ARM_LEN)
    off_arm = apply_tint(off_arm, HURT_TINT, tint_strength)
    pivot = (off_arm.width / 2, 2)
    canvas_size = max(off_arm.size) + 8
    rotated = rotate_about_pivot(("arm", ARM_LEN, tint_strength > 0), off_arm, pivot,
                                  -swing * 0.5, canvas_size)
    paste_at_pivot(tile, rotated, (cx - 12, SHOULDER_Y + bob))

    head = apply_tint(head_glyph(), HURT_TINT, tint_strength)
    tile.alpha_composite(head, (int(cx - head.width / 2), int(HEAD_Y + bob - head.height / 2)))

    return cx, SHOULDER_Y + bob, dx, dy


def compose_weapon(tile, weapon, angle_deg, pose, weapon_pivot):
    spec = WEAPON_SPECS[weapon]
    glyph = weapon_glyph(weapon)
    total_angle = angle_deg + pose["weapon_offset"]
    pivot = (4, glyph.height / 2)
    canvas_size = max(glyph.size) * 2 + 16
    rotated = rotate_about_pivot((weapon, "w"), glyph, pivot, total_angle, canvas_size)
    paste_at_pivot(tile, rotated, weapon_pivot)

    if pose.get("glow", 0) > 0 and weapon in ("staff", "shield"):
        dx = math.cos(math.radians(total_angle))
        dy = math.sin(math.radians(total_angle))
        reach = spec["reach"]
        tip = (weapon_pivot[0] + dx * reach, weapon_pivot[1] + dy * reach)
        glow_r = 3 + pose["glow"] * 5
        d = ImageDraw.Draw(tile)
        alpha = int(180 * pose["glow"])
        d.ellipse([tip[0] - glow_r, tip[1] - glow_r, tip[0] + glow_r, tip[1] + glow_r],
                  fill=(255, 240, 160, alpha))


def compose_armor_piece(tile, tier, slot, cx, shoulder_y, bob, tint_strength):
    glyph = apply_tint(armor_glyph(tier, slot), HURT_TINT, tint_strength)
    if slot == "head":
        y = HEAD_Y + bob
    elif slot == "chest":
        y = TORSO_Y + bob
    else:
        y = HIP_Y + bob + 6
    tile.alpha_composite(glyph, (int(cx - glyph.width / 2), int(y - glyph.height / 2)))


def new_tile():
    return Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))


def build_base_tile(anim, frame, direction_idx, show_labels=True):
    angle = DIRECTION_ANGLES[direction_idx]
    pose = pose_for(anim, frame)
    tile = new_tile()
    compose_character(tile, angle, pose, pose.get("flash", 0))
    if show_labels:
        draw_label(tile, ["BASE", anim.upper()], DIRECTIONS[direction_idx][2])
    return tile


def build_weapon_tile(weapon, anim, frame, direction_idx, show_labels=True):
    angle = DIRECTION_ANGLES[direction_idx]
    pose = pose_for(anim, frame)
    tile = new_tile()
    cx, shoulder_y, dx, dy = compose_character(tile, angle, pose, pose.get("flash", 0))
    weapon_pivot = (cx + dx * 14, shoulder_y + dy * 6 + 4)
    compose_weapon(tile, weapon, angle, pose, weapon_pivot)
    if show_labels:
        label = weapon.replace("_", " ").upper()
        draw_label(tile, [label, anim.upper()], DIRECTIONS[direction_idx][2])
    return tile


def build_armor_tile(tier, slot, anim, frame, direction_idx, show_labels=True):
    angle = DIRECTION_ANGLES[direction_idx]
    pose = pose_for(anim, frame)
    tile = new_tile()
    cx, shoulder_y, dx, dy = compose_character(tile, angle, pose, 0.0)
    compose_armor_piece(tile, tier, slot, cx, shoulder_y, pose.get("bob", 0) * -1, pose.get("flash", 0))
    if show_labels:
        draw_label(tile, [tier[:10], slot.upper()], DIRECTIONS[direction_idx][2])
    return tile


def build_weapon_icon(weapon, show_labels=True):
    spec = WEAPON_SPECS[weapon]
    icon = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    d.rectangle([3, 3, ICON_SIZE - 4, ICON_SIZE - 4], outline=spec["color"], width=3)
    glyph = weapon_glyph(weapon, scale=1.8)
    y_shift = 10 if show_labels else 0
    icon.alpha_composite(glyph, ((ICON_SIZE - glyph.width) // 2, (ICON_SIZE - glyph.height) // 2 - y_shift))
    if show_labels:
        draw_label(icon, [weapon.replace("_", " ").upper()])
    return icon


def build_armor_icon(tier, slot, show_labels=True):
    spec = ARMOR_SPECS[tier]
    icon = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    d.rectangle([3, 3, ICON_SIZE - 4, ICON_SIZE - 4], outline=spec["color"], width=3)
    glyph = armor_glyph(tier, slot, scale=2.2)
    y_shift = 10 if show_labels else 0
    icon.alpha_composite(glyph, ((ICON_SIZE - glyph.width) // 2, (ICON_SIZE - glyph.height) // 2 - y_shift))
    if show_labels:
        draw_label(icon, [tier, slot.upper()])
    return icon


def build_sheet(tile_fn, anim, out_path):
    sheet = Image.new("RGBA", (SHEET_W, SHEET_H), (0, 0, 0, 0))
    for row in range(ROWS):
        for col in range(COLS):
            tile = tile_fn(anim, col, row)
            sheet.alpha_composite(tile, (col * TILE, row * TILE))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path)
    return out_path


def build_projectile():
    size = 32
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glyph = render_ascii("*=>", 14, (255, 210, 90, 255))
    img.alpha_composite(glyph, ((size - glyph.width) // 2, (size - glyph.height) // 2))
    os.makedirs(os.path.dirname(PROJECTILE_PATH), exist_ok=True)
    img.save(PROJECTILE_PATH)
    return PROJECTILE_PATH


# --- Job list / dispatch ---------------------------------------------------

def build_icon(img, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path)
    return out_path


def run_job(job):
    kind = job[0]
    if kind == "base":
        _, anim, show_labels = job
        return build_sheet(lambda a, c, r: build_base_tile(a, c, r, show_labels), anim,
                            f"{BASE_DIR}/base_{anim}.png")
    if kind == "weapon":
        _, weapon, anim, show_labels = job
        return build_sheet(lambda a, c, r: build_weapon_tile(weapon, a, c, r, show_labels), anim,
                            f"{WEAPON_DIR}/{weapon}_{anim}.png")
    if kind == "armor":
        _, tier, slot, anim, show_labels = job
        return build_sheet(lambda a, c, r: build_armor_tile(tier, slot, a, c, r, show_labels), anim,
                            f"{ARMOR_DIR}/{tier}/{tier}_{slot}_{anim}.png")
    if kind == "projectile":
        return build_projectile()
    if kind == "icon_weapon":
        _, weapon, show_labels = job
        return build_icon(build_weapon_icon(weapon, show_labels), f"{ICON_DIR}/Weapons/{weapon}.png")
    if kind == "icon_armor":
        _, tier, slot, show_labels = job
        return build_icon(build_armor_icon(tier, slot, show_labels), f"{ICON_DIR}/Armor/{tier}/{tier}_{slot}.png")
    raise ValueError(job)


def collect_jobs(only, show_labels=True):
    jobs = []
    if only in (None, "base"):
        jobs += [("base", a, show_labels) for a in ANIMATION_SUFFIXES]
    if only in (None, "weapons"):
        jobs += [("weapon", w, a, show_labels) for w in WEAPON_NAMES for a in ANIMATION_SUFFIXES]
    if only in (None, "armor"):
        jobs += [("armor", t, s, a, show_labels) for t in ARMOR_TIERS for s in ARMOR_SLOTS for a in ANIMATION_SUFFIXES]
    if only in (None, "projectile"):
        jobs += [("projectile",)]
    if only in (None, "icons"):
        jobs += [("icon_weapon", w, show_labels) for w in WEAPON_NAMES]
        jobs += [("icon_armor", t, s, show_labels) for t in ARMOR_TIERS for s in ARMOR_SLOTS]
    return jobs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=["base", "weapons", "armor", "projectile", "icons"], default=None)
    parser.add_argument("--no-labels", action="store_true",
                         help="omit the item/animation name text baked into each texture")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 1,
                         help="parallel worker processes (default: cpu count)")
    args = parser.parse_args()

    jobs = collect_jobs(args.only, show_labels=not args.no_labels)
    total = len(jobs)
    print(f"Generating {total} sheet(s)...")

    if args.jobs <= 1:
        for i, job in enumerate(jobs, 1):
            path = run_job(job)
            print(f"[{i}/{total}] {path}")
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as ex:
            for i, path in enumerate(ex.map(run_job, jobs), 1):
                print(f"[{i}/{total}] {path}")

    print("Done.")


if __name__ == "__main__":
    main()
