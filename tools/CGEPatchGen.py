from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget, QLabel, QFileDialog
import re

from ParadoxParser import ParadoxScriptParser
from ParadoxParser.ParadoxNodes import GenericBlock, GenericKeyValue, GenericString, GenericComment, GenericComparator, GenericToken, GenericNode
from ParadoxParser.queries import find_node, find_nodes, all_nodes


CHARACTER_FILES = dict()
CHARACTERS = list()
PORTRAITS = dict()

class QPathInputWithButton(QWidget):
    def __init__(self):
        super().__init__()
        self.element = QHBoxLayout(self)
        self.element_text = QLineEdit()
        self.element_button = QPushButton("...")
        self.element_button.clicked.connect(self._browse_path)
        self.element.addWidget(self.element_text)
        self.element.addWidget(self.element_button)

    def _browse_path(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        filepath = QFileDialog.getExistingDirectory(
            self, "Select Paradox Game install directory", "", QFileDialog.ShowDirsOnly
        )
        self.element_text.setText(filepath)

    def get_value(self):
        return Path(self.element_text.text())

class PathSelectors(QMainWindow):
    def __init__(self):
        super().__init__()
    
        self.setWindowTitle("CGE Patch Builder")
        self.resize(550, 150)
        # self.setLayout(QFormLayout())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.form = QFormLayout(central_widget)

        self.source_mod_path = QPathInputWithButton()
        self.form.addRow("source mod path:", self.source_mod_path)

        self.compat_mod_path = QPathInputWithButton()
        self.form.addRow("patch mod path:", self.compat_mod_path)

        self.continue_button = QPushButton("Continue")
        # self.continue_button.clicked.connect(self._submit)
        self.form.addRow(self.continue_button)

    def _submit(self):
        self.source_mod_path = Path(self.source_mod_path.get_value())
        self.patch_mod_path = Path(self.compat_mod_path.get_value())

        def _get_portrait(block:GenericBlock)-> GenericNode:
            for portrait_b in all_nodes(block, GenericBlock, "portraits"):
                for army_portraits_b in all_nodes(portrait_b, GenericBlock, "army"):
                    return find_node(army_portraits_b, GenericKeyValue, "large")

        def _build_portrait_icon(name:str, texture:str) -> GenericBlock:
            icon = GenericBlock("spritetype")
            icon_name = GenericKeyValue("name", GenericString(f"GFX_{name}"))
            icon_path = GenericKeyValue("texturefile", GenericString(texture))
            icon.nodes = [icon_name, icon_path]
            return icon

        def _build_character_trigger(characters:list) -> GenericBlock:
            def _get_character_check_individual(char:str) -> GenericBlock:
                return GenericBlock("check_variable",
                                    [GenericComparator(
                                        GenericToken("selected_character"),
                                        "=",
                                        GenericToken(f"token:{char}")
                                    )])

            return GenericBlock("character_not_generic",
                                [GenericBlock("OR",
                                            [_get_character_check_individual(char) for char in characters]
                                )])

        def _build_descriptor(source_mod:Path, path_mod:Path) -> ParadoxScriptParser:
            source_descriptor = ParadoxScriptParser.load(source_mod / "descriptor.mod")
            source_mod_name = find_node(source_descriptor, GenericKeyValue, "name").get_value()

            return  ParadoxScriptParser.create(path_mod / "descriptor.mod",
                                                [GenericKeyValue("version", GenericString("1.0.0")),
                                                    GenericBlock("tags", [
                                                        GenericString("Gameplay"), 
                                                        GenericString("Utilities")
                                                    ]),
                                                    GenericKeyValue("name", GenericString(f"{source_mod_name} - CGE Patch")),
                                                    GenericBlock("dependencies",
                                                                [
                                                                    GenericString("Captured Generals Expanded"),
                                                                    GenericString(source_mod_name)
                                                                ]),
                                                    GenericKeyValue("picture", "thumbnail.png"),
                                                    GenericKeyValue("supported_version", GenericString("1.19.*"))
                                                    ])

        for file in (self.source_mod_path / "common" / "characters").iterdir():
            if file.is_file():
                file_change_counter = 0 
                file_obj = ParadoxScriptParser.load(file)
                file_obj.filepath = self.patch_mod_path / "common" / "character" / file_obj.filename
                CHARACTER_FILES[file.name] = file_obj

                for block in file_obj.nodes:
                    if isinstance(block, GenericBlock) and block.key == "characters":
                        for node in block.nodes:
                            char_name = node.key
                            CHARACTERS.append(char_name)
                            portrait_kv = _get_portrait(node)
                            if portrait_kv:
                                file_change_counter =+1
                                portrait_path = portrait_kv.get_value()
                                portrait_key = f"GFX_{char_name}_portrait"
                                portrait_kv.value.value = GenericToken(portrait_key)
                                PORTRAITS[portrait_key] = portrait_path
                        if file_change_counter > 0:
                            file_obj.to_pdx_file()
                            print(f"{file_obj.filepath} saved.")

            sprite_file_nodes = GenericBlock("spritetypes")
            for key, value in PORTRAITS.items():
                icon = _build_portrait_icon(key, value)
                sprite_file_nodes.nodes.append(icon)

            icon_file_path = self.patch_mod_path / "interface" / "portrait_icons.gfx"
            icon_file = ParadoxScriptParser.create( path = icon_file_path, nodes = sprite_file_nodes)
            icon_file.to_pdx_file()

            character_trigger = _build_character_trigger(CHARACTERS)
            character_trigger_path = self.patch_mod_path / "common" / "scripted_triggers" / "CGE_scripted_triggers.txt"
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

            descriptor_file = _build_descriptor(self.source_mod_path, self.compat_mod_path)
            descriptor_file.to_pdx_file()

app = QApplication([])
window = PathSelectors()
window.show()
app.exec_()