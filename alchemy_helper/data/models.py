from dataclasses import dataclass


@dataclass(frozen=True)
class Effect:
    id: str            # slug, e.g. "fortify-health"
    name: str          # "Fortify Health"
    description: str
    harmful: bool


@dataclass(frozen=True)
class Ingredient:
    id: str                             # slug, e.g. "wheat"
    name: str                           # "Wheat"
    plugin: str                         # e.g. "Skyrim.esm", "ccBGSSSE037-Curios.esl"
    form_id: int                        # object id WITHOUT load-order prefix
                                        #   .esm/.esp: lower 24 bits; .esl: lower 12 bits
    effects: tuple[str, str, str, str]  # effect ids, in-game slot order


@dataclass(frozen=True)
class Pack:
    """A mod's ingredient records, shipped as data and activated when the
    save's load order contains one of the pack's plugins."""
    id: str                        # slug, e.g. "the-cause"
    name: str                      # "The Cause (Creation)"
    plugins: tuple[str, ...]       # plugin filenames that activate the pack
    mode: str                      # "extend": new records only;
                                   # "overhaul": may also replace base records
    effects: tuple[Effect, ...]
    ingredients: tuple[Ingredient, ...]
