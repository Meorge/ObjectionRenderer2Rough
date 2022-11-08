from PIL import Image, ImageDraw, ImageFont
import ffmpeg
from math_helpers import lerp
from typing import Callable

class Scene:
    w: int = 0
    h: int = 0
    __root: 'SceneObject' = None

    def __init__(self, w: int = 0, h: int = 0, root: 'SceneObject' = None):
        self.w = w
        self.h = h
        self.__root = root

    def render(self, path: str):
        img = Image.new("RGBA", (self.w, self.h))
        ctx = ImageDraw.ImageDraw(img)

        all_objects: list[SceneObject] = sorted(self.__root.get_self_and_children_as_flat_list(), key=lambda obj: obj.z)

        for object in all_objects:
            if object.get_absolute_visibility():
                object.render(img, ctx)

        img.save(path)

    def update(self, delta: float):
        for object in self.__root.get_self_and_children_as_flat_list():
            object.update(delta)

class SceneObject:
    x: int = 0
    y: int = 0
    z: int = 0
    name: str = ""
    visible: bool = True
    __children: list['SceneObject'] = []
    __parent: 'SceneObject' = None

    def __init__(self, parent: 'SceneObject' = None, pos: tuple[int, int, int] = (0,0,0)):
        self.x, self.y, self.z = pos
        self.__children = []

        if parent is not None:
            parent.add_child(self)

    def __repr__(self) -> str:
        return type(self).__name__ + f" \"{self.name}\" ({self.x}, {self.y}, {self.z})"

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        pass

    def update(self, delta):
        pass

    def get_x(self) -> int:
        return self.x

    def get_y(self) -> int:
        return self.y

    def set_x(self, x: int):
        self.x = int(x)

    def set_y(self, y: int):
        self.y = int(y)

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def add_child(self, new_child: 'SceneObject'):
        self.__children.append(new_child)
        if new_child.__parent is not None:
            new_child.__parent.__children.remove(new_child)
        new_child.__parent = self

    def get_absolute_position(self) -> tuple[int, int, int]:
        p = self
        x_out = 0
        y_out = 0
        z_out = 0
        while p is not None:
            x_out += p.x
            y_out += p.y
            z_out += p.z
            p = p.__parent
        return (x_out, y_out, z_out)

    def get_absolute_visibility(self) -> bool:
        p = self
        while p is not None:
            if not p.visible:
                return False
            p = p.__parent
        return True

    def print_hierarchy(self):
        self.__internal_print_hierarchy(0)

    def __internal_print_hierarchy(self, i: int = 0):
        print(('\t' * i) + str(self))
        for child in self.__children:
            child.__internal_print_hierarchy(i+1)

    def get_self_and_children_as_flat_list(self) -> list['SceneObject']:
        nodes: list['SceneObject'] = []
        def f(c):
            for ch in c.__children:
                nodes.append(ch)
                f(ch)
        f(self)
        return nodes

class ImageObject(SceneObject):
    filepath: str = ""
    t: float = 0.0

    width: int = None
    height: int = None

    image_data: list[tuple[Image.Image, float]] = []

    def __init__(self, parent: 'SceneObject' = None, pos: tuple[int, int, int] = (0, 0, 0), \
        width: int = None,
        height: int = None,
        filepath: str = None):
        super().__init__(parent, pos)
        self.width = width
        self.height = height
        self.set_filepath(filepath)

    def update(self, delta):
        self.t += delta

    def set_filepath(self, filepath: str):
        self.filepath = filepath
        with Image.open(self.filepath) as my_img:
            if my_img.is_animated:
                self.image_data = []
                time_so_far = 0.0
                for frame_no in range(my_img.n_frames):
                    my_img.seek(frame_no)
                    time_so_far += my_img.info['duration'] / 1000
                    self.image_data.append((
                        my_img.convert('RGBA'),
                        time_so_far
                    ))
                self.image_duration = time_so_far
            else:
                self.image_data = my_img.convert('RGBA')
                self.image_duration = None

    def get_current_frame(self):
        t = self.t % self.image_duration
        for image, max_time in self.image_data:
            if max_time > t:
                return image
        return None

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        x, y, _ = self.get_absolute_position()
        box = (x, y)
        if isinstance(self.image_data, Image.Image):
            w = self.image_data.width if self.width is None else self.width
            h = self.image_data.height if self.height is None else self.height
            resized = self.image_data.resize((w, h))
        elif isinstance(self.image_data, list):
            current_frame = self.get_current_frame()
            w = current_frame.width if self.width is None else self.width
            h = current_frame.height if self.height is None else self.height
            resized = current_frame.resize((w, h))
        img.paste(resized, box, mask=resized)

class SimpleTextObject(SceneObject):
    def __init__(self, parent: 'SceneObject' = None, pos: tuple[int, int, int] = (0,0,0), \
        text: str = "", font: ImageFont.FreeTypeFont = None):
        super().__init__(parent, pos)
        self.text = text
        self.font = font

    def get_width(self):
        if self.font is not None:
            return self.font.getlength(self.text)

    def render(self, img: Image.Image, ctx: ImageDraw.ImageDraw):
        x, y, _ = self.get_absolute_position()

        args = {
            "xy": (x,y),
            "text": self.text,
            "fill": (255,255,255)
        }

        if self.font is not None:
            args["font"] = self.font
        ctx.text(**args)

class Sequencer:
    actions: list['SequenceAction'] = []
    current_action: 'SequenceAction' = None

    def add_action(self, action: 'SequenceAction'):
        self.actions.append(action)
        action.sequencer = self

    def update(self, delta):
        if len(self.actions) <= 0:
            return False
        new_current_action = self.actions[0]
        if new_current_action != self.current_action:
            print(f"Start action {new_current_action}")
            new_current_action.start()
        self.current_action = new_current_action
        self.current_action.update(delta)
        return True

    def action_finished(self):
        if len(self.actions) > 0:
            self.actions.pop(0)

class SequenceAction:
    sequencer: Sequencer

    def start(self):
        ...

    def update(self, delta):
        ...

class MoveSceneObjectAction(SequenceAction):
    target_value: tuple[int, int] = (0,0)
    duration: float = 0.0
    
    scene_object: SceneObject = None
    ease_function = lambda self, x: x

    on_complete = lambda self: ...
    completed: bool = False

    time_passed: float = 0.0
    current_value: float = 0

    def __init__(self, target_value: tuple[int, int],
        duration: float,
        scene_object: SceneObject = None,
        ease_function: Callable[[float], float] = None,
        on_complete_function: Callable[[], None] = None):
        self.target_value = target_value
        self.duration = duration
        self.scene_object = scene_object
        if ease_function is not None:
            self.ease_function = ease_function
        if on_complete_function is not None:
            self.on_complete = on_complete_function

    def update(self, delta):
        if self.time_passed == 0:
            self.initial_value = (self.scene_object.x, self.scene_object.y)
        
        self.time_passed += delta
        percent_complete = self.time_passed / self.duration

        percent_complete_eased = self.ease_function(percent_complete)
        new_x = lerp(self.initial_value[0], self.target_value[0], percent_complete_eased)
        new_y = lerp(self.initial_value[1], self.target_value[1], percent_complete_eased)
        self.scene_object.set_x(new_x)
        self.scene_object.set_y(new_y)
        
        if percent_complete_eased >= 1.0 and not self.completed:
            self.completed = True
            if self.on_complete is not None:
                self.on_complete()
            self.sequencer.action_finished()

class SetSceneObjectPositionAction(SequenceAction):
    target_value: tuple[int, int] = (0,0)

    scene_object: SceneObject = None
    on_complete: Callable[[], None] = lambda self: ...
    completed: bool = False

    def __init__(self, target_value: tuple[int, int],
        scene_object: SceneObject = None,
        on_complete_function: Callable[[], None] = None):
        self.target_value = target_value
        self.scene_object = scene_object
        if on_complete_function is not None:
            self.on_complete = on_complete_function

    def update(self, delta):
        self.scene_object.set_x(self.target_value[0])
        self.scene_object.set_y(self.target_value[1])
        if self.on_complete is not None:
            self.on_complete()
        self.sequencer.action_finished()

class WaitAction(SequenceAction):
    duration: float = 0.0
    time_passed: float = 0.0
    on_complete: Callable[[], None] = lambda self: ...
    completed: bool = False

    def __init__(self, duration: float,
        on_complete_function: Callable[[], None] = None):
        self.duration = duration
        if on_complete_function is not None:
            self.on_complete = on_complete_function

    def update(self, delta):
        self.time_passed += delta
        if self.time_passed > self.duration:
            self.completed = True
            if self.on_complete is not None:
                self.on_complete()
            self.sequencer.action_finished()

class SetImageObjectSpriteAction(SequenceAction):
    new_filepath: str = ""
    image_object: ImageObject = None

    def __init__(self, new_filepath: str, image_object: ImageObject):
        self.new_filepath = new_filepath
        self.image_object = image_object

    def update(self, delta):
        self.image_object.set_filepath(self.new_filepath)
        self.sequencer.action_finished()

class RunFunctionAction(SequenceAction):
    func: Callable[[], None] = None

    def __init__(self, func: Callable[[], None]):
        self.func = func

    def update(self, delta):
        self.func()
        self.sequencer.action_finished()