import re
import os
import glob
from typing import Dict, Any, List

# Build canonical list of hero names
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORTRAITS_DIR = os.path.join(BASE_DIR, "assets", "heroes", "portraits")
CACHE_DIR = os.path.join(BASE_DIR, "assets", "heroes", "cache")

def get_known_heroes() -> Dict[str, str]:
    """
    Returns a mapping of normalized_hero_name -> display_name.
    Loaded dynamically from assets/heroes/.
    """
    mapping = {}
    if os.path.exists(PORTRAITS_DIR):
        for f in glob.glob(os.path.join(PORTRAITS_DIR, "*.png")):
            name = os.path.splitext(os.path.basename(f))[0]
            display = name.capitalize()
            # Special capitalization fixes
            if name == "popolkupa":
                display = "Popol and Kupa"
            elif name == "yisunshin":
                display = "Yi Sun-shin"
            elif name == "yuzhong":
                display = "Yu Zhong"
            elif name == "xborg":
                display = "X.Borg"
            elif name == "change":
                display = "Chang'e"
            elif name == "lapulapu":
                display = "Lapu-Lapu"
            elif name == "luoyi":
                display = "Luo Yi"
            elif name == "gatotkaca":
                display = "Gatotkaca"
            mapping[name.lower()] = display

    if os.path.exists(CACHE_DIR):
        for f in glob.glob(os.path.join(CACHE_DIR, "*.png")):
            name = os.path.splitext(os.path.basename(f))[0].lower()
            if name not in mapping:
                clean = name.replace("-", " ").replace("_", " ").title()
                mapping[name] = clean
    return mapping


def extract_heroes_from_text(text: str, title: str = "") -> Dict[str, Any]:
    """
    Automatically extracts version, server, buffs, nerfs, adjustments, and revamps
    from any raw patch article or text by analyzing hero mentions and surrounding context.
    """
    heroes_map = get_known_heroes()
    full_text = f"{title}\n{text}"

    # Extract version
    ver_match = re.search(r"(\d+\.\d+\.\d+[a-z]?)", full_text)
    version = ver_match.group(1) if ver_match else "1.9.xx"

    # Extract server
    server = "ADVANCED SERVER" if "advanced" in full_text.lower() else "ORIGINAL SERVER"

    result = {
        "version": version,
        "server": server,
        "buffs": [],
        "nerfs": [],
        "adjustments": [],
        "revamps": []
    }

    current_cat = None
    lines = full_text.splitlines()

    for line in lines:
        lower_line = line.lower().strip()
        if not lower_line:
            continue

        # Detect category headers
        if any(k in lower_line for k in ["buff:", "buffed", "[buff", "buffs", "kuchaytirildi"]):
            current_cat = "buffs"
        elif any(k in lower_line for k in ["nerf:", "nerfed", "[nerf", "nerfs", "zaiflashtirildi"]):
            current_cat = "nerfs"
        elif any(k in lower_line for k in ["revamp:", "revamped", "[revamp", "revamps", "yangilandi"]):
            current_cat = "revamps"
        elif any(k in lower_line for k in ["adjustment:", "adjusted", "[adjustment", "adjustments", "moslashtirildi", "hero adjustments"]):
            current_cat = "adjustments"

        # Check for heroes mentioned in this line
        for h_key, display_name in heroes_map.items():
            if len(h_key) < 3:
                continue
            # Regex match on word boundary
            pattern = r"(?<![a-zA-Z0-9])" + re.escape(h_key) + r"(?![a-zA-Z0-9])"
            if re.search(pattern, lower_line):
                # Determine category for this line
                target_cat = current_cat
                if any(w in lower_line for w in ["buff", "kuchaytir"]):
                    target_cat = "buffs"
                elif any(w in lower_line for w in ["nerf", "zaiflashtir"]):
                    target_cat = "nerfs"
                elif any(w in lower_line for w in ["revamp", "qayta"]):
                    target_cat = "revamps"
                elif any(w in lower_line for w in ["adjust", "moslash", "o'zgarish"]):
                    target_cat = "adjustments"

                if not target_cat:
                    target_cat = "adjustments"

                # Check not already in any category
                already_added = any(display_name in result[cat] for cat in result)
                if not already_added:
                    result[target_cat].append(display_name)

    return result
