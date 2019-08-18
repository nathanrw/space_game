"""
templates of components.

An template is a function f(game_services) which produces an entity configured
with a particular template of components.
"""

import sgm.components as components


def create_endgame_message(game_services, **kwargs):
    return create_message(game_services, blink=False, lifetime=10, **kwargs)


def create_update_message(game_services, **kwargs):
    return create_message(game_services, blink=True, lifetime=4, **kwargs)


def create_message(game_services, **kwargs):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()

    kill_on_timer = ecs.create_component(entity, components.KillOnTimer)
    kill_on_timer.lifetime = kwargs.get("lifetime", 4)

    text = ecs.create_component(entity, components.Text)
    text.text = kwargs.get("text", "Hello, World!")
    text.blink = kwargs.get("blink", False)
    text.font_colour = (255, 255, 255)
    text.font_name = "nasdaqer"
    text.font_size = 62

    return entity


def create_camera(game_services):
    ecs = game_services.get_entity_manager()
    camera = ecs.create_entity_with(
        components.Camera,
        components.Body,
        components.Tracking,
        components.FollowsTracked
    )
    camera.get_component(components.FollowsTracked).follow_type = "instant"
    camera.name = "Camera"
    return camera