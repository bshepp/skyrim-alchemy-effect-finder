"""App state and manual overrides for the alchemy helper.

Provides AppState which combines parsed save data with manual overrides,
supporting both save-based and manual modes. Overrides persist to disk as JSON.
"""
import json
from dataclasses import dataclass
from pathlib import Path

from alchemy_helper.data.loader import Dataset
from alchemy_helper.saveparser.api import PlayerState


class Overrides:
    """Manual overrides for inventory and known effects.

    Overrides always win over data from a parsed save file. Supports
    persistent storage to JSON.
    """

    def __init__(self, path: Path):
        """Initialize from JSON file if it exists, else empty.

        Args:
            path: Path to overrides.json file (may not exist yet).
        """
        self.path = Path(path)
        self.have: dict[str, int] = {}
        self.known: dict[str, set[int]] = {}

        if self.path.exists():
            self._load()

    def _load(self) -> None:
        """Load overrides from JSON file, degrading to empty on any corruption."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))

            # Validate top-level is a dict
            if not isinstance(data, dict):
                self.have = {}
                self.known = {}
                return

            # Load have: must be dict with int values
            have_data = data.get("have", {})
            if isinstance(have_data, dict):
                self.have = {
                    k: v for k, v in have_data.items()
                    if isinstance(k, str) and isinstance(v, int)
                }
            else:
                self.have = {}

            # Load known: must be dict with list[int] values
            known_data = data.get("known", {})
            if isinstance(known_data, dict):
                self.known = {}
                for k, v in known_data.items():
                    if isinstance(k, str) and isinstance(v, list):
                        # Validate all elements are ints
                        if all(isinstance(slot, int) for slot in v):
                            self.known[k] = set(v)
            else:
                self.known = {}

        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            # If file is corrupt, unreadable, or wrong encoding, start fresh
            self.have = {}
            self.known = {}

    def set_have(self, ingredient_id: str, count: int | None) -> None:
        """Set or clear the inventory count override.

        Args:
            ingredient_id: The ingredient id.
            count: The override count, or None to clear.
        """
        if count is None:
            self.have.pop(ingredient_id, None)
        else:
            self.have[ingredient_id] = count

    def set_known(self, ingredient_id: str, slots: set[int] | None) -> None:
        """Set or clear the known effects override.

        Args:
            ingredient_id: The ingredient id.
            slots: Set of known effect slots (0-3), or None to clear.
        """
        if slots is None:
            self.known.pop(ingredient_id, None)
        else:
            self.known[ingredient_id] = set(slots)

    def save(self) -> None:
        """Write overrides to JSON file, creating parent directories."""
        self.path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize sets as sorted lists for JSON compatibility
        data = {
            "have": self.have,
            "known": {k: sorted(v) for k, v in self.known.items()}
        }

        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@dataclass
class AppState:
    """Application state combining dataset, player data, and manual overrides.

    Supports both save-based mode (player present) and manual mode (player=None).
    Overrides always take precedence over parsed save data.
    """
    dataset: Dataset
    player: PlayerState | None  # None indicates manual mode
    overrides: Overrides
    last_error: str | None  # Diagnostic from a failed parse

    def effective_inventory(self) -> dict[str, int]:
        """Get effective inventory with overrides winning over player data.

        In save mode: combines player inventory with overrides.
        In manual mode: returns only overrides.

        Returns:
            dict mapping ingredient id to count.
        """
        result = {}

        # In save mode, start with player inventory
        if self.player is not None:
            result.update(self.player.inventory)

        # Overrides always win
        result.update(self.overrides.have)

        return result

    def effective_known(self) -> dict[str, frozenset[int]]:
        """Get effective known effects with overrides winning over player data.

        In save mode: combines player known effects with overrides.
        In manual mode: returns only overrides as frozensets.

        Returns:
            dict mapping ingredient id to frozenset of known slots (0-3).
        """
        result = {}

        # In save mode, start with player known effects
        if self.player is not None:
            result.update(self.player.known_effects)

        # Overrides always win (convert sets to frozensets)
        for ingredient_id, slots in self.overrides.known.items():
            result[ingredient_id] = frozenset(slots)

        return result

    def mode(self) -> str:
        """Return the current mode: 'save' or 'manual'.

        Returns:
            'save' if player data is present, 'manual' otherwise.
        """
        return "save" if self.player is not None else "manual"
