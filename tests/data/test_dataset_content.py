from alchemy_helper.data.loader import load_dataset

# Survival Mode (ccQDRSSE001-SurvivalMode.esl) was verified against
# https://en.uesp.net/wiki/Skyrim:Survival_Mode — its "Content" section lists
# only 12 new Hot Soup recipes (which reuse the vanilla Fire Salts ingredient);
# it adds zero new alchemy ingredients, so it contributes nothing to the dataset.

# Flame Stalk is shipped as TWO distinct dataset entries, "flame-stalk" and
# "flame-stalk-solitude", because UESP's own Flame Stalk page documents two
# separate game records with identical effects: FExxx82A (form_id 2090,
# ccBGSSSE037-Curios.esl, "Added by Rare Curios, Saints & Seducers") and
# xx095E23 (form_id 613923, ccBGSSSE025-AdvDSGS.esm, "Added by Saints &
# Seducers" — harvested from Flame Stalk plants in Solitude Sewers). The app
# resolves save-file formIDs against this dataset and Skyrim tracks discovered
# alchemy effects per record, so a player who only ever harvests the Solitude
# Sewers variant needs the second record represented, not just the Curios one.

def test_shipped_dataset_is_valid():
    ds = load_dataset()  # default dir → shipped JSON
    # 179 ingredients: 110 vanilla+Dawnguard+Hearthfire+Dragonborn+_ResourcePack.esl
    # ("Skyrim:Ingredients" intro: 91 base + 5 DG + 11 DB + 2 HF + 1 _ResourcePack.esl)
    # + 2 real quest ingredients (Berit's Ashes, Jarrin Root) + 51 Rare Curios
    # + 9 Fishing + 6 Saints & Seducers (3 native + 3 Update.esm gated by S&S) + 0 Survival Mode
    # + 1 extra record for the Saints & Seducers-sourced Flame Stalk (xx095E23,
    # see comment above) which is a distinct game record from the Rare Curios one.
    assert len(ds.ingredients) == 179
    # 60 effects: the 59 listed on "Skyrim:Alchemy Effects" + Fortify Persuasion
    # (exclusive to Glassfish, documented on "Skyrim:Fortify Persuasion" but
    # omitted from the main effect table since it can't be combined into a potion).
    assert len(ds.effects) == 60

def test_wheat_golden():
    ds = load_dataset()
    assert ds.ingredients["wheat"].effects == (
        "restore-health", "fortify-health",
        "damage-stamina-regen", "lingering-damage-magicka")
    assert ds.ingredients["wheat"].plugin == "Skyrim.esm"

def test_giants_toe_golden():
    ds = load_dataset()
    assert ds.ingredients["giants-toe"].effects == (
        "damage-stamina", "fortify-health",
        "fortify-carry-weight", "damage-stamina-regen")

def test_blue_mountain_flower_golden():
    ds = load_dataset()
    assert ds.ingredients["blue-mountain-flower"].effects == (
        "restore-health", "fortify-conjuration",
        "fortify-health", "damage-magicka-regen")

def test_creation_club_plugins_present():
    ds = load_dataset()
    plugins = {i.plugin for i in ds.ingredients.values()}
    assert any("curios" in p.lower() for p in plugins)      # Rare Curios
    assert any(p == "Skyrim.esm" for p in plugins)
