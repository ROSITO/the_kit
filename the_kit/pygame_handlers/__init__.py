from the_kit.pygame_handlers.keyboard import run_keyboard_response_node
from the_kit.pygame_handlers.mot import run_mot_node
from the_kit.pygame_handlers.neuroconn_gvs import run_neuroconn_gvs_node
from the_kit.pygame_handlers.occultation import run_occultation_node
from the_kit.pygame_handlers.optic_flow import run_optic_flow_node
from the_kit.pygame_handlers.scene import run_pygame_scene_node
from the_kit.pygame_handlers.shadow_ball import run_shadow_ball_node

HANDLERS = {
    "pygame_scene": run_pygame_scene_node,
    "optic_flow": run_optic_flow_node,
    "keyboard_response": run_keyboard_response_node,
    "occultation": run_occultation_node,
    "shadow_ball": run_shadow_ball_node,
    "mot": run_mot_node,
    "neuroconn_gvs": run_neuroconn_gvs_node,
}
