from MovieKit import Scene, SceneObject, ImageObject, MoveSceneObjectAction, \
    Sequencer, SetSceneObjectPositionAction, WaitAction, SetImageObjectSpriteAction, \
        SimpleTextObject, SequenceAction, RunFunctionAction
import ffmpeg
from math_helpers import ease_in_out_cubic
from PIL import Image, ImageDraw, ImageFont
from parse_tags import DialoguePage, get_rich_boxes
from font_tools import get_best_font
from font_constants import TEXT_COLORS, FONT_ARRAY
from typing import Callable


root = SceneObject()
root.name = "Root"

bg = ImageObject(
    parent=root,
    pos=(0, 0, 0),
    filepath="courtroom_bg.png"
    )
bg.name = "Background"

phoenix = ImageObject(
    parent=bg,
    pos=(0, 0, 1),
    filepath="phoenix-normal(a).gif"
    )
phoenix.name = "Phoenix"

edgeworth = ImageObject(
    parent=bg,
    pos=(1034, 0, 2),
    filepath="edgeworth-normal(a).gif"
    )
edgeworth.name = "Edgeworth"

class NameBox(SceneObject):
    def __init__(self, parent: SceneObject, pos: tuple[int, int, int]):
        super().__init__(parent, pos)
        self.namebox_l = ImageObject(parent=self, pos=(0, 0, 11), filepath="nametag_left.png")
        self.namebox_c = ImageObject(parent=self, pos=(1, 0, 11), filepath="nametag_center.png")
        self.namebox_r = ImageObject(parent=self, pos=(2, 0, 11), filepath="nametag_right.png")
        self.namebox_text = SimpleTextObject(parent=self, pos=(4, 0, 12))

        self.font = ImageFont.truetype("ace-name/ace-name.ttf", size=8)
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
    def __init__(self, parent: SceneObject):
        super().__init__(parent, (0, 128, 12))
        self.bg = ImageObject(parent=self, pos=(0, 0, 10), filepath="mainbox.png")
        self.namebox = NameBox(parent=self, pos=(1, -11, 0))
        self.arrow = ImageObject(parent=self, pos=(256 - 9 - 6, 48, 11), filepath="arrow.png")
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

    def update(self, delta):
        self.time += delta

        if self.get_all_done():
            self.arrow.visible = True
            self.time_on_completed += delta
            if self.time_on_completed >= 1.0:
                self.reset()
                if self.on_complete is not None:
                    self.on_complete()
                else:
                    print(f"Text box for \"{self.page.get_raw_text()}\" is done but no on_complete")
        else:
            self.arrow.visible = False


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

textbox = DialogueBox(parent=root)

my_scene = Scene(256, 192, root)

DURATION = 20
FRAMES_PER_SECOND = 30


# boxes_for_this_thing = []
# raw_text_1 = "Hi here's a bunch of text also maybe the rich text is breaking again??? if so yay cool great"
# boxes_for_this_thing.extend(get_rich_boxes(raw_text_1))

# def next_box():
#     if len(boxes_for_this_thing) > 0:
#         box = boxes_for_this_thing.pop(0)
#         textbox.set_page(box, on_complete=next_box)

# next_box()
# raw_text_2 = "And here's another box worth of text aint that just the neato burrito"
# text_boxes_2 = get_rich_boxes(raw_text_2)

sequencer = Sequencer()

for box in get_rich_boxes("Hi here's a bunch of text also maybe the rich text is breaking again??? if so yay cool great"):
    sequencer.add_action(
        DisplayTextInTextBoxAction(
            textbox,
            "Phoenix",
            box
        )
    )

sequencer.add_action(
    RunFunctionAction(
        lambda: textbox.hide()
    )
)

sequencer.add_action(
        MoveSceneObjectAction(
        target_value=(-1290 + 256, 0),
        duration=1.0,
        scene_object=bg,
        ease_function=ease_in_out_cubic
    )
)

sequencer.add_action(
    RunFunctionAction(
        lambda: textbox.show()
    )
)

for box in get_rich_boxes("hey its me, mr edge worth uhhhhh updated autopsy report"):
    sequencer.add_action(
        DisplayTextInTextBoxAction(
            textbox,
            "Edgeworth",
            box
        )
    )

sequencer.add_action(
    RunFunctionAction(
        lambda: textbox.hide()
    )
)

sequencer.add_action(
    MoveSceneObjectAction(
        target_value=(1290, 0),
        duration=5.0,
        scene_object=edgeworth
    )
)

sequencer.add_action(
    SetImageObjectSpriteAction(new_filepath="phoenix-sweating(a).gif", image_object=phoenix)
)

sequencer.add_action(
    SetSceneObjectPositionAction(target_value=(0,0), scene_object=bg)
)

sequencer.add_action(
    WaitAction(0.5)
)

for box in get_rich_boxes("uh ok bye"):
    sequencer.add_action(
        DisplayTextInTextBoxAction(
            textbox,
            "Phoenix",
            box
        )
    )

sequencer.add_action(
    RunFunctionAction(
        lambda: textbox.hide()
    )
)

def render():
    for frame in range(FRAMES_PER_SECOND * DURATION):
        t = frame / FRAMES_PER_SECOND
        sequencer.update(1 / FRAMES_PER_SECOND)
        my_scene.update(1 / FRAMES_PER_SECOND)
        my_scene.render(f"outputs/{frame:010d}.png")

    stream = ffmpeg.input("outputs/*.png", pattern_type="glob", framerate=FRAMES_PER_SECOND)
    stream = ffmpeg.output(stream, "movie.mp4", vcodec='mpeg4')
    stream = ffmpeg.overwrite_output(stream)
    ffmpeg.run(stream)

render()