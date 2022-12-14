from ace_attorney_scene import AceAttorneyDirector

from tag_macros import (
    SPR_PHX_NORMAL_T,
    SPR_PHX_NORMAL_I,
    SPR_PHX_SWEAT_T,
    SPR_PHX_SWEAT_I,
    SPR_EDW_NORMAL_T,
    SPR_EDW_NORMAL_I,
    SLAM_PHX,
    SLAM_EDW,
    OBJ_PHX,
    OBJ_EDW,
    HDI_PHX,
    END_BOX,
    S_DRAMAPOUND,
    S_SMACK,
)

from parse_tags import DialoguePage, get_rich_boxes

test_dialogue_1 = (
    f'<music start cross-moderato/><nametag "Phoenix right"/><showbox/>'
    + f"{SPR_PHX_NORMAL_T}I am going to <red>slam the desk</red>!"
    + f"{SPR_PHX_NORMAL_I}<wait 0.25/>{OBJ_PHX}"
    + f"{SLAM_PHX}{SPR_PHX_NORMAL_T} I just did it!{SPR_PHX_NORMAL_I}{HDI_PHX}"
    + f" {SPR_PHX_NORMAL_T}Did you see that?{SPR_PHX_NORMAL_I}{S_DRAMAPOUND}<wait 0.5/>"
    + f" {SPR_PHX_NORMAL_T}<green>Was I cool?</green>{SPR_PHX_NORMAL_I}{END_BOX}<hidebox/>"
)

test_dialogue_2 = (
    f'<nametag "Phoenix right"/><showbox/>{SPR_PHX_SWEAT_T}...Hello?'
    + f"{SPR_PHX_SWEAT_I}<wait 0.25/>{SPR_PHX_SWEAT_T} ...Is anyone there?"
    + f" {SPR_PHX_SWEAT_I}{END_BOX}<hidebox/>"
)

test_dialogue_3 = (
    f"<music stop/>{OBJ_EDW}<pan right/><wait 1/>"
    + f'<nametag "Mr edge worth"/><showbox/>'
    + f"{SPR_EDW_NORMAL_T}Yes, I saw it.{SPR_EDW_NORMAL_I}<wait 0.1/> "
    + f"{SPR_EDW_NORMAL_T}But it was not very impressive.<music start pursuit/>{SPR_EDW_NORMAL_I}<wait 1/> "
    + f"{SPR_EDW_NORMAL_T}Look,{S_SMACK} I can do the same thing.{SLAM_EDW} "
    + f"{SPR_EDW_NORMAL_T}See?{SPR_EDW_NORMAL_I}"
    + f"{END_BOX}"
)

pages: list[DialoguePage] = []
pages.extend(get_rich_boxes(test_dialogue_1))
pages.extend(get_rich_boxes(test_dialogue_2))
pages.extend(get_rich_boxes(test_dialogue_3))
director = AceAttorneyDirector()
director.set_current_pages(pages)
director.render_movie(-15)
