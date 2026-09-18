from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from ParadoxParser import ParadoxScriptParser
from ParadoxParser.ParadoxNodes import GenericBlock, GenericKeyValue, GenericToken
from ParadoxParser.queries import find_node, find_nodes


CONTROL_BLOCKS = {"if", "else_if", "else", "limit", "hidden_trigger"}
STATIC_FAMILIES = (
    ("CGEBR_PR_S", "CGE_BR_PR_S", "cge_cge_character_key"),
    ("CGEBR_REC_S", "CGE_BR_REC_S", "cge_recruitment_character_key"),
    ("CGEBR_OV_S", "CGE_BR_OV_S", "cge_overview_selected_character_key"),
)
BATCH_SIZE = 32


@dataclass
class CharacterInfo:
    token: str
    portraits: list[str] = field(default_factory=list)
    has_army_role: bool = False
    source_files: list[str] = field(default_factory=list)

    @property
    def portrait(self) -> str | None:
        return self.portraits[0] if self.portraits else None


@dataclass
class BuildState:
    warnings: list[str] = field(default_factory=list)
    duplicate_tokens: list[str] = field(default_factory=list)
    ambiguous_portraits: dict[str, list[str]] = field(default_factory=dict)
    unresolved_portraits: list[str] = field(default_factory=list)
    parser_failures: list[str] = field(default_factory=list)


def kv(key: str, value: str | int) -> GenericKeyValue:
    return GenericKeyValue(key, GenericToken(str(value)))


def block(key: str, nodes: list | None = None) -> GenericBlock:
    return GenericBlock(key, nodes or [])


def walk_blocks(node) -> list[GenericBlock]:
    result = []
    if isinstance(node, GenericBlock):
        result.append(node)
        for child in node.nodes:
            if isinstance(child, GenericBlock):
                result.extend(walk_blocks(child))
    return result


def walk_keyvalues(node, key: str | None = None) -> list[GenericKeyValue]:
    result = []
    if isinstance(node, GenericKeyValue):
        if key is None or node.key == key:
            result.append(node)
    if isinstance(node, GenericBlock):
        for child in node.nodes:
            result.extend(walk_keyvalues(child, key))
    return result


def scalar(node: GenericKeyValue) -> str:
    return str(node.get_value()).strip().strip('"')


def direct_army_portraits(scope: GenericBlock) -> list[str]:
    result = []
    for portraits_block in find_nodes(scope, GenericBlock, "portraits"):
        for army_block in find_nodes(portraits_block, GenericBlock, "army"):
            for large in find_nodes(army_block, GenericKeyValue, "large"):
                value = scalar(large)
                if value and value not in result:
                    result.append(value)
    return result


def character_portraits(character: GenericBlock) -> list[str]:
    result = []
    for value in direct_army_portraits(character):
        if value not in result:
            result.append(value)
    for candidate in walk_blocks(character):
        if candidate is character or candidate.key != "instance":
            continue
        for value in direct_army_portraits(candidate):
            if value not in result:
                result.append(value)
    return result


def has_army_role(character: GenericBlock) -> bool:
    return any(candidate.key in {"corps_commander", "field_marshal"} for candidate in walk_blocks(character))


def iter_character_blocks(container: GenericBlock):
    for node in container.nodes:
        if not isinstance(node, GenericBlock):
            continue
        if node.key in CONTROL_BLOCKS:
            yield from iter_character_blocks(node)
            continue
        yield node


def scan_source_characters(source_mod: Path, state: BuildState) -> dict[str, CharacterInfo]:
    character_dir = source_mod / "common" / "characters"
    if not character_dir.is_dir():
        raise RuntimeError(f"No common/characters folder found in source mod: {character_dir}")
    characters: dict[str, CharacterInfo] = {}
    for path in sorted(character_dir.rglob("*.txt"), key=lambda p: str(p).lower()):
        try:
            file_obj = ParadoxScriptParser.load(path=path)
        except Exception as exc:
            state.parser_failures.append(f"{path}: {exc}")
            continue
        roots = [node for node in file_obj.nodes if isinstance(node, GenericBlock) and node.key == "characters"]
        if not roots:
            continue
        relative = str(path.relative_to(source_mod)).replace("\\", "/")
        for root in roots:
            for character in iter_character_blocks(root):
                token = character.key
                portraits = character_portraits(character)
                army_role = has_army_role(character)
                if not portraits and not army_role:
                    continue
                if token in characters:
                    state.duplicate_tokens.append(token)
                    existing = characters[token]
                    existing.has_army_role = existing.has_army_role or army_role
                    existing.source_files.append(relative)
                    if portraits:
                        existing.portraits = portraits
                    continue
                characters[token] = CharacterInfo(
                    token=token,
                    portraits=portraits,
                    has_army_role=army_role,
                    source_files=[relative],
                )
    for token, info in characters.items():
        if len(info.portraits) > 1:
            state.ambiguous_portraits[token] = info.portraits
    return characters


def extract_cge_registry(registry_path: Path) -> tuple[dict[str, int], int]:
    file_obj = ParadoxScriptParser.load(path=registry_path)
    token_to_key: dict[str, int] = {}
    max_name_order = 0
    for node in file_obj.nodes:
        if not isinstance(node, GenericBlock):
            continue
        for candidate in walk_blocks(node):
            if candidate.key not in {"if", "else_if"}:
                continue
            key_values = walk_keyvalues(candidate, "cge_registry_character_key")
            character_values = walk_keyvalues(candidate, "is_character")
            if len(key_values) != 1 or not character_values:
                continue
            try:
                character_key = int(float(scalar(key_values[0])))
            except ValueError:
                continue
            for character_value in character_values:
                token_to_key[scalar(character_value)] = character_key
        for name_order in walk_keyvalues(node, "cge_registry_name_order"):
            try:
                max_name_order = max(max_name_order, int(float(scalar(name_order))))
            except ValueError:
                pass
    return token_to_key, max_name_order


def extract_static_portrait_max(localisation_path: Path) -> int:
    text = localisation_path.read_text(encoding="utf-8-sig", errors="replace")
    values = [int(match.group(1)) for match in re.finditer(r"(?m)^\s*CGE_STATIC_PORTRAIT_(\d+):\d*\s+", text)]
    return max(values, default=0)


def find_registry_chain_container(effect: GenericBlock) -> GenericBlock | None:
    for candidate in walk_blocks(effect):
        direct_branches = [node for node in candidate.nodes if isinstance(node, GenericBlock) and node.key in {"if", "else_if"}]
        matching = 0
        for branch in direct_branches:
            key_values = walk_keyvalues(branch, "cge_registry_character_key")
            character_values = walk_keyvalues(branch, "is_character")
            if len(key_values) == 1 and character_values:
                matching += 1
        if matching >= 2:
            return candidate
    return None


def build_registry_branch(token: str, character_key: int, name_order: int) -> GenericBlock:
    return block(
        "else_if",
        [
            block("limit", [kv("is_character", token)]),
            block("set_variable", [kv("cge_registry_character_key", character_key)]),
            block("set_variable", [kv("cge_registry_name_order", name_order)]),
        ],
    )


def patch_character_registry(cge_mod: Path, output: Path, new_characters: dict[str, int], max_name_order: int) -> None:
    source = cge_mod / "common" / "scripted_effects" / "cge_character_registry.txt"
    target = output / source.relative_to(cge_mod)
    target.parent.mkdir(parents=True, exist_ok=True)
    file_obj = ParadoxScriptParser.load(path=source)
    effect = find_node(file_obj, GenericBlock, "cge_identify_character_on_from_base")
    if effect is None:
        raise RuntimeError("CGE cge_identify_character_on_from_base was not found")
    container = find_registry_chain_container(effect)
    if container is None:
        raise RuntimeError("CGE character registry branch chain was not found")
    insert_at = next((i for i, node in enumerate(container.nodes) if isinstance(node, GenericBlock) and node.key == "else"), len(container.nodes))
    next_name_order = max_name_order + 1
    for token, character_key in sorted(new_characters.items(), key=lambda item: item[1]):
        container.nodes.insert(insert_at, build_registry_branch(token, character_key, next_name_order))
        insert_at += 1
        next_name_order += 1
    file_obj.filepath = target
    file_obj.to_pdx_file()


def build_return_bind_effect(character_key: int, token: str) -> GenericBlock:
    return block(
        f"cge_return_bind_native_key_{character_key}",
        [
            block(
                "if",
                [
                    block("limit", [block("NOT", [kv("has_global_flag", "cge_logic_disabled")])]),
                    block(
                        "every_army_leader",
                        [
                            kv("include_invisible", "yes"),
                            block("limit", [kv("is_unit_leader", "yes"), kv("is_character", token)]),
                            kv("cge_return_bind_current_native", "yes"),
                        ],
                    ),
                ],
            )
        ],
    )


def patch_return_identity_lookup(cge_mod: Path, output: Path, new_characters: dict[str, int]) -> None:
    source = cge_mod / "common" / "scripted_effects" / "cge_return_identity_lookup.txt"
    target = output / source.relative_to(cge_mod)
    target.parent.mkdir(parents=True, exist_ok=True)
    file_obj = ParadoxScriptParser.load(path=source)
    for token, character_key in sorted(new_characters.items(), key=lambda item: item[1]):
        file_obj.nodes.append(build_return_bind_effect(character_key, token))
    file_obj.filepath = target
    file_obj.to_pdx_file()


def check_variable(var: str, value: int, compare: str) -> GenericBlock:
    return block("check_variable", [kv("var", var), kv("value", value), kv("compare", compare)])


def contains_return_identity_checks(candidate: GenericBlock) -> bool:
    return any(scalar(node) == "cge_return_identity_key" for node in walk_keyvalues(candidate, "var"))


def patch_return_effects(cge_mod: Path, output: Path, old_max: int, new_max: int) -> None:
    source = cge_mod / "common" / "scripted_effects" / "cge_return_effects.txt"
    target = output / source.relative_to(cge_mod)
    target.parent.mkdir(parents=True, exist_ok=True)
    file_obj = ParadoxScriptParser.load(path=source)
    patched = 0
    for root in file_obj.nodes:
        if not isinstance(root, GenericBlock):
            continue
        for candidate in walk_blocks(root):
            if candidate.key != "OR" or not contains_return_identity_checks(candidate):
                continue
            if not any(
                scalar(node) == str(old_max)
                for node in walk_keyvalues(candidate, "value")
            ):
                continue
            candidate.nodes.append(
                block(
                    "AND",
                    [
                        check_variable("cge_return_identity_key", old_max, "greater_than"),
                        check_variable("cge_return_identity_key", new_max + 1, "less_than"),
                    ],
                )
            )
            patched += 1
    if patched == 0:
        raise RuntimeError("No CGE return identity range checks were found to extend")
    file_obj.filepath = target
    file_obj.to_pdx_file()


def defined_text_name(node: GenericBlock) -> str | None:
    if node.key != "defined_text":
        return None
    name = find_node(node, GenericKeyValue, "name")
    return scalar(name) if name is not None else None


def static_text_entry(variable: str, character_key: int) -> GenericBlock:
    return block(
        "text",
        [
            block("trigger", [check_variable(variable, character_key, "equals")]),
            kv("localization_key", f"CGE_STATIC_PORTRAIT_{character_key}"),
        ],
    )


def static_router_entry(variable: str, max_key: int, bridge_prefix: str, batch: int) -> GenericBlock:
    return block(
        "text",
        [
            block("trigger", [block("NOT", [check_variable(variable, max_key, "greater_than")])]),
            kv("localization_key", f"{bridge_prefix}_B{batch:02d}"),
        ],
    )


def unknown_text_entry() -> GenericBlock:
    return block("text", [kv("localization_key", "CGE_SPRITE_GFX_leader_unknown")])


def build_static_family(name_prefix: str, bridge_prefix: str, variable: str, max_key: int) -> list[GenericBlock]:
    batch_count = math.ceil(max_key / BATCH_SIZE)
    router_nodes = [kv("name", f"{name_prefix}_ROUTER")]
    for batch in range(1, batch_count + 1):
        router_nodes.append(static_router_entry(variable, min(batch * BATCH_SIZE, max_key), bridge_prefix, batch))
    router_nodes.append(unknown_text_entry())
    result = [block("defined_text", router_nodes)]
    for batch in range(1, batch_count + 1):
        start = (batch - 1) * BATCH_SIZE + 1
        end = min(batch * BATCH_SIZE, max_key)
        nodes = [kv("name", f"{name_prefix}_B{batch:02d}")]
        nodes.extend(static_text_entry(variable, character_key) for character_key in range(start, end + 1))
        nodes.append(unknown_text_entry())
        result.append(block("defined_text", nodes))
    return result


def patch_portrait_resolvers(cge_mod: Path, output: Path, new_max: int) -> None:
    source = cge_mod / "common" / "scripted_localisation" / "cge_portrait_resolvers.txt"
    target = output / source.relative_to(cge_mod)
    target.parent.mkdir(parents=True, exist_ok=True)
    file_obj = ParadoxScriptParser.load(path=source)
    family_prefixes = tuple(f"{family[0]}_" for family in STATIC_FAMILIES)
    retained = []
    for node in file_obj.nodes:
        if isinstance(node, GenericBlock):
            name = defined_text_name(node)
            if name and name.startswith(family_prefixes):
                continue
        retained.append(node)
    file_obj.nodes = retained
    for name_prefix, bridge_prefix, variable in STATIC_FAMILIES:
        file_obj.nodes.extend(build_static_family(name_prefix, bridge_prefix, variable, new_max))
    file_obj.filepath = target
    file_obj.to_pdx_file()


def parse_loc_values(path: Path) -> dict[int, str]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    result = {}
    pattern = re.compile(r'(?m)^\s*CGE_STATIC_PORTRAIT_(\d+):\d*\s+"([^"]*)"')
    for match in pattern.finditer(text):
        result[int(match.group(1))] = match.group(2)
    return result


def write_registry_localisation(cge_mod: Path, output: Path, replacements: dict[int, str]) -> None:
    source = cge_mod / "localisation" / "english" / "cge_registry_l_english.yml"
    target = output / source.relative_to(cge_mod)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    existing = parse_loc_values(source)
    for character_key, sprite in sorted(replacements.items()):
        if character_key in existing:
            pattern = re.compile(rf'(?m)^(\s*CGE_STATIC_PORTRAIT_{character_key}:\d*\s+")[^"]*("\s*)$')
            text, count = pattern.subn(rf'\1{sprite}\2', text, count=1)
            if count != 1:
                raise RuntimeError(f"Could not replace CGE_STATIC_PORTRAIT_{character_key}")
        else:
            if not text.endswith("\n"):
                text += "\n"
            text += f' CGE_STATIC_PORTRAIT_{character_key}:0 "{sprite}"\n'
    target.write_text(text, encoding="utf-8-sig")


def existing_bridge_batches(path: Path, bridge_prefix: str) -> set[int]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    pattern = re.compile(rf'(?m)^\s*{re.escape(bridge_prefix)}_B(\d+):\d*\s+')
    return {int(match.group(1)) for match in pattern.finditer(text)}


def write_bridge_localisation(cge_mod: Path, output: Path, new_max: int) -> bool:
    source = cge_mod / "localisation" / "english" / "cge_resolver_bridge_l_english.yml"
    batch_count = math.ceil(new_max / BATCH_SIZE)
    additions = []
    for name_prefix, bridge_prefix, variable in STATIC_FAMILIES:
        existing = existing_bridge_batches(source, bridge_prefix)
        for batch in range(1, batch_count + 1):
            if batch not in existing:
                additions.append(f' {bridge_prefix}_B{batch:02d}:0 "[{name_prefix}_B{batch:02d}]"')
    if not additions:
        return False
    target = output / source.relative_to(cge_mod)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    if not text.endswith("\n"):
        text += "\n"
    text += "\n".join(additions) + "\n"
    target.write_text(text, encoding="utf-8-sig")
    return True


def sanitize_token(token: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", token)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned[:80] or "character"


def portrait_sprite_for(token: str, portrait: str | None, aliases: dict[str, str], state: BuildState) -> str | None:
    if not portrait:
        state.unresolved_portraits.append(token)
        return None
    value = portrait.strip().strip('"').replace("\\", "/")
    if not value:
        state.unresolved_portraits.append(token)
        return None
    if value.startswith("GFX_"):
        return value
    if "/" in value or value.lower().endswith((".dds", ".tga", ".png")):
        digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:8]
        sprite = f"GFX_CGE_COMPAT_{sanitize_token(token)}_{digest}"
        aliases[sprite] = value
        return sprite
    return value


def write_portrait_gfx(output: Path, aliases: dict[str, str]) -> bool:
    if not aliases:
        return False
    target = output / "interface" / "cge_compat_portraits.gfx"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["spriteTypes = {"]
    for sprite, texture in sorted(aliases.items()):
        safe_texture = texture.replace('"', "")
        lines.extend(
            [
                "\tspriteType = {",
                f'\t\tname = "{sprite}"',
                f'\t\ttexturefile = "{safe_texture}"',
                "\t}",
            ]
        )
    lines.append("}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def is_capture_site_hook(node) -> bool:
    if not isinstance(node, GenericBlock) or node.key != "if":
        return False
    return any(
        candidate.key == "cge_record_capture_site" and scalar(candidate) == "yes"
        for candidate in walk_keyvalues(node)
    )


def build_capture_site_hook() -> GenericBlock:
    return block(
        "if",
        [
            block("limit", [block("NOT", [kv("has_global_flag", "cge_logic_disabled")])]),
            kv("cge_record_capture_site", "yes"),
        ],
    )


def inject_capture_site_before_capture_by(scope: GenericBlock) -> int:
    inserted = 0
    index = 0
    while index < len(scope.nodes):
        node = scope.nodes[index]
        if isinstance(node, GenericKeyValue) and node.key == "capture_by" and scalar(node) == "FROM":
            already_present = index > 0 and is_capture_site_hook(scope.nodes[index - 1])
            if not already_present:
                scope.nodes.insert(index, build_capture_site_hook())
                inserted += 1
                index += 1
        elif isinstance(node, GenericBlock):
            inserted += inject_capture_site_before_capture_by(node)
        index += 1
    return inserted


def patch_source_capture_site_on_actions(source_mod: Path, output: Path, state: BuildState) -> tuple[list[str], int]:
    on_actions_dir = source_mod / "common" / "on_actions"
    if not on_actions_dir.is_dir():
        state.warnings.append("Target mod has no common/on_actions directory.")
        return [], 0
    patched_files = []
    total_inserted = 0
    for path in sorted(on_actions_dir.rglob("*.txt"), key=lambda p: str(p).lower()):
        try:
            file_obj = ParadoxScriptParser.load(path=path)
        except Exception as exc:
            state.parser_failures.append(f"{path}: {exc}")
            continue
        inserted = 0
        for root in file_obj.nodes:
            if not isinstance(root, GenericBlock) or root.key != "on_actions":
                continue
            for candidate in walk_blocks(root):
                if candidate.key == "on_deployed_leader_defeated":
                    inserted += inject_capture_site_before_capture_by(candidate)
        if inserted <= 0:
            continue
        relative = path.relative_to(source_mod)
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        file_obj.filepath = target
        file_obj.to_pdx_file()
        patched_files.append(relative.as_posix())
        total_inserted += inserted
    if total_inserted == 0:
        state.warnings.append("No compatible capture-site hook was found in target on_actions.")
    return patched_files, total_inserted


def descriptor_replace_paths(mod_path: Path) -> list[str]:
    descriptor = mod_path / "descriptor.mod"
    if not descriptor.is_file():
        return []
    text = descriptor.read_text(encoding="utf-8-sig", errors="replace")
    values = []
    for match in re.finditer(r'(?m)^\s*replace_path\s*=\s*"([^"]+)"', text):
        value = match.group(1).strip().replace("\\", "/").strip("/")
        if value and value not in values:
            values.append(value)
    return values


def path_is_under(relative: Path, replace_path: str) -> bool:
    rel = relative.as_posix().strip("/")
    root = replace_path.strip("/")
    return rel == root or rel.startswith(root + "/")


def restore_cge_files_hidden_by_replace_paths(source_mod: Path, cge_mod: Path, output: Path, replace_paths: list[str]) -> tuple[list[str], list[str]]:
    restored = []
    collisions = []
    if not replace_paths:
        return restored, collisions
    for path in sorted(cge_mod.rglob("*"), key=lambda p: str(p).lower()):
        if not path.is_file():
            continue
        relative = path.relative_to(cge_mod)
        if relative.as_posix() == "descriptor.mod":
            continue
        if not any(path_is_under(relative, replace_path) for replace_path in replace_paths):
            continue
        target = output / relative
        if target.exists():
            continue
        source_counterpart = source_mod / relative
        if source_counterpart.exists():
            collisions.append(relative.as_posix())
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        restored.append(relative.as_posix())
    return restored, collisions

def descriptor_value(mod_path: Path, key: str) -> str | None:
    descriptor = mod_path / "descriptor.mod"
    if not descriptor.is_file():
        return None
    text = descriptor.read_text(encoding="utf-8-sig", errors="replace")
    match = re.search(rf'(?m)^\s*{re.escape(key)}\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else None


def descriptor_lines(name: str, cge_name: str, source_name: str, supported_version: str | None) -> list[str]:
    lines = [f'name="{name}"', 'tags={', '\t"Gameplay"', '}', 'dependencies={', f'\t"{cge_name}"', f'\t"{source_name}"', '}']
    if supported_version:
        lines.append(f'supported_version="{supported_version}"')
    return lines


def write_descriptor(output: Path, name: str, cge_name: str, source_name: str, supported_version: str | None) -> None:
    lines = descriptor_lines(name, cge_name, source_name, supported_version)
    (output / "descriptor.mod").write_text("\n".join(lines) + "\n", encoding="utf-8")


def default_launcher_mod_dir() -> Path:
    home = Path.home()
    if sys.platform.startswith("linux"):
        return home / ".local" / "share" / "Paradox Interactive" / "Hearts of Iron IV" / "mod"
    return home / "Documents" / "Paradox Interactive" / "Hearts of Iron IV" / "mod"


def launcher_filename(output: Path) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", output.name).strip("._")
    return f"{name or 'CGE_Compatibility'}.mod"


def write_launcher_descriptor(output: Path, launcher_mod_dir: Path, name: str, cge_name: str, source_name: str, supported_version: str | None) -> Path:
    launcher_mod_dir.mkdir(parents=True, exist_ok=True)
    target = launcher_mod_dir / launcher_filename(output)
    lines = descriptor_lines(name, cge_name, source_name, supported_version)
    output_path = output.as_posix().replace('"', '')
    lines.append(f'path="{output_path}"')
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_character_hash(source_mod: Path) -> str:
    digest = hashlib.sha256()
    directory = source_mod / "common" / "characters"
    for path in sorted(directory.rglob("*.txt"), key=lambda p: str(p).lower()):
        digest.update(str(path.relative_to(source_mod)).replace("\\", "/").encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_paths(source_mod: Path, cge_mod: Path) -> None:
    required = [
        cge_mod / "common" / "scripted_effects" / "cge_character_registry.txt",
        cge_mod / "common" / "scripted_effects" / "cge_return_identity_lookup.txt",
        cge_mod / "common" / "scripted_effects" / "cge_return_effects.txt",
        cge_mod / "common" / "scripted_localisation" / "cge_portrait_resolvers.txt",
        cge_mod / "localisation" / "english" / "cge_registry_l_english.yml",
        cge_mod / "localisation" / "english" / "cge_resolver_bridge_l_english.yml",
        source_mod / "common" / "characters",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Missing required paths:\n" + "\n".join(missing))


def prepare_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()):
        if not force:
            raise RuntimeError(f"Output folder is not empty: {output}. Use --force to replace it.")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)


def build(args) -> dict:
    source_mod = Path(args.source_mod).expanduser().resolve()
    cge_mod = Path(args.cge_mod).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    validate_paths(source_mod, cge_mod)
    prepare_output(output, args.force)
    source_replace_paths = descriptor_replace_paths(source_mod)
    restored_replace_path_files, replace_path_collisions = restore_cge_files_hidden_by_replace_paths(
        source_mod, cge_mod, output, source_replace_paths
    )
    state = BuildState()
    capture_site_on_action_files, capture_site_hooks_inserted = patch_source_capture_site_on_actions(
        source_mod, output, state
    )
    characters = scan_source_characters(source_mod, state)
    registry_path = cge_mod / "common" / "scripted_effects" / "cge_character_registry.txt"
    registry_loc_path = cge_mod / "localisation" / "english" / "cge_registry_l_english.yml"
    token_to_key, max_name_order = extract_cge_registry(registry_path)
    static_max = extract_static_portrait_max(registry_loc_path)
    old_max = max(max(token_to_key.values(), default=0), static_max)
    new_characters: dict[str, int] = {}
    mapping: dict[str, int] = {}
    next_key = old_max + 1
    for token in sorted(characters, key=str.casefold):
        if token in token_to_key:
            mapping[token] = token_to_key[token]
        else:
            mapping[token] = next_key
            new_characters[token] = next_key
            next_key += 1
    new_max = max(old_max, max(mapping.values(), default=old_max))
    aliases: dict[str, str] = {}
    replacements: dict[int, str] = {}
    character_report = {}
    for token in sorted(characters, key=str.casefold):
        info = characters[token]
        character_key = mapping[token]
        sprite = portrait_sprite_for(token, info.portrait, aliases, state)
        existing_character = token in token_to_key
        if sprite is not None:
            replacements[character_key] = sprite
        elif not existing_character:
            replacements[character_key] = "GFX_leader_unknown"
        character_report[token] = {
            "key": character_key,
            "new_key": not existing_character,
            "portrait_source": info.portrait,
            "portrait_sprite": replacements.get(character_key),
            "has_army_role": info.has_army_role,
            "source_files": info.source_files,
        }
    if new_characters:
        patch_character_registry(cge_mod, output, new_characters, max_name_order)
        patch_return_identity_lookup(cge_mod, output, new_characters)
        patch_return_effects(cge_mod, output, old_max, new_max)
        patch_portrait_resolvers(cge_mod, output, new_max)
    write_registry_localisation(cge_mod, output, replacements)
    bridge_written = write_bridge_localisation(cge_mod, output, new_max) if new_characters else False
    gfx_written = write_portrait_gfx(output, aliases)
    source_name = descriptor_value(source_mod, "name") or source_mod.name
    cge_name = "Captured Generals Expanded"
    submod_name = args.submod_name or f"{cge_name} - {source_name} Compatibility"
    supported_version = args.supported_version or descriptor_value(source_mod, "supported_version") or descriptor_value(cge_mod, "supported_version")
    write_descriptor(output, submod_name, cge_name, source_name, supported_version)
    launcher_mod_dir = default_launcher_mod_dir()
    launcher_descriptor = write_launcher_descriptor(output, launcher_mod_dir, submod_name, cge_name, source_name, supported_version)
    cge_files = [
        cge_mod / "common" / "scripted_effects" / "cge_character_registry.txt",
        cge_mod / "common" / "scripted_effects" / "cge_return_identity_lookup.txt",
        cge_mod / "common" / "scripted_effects" / "cge_return_effects.txt",
        cge_mod / "common" / "scripted_localisation" / "cge_portrait_resolvers.txt",
        cge_mod / "localisation" / "english" / "cge_registry_l_english.yml",
        cge_mod / "localisation" / "english" / "cge_resolver_bridge_l_english.yml",
    ]
    manifest = {
        "submod_name": submod_name,
        "source_mod_name": source_name,
        "cge_mod_name": cge_name,
        "source_character_hash": source_character_hash(source_mod),
        "cge_input_hashes": {str(path.relative_to(cge_mod)).replace("\\", "/"): sha256_file(path) for path in cge_files},
        "old_static_key_max": old_max,
        "new_static_key_max": new_max,
        "characters_scanned": len(characters),
        "existing_cge_characters_updated": sum(1 for token in characters if token in token_to_key and mapping[token] in replacements),
        "new_cge_characters_registered": len(new_characters),
        "portrait_aliases_generated": len(aliases),
        "bridge_localisation_extended": bridge_written,
        "portrait_gfx_generated": gfx_written,
        "launcher_descriptor": str(launcher_descriptor) if launcher_descriptor else None,
        "source_replace_paths": source_replace_paths,
        "cge_files_restored_after_replace_path": restored_replace_path_files,
        "replace_path_collisions_requiring_manual_merge": replace_path_collisions,
        "capture_site_on_action_files_patched": capture_site_on_action_files,
        "capture_site_hooks_inserted": capture_site_hooks_inserted,
        "warnings": state.warnings,
        "duplicate_tokens": sorted(set(state.duplicate_tokens), key=str.casefold),
        "ambiguous_portraits": state.ambiguous_portraits,
        "unresolved_portraits": sorted(set(state.unresolved_portraits), key=str.casefold),
        "parser_failures": state.parser_failures,
        "characters": character_report,
    }
    (output / "cge_compat_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Generate a CGE compatibility submod.")
    result.add_argument("--source-mod", required=True, help="Target mod path.")
    result.add_argument("--cge-mod", required=True, help="CGE mod path.")
    result.add_argument("--output", required=True, help="Output submod path.")
    result.add_argument("--submod-name", help="Generated submod display name.")
    result.add_argument("--supported-version", help="HOI4 supported_version value.")
    result.add_argument("--force", action="store_true", help="Replace a non-empty output folder.")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        manifest = build(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"Generated: {Path(args.output).expanduser().resolve()}")
    print(f"Characters scanned: {manifest['characters_scanned']}")
    print(f"Existing CGE characters with portrait updates: {manifest['existing_cge_characters_updated']}")
    print(f"New CGE characters registered: {manifest['new_cge_characters_registered']}")
    print(f"Portrait aliases generated: {manifest['portrait_aliases_generated']}")
    if manifest["launcher_descriptor"]:
        print(f"Launcher descriptor: {manifest['launcher_descriptor']}")
    if manifest["source_replace_paths"]:
        print(f"Source replace_path entries detected: {len(manifest['source_replace_paths'])}")
        print(f"CGE files restored after replace_path: {len(manifest['cge_files_restored_after_replace_path'])}")
    if manifest["replace_path_collisions_requiring_manual_merge"]:
        print(f"replace_path collisions requiring manual merge: {len(manifest['replace_path_collisions_requiring_manual_merge'])}")
    if manifest["capture_site_hooks_inserted"]:
        print(f"Capture-site hooks merged into target on_actions: {manifest['capture_site_hooks_inserted']}")
    if manifest["warnings"]:
        print(f"Compatibility warnings: {len(manifest['warnings'])}")
        for warning in manifest["warnings"]:
            print(f"WARNING: {warning}")
    if manifest["ambiguous_portraits"]:
        print(f"Characters with multiple portrait variants: {len(manifest['ambiguous_portraits'])}")
    if manifest["unresolved_portraits"]:
        print(f"Characters without a resolvable portrait: {len(manifest['unresolved_portraits'])}")
    if manifest["parser_failures"]:
        print(f"Character files that could not be parsed: {len(manifest['parser_failures'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
