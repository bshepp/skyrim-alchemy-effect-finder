from pathlib import Path
from alchemy_helper.saveparser.header import parse_header
from alchemy_helper.saveparser.body import read_body, parse_plugins

FIXTURE = Path(__file__).parent.parent / "fixtures" / "player.ess"


def test_body_decompresses():
    data = FIXTURE.read_bytes()
    body = read_body(data, parse_header(data))
    assert len(body) > 1_000_000   # decompressed SE bodies are multi-MB

# Pinned from an actual run against the fixture (see body.py's module
# docstring for how the plugin-block layout was verified). This is the full
# vanilla SE base game + all DLC + the complete Anniversary Edition free
# Creations bundle (cross-checked against FACTS.md: user reported vanilla +
# free Creations, e.g. Fishing/Survival Mode/Rare Curios/Saints & Seducers,
# all present below alongside the rest of the free CC content AE grants).
EXPECTED_PLUGINS = (
    "Skyrim.esm",
    "Update.esm",
    "Dawnguard.esm",
    "HearthFires.esm",
    "Dragonborn.esm",
    "ccasvsse001-almsivi.esm",
    "ccbgssse001-fish.esm",
    "cctwbsse001-puzzledungeon.esm",
    "cceejsse001-hstead.esm",
    "ccbgssse016-umbra.esm",
    "ccbgssse031-advcyrus.esm",
    "ccbgssse067-daedinv.esm",
    "ccbgssse025-advdsgs.esm",
    "cceejsse005-cave.esm",
    "ccafdsse001-dwesanctuary.esm",
)

EXPECTED_LIGHT_PLUGINS = (
    "ccbgssse002-exoticarrows.esl",
    "ccbgssse003-zombies.esl",
    "ccbgssse004-ruinsedge.esl",
    "ccbgssse005-goldbrand.esl",
    "ccbgssse006-stendarshammer.esl",
    "ccbgssse007-chrysamere.esl",
    "ccbgssse010-petdwarvenarmoredmudcrab.esl",
    "ccbgssse011-hrsarmrelvn.esl",
    "ccbgssse012-hrsarmrstl.esl",
    "ccbgssse014-spellpack01.esl",
    "ccbgssse019-staffofsheogorath.esl",
    "ccbgssse020-graycowl.esl",
    "ccbgssse021-lordsmail.esl",
    "ccmtysse001-knightsofthenine.esl",
    "ccqdrsse001-survivalmode.esl",
    "ccqdrsse002-firewood.esl",
    "ccbgssse018-shadowrend.esl",
    "ccbgssse035-petnhound.esl",
    "ccfsvsse001-backpacks.esl",
    "cceejsse002-tower.esl",
    "ccedhsse001-norjewel.esl",
    "ccvsvsse002-pets.esl",
    "ccbgssse037-curios.esl",
    "ccbgssse034-mntuni.esl",
    "ccbgssse045-hasedoki.esl",
    "ccbgssse008-wraithguard.esl",
    "ccbgssse036-petbwolf.esl",
    "ccffbsse001-imperialdragon.esl",
    "ccmtysse002-ve.esl",
    "ccbgssse043-crosselv.esl",
    "ccvsvsse001-winter.esl",
    "cceejsse003-hollow.esl",
    "ccbgssse038-bowofshadows.esl",
    "ccbgssse040-advobgobs.esl",
    "ccbgssse050-ba_daedric.esl",
    "ccbgssse052-ba_iron.esl",
    "ccbgssse054-ba_orcish.esl",
    "ccbgssse058-ba_steel.esl",
    "ccbgssse059-ba_dragonplate.esl",
    "ccbgssse061-ba_dwarven.esl",
    "ccpewsse002-armsofchaos.esl",
    "ccbgssse041-netchleather.esl",
    "ccedhsse002-splkntset.esl",
    "ccbgssse064-ba_elven.esl",
    "ccbgssse063-ba_ebony.esl",
    "ccbgssse062-ba_dwarvenmail.esl",
    "ccbgssse060-ba_dragonscale.esl",
    "ccbgssse056-ba_silver.esl",
    "ccbgssse055-ba_orcishscaled.esl",
    "ccbgssse053-ba_leather.esl",
    "ccbgssse051-ba_daedricmail.esl",
    "ccbgssse057-ba_stalhrim.esl",
    "ccbgssse066-staves.esl",
    "ccbgssse068-bloodfall.esl",
    "ccbgssse069-contest.esl",
    "ccvsvsse003-necroarts.esl",
    "ccvsvsse004-beafarmer.esl",
    "ccffbsse002-crossbowpack.esl",
    "ccbgssse013-dawnfang.esl",
    "ccrmssse001-necrohouse.esl",
    "ccedhsse003-redguard.esl",
    "cceejsse004-hall.esl",
    "cckrtsse001_altar.esl",
    "cccbhsse001-gaunt.esl",
    "_ResourcePack.esl",
)


def test_plugin_lists():
    data = FIXTURE.read_bytes()
    plugins, _ = parse_plugins(read_body(data, parse_header(data)))
    assert "Skyrim.esm" in plugins.plugins
    assert any(p.lower().startswith("cc") for p in
               plugins.plugins + plugins.light_plugins)  # free Creations present
    assert plugins.plugins == EXPECTED_PLUGINS
    assert plugins.light_plugins == EXPECTED_LIGHT_PLUGINS
    assert plugins.form_version == 78
