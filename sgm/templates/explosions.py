from sgm import components as components


def create_big_explosion(game_services):
    return create_explosion(game_services, "big_explosion")


def create_green_explosion(game_services):
    return create_explosion(game_services, "green_explosion")


def create_red_explosion(game_services):
    return create_explosion(game_services, "red_explosion")


def create_explosion(game_services, anim_name):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    body = ecs.create_component(entity, components.Body)
    body.is_collideable = False

    anim = ecs.create_component(entity, components.AnimationComponent)
    anim.anim_name = anim_name
    anim.kill_on_finish = True
    anim.brightness = 10

    return entity