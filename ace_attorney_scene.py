from MovieKit import Scene, SceneObject, ImageObject, MoveSceneObjectAction, \
    Sequencer, SetSceneObjectPositionAction, WaitAction, SetImageObjectSpriteAction, \
        SimpleTextObject
import ffmpeg
from math_helpers import ease_in_out_cubic
from PIL import Image, ImageDraw, ImageFont
from parse_tags import DialoguePage, get_rich_boxes
from font_tools import get_best_font
from font_constants import TEXT_COLORS, FONT_ARRAY

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
    def __init__(self, parent: SceneObject):
        super().__init__(parent, (0, 128, 12))
        self.bg = ImageObject(parent=self, pos=(0, 0, 10), filepath="mainbox.png")
        self.namebox = NameBox(parent=self, pos=(1, -11, 0))
        self.arrow = ImageObject(parent=self, pos=(256 - 9 - 6, 48, 11), filepath="arrow.png")

        self.page: DialoguePage = None

        self.use_rtl = False
        self.font_size = 16

    def set_page(self, page: DialoguePage):
        self.page = page
        self.font_data = get_best_font(
            self.page.get_raw_text(),
            FONT_ARRAY
        )
        self.font = ImageFont.truetype(self.font_data["path"], self.font_size)

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        _text = self.page.get_visible_text(100)
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



textbox = DialogueBox(parent=root)

my_scene = Scene(256, 192, root)

DURATION = 10
FRAMES_PER_SECOND = 30


raw_text = "Hi here's a bunch of text also maybe the rich text is breaking again??? if so yay cool great"
text_boxes = get_rich_boxes(raw_text)
textbox.set_page(text_boxes[0])
print(text_boxes)

sequencer = Sequencer()
sequencer.add_action(
        MoveSceneObjectAction(
        target_value=(-1290 + 256, 0),
        duration=1.0,
        scene_object=bg,
        ease_function=ease_in_out_cubic
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
    SetSceneObjectPositionAction(target_value=(0,0), scene_object=bg)
)

sequencer.add_action(
    WaitAction(duration=1.0)
)

sequencer.add_action(
    SetImageObjectSpriteAction(new_filepath="phoenix-sweating(a).gif", image_object=phoenix)
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