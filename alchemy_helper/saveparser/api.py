"""The save parser's public surface.

Everything else in `alchemy_helper.saveparser` is an implementation
detail; the web layer imports only `parse_save`, `PlayerState`,
`UnknownForm` and `SaveFormatError` from here.

`parse_save` is the app's never-brick boundary: whatever goes wrong
inside -- a missing file, a truncated read, a layout this parser
doesn't understand, a bug -- comes back out as a single SaveFormatError
whose message names the save version, the form version and the step
that failed, so the UI always has something specific to show.
"""
from dataclasses import dataclass
from pathlib import Path

from alchemy_helper.data.loader import Dataset
from alchemy_helper.saveparser.body import parse_plugins, read_body
from alchemy_helper.saveparser.changeforms import (
    iter_change_forms, parse_file_location_table, parse_form_id_array)
from alchemy_helper.saveparser.extract import extract_forms
from alchemy_helper.saveparser.header import SaveFormatError, parse_header

__all__ = ["PlayerState", "UnknownForm", "SaveFormatError", "parse_save"]


@dataclass(frozen=True)
class UnknownForm:
    """An ingredient-use change form whose form isn't in the dataset --
    almost always an ingredient added by a mod this app doesn't ship
    data for. Collected and reported instead of being fatal.
    """
    plugin: str
    form_id: int   # local id: low 24 bits (.esm/.esp) or low 12 (.esl)


@dataclass(frozen=True)
class PlayerState:
    save_path: str
    character_name: str
    save_number: int
    inventory: dict[str, int]                 # ingredient id -> carried count
    known_effects: dict[str, frozenset[int]]  # ingredient id -> known slots 0-3
    unknown_forms: tuple[UnknownForm, ...]


def parse_save(path: Path, dataset: Dataset) -> PlayerState:
    """Read a Skyrim SE save and return what the player is carrying and
    what they have already discovered.

    Raises:
        SaveFormatError: for every failure mode, with the save version,
            form version (once known) and failing step in the message.
    """
    path = Path(path)
    save_version: object = "unknown"
    form_version: object = "unknown"
    step = "opening the file"

    def fail(exc: Exception) -> SaveFormatError:
        return SaveFormatError(
            f"Could not read {path.name}: failed at step {step!r} "
            f"(save version {save_version}, form version {form_version}) "
            f"-- {type(exc).__name__}: {exc}"
        )

    try:
        data = path.read_bytes()

        step = "parsing the header"
        header = parse_header(data)
        save_version = header.version

        step = "decompressing the save body"
        body = read_body(data, header)

        step = "reading the plugin list"
        plugins, after_plugins = parse_plugins(body)
        form_version = plugins.form_version

        step = "reading the file location table"
        table = parse_file_location_table(body, after_plugins, header.body_offset)

        step = "reading the form id array"
        form_id_array = parse_form_id_array(body, table)

        step = "extracting inventory and known effects from change forms"
        extracted = extract_forms(
            iter_change_forms(body, table), plugins, form_id_array, dataset)
    except Exception as exc:
        raise fail(exc) from exc

    return PlayerState(
        save_path=str(path),
        character_name=header.player_name,
        save_number=header.save_number,
        inventory=dict(extracted.inventory),
        known_effects=dict(extracted.known_effects),
        unknown_forms=tuple(
            UnknownForm(plugin=plugin, form_id=form_id)
            for plugin, form_id in extracted.unknown_forms
        ),
    )
