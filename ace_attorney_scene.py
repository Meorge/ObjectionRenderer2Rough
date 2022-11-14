from MovieKit import (
    Scene,
    SceneObject,
    ImageObject,
    MoveSceneObjectAction,
    SetSceneObjectPositionAction,
    WaitAction,
    SetImageObjectSpriteAction,
    SimpleTextObject,
    SequenceAction,
    RunFunctionAction,
    Director,
)
from math_helpers import ease_in_out_cubic
from PIL import Image, ImageDraw, ImageFont
from parse_tags import DialoguePage, get_rich_boxes, DialogueTextChunk
from font_tools import get_best_font
from font_constants import TEXT_COLORS, FONT_ARRAY
from typing import Callable, Optional
from os.path import exists

class NameBox(SceneObject):
    def __init__(self, parent: SceneObject, pos: tuple[int, int, int]):
        super().__init__(parent, "Name Box", pos)
        self.namebox_l = ImageObject(
            parent=self,
            name="Name Box Left",
            pos=(0, 0, 11),
            filepath="new_assets/textbox/nametag_left.png",
        )
        self.namebox_c = ImageObject(
            parent=self,
            name="Name Box Center",
            pos=(1, 0, 11),
            filepath="new_assets/textbox/nametag_center.png",
        )
        self.namebox_r = ImageObject(
            parent=self,
            name="Name Box Right",
            pos=(2, 0, 11),
            filepath="new_assets/textbox/nametag_right.png",
        )
        self.namebox_text = SimpleTextObject(
            parent=self, name="Name Box Text", pos=(4, 0, 12)
        )

        self.font = ImageFont.truetype(
            "new_assets/textbox/font/ace-name/ace-name.ttf", size=8
        )
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

    chars_visible: int = 0
    current_char_time: float = 0.0
    max_current_char_time: float = 1 / 30

    current_wait_time: float = 0.0
    max_wait_time: float = 0.0

    def __init__(self, parent: SceneObject, director: "AceAttorneyDirector"):
        super().__init__(parent=parent, name="Dialogue Box", pos=(0, 128, 12))
        self.director = director
        self.bg = ImageObject(
            parent=self,
            name="Dialogue Box Background",
            pos=(0, 0, 10),
            filepath="new_assets/textbox/mainbox.png",
        )
        self.namebox = NameBox(parent=self, pos=(1, -11, 0))
        self.arrow = ImageObject(
            parent=self,
            name="Dialogue Box Arrow",
            pos=(256 - 15 - 5, 64 - 15 - 5, 11),
            filepath="new_assets/textbox/arrow.gif",
        )
        self.arrow.visible = False

        self.page: DialoguePage = None

        self.use_rtl = False
        self.font_size = 16

        self.chars_visible = 0
        self.current_char_time = 0

        self.on_complete: Callable[[], None] = None

    def set_page(
        self,
        page: DialoguePage,
        character_name: str,
        on_complete: Callable[[], None] = None,
    ):
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

        self.chars_visible = 0
        self.current_char_time = 0

    def get_all_done(self):
        if self.page is None:
            return False

        full_text = self.page.get_raw_text()
        visible_text_chunks = self.page.get_visible_text(self.chars_visible)
        visible_text = visible_text_chunks.get_raw_text()
        full_text_len = len(full_text)
        visible_text_len = len(visible_text)
        return full_text_len == visible_text_len

    def handle_tags(self):
        for tag in self.last_latest_chunk_tags:
            tag_parts = tag.split()
            if tag_parts[0] == "sprite":
                self.handle_switch_sprite_tag(tag_parts[1], tag_parts[2])
            elif tag_parts[0] == "phoenixslam":
                self.director.play_phoenix_desk_slam()
            elif tag_parts[0] == "edgeworthslam":
                self.director.play_edgeworth_desk_slam()
            elif tag_parts[0] == "wait":
                time_to_wait = float(tag_parts[1])
                self.max_wait_time = time_to_wait
                self.current_wait_time = 0.0
            elif tag_parts[0] == "startblip":
                self.director.start_voice_blips(tag_parts[1])
            elif tag_parts[0] == "stopblip":
                self.director.end_voice_blips()
            elif tag_parts[0] == "showarrow":
                self.director.textbox.arrow.show()
            elif tag_parts[0] == "hidearrow":
                self.director.textbox.arrow.hide()
            elif tag_parts[0] == "objection":
                self.director.exclamation.play_objection(tag_parts[1])
            elif tag_parts[0] == "holdit":
                self.director.exclamation.play_holdit(tag_parts[1])
            elif tag_parts[0] == "takethat":
                self.director.exclamation.play_takethat(tag_parts[1])
            elif tag_parts[0] == "playsound":
                self.director.audio_commands.append({
                    "type": "audio",
                    "path": f"new_assets/sound/sfx-{tag_parts[1]}.wav",
                    "offset": self.director.time
                })

    def handle_switch_sprite_tag(self, position: str, new_path: str):
        if position == "left":
            self.director.phoenix.set_filepath(new_path)
        elif position == "right":
            self.director.edgeworth.set_filepath(new_path)

    last_latest_chunk_tags: list[str] = None
    def update(self, delta):
        # If we're pausing, then don't do anything else
        if self.max_wait_time != 0.0:
            self.current_wait_time += delta
            if self.current_wait_time >= self.max_wait_time:
                self.max_wait_time = 0.0
                self.current_wait_time = 0.0
            return

        self.current_char_time += delta
        while self.current_char_time >= self.max_current_char_time:
            self.chars_visible += 1
            self.current_char_time -= self.max_current_char_time

        # Check for actions on current chunk
        if self.page is None:
            return

        text_so_far = self.page.get_visible_text(self.chars_visible)
        try:
            latest_chunk_tags = text_so_far.lines[-1][-1].tags
            if latest_chunk_tags != self.last_latest_chunk_tags:
                self.last_latest_chunk_tags = latest_chunk_tags
                self.handle_tags()
        except IndexError as e:
            pass

        if self.get_all_done():
            self.reset()
            self.on_complete()

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        if self.page is None:
            return
        _text = self.page.get_visible_text(self.chars_visible)
        for line_no, line in enumerate(_text.lines):
            x_offset = 220 if self.use_rtl else 0
            for chunk_no, chunk in enumerate(line):
                text_str = chunk.text#.replace('\u200B', '')
                drawing_args = {
                    "xy": (
                        10 + self.x + x_offset,
                        4 + self.y + (self.font_size) * line_no,
                    ),
                    "text": text_str,
                    "fill": (255, 0, 255),
                    "anchor": ("r" if self.use_rtl else "l") + "a",
                }

                if len(chunk.tags) == 0:
                    drawing_args["fill"] = (255, 255, 255)
                else:
                    drawing_args["fill"] = TEXT_COLORS.get(
                        chunk.tags[-1], (255, 255, 255)
                    )

                if self.font is not None:
                    drawing_args["font"] = self.font

                ctx.text(**drawing_args)

                try:
                    add_to_x_offset = ctx.textlength(text_str, font=self.font)
                    if chunk_no < len(line) - 1:
                        next_char = line[chunk_no + 1].text[0]
                        add_to_x_offset = ctx.textlength(
                            chunk.text + next_char, self.font
                        ) - ctx.textlength(next_char, self.font)
                except UnicodeEncodeError:
                    add_to_x_offset = self.font.getsize(text_str)[0]

                x_offset += (add_to_x_offset * -1) if self.use_rtl else add_to_x_offset

class ExclamationObject(ImageObject):
    def __init__(self, parent: SceneObject, director: 'AceAttorneyDirector'):
        super().__init__(
            parent=parent,
            name="Exclamation Image",
            pos=(0, 0, 20)
            )
        self.director = director

    def get_exclamation_path(self, type: str, speaker: str):
        base_name = f"new_assets/exclamations/{type}-{speaker}"
        if exists(f"{base_name}.mp3"):
            return f"{base_name}.mp3"
        elif exists(f"{base_name}.wav"):
            return f"{base_name}.wav"
        return f"new_assets/exclamations/objection-generic.wav"

    def play_objection(self, speaker: str):
        self.play_exclamation("objection", speaker)

    def play_holdit(self, speaker: str):
        self.play_exclamation("holdit", speaker)

    def play_takethat(self, speaker: str):
        self.play_exclamation("takethat", speaker)

    def play_exclamation(self, type: str, speaker: str):
        self.set_filepath(
            f"new_assets/exclamations/{type}.gif",
            {
                0.7: lambda: self.set_filepath(None)
            })

        audio_path = self.get_exclamation_path(type, speaker)

        self.director.audio_commands.append({
            "type": "audio",
            "path": audio_path,
            "offset": self.director.time
        })

    


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
            filepath="new_assets/bg/bg_main.png",
        )

        self.phoenix = ImageObject(
            parent=self.bg,
            name="Left Character",
            pos=(0, 0, 1),
            filepath="new_assets/character_sprites/phoenix/phoenix-normal-idle.gif",
        )

        self.edgeworth = ImageObject(
            parent=self.bg,
            name="Right Character",
            pos=(1034, 0, 2),
            filepath="new_assets/character_sprites/edgeworth/edgeworth-normal-idle.gif",
        )

        self.exclamation = ExclamationObject(
            parent=self.root,
            director=self
        )

        self.textbox = DialogueBox(parent=self.root, director=self)

        self.scene = Scene(256, 192, self.root)

    def text_box(self, speaker: str, body: str):
        for box in get_rich_boxes(body):
            print(body)
            print()
            self.sequencer.add_action(
                DisplayTextInTextBoxAction(self.textbox, speaker, box)
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
                ease_function=ease_in_out_cubic,
            )
        )

    def pan_to_left(self):
        self.sequencer.add_action(
            MoveSceneObjectAction(
                target_value=(0, 0),
                duration=1.0,
                scene_object=self.bg,
                ease_function=ease_in_out_cubic,
            )
        )

    def cut_to_left(self):
        self.sequencer.add_action(
            SetSceneObjectPositionAction(target_value=(0, 0), scene_object=self.bg)
        )

    def cut_to_right(self):
        self.sequencer.add_action(
            SetSceneObjectPositionAction(
                target_value=(-1920 + 256, 0), scene_object=self.bg
            )
        )

    def wait(self, t):
        self.sequencer.add_action(WaitAction(t))

    def set_left_character_sprite(self, path):
        self.sequencer.add_action(
            SetImageObjectSpriteAction(new_filepath=path, image_object=self.phoenix)
        )

    current_music_track: Optional[dict] = None
    current_voice_blips: Optional[dict] = None

    def start_music_track(self, name: str):
        self.end_music_track()
        self.current_music_track = {
            "type": "audio",
            "path": f"new_assets/music/{name}.mp3",
            "offset": self.time,
            "loop_type": "loop_until_truncated"
        }
        self.audio_commands.append(self.current_music_track)

    def end_music_track(self):
        if self.current_music_track is not None:
            self.current_music_track["end"] = self.time
            self.current_music_track = None

    def start_voice_blips(self, gender: str):
        self.end_voice_blips()
        self.current_voice_blips = {
            "type": "audio",
            "path": f"new_assets/sound/sfx-blip{gender}.wav",
            "offset": self.time,
            "loop_delay": 0.06,
            "loop_type": "loop_complete_only",
        }
        self.audio_commands.append(self.current_voice_blips)

    def end_voice_blips(self):
        if self.current_voice_blips is not None:
            self.current_voice_blips["end"] = self.time
            self.current_voice_blips = None

    def next_dialogue_sound(self):
        self.audio_commands.append({
            "type": "audio",
            "path": "new_assets/sound/sfx-pichoop.wav",
            "offset": self.time
        })

    def play_phoenix_desk_slam(self):
        fp_before = self.phoenix.filepath
        cb_before = self.phoenix.callbacks
        self.phoenix.set_filepath(
            get_sprite_location("phoenix", "deskslam"),
            {
                0.8: lambda: self.phoenix.set_filepath(fp_before, cb_before)
            })
        self.audio_commands.append({
            "type": "audio",
            "path": "new_assets/sound/sfx-deskslam.wav",
            "offset": self.time + 0.15
        })

    def play_edgeworth_desk_slam(self):
        fp_before = self.edgeworth.filepath
        cb_before = self.edgeworth.callbacks
        self.edgeworth.set_filepath(
            get_sprite_location("edgeworth", "deskslam"),
            {
                0.8: lambda: self.edgeworth.set_filepath(fp_before, cb_before)
            })
        self.audio_commands.append({
            "type": "audio",
            "path": "new_assets/sound/sfx-deskslam.wav",
            "offset": self.time + 0.25
        })

def get_sprite_location(character: str, emotion: str):
    return f"new_assets/character_sprites/{character}/{character}-{emotion}.gif"


def get_sprite_tag(location: str, character: str, emotion: str):
    return f"<sprite {location} {get_sprite_location(character, emotion)}/>"

SPR_PHX_NORMAL_T = get_sprite_tag('left', 'phoenix', 'normal-talk')
SPR_PHX_NORMAL_I = get_sprite_tag('left', 'phoenix', 'normal-idle')
SPR_PHX_SWEAT_T = get_sprite_tag('left', 'phoenix', 'sweating-talk')
SPR_PHX_SWEAT_I = get_sprite_tag('left', 'phoenix', 'sweating-idle')

SPR_EDW_NORMAL_T = get_sprite_tag('right', 'edgeworth', 'normal-talk')
SPR_EDW_NORMAL_I = get_sprite_tag('right', 'edgeworth', 'normal-idle')

B_M = "<startblip male/>"
B_F = "<startblip female/>"
B_ST = "<stopblip/>"

SLAM_PHX = "<phoenixslam/><wait 0.8/>"
SLAM_EDW = "<edgeworthslam/><wait 0.8/>"

director = AceAttorneyDirector()
director.start_music_track("cross-moderato")
director.text_box(
    "Phoenix",
    f"{B_M}{SPR_PHX_NORMAL_T}I am going to <red>slam the desk</red>" + \
    f"{SPR_PHX_NORMAL_I}{B_ST}<wait 1/> {B_ST}<objection phoenix/><wait 0.8/> " + \
    f"{SLAM_PHX} I{B_M}{SPR_PHX_NORMAL_T} just did it{B_ST}<holdit phoenix/><wait 0.8/>" + \
    f" {B_M}did you see that " + \
    f"<green>was i cool</green>{SPR_PHX_NORMAL_I}{B_ST}<showarrow/><wait 3/>?<hidearrow/><playsound pichoop/>"
)
director.hide_text_box()
director.pan_to_right()
director.show_text_box()
director.text_box(
    "Edgeworth",
    f"{B_M}{SPR_EDW_NORMAL_T}hey its me, <red>edge worth</red>{B_ST}<objection edgeworth/><wait 0.8/> {SLAM_EDW}<wait 0.8/> {B_M}uhh updated <green>autopsy report</green> ive got you now <red>phoenix right!{B_ST}<takethat edgeworth/><wait 0.8/></red> {SPR_EDW_NORMAL_I}<showarrow/><wait 3/> <hidearrow/><playsound pichoop/>",
)
director.hide_text_box()
director.set_left_character_sprite(get_sprite_location("phoenix", "sweating-idle"))
director.pan_to_left()
director.text_box(
    "Phoenix",
    f"{B_M}{SPR_PHX_SWEAT_T}<blue>(cool great thanks im so happy)</blue>{SPR_PHX_SWEAT_I}{B_ST} <showarrow/><wait 3/>.<hidearrow/><playsound pichoop/>",
)
director.hide_text_box()
director.render_movie(-15)
