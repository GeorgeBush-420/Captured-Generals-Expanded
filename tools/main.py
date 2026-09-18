from pathlib import Path
import re

from ParadoxParser import ParadoxScriptParser
from ParadoxParser.ParadoxNodes import GenericBlock, GenericKeyValue, GenericString, GenericComment, GenericComparator, GenericToken
from ParadoxParser.queries import find_node, find_nodes, all_nodes

#### EDIT these
SOURCE_MOD_FOLDER = "/mnt/RAID/Projects/extremis-ultimis-dev/eu"
COMPAT_PATH_FOLDER = "/mnt/RAID/Projects/extremis-ultimis-dev/CGE-Patch"

#DO NOT TOUCH
SOURCE_MOD = Path(SOURCE_MOD_FOLDER)
PATCH_MOD = Path(COMPAT_PATH_FOLDER)

CHARACTER_FILES = dict()
CHARACTERS = list()
PORTRAITS = dict()

def get_portrait(block):
    for portrait_b in all_nodes(block, GenericBlock, "portraits"):
        for army_portraits_b in all_nodes(portrait_b, GenericBlock, "army"):
            return find_node(army_portraits_b, GenericKeyValue, "large")

def build_portrait_icon(name, texture):
    icon = GenericBlock("sprtitetype")
    icon_name = GenericKeyValue("name", GenericString(name))
    icon_path = GenericKeyValue("texturefile", GenericString(texture))
    icon.nodes = [icon_name, icon_path]
    return icon


def build_character_trigger(characters):
    def get_character_check_individual(char):
        return GenericBlock("check_variable",
                            [GenericComparator(
                                GenericToken("selected_character"),
                                "=",
                                GenericToken(f"token:{char}")
                            )])

    return GenericBlock("character_not_generic",
                        [GenericBlock("OR",
                                      [get_character_check_individual(char) for char in characters]
                        )])
#main block
if __name__ == "__main__":
    for file in (SOURCE_MOD / "common" / "characters").iterdir():
        if file.is_file():
            file_change_counter = 0 
            file_obj = ParadoxScriptParser.load(file)
            file_obj.filepath = PATCH_MOD / "common" / "characters" / file_obj.filename
            CHARACTER_FILES[file.name] = file_obj

            #overwrite (storing paths)
            if not (len(file_obj.nodes) >= 1 and file_obj.nodes[0].key == "characters"):
                CHARACTER_FILES.pop(file.name)
                print(f"{file.name} is not a character file?")
                continue

            block = file_obj.nodes[0]
            actual_portrait = None
            for node in block.nodes:
                if isinstance(node, GenericComment):
                    continue
                char_name = node.key
                CHARACTERS.append(char_name)
                instances = find_nodes(node, GenericBlock, "instance")
                if instances:
                    portrait_kv = get_portrait(instances)
                else:
                    portrait_kv = get_portrait(node)

                if portrait_kv:
                    file_change_counter =+ 1
                    portrait_path = portrait_kv.get_value()
                    portrait_key = f"{char_name}_portrait"
                    portrait_kv.value.value = portrait_key
                    PORTRAITS[portrait_key] = portrait_path
            if file_change_counter > 0:
                file_obj.to_pdx_file()

    sprite_file_nodes = GenericBlock("spritetypes")
    for key, value in PORTRAITS.items():
        icon = build_portrait_icon(key, value)
        sprite_file_nodes.nodes.append(icon)

    icon_file_path = PATCH_MOD / "interface" / "portrait_icons.gfx"
    icon_file = ParadoxScriptParser.create( path = icon_file_path, nodes = sprite_file_nodes)
    icon_file.to_pdx_file()

    character_trigger = build_character_trigger(CHARACTERS)
    character_trigger_path = PATCH_MOD / "common" / "scripted_triggers" / "CGE_scripted_triggers.txt"
    trigger_file = ParadoxScriptParser.create(path=character_trigger_path, nodes = character_trigger)
    trigger_file.to_pdx_file()

    # #reformat trigger file
    text = trigger_file.filepath.read_text(encoding="UTF-8")

    text = re.sub(
        r"(?m)^([ \t]*)check_variable = \{\n"
        r"[ \t]+selected_character = (token:[^\n]+)\n"
        r"[ \t]*\}",
        r"\1check_variable = { selected_character = \2 }",
        text,
    )

    trigger_file.filepath.write_text(text, encoding="UTF-8")
