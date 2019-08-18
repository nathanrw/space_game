from sgm import components as components
from sgm.templates.bullets import create_red_bullet, create_green_bullet, \
    create_torpedo_bullet


def create_laser_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon, {
        "type": "beam",
        "range": 5000,
        "radius": 6,
        "damage": 30,
        "power_usage": 20
    })
    return entity


def create_red_blaster_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon, {
        "type": "projectile_thrower",
        "bullet_template": create_red_bullet,
        "bullet_speed": 2000,
        "shots_per_second": 10,
        "spread": 10,
        "shot_sound": "143609__d-w__weapons-synth-blast-03.wav"
    })
    return entity


def create_green_blaster_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon, {
        "type": "projectile_thrower",
        "bullet_template": create_green_bullet,
        "bullet_speed": 2000,
        "shots_per_second": 4,
        "spread": 10,
        "shot_sound": "143609__d-w__weapons-synth-blast-03.wav"
    })
    return entity


def create_rapid_red_blaster_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon, {
        "type": "projectile_thrower",
        "bullet_template": create_red_bullet,
        "bullet_speed": 2000,
        "shots_per_second": 24,
        "spread": 10,
        "shot_sound": "143609__d-w__weapons-synth-blast-03.wav"
    })
    return entity


def create_torpedo_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon, {
        "type": "projectile_thrower",
        "bullet_template": create_torpedo_bullet,
        "bullet_speed": 1000,
        "shots_per_second": 1,
        "spread": 1,
        "shot_sound": "143609__d-w__weapons-synth-blast-03.wav"
    })
    return entity