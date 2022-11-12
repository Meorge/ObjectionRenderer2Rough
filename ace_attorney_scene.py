from MovieKit import Scene, SceneObject, ImageObject, MoveSceneObjectAction, \
    SetSceneObjectPositionAction, WaitAction, SetImageObjectSpriteAction, \
        SimpleTextObject, SequenceAction, RunFunctionAction, Director
from math_helpers import ease_in_out_cubic
from PIL import Image, ImageDraw, ImageFont
from parse_tags import DialoguePage, get_rich_boxes, DialogueTextChunk
from font_tools import get_best_font
from font_constants import TEXT_COLORS, FONT_ARRAY
from typing import Callable

class NameBox(SceneObject):
    def __init__(self, parent: SceneObject, pos: tuple[int, int, int]):
        super().__init__(parent, "Name Box", pos)
        self.namebox_l = ImageObject(
            parent=self,
            name="Name Box Left",
            pos=(0, 0, 11),
            filepath="new_assets/textbox/nametag_left.png"
        )
        self.namebox_c = ImageObject(
            parent=self,
            name="Name Box Center",
            pos=(1, 0, 11),
            filepath="new_assets/textbox/nametag_center.png"
        )
        self.namebox_r = ImageObject(
            parent=self,
            name="Name Box Right",
            pos=(2, 0, 11),
            filepath="new_assets/textbox/nametag_right.png"
        )
        self.namebox_text = SimpleTextObject(
            parent=self,
            name="Name Box Text",
            pos=(4, 0, 12)
        )

        self.font = ImageFont.truetype("new_assets/textbox/font/ace-name/ace-name.ttf", size=8)
        self.namebox_text.font = self.font
        self.set_text("Phoenix")
    
    def set_text(self, text: str):
        self.text = text
        self.namebox_text.text = self.text

    def update(self, delta):
        length = int(self.font.getlength(self.text))
        self.namebox_c.width = length + 4
        self.namebox_r.x = 1 + length + 4

class DialogueBox(SceneObject):
    time: float = 0
    def __init__(self, parent: SceneObject, director: 'AceAttorneyDirector'):
        super().__init__(
            parent=parent,
            name="Dialogue Box",
            pos=(0, 128, 12)
        )
        self.director = director
        self.bg = ImageObject(
            parent=self,
            name="Dialogue Box Background",
            pos=(0, 0, 10),
            filepath="new_assets/textbox/mainbox.png"
        )
        self.namebox = NameBox(parent=self, pos=(1, -11, 0))
        self.arrow = ImageObject(
            parent=self,
            name="Dialogue Box Arrow",
            pos=(256 - 15 - 5, 64 - 15 - 5, 11),
            filepath="new_assets/textbox/arrow.gif"
        )
        self.arrow.visible = False

        self.page: DialoguePage = None

        self.use_rtl = False
        self.font_size = 16
        self.time = 0.0

        self.on_complete: Callable[[], None] = None

    def set_page(self, page: DialoguePage, character_name: str, on_complete: Callable[[], None] = None):
        self.reset()
        self.namebox.set_text(character_name)
        self.page = page
        self.font_data = get_best_font(self.page.get_raw_text(), FONT_ARRAY)
        self.font = ImageFont.truetype(self.font_data["path"], self.font_size)
        self.on_complete = on_complete
        self.visible = True

    def reset(self, hide_box: bool = True):
        self.page = None
        self.time_on_completed = 0.0
        self.time = 0

    def get_num_visible_chars(self):
        return int(self.time * 20)

    def get_all_done(self):
        if self.page is None:
            return False
        full_text_len = len(self.page.get_raw_text())
        visible_text_len = len(self.page.get_visible_text(self.get_num_visible_chars()).get_raw_text())
        return full_text_len == visible_text_len

    def handle_tags(self):
        for tag in self.last_latest_chunk_tags:
            tag_parts = tag.split()
            if tag_parts[0] == "sprite":
                self.handle_switch_sprite_tag(tag_parts[1], tag_parts[2])

    def handle_switch_sprite_tag(self, position: str, new_path: str):
        if position == "left":
            print(f"Left sprite should become {new_path}")
            self.director.phoenix.set_filepath(new_path)

        elif position == "right":
            print(f"Right sprite should become {new_path}")
            self.director.edgeworth.set_filepath(new_path)

    last_latest_chunk_tags: list[str] = None
    def update(self, delta):
        self.time += delta

        self.arrow.visible = False
        if self.get_all_done():
            self.arrow.visible = True
            self.time_on_completed += delta
            if self.time_on_completed >= 1.0:
                self.reset()
                if self.on_complete is not None:
                    self.emit_message("box be done")
                    self.on_complete()
                else:
                    print(f"Text box for \"{self.page.get_raw_text()}\" is done but no on_complete")

            return
        
        if self.page is None:
            return

        # Check for actions on current chunk
        text_so_far = self.page.get_visible_text(self.get_num_visible_chars())
        try:
            latest_chunk_tags = text_so_far.lines[-1][-1].tags
            if latest_chunk_tags != self.last_latest_chunk_tags:
                print(f"Latest chunk changed to {latest_chunk_tags}")
                self.last_latest_chunk_tags = latest_chunk_tags
                self.handle_tags()
        except IndexError as e:
            print(f"{e}")
            

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        if self.page is None:
            return
        _text = self.page.get_visible_text(self.get_num_visible_chars())
        for line_no, line in enumerate(_text.lines):
            x_offset = 220 if self.use_rtl else 0
            for chunk_no, chunk in enumerate(line):
                drawing_args = {
                    "xy": (10 + self.x + x_offset, 4 + self.y + (self.font_size) * line_no),
                    "text": chunk.text,
                    "fill": (255,0,255),
                    "anchor": ("r" if self.use_rtl else "l") + "a"
                }

                if len(chunk.tags) == 0:
                    drawing_args["fill"] = (255,255,255)
                else:
                    drawing_args["fill"] = TEXT_COLORS.get(chunk.tags[-1], (255,255,255))

                if self.font is not None:
                    drawing_args["font"] = self.font

                ctx.text(**drawing_args)

                try:
                    add_to_x_offset = ctx.textlength(chunk.text, font=self.font)
                    if chunk_no < len(line) - 1:
                        next_char = line[chunk_no + 1].text[0]
                        add_to_x_offset = ctx.textlength(chunk.text + next_char, self.font) - ctx.textlength(next_char, self.font)
                except UnicodeEncodeError:
                    add_to_x_offset = self.font.getsize(chunk.text)[0]

                x_offset += (add_to_x_offset * -1) if self.use_rtl else add_to_x_offset

class DisplayTextInTextBoxAction(SequenceAction):
    def __init__(self, tb: DialogueBox, character_name: str, page: DialoguePage):
        self.tb = tb
        self.character_name = character_name
        self.page = page

    def start(self):
        self.tb.set_page(self.page, self.character_name, self.sequencer.action_finished)

    def update(self, delta):
        if self.tb.time_on_completed >= 1:
            self.sequencer.action_finished()

class AceAttorneyDirector(Director):
    def __init__(self, fps: float = 30):
        super().__init__(None, fps)

        self.root = SceneObject(name="Root")

        self.bg = ImageObject(
            parent=self.root,
            name="Background",
            pos=(0, 0, 0),
            filepath="new_assets/bg/bg_main.png"
            )

        self.phoenix = ImageObject(
            parent=self.bg,
            name="Left Character",
            pos=(0, 0, 1),
            filepath="new_assets/character_sprites/phoenix/phoenix-normal-idle.gif"
            )

        self.edgeworth = ImageObject(
            parent=self.bg,
            name="Right Character",
            pos=(1034, 0, 2),
            filepath="new_assets/character_sprites/edgeworth/edgeworth-normal-idle.gif"
            )

        self.textbox = DialogueBox(parent=self.root, director=self)

        self.scene = Scene(256, 192, self.root)


    def text_box(self, speaker: str, body: str):
        for box in get_rich_boxes(body):
            self.sequencer.add_action(
                DisplayTextInTextBoxAction(
                    self.textbox,
                    speaker,
                    box
                )
            ) 

    def show_text_box(self):
        self.sequencer.add_action(RunFunctionAction(lambda: self.textbox.show()))

    def hide_text_box(self):
        self.sequencer.add_action(RunFunctionAction(lambda: self.textbox.hide()))

    def pan_to_right(self):
        self.sequencer.add_action(
                MoveSceneObjectAction(
                target_value=(-1290 + 256, 0),
                duration=1.0,
                scene_object=self.bg,
                ease_function=ease_in_out_cubic
            )
        )

    def pan_to_left(self):
        self.sequencer.add_action(
                MoveSceneObjectAction(
                target_value=(0, 0),
                duration=1.0,
                scene_object=self.bg,
                ease_function=ease_in_out_cubic
            )
        )

    def cut_to_left(self):
        self.sequencer.add_action(SetSceneObjectPositionAction(target_value=(0, 0), scene_object=self.bg))

    def cut_to_right(self):
        self.sequencer.add_action(SetSceneObjectPositionAction(target_value=(-1920 + 256, 0), scene_object=self.bg))

    def wait(self, t):
        self.sequencer.add_action(
            WaitAction(0.5)
        )

    def set_left_character_sprite(self, path):
        self.sequencer.add_action(
            SetImageObjectSpriteAction(new_filepath=path, image_object=self.phoenix)
        )

def get_sprite_location(character: str, emotion: str):
    return f"new_assets/character_sprites/{character}/{character}-{emotion}.gif"

def get_sprite_tag(location: str, character: str, emotion: str):
    return f"<sprite {location} {get_sprite_location(character, emotion)}/>"

director = AceAttorneyDirector()
director.text_box("Phoenix", f"{get_sprite_tag('left', 'phoenix', 'normal-talk')}Hello world{get_sprite_tag('left', 'phoenix', 'normal-idle')}")
# director.text_box("Phoenix", f"{get_sprite_tag('left', 'phoenix', 'normal-talk')}Hi here's a <green>bunch of text</green> also {get_sprite_tag('left', 'phoenix', 'sweating-talk')}<red>maybe the rich text is breaking again</red>{get_sprite_tag('left', 'phoenix', 'sweating-idle')}???")
director.hide_text_box()
# director.pan_to_right()
# director.show_text_box()
# director.text_box("Edgeworth", f"{get_sprite_tag('right', 'edgeworth', 'normal-talk')}hey its me, mr edge worth uhhhhh updated autopsy report{get_sprite_tag('right', 'edgeworth', 'normal-idle')}.")
# director.hide_text_box()
# director.wait(0.5)
# director.set_left_character_sprite(get_sprite_location('phoenix', 'sweating-idle'))
# director.pan_to_left()
# director.wait(0.5)
# director.text_box("Phoenix", f"{get_sprite_tag('left', 'phoenix', 'sweating-talk')}cool great thanks im so happy{get_sprite_tag('left', 'phoenix', 'sweating-idle')}.")
# director.hide_text_box()
director.render_movie()
