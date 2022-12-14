from MovieKit import (
    Scene,
    SceneObject,
    ImageObject,
    MoveSceneObjectAction,
    SimpleTextObject,
    Director,
)
from math_helpers import ease_in_out_cubic
from PIL import Image, ImageDraw, ImageFont
from parse_tags import DialoguePage, DialogueTextChunk, DialogueAction, DialogueTextLineBreak
from font_tools import get_best_font
from font_constants import TEXT_COLORS, FONT_ARRAY
from typing import Callable, Optional
from os.path import exists
from shlex import split
from math import cos, sin, pi
from random import random

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

        self.font_data = {}
        self.font: ImageFont.ImageFont = None
        self.use_rtl = False
        self.font_size = 16

        self.chars_visible = 0
        self.current_char_time = 0

        self.on_complete: Callable[[], None] = None

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        if self.page is None:
            return

        # x, y, _ = self.get_absolute_position()
        x, y = self.x, self.y
        line_no = 0
        x_offset = 220 if self.use_rtl else 0
        for command in self.page.commands:
            if isinstance(command, DialogueTextLineBreak):
                line_no += 1
                x_offset = 220 if self.use_rtl else 0
            elif isinstance(command, DialogueTextChunk):
                text_str = command.text[:command.position]
                drawing_args = {
                    "xy": (
                        10 + x + x_offset,
                        4 + y + (self.font_size) * line_no,
                    ),
                    "text": text_str,
                    "fill": (255, 0, 255),
                    "anchor": ("r" if self.use_rtl else "l") + "a",
                }

                if len(command.tags) == 0:
                    drawing_args["fill"] = (255, 255, 255)
                else:
                    drawing_args["fill"] = TEXT_COLORS.get(
                        command.tags[-1], (255, 255, 255)
                    )

                if self.font is not None:
                    drawing_args["font"] = self.font

                ctx.text(**drawing_args)

                try:
                    # TODO: I think the Pillow docs say this isn't actually
                    # how you should get the true text length due to kerning,
                    # but I'm too tired right now to do it the "right" way
                    # and so far it doesn't seem to have broken significantly.
                    add_to_x_offset = ctx.textlength(text_str, font=self.font)
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

class ShakerObject(SceneObject):
    magnitude: float = 0.0
    remaining: float = 0.0
    def start_shaking(self, magnitude, duration):
        self.magnitude = magnitude
        self.remaining = duration

    def update(self, delta):
        self.remaining -= delta
        if self.remaining > 0:
            angle = random() * 2 * pi
            x_offset = int(cos(angle) * self.magnitude)
            y_offset = int(sin(angle) * self.magnitude)
            self.set_x(x_offset)
            self.set_y(y_offset)
        else:
            self.remaining = 0
            self.magnitude = 0
            self.set_x(0)
            self.set_y(0)

class ColorOverlayObject(SceneObject):
    color: tuple[int, int, int] = (0, 0, 0)
    remaining: float = 0.0
    def start_color(self, color, duration):
        self.color = color
        self.remaining = duration

    def update(self, delta):
        self.remaining -= delta
        if self.remaining < 0:
            self.remaining = 0

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        if self.remaining > 0:
            ctx.rectangle(xy=(0, 0, img.width, img.height), fill=self.color)

class AceAttorneyDirector(Director):
    def __init__(self, fps: float = 30):
        super().__init__(None, fps)

        self.root = SceneObject(name="Root")

        self.white_flash = ColorOverlayObject(
            parent=self.root,
            name="White Flash Overlay",
            pos=(0,0,30)
        )
        self.white_flash.color = (255, 255, 255)

        self.bg_shaker = ShakerObject(
            parent=self.root,
            name="Background Shaker",
            pos=(0, 0, 0)
        )

        self.bg = ImageObject(
            parent=self.bg_shaker,
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

        self.textbox_shaker = ShakerObject(
            parent=self.root,
            name="Text Box Shaker",
            pos=(0,0,0)
        )

        self.exclamation = ExclamationObject(
            parent=self.root,
            director=self
        )

        self.textbox = DialogueBox(parent=self.textbox_shaker, director=self)

        self.scene = Scene(256, 192, self.root)

    def set_current_pages(self, pages: list[DialoguePage]):
        self.pages = pages
        self.page_index = 0
        self.local_time = 0
        self.cur_time_for_char = 0.0

    cur_time_for_char: float = 0.0
    max_time_for_char: float = 0.03

    def update(self, delta: float):
        # If the current page index is greater than the number of pages, then we've
        # used all the pages - in other words, we're done.
        if self.page_index >= len(self.pages):
            self.end_music_track()
            self.end_voice_blips()
            self.is_done = True
            return

        # Find which page we are on
        self.current_page = self.pages[self.page_index]
        self.textbox.page = self.current_page
        self.textbox.font_data = get_best_font(self.current_page.get_raw_text(), FONT_ARRAY)
        self.textbox.font = ImageFont.truetype(self.textbox.font_data["path"], 16)

        # Within that page, get the current object
        current_dialogue_obj = self.current_page.get_current_item()

        if isinstance(current_dialogue_obj, DialogueTextChunk):
            self.cur_time_for_char += delta
            if self.cur_time_for_char >= self.max_time_for_char:
                # Increment the progress through the current dialogue object
                # by one. This will make it render more characters in render()
                current_dialogue_obj.position += 1
                self.cur_time_for_char = 0
                if current_dialogue_obj.position >= len(current_dialogue_obj.text):
                    current_dialogue_obj.completed = True

        elif isinstance(current_dialogue_obj, DialogueAction):
            # Handle actions
            # Most actions can be taken care of instantly and then marked complete
            # Wait actions need the timer to fill up before they can be marked complete
            action_split = split(current_dialogue_obj.name)
            match action_split:
                case ["startblip", voice_type]:
                    self.start_voice_blips(voice_type)
                    current_dialogue_obj.completed = True

                case ["stopblip"]:
                    self.end_voice_blips()
                    current_dialogue_obj.completed = True

                case ["sprite", position, path]:
                    if position == "left":
                        self.phoenix.set_filepath(path)
                    elif position == "right":
                        self.edgeworth.set_filepath(path)
                    else:
                        print(f"Error in sprite command: unknown position \"{position}\"")
                    current_dialogue_obj.completed = True

                case ["wait", duration_str]:
                    self.cur_time_for_char += delta
                    if self.cur_time_for_char >= float(duration_str):
                        current_dialogue_obj.completed = True
                        self.cur_time_for_char = 0.0

                case ["bubble", exclamation_type, character]:
                    self.exclamation.play_exclamation(exclamation_type, character)
                    current_dialogue_obj.completed = True

                case ["deskslam", character]:
                    if character == "phoenix":
                        self.play_phoenix_desk_slam()
                    elif character == "edgeworth":
                        self.play_edgeworth_desk_slam()
                    current_dialogue_obj.completed = True

                case ["showarrow"]:
                    self.textbox.arrow.visible = True
                    current_dialogue_obj.completed = True
                
                case ["hidearrow"]:
                    self.textbox.arrow.visible = False
                    current_dialogue_obj.completed = True

                case ["showbox"]:
                    self.textbox.show()
                    current_dialogue_obj.completed = True

                case ["hidebox"]:
                    self.textbox.hide()
                    current_dialogue_obj.completed = True

                case ["nametag", name]:
                    self.textbox.namebox.set_text(name)
                    current_dialogue_obj.completed = True

                case ["sound", sound_path]:
                    self.audio_commands.append({
                        "type": "audio",
                        "path": f"new_assets/sound/sfx-{sound_path}.wav",
                        "offset": self.time
                    })
                    current_dialogue_obj.completed = True

                case ["shake", magnitude_str, duration_str]:
                    magnitude = float(magnitude_str)
                    duration = float(duration_str)
                    self.bg_shaker.start_shaking(magnitude, duration)
                    self.textbox_shaker.start_shaking(magnitude, duration)
                    current_dialogue_obj.completed = True

                case ["flash", duration_str]:
                    duration = float(duration_str)
                    self.white_flash.start_color((255,255,255), duration)
                    current_dialogue_obj.completed = True

                case ["music", "start", music_name]:
                    self.start_music_track(music_name)
                    current_dialogue_obj.completed = True

                case ["music", "stop"]:
                    self.end_music_track()
                    current_dialogue_obj.completed = True

                case ["cut", position]:
                    if position == "left":
                        self.cut_to_left()
                    elif position == "right":
                        self.cut_to_right()
                    current_dialogue_obj.completed = True

                case ["pan", position]:
                    if position == "left":
                        self.pan_to_left()
                    elif position == "right":
                        self.pan_to_right()
                    current_dialogue_obj.completed = True

                case _:
                    current_dialogue_obj.completed = True
     
        elif isinstance(current_dialogue_obj, DialogueTextLineBreak):
            # Does anything need to be done here? I think this can be handled
            # entirely in render()
            current_dialogue_obj.completed = True

        elif current_dialogue_obj is None:
            # Done with the current page - let's try to get the next page!
            self.page_index += 1

    def pan_to_right(self):
        self.sequencer.run_action(
            MoveSceneObjectAction(
                target_value=(-1290 + 256, 0),
                duration=1.0,
                scene_object=self.bg,
                ease_function=ease_in_out_cubic,
            )
        )

    def pan_to_left(self):
        self.sequencer.run_action(
            MoveSceneObjectAction(
                target_value=(0, 0),
                duration=1.0,
                scene_object=self.bg,
                ease_function=ease_in_out_cubic,
            )
        )

    def cut_to_left(self):
        self.bg.set_x(0)

    def cut_to_right(self):
        self.bg.set_x(-1296 + 256)

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