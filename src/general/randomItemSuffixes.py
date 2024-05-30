suffixes = {
    "of the galeburst": "(hit+exp)",
    "of the stormblast": "(hit+crit)",
    "of the windflurry": "(haste+crit)",
    "of the windstorm": "(crit+mast)",
    "of the zephyr": "(haste+mast)",  # wowhead typo
    "of the zehpyr": "(haste+mast)",
    "of the feverflare": "(haste+mast)",
    "of the fireflash": "(haste+crit)",
    "of the flameblaze": "(hit+mast)",
    "of the undertow": "(spir+haste)",
    "of the wavecrest": "(spir+mast)",
    "of the wildfire": "(hit+crit)",
    "of the bedrock": "(mast+parry)",
    "of the bouldercrag": "(dodge+parry)",
    "of the earthbreaker": "(crit+mast)",
    "of the earthfall": "(haste+crit)",
    "of the earthshaker": "(hit+crit)",
    "of the faultline": "(haste+mast)",
    "of the landslide": "(hit+exp)",
    "of the mountainbed": "(exp+mast)",
    "of the rockslab": "(dodge+mast)",
}


def find_suffix(string: str):
    string = string.lower()
    if "of the" in string:
        for suffix in suffixes.keys():
            if suffix in string:
                return suffix, suffixes[suffix]
    return None, ""
