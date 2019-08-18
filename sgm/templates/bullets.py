from sgm import components as components
from sgm.templates.explosions import create_red_explosion, \
    create_green_explosion, create_big_explosion
from sgm.templates.thrusters import add_thrusters, standard_thruster_layout
from sgm.templates.turrets import add_turrets, TurretSpec, create_turret
from sgm.templates.weapons import create_rapid_red_blaster_weapon


def create_pewpew_bullet(game_services, **kwargs):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()

    doc = ecs.create_component(entity, components.DamageOnContact)
    doc.damage = 1

    eod = ecs.create_component(entity, components.ExplodesOnDeath)
    eod.explosion_template = kwargs["explosion_template"]
    eod.sound = "234082__211redman112__lasgun-impact.ogg"

    kot = ecs.create_component(entity, components.KillOnTimer)
    kot.lifetime = 2

    anim = ecs.create_component(entity, components.AnimationComponent)
    anim.anim_name = kwargs["anim_name"]
    anim.brightness = 0.5

    body = ecs.create_component(entity, components.Body)
    body.mass = 1
    body.size = 3

    return entity


def create_red_bullet(game_services):
    return create_pewpew_bullet(
        game_services,
        explosion_template=create_red_explosion,
        anim_name="pewpew_red"
    )


def create_green_bullet(game_services):
    return create_pewpew_bullet(
        game_services,
        explosion_template=create_green_explosion,
        anim_name="pewpew_green"
    )


def create_torpedo_bullet(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()

    doc = ecs.create_component(entity, components.DamageOnContact)
    doc.damage = 5

    eod = ecs.create_component(entity, components.ExplodesOnDeath)
    eod.explosion_template = create_big_explosion
    eod.sound = "234082__211redman112__lasgun-impact.ogg"

    kot = ecs.create_component(entity, components.KillOnTimer)
    kot.lifetime = 2

    anim = ecs.create_component(entity, components.AnimationComponent)
    anim.anim_name = "rocket"
    anim.brightness = 0

    body = ecs.create_component(entity, components.Body)
    body.mass = 10
    body.size = 10

    team = ecs.create_component(entity, components.Team)

    tracking = ecs.create_component(entity, components.Tracking)

    follows = ecs.create_component(entity, components.FollowsTracked)
    follows.acceleration = 3000
    follows.desired_distance_to_player = 0.1

    turrets = ecs.create_component(entity, components.Turrets)
    add_turrets(
        entity,
        [
            TurretSpec(weapon_template=create_rapid_red_blaster_weapon,
                       turret_template=create_turret,
                       position=(0, 0))
        ]
    )
    thrusters = ecs.create_component(entity, components.Thrusters)
    add_thrusters(
        entity,
        standard_thruster_layout(40, 40, 50000)
    )
    return entity