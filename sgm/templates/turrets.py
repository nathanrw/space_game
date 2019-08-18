from pymunk import Vec2d

from sge.renderer import Renderer
from sgm import components as components
from sgm.utils import setup_team


class TurretSpec(object):
    def __init__(self, **kwargs):
        self.position = kwargs.get("position", Vec2d(0, 0))
        self.weapon_template = kwargs["weapon_template"]
        self.turret_template = kwargs["turret_template"]


def add_turrets(entity, turret_specs):
    body = entity.get_component(components.Body)
    turrets = entity.get_component(components.Turrets)
    assert body is not None
    assert turrets is not None
    for spec in turret_specs:

        # Create the weapon and turret
        weapon_entity = spec.weapon_template(entity.game_services)
        turret_entity = spec.turret_template(entity.game_services)

        # Get the corresponding components
        weapon = weapon_entity.get_component(components.Weapon)
        turret = turret_entity.get_component(components.Turret)
        assert weapon is not None
        assert turret is not None

        # Attach the weapon to the turret
        turret.weapon.entity = weapon_entity
        turret.position = Vec2d(spec.position)
        weapon.owner.entity = turret_entity

        # Set the level so that turrets display on top of ships.
        anim = turret_entity.get_component(components.AnimationComponent)
        if anim is not None:
            anim.level = Renderer.LEVEL_MID_NEAR

        # Add the backreference and add to our list of turrets.
        turret.attached_to.entity = entity
        turrets.turrets.add_ref_to(turret_entity)

        # Set the turret's team.
        setup_team(entity, turret_entity)

        physics = entity.ecs().get_system(physics.Physics)

        # Match position and velocity.
        physics.teleport(
            turret_entity,
            to_position=physics.local_to_world(body.entity,
                                               turret.position),
            to_velocity=body.velocity
        )

        # Pin the bodies together.
        physics.create_joint(
            entity,
            turret.position,
            turret_entity,
            Vec2d(0, 0)
        )


def create_turret(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    anim = ecs.create_component(entity, components.AnimationComponent, {
        "anim_name": "enemy_turret"
    })
    body = ecs.create_component(entity, components.Body, {
        "mass": 1,
        "size": 1
    })
    turret = ecs.create_component(entity, components.Turret, {})
    power = ecs.create_component(entity, components.Power, {
        "capacity": 100,
        "recharge_rate": 10
    })
    team = ecs.create_component(entity, components.Team, {})
    tracking = ecs.create_component(entity, components.Tracking, {})
    return entity