#!/usr/bin/env python3
"""Convert dungeonSprites v1.5 compiled spritesheets into the engine's format.

Source format (v1.5 compiled):
  - Character sheets like mHero_.png: 192x144 (8 cols x 6 rows, 24x24 tiles)
    - Rows: 0=idle, 1=walkRun, 2=jump, 3=turn, 4=hurt, 5=death
    - Cols 0-3: left-facing frames, Cols 4-7: right-facing frames
  - weapons_.png: 60x120 (4 cols x 8 rows, 15x15 tiles)

Engine format:
  - Per-animation spritesheets at assets/<anim>/<anim>.png
  - 8 direction rows x N columns, 128x128 tiles
  - Direction rows match dirIndex in Constants.h
"""

import os
import sys
from PIL import Image

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
SRC_DIR = os.path.join(os.path.dirname(__file__), "dungeonSprites_v1.5", "dungeonSprites_ v1.5")
if not os.path.isdir(SRC_DIR):
    SRC_DIR = os.path.join(os.path.dirname(__file__), "dungeonSprites_ v1.5")
TILE_OUT = 128  # engine tile size (matches generate_placeholder_textures.py)

# Character sprite: 24x24 native tiles
CHAR_TILE = 24
CHAR_COLS = 8
CHAR_ROWS = 6

CHARACTER_CHOICES = ["mHero_", "fHero_", "knight_", "demon_", "goblin_",
                     "hobgoblin_", "goblinKing_", "orc_", "skeleton_",
                     "warlock_", "ghost_", "necromancer_", "devil_",
                     "dragon_", "slime_", "slimeball_"]

# Direction row map for engine (dirIndex order in Constants.h):
#   row 0: NE  { 1,-1}   row 1: N   { 0,-1}
#   row 2: NW  {-1,-1}   row 3: W   {-1, 0}
#   row 4: SW  {-1, 1}   row 5: S   { 0, 1}
#   row 6: SE  { 1, 1}   row 7: E   { 1, 0}
#
# For source direction assignment: left='L', right='R'
# Right-facing = character faces East (dx>0), Left-facing = faces West (dx<0)
# Use R for right-side directions, L for left-side directions.
# Frames are 4 per direction (cols 0-3 = L, cols 4-7 = R).
DIRECTION_MAP = [
    ("NE",  0, "L"),  # row 0: facing up-right → left-facing (reverses mirrored spritesheet)
    ("N",   1, "R"),  # row 1: facing up → right-facing
    ("NW",  2, "R"),  # row 2: facing up-left → right-facing
    ("W",   3, "R"),  # row 3: facing left → right-facing
    ("SW",  4, "R"),  # row 4: facing down-left → right-facing
    ("S",   5, "L"),  # row 5: facing down → left-facing
    ("SE",  6, "L"),  # row 6: facing down-right → left-facing
    ("E",   7, "L"),  # row 7: facing right → left-facing
]

# Source animation rows → engine animation names
# Map source row index to list of engine animation names
ANIM_MAP = {
    0: ["idle"],
    1: ["walk", "run"],
    2: ["dash"],
    3: [],
    4: ["hurt"],
    5: ["death"],
}

ANIM_FRAMES = 4  # each direction has 4 frames in source

# Engine animation suffixes order
ENGINE_ANIMS = ["idle", "walk", "run", "cast", "slash", "slash2", "slash3", "hurt", "dash", "death"]
# For animations without a source, copy from a fallback
FALLBACK_MAP = {
    "cast":   "idle",
    "slash":  "idle",
    "slash2": "idle",
    "slash3": "idle",
}


def extract_source_frames(img):
    """Extract all 24x24 tiles from a character sheet.
    Returns dict: anim_row -> { 'L': [frames], 'R': [frames] }
    """
    frames = {}
    for row in range(CHAR_ROWS):
        left = []
        right = []
        for col in range(CHAR_COLS):
            x, y = col * CHAR_TILE, row * CHAR_TILE
            tile = img.crop((x, y, x + CHAR_TILE, y + CHAR_TILE))
            if col < 4:
                left.append(tile)
            else:
                right.append(tile)
        frames[row] = {"L": left, "R": right}
    return frames


def build_animation_sheet(source_frames, src_row, engine_side, num_frames=ANIM_FRAMES):
    """Build a single engine spritesheet row given source side (L or R).
    Returns list of PIL Images (one per frame), each 128x128.
    """
    frames = source_frames[src_row][engine_side]
    result = []
    for i in range(num_frames):
        if i < len(frames):
            f = frames[i]
        else:
            f = frames[-1] if frames else Image.new("RGBA", (CHAR_TILE, CHAR_TILE), (0,0,0,0))
        scaled = f.resize((TILE_OUT, TILE_OUT), Image.NEAREST)
        result.append(scaled)
    return result


def build_spritesheet(source_frames, src_row, fallback_row=None, num_frames=ANIM_FRAMES):
    """Build a full engine spritesheet (8 rows x num_frames cols) for one animation.
    Returns a PIL Image.
    """
    sheet = Image.new("RGBA", (TILE_OUT * num_frames, TILE_OUT * 8), (0, 0, 0, 0))
    for dir_name, engine_row, side in DIRECTION_MAP:
        actual_row = src_row
        if actual_row is None and fallback_row is not None:
            actual_row = fallback_row
        if actual_row is None:
            # Empty row
            continue
        frames = build_animation_sheet(source_frames, actual_row, side, num_frames)
        for col_idx, frame_img in enumerate(frames):
            x = col_idx * TILE_OUT
            y = engine_row * TILE_OUT
            sheet.paste(frame_img, (x, y), frame_img)
    return sheet


def convert_character(char_name):
    """Convert a single character's spritesheet into engine format."""
    src_path = os.path.join(SRC_DIR, f"{char_name}.png")
    if not os.path.exists(src_path):
        print(f"  MISSING: {src_path}")
        return False
    img = Image.open(src_path).convert("RGBA")
    if img.size != (192, 144):
        print(f"  SKIP {char_name}: unexpected size {img.size}")
        return False

    source_frames = extract_source_frames(img)

    for anim_name in ENGINE_ANIMS:
        src_row = None
        fallback_row = None

        for srow, anames in ANIM_MAP.items():
            if anim_name in anames:
                src_row = srow
                break

        if src_row is None:
            fallback_name = FALLBACK_MAP.get(anim_name)
            if fallback_name:
                for srow, anames in ANIM_MAP.items():
                    if fallback_name in anames:
                        fallback_row = srow
                        break

        # Determine number of frames
        nframes = ANIM_FRAMES

        sheet = build_spritesheet(source_frames, src_row, fallback_row, nframes)

        anim_dir = os.path.join(ASSETS_DIR, anim_name)
        os.makedirs(anim_dir, exist_ok=True)
        out_path = os.path.join(anim_dir, f"{anim_name}.png")
        sheet.save(out_path)
        print(f"  {anim_name}: {out_path} ({sheet.size[0]}x{sheet.size[1]}, {nframes} frames)")

    return True


def extract_weapons():
    """Extract weapon icons from weapons_.png and save individually."""
    src_path = os.path.join(SRC_DIR, "weapons_.png")
    if not os.path.exists(src_path):
        print(f"  MISSING: {src_path}")
        return

    img = Image.open(src_path).convert("RGBA")
    
    # Corrected: With a 60x120 image, 5 columns, and 5 rows,
    # the tiles are exactly 12x24 pixels each.
    tw, th = 12, 24
    cols, rows = 5, 5

    weapon_dir = os.path.join(ASSETS_DIR, "weapons")
    os.makedirs(weapon_dir, exist_ok=True)

    weapon_names = []
    for row in range(rows):
        for col in range(cols):
            x, y = col * tw, row * th
            tile = img.crop((x, y, x + tw, y + th))
            non_transparent = sum(1 for px in range(tw) for py in range(th) if tile.getpixel((px, py))[3] > 0)
            if non_transparent > 5:
                name = f"weapon_r{row}_c{col}"
                weapon_names.append((name, tile))
                # Save at original size and also scaled to 128x128 for the game
                tile_out = tile.resize((TILE_OUT, TILE_OUT), Image.NEAREST)
                out_path = os.path.join(weapon_dir, f"{name}.png")
                tile_out.save(out_path)
                print(f"  weapon: {out_path}")

    print(f"\n  Extracted {len(weapon_names)} weapon sprites to {weapon_dir}/")
    print(f"  Weapons_ grid: {cols}x{rows} tiles of {tw}x{th}")


def main():
    parser = argparse.ArgumentParser(description="Convert dungeonSprites to engine format")
    parser.add_argument("--character", default="mHero_",
                        help="Character sheet to convert (default: mHero_)")
    parser.add_argument("--list", action="store_true",
                        help="List available characters")
    parser.add_argument("--weapons", action="store_true", default=True,
                        help="Extract weapons (default: True)")

    args = parser.parse_args()

    if args.list:
        print("Available characters in v1.5:")
        for c in CHARACTER_CHOICES:
            path = os.path.join(SRC_DIR, f"{c}.png")
            exists = "✓" if os.path.exists(path) else "✗"
            if os.path.exists(path):
                img = Image.open(path)
                print(f"  {c:20s} [{exists}] {img.size}")
        return

    print(f"Converting character: {args.character}")
    ok = convert_character(args.character)
    if not ok:
        print(f"Failed to convert {args.character}")
        sys.exit(1)

    if args.weapons:
        print("\nExtracting weapons...")
        extract_weapons()

    print("\nDone! Generated spritesheets in assets/")


if __name__ == "__main__":
    import argparse
    main()
