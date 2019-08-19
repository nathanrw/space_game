from sgm import components as components
from sgm.templates.bullets import create_red_bullet, create_green_bullet, \
    create_torpedo_bullet


def create_laser_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon)
    weapon.type = "beam"
    weapon.range = 5000
    weapon.radius = 6
    weapon.damage = 30
    weapon.power_usage = 20
    return entity


def create_red_blaster_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon)
    weapon.type = "projectile_thrower"
    weapon.bullet_template = create_red_bullet
    weapon.bullet_speed = 2000
    weapon.shots_per_second = 10
    weapon.spread = 10
    weapon.shot_sound = "143609__d-w__weapons-synth-blast-03.wav"
    return entity


def create_green_blaster_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon)
    weapon.type = "projectile_thrower"
    weapon.bullet_template = create_green_bullet
    weapon.bullet_speed = 2000
    weapon.shots_per_second = 10
    weapon.spread = 10
    weapon.shot_sound = "143609__d-w__weapons-synth-blast-03.wav"
    return entity


def create_rapid_red_blaster_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon)
    weapon.type = "projectile_thrower"
    weapon.bullet_template = create_red_bullet
    weapon.bullet_speed = 2000
    weapon.shots_per_second = 24
    weapon.spread = 10
    weapon.shot_sound = "143609__d-w__weapons-synth-blast-03.wav"
    return entity


def create_torpedo_weapon(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    weapon = ecs.create_component(entity, components.Weapon)
    weapon.type = "projectile_thrower"
    weapon.bullet_template = create_torpedo_bullet
    weapon.bullet_speed = 1000
    weapon.shots_per_second = 1
    weapon.spread = 1
    weapon.shot_sound = "143609__d-w__weapons-synth-blast-03.wav"
    return entity