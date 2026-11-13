# The wh spec list matches the canonical list, so we reuse it.
from src.general.specs import specs

# Canonical spec id -> Wowhead Forever BiS page path, appended to
# https://www.wowhead.com/forever/guide/classes/ . Feral druid has two BiS pages
# (DPS / Tank); every other spec uses the plain "bis-gear" page.
spec_to_wh_bis_path = {
    "balance-druid": "druid/balance/bis-gear",
    "feral-dps-druid": "druid/feral/bis-gear-dps",
    "feral-tank-druid": "druid/feral/bis-gear-tank",
    "restoration-druid": "druid/restoration/bis-gear",
    "beast-mastery-hunter": "hunter/beast-mastery/bis-gear",
    "marksmanship-hunter": "hunter/marksmanship/bis-gear",
    "survival-hunter": "hunter/survival/bis-gear",
    "arcane-mage": "mage/arcane/bis-gear",
    "fire-mage": "mage/fire/bis-gear",
    "frost-mage": "mage/frost/bis-gear",
    "holy-paladin": "paladin/holy/bis-gear",
    "protection-paladin": "paladin/protection/bis-gear",
    "retribution-paladin": "paladin/retribution/bis-gear",
    "discipline-priest": "priest/discipline/bis-gear",
    "holy-priest": "priest/holy/bis-gear",
    "shadow-priest": "priest/shadow/bis-gear",
    "assassination-rogue": "rogue/assassination/bis-gear",
    "combat-rogue": "rogue/combat/bis-gear",
    "subtlety-rogue": "rogue/subtlety/bis-gear",
    "elemental-shaman": "shaman/elemental/bis-gear",
    "enhancement-shaman": "shaman/enhancement/bis-gear",
    "restoration-shaman": "shaman/restoration/bis-gear",
    "affliction-warlock": "warlock/affliction/bis-gear",
    "demonology-warlock": "warlock/demonology/bis-gear",
    "destruction-warlock": "warlock/destruction/bis-gear",
    "arms-warrior": "warrior/arms/bis-gear",
    "fury-warrior": "warrior/fury/bis-gear",
    "protection-warrior": "warrior/protection/bis-gear"
}
