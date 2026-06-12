# BiS-Tooltip — data pipeline

This repository contains the **data-generation pipeline** behind the **BiS-Tooltip**
World of Warcraft addon. The Python code
scrapes BiS gear guides from the web, normalizes them into a common model,
and produces Lua data files for the addon.

The addon itself lives in [`addon/Bistooltip`](addon/Bistooltip) as a **git submodule**
([BistooltipAddon](https://github.com/Hellixoid/BistooltipAddon)).

---

## What it does

For every class/spec and game phase it:

1. **Gathers** raw BiS data from a source website and caches it on disk.
2. **Parses** that raw data into an internal model (`SortedSpec` → `Slot` → `Phase` → `Item`),
   resolving item / gem / enchant names to numeric IDs and applying faction and tier token mappings.
3. **Constructs** two Lua tables per source and writes them into the addon:
    - an **items** table (`*_items.lua`) — keyed by item ID, listing which specs/slots/phases
      each item is BiS for (used to enrich item tooltips in-game);
    - a **bislists** table (`*_bislists.lua`) — the full per-spec, per-phase BiS list with gems
      and enchants (used to render the in-game BiS list UI).

### Data sources

The pipeline supports two interchangeable sources (`src/dataSources.py`):

| Source   | Site        | Fetch method                | Raw cache                       |
|----------|-------------|-----------------------------|---------------------------------|
| `wh`     | wowhead.com | Selenium + headless Chrome  | `data/wh/<spec>.<phase>` (HTML) |
| `wowtbc` | wowtbc.gg   | `requests` (page-data JSON) | `data/wowtbc/<spec>.json`       |

Phases are defined in [`src/general/phases.py`](src/general/phases.py).

---

## Tech stack

- **Python 3.6+**.
- [`beautifulsoup4`](https://pypi.org/project/beautifulsoup4/) — HTML parsing (`wh` source).
- [`selenium`](https://pypi.org/project/selenium/) + a local **Chrome / ChromeDriver** — page
  rendering for the `wh` source (Wowhead guides are JS-rendered).
- [`requests`](https://pypi.org/project/requests/) — fetching the `wowtbc` source.

These are listed in [`requirements.txt`](requirements.txt) (see Setup).

---

## Data files

All paths are defined in [`src/dirsAndFiles.py`](src/dirsAndFiles.py) and are relative to the
`src/` directory (the pipeline expects to run from there).

### Item collections (`data/items/`)

These are reference databases (item/gem/enchant name → numeric ID + item level) used to
resolve item names found in the guides (mainly used for `wowtbc`).

| File                                  | Purpose                                                    |
|---------------------------------------|------------------------------------------------------------|
| `data/items/list.json`                | Item collection — resolves item names → IDs.               |
| `data/items/gems.json`                | Gem collection — resolves gem names → IDs.                 |
| `data/items/consumablesAndQuest.json` | Enchant-as-**item** collection (enchant `type: "item"`).   |
| `data/items/ench_spells.json`         | Enchant-as-**spell** collection (enchant `type: "spell"`). |

### item mappings

| File                    | Purpose                                                                                                                                                                                                                                                                                 |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `data/alitohorde.json`  | Horde item ID → Alliance item ID mapping. Applied during parsing so both factions resolve to one item; the reverse map is emitted as `Bistooltip_horde_to_ali.lua`. **Deprecated** — this was used back in WotLK, when factions had distinct item IDs; kept for backward compatibility. |
| `data/tokens.json`      | Tier-token ID → list of item IDs it can be exchanged for; BiS statements are copied onto the token.                                                                                                                                                                                     |
| `data/soo_wf_gear.json` | Heroic item ID → Siege of Orgrimmar warforged item ID.                                                                                                                                                                                                                                  |

---

## Setup

1. **Clone with the addon submodule:**
   ```bash
   git clone --recurse-submodules <repo-url>
   # or, if already cloned:
   git submodule update --init --recursive
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **For the `wh` source only** — install **Google Chrome** and a matching **ChromeDriver**
   on `PATH`. The scraper also points at a specific Chrome user-data dir and profile in
   [`whSpecDataGatherer.py`](src/wh/whSpecDataGatherer.py):
   ```python
   options.add_argument(r'--user-data-dir=D:\code')
   options.add_argument('--profile-directory=Profile 2')
   ```
   Adjust these to a Chrome profile on your machine (or remove them to use a fresh profile).
   The `wowtbc` source needs no browser.

---

## Running

The pipeline uses paths relative to `src/` (e.g. `../data/...`), so **run it from inside the
`src/` directory**:

```bash
cd src
python main.py
```

### Choosing what to build

[`src/main.py`](src/main.py) is driven by a couple of switches in its `__main__` block:

```python
if __name__ == '__main__':
    data_collection = True  # True = re-scrape sources; False = reuse cached raw data
    # process_wowtbc()          # build the wowtbc.gg data
    process_wh()  # build the Wowhead data
    # build_ali_to_horde_mapping()
```

- **`data_collection`** — `True` re-scrapes the source website into the raw cache before
  parsing; `False` parses the existing cache in `data/wh` / `data/wowtbc` (fast, offline,
  no Chrome needed).
- Uncomment **`process_wh()`**, **`process_wowtbc()`**, and/or **`build_ali_to_horde_mapping()`**
  to choose which outputs to (re)generate.

Each `process_*` run: (optionally) gathers → parses every spec → writes the `*_items.lua` and
`*_bislists.lua` files → copies them into `addon/Bistooltip/`.

### Packaging a release

[`src/package.py`](src/package.py) bumps the version string in the addon's `.toc` and
`Core.lua`, then zips the addon into `addonZips/`:

```bash
cd src
python package.py        # uses addon_version defined at the top of package.py
```

## License

MIT — see [LICENSE](LICENSE).
