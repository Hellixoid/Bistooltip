# The wh spec list currently matches the canonical list, so we reuse it. If the wh source
# ever diverges (it has in the past), replace this with an explicit list specific to wh.
from src.general.specs import specs

spec_to_url_path = {
    "blood-tank-death-knight": "death-knight/blood/tank",
    "frost-death-knight": "death-knight/frost/dps",
    "unholy-death-knight": "death-knight/unholy/dps",
    "balance-druid": "druid/balance/dps",
    "guardian-druid": "druid/guardian/tank",
    "feral-druid": "druid/feral/dps",
    "restoration-druid": "druid/restoration/healer",
    "beast-mastery-hunter": "hunter/beast-mastery/dps",
    "marksmanship-hunter": "hunter/marksmanship/dps",
    "survival-hunter": "hunter/survival/dps",
    "arcane-mage": "mage/arcane/dps",
    "fire-mage": "mage/fire/dps",
    "frost-mage": "mage/frost/dps",
    "brewmaster-monk": "monk/brewmaster/tank",
    "mistweaver-monk": "monk/mistweaver/healer",
    "windwalker-monk": "monk/windwalker/dps",
    "holy-paladin": "paladin/holy/healer",
    "protection-paladin": "paladin/protection/tank",
    "retribution-paladin": "paladin/retribution/dps",
    "discipline-priest": "priest/discipline/healer",
    "holy-priest": "priest/holy/healer",
    "shadow-priest": "priest/shadow/dps",
    "assassination-rogue": "rogue/assassination/dps",
    "combat-rogue": "rogue/combat/dps",
    "subtlety-rogue": "rogue/subtlety/dps",
    "elemental-shaman": "shaman/elemental/dps",
    "enhancement-shaman": "shaman/enhancement/dps",
    "restoration-shaman": "shaman/restoration/healer",
    "affliction-warlock": "warlock/affliction/dps",
    "demonology-warlock": "warlock/demonology/dps",
    "destruction-warlock": "warlock/destruction/dps",
    "arms-warrior": "warrior/arms/dps",
    "fury-warrior": "warrior/fury/dps",
    "protection-warrior": "warrior/protection/tank"
}

