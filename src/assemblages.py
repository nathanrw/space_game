"""
Assemblages of components.

An assemblage is a function f(game_services) which produces an entity configured
with a particular assemblage of components.
"""

import components

from .utils import Vec2d


class ThrusterSpec(object):
    def __init__(self, **kwargs):
        self.position = kwargs.get("position", Vec2d(0, 0))
        self.orientation = kwargs.get("orientation", Vec2d(1, 0))
        self.max_thrust = kwargs.get("max_thrust", 0)


class TurretSpec(object):
    def __init__(self, **kwargs):
        self.position = kwargs.get("position", Vec2d(0, 0))
        self.weapon_assemblage = kwargs["weapon_assemblage"]
        self.turret_assemblage = kwargs["turret_assemblage"]


def create_big_explosion(game_services):
    return create_explosion(game_services, anim_name="big_explosion")


def create_explosion(game_services, **kwargs):
    anim_name = kwargs["anim_name"]
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    body = ecs.create_component(entity, components.Body, {
        "is_collideable": False
    })
    anim = ecs.create_component(entity, components.AnimationComponent, {
        "anim_name": anim_name,
        "kill_on_finish": True,
        "brightness": 10
    })
    return entity


def create_player(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    player = ecs.create_component(entity, components.Player)
    body = ecs.create_component(entity, components.Body, {
        "mass": 100,
        "size": 35
    })
    power = ecs.create_component(entity, components.Power, {
        "capacity": 100,
        "recharge_rate": 10
    })
    explodes = ecs.create_component(entity, components.ExplodesOnDeath, {
        "explosion_assemblage": create_big_explosion
    })
    hp = ecs.create_component(entity, components.Hitpoints, {
        "hp": 50
    })
    shields = ecs.create_component(entity, components.Shields, {
        "hp": 5,
        "recharge_rate": 2
    })
    turrets = ecs.create_component(entity, components.Turrets)
    add_turrets(
        entity,
        [
            TurretSpec(weapon_assemblage=create_laser_weapon,
                       turret_assemblage=create_turret,
                       position=(-20, 0)),
            TurretSpec(weapon_assemblage=create_laser_weapon,
                       turret_assemblage=create_turret,
                       position=(20, 0))
        ]
    )
    thrusters = ecs.create_component(entity, components.Thrusters)
    add_thrusters(
        entity,
        standard_thruster_layout(40, 40, 50000)
    )
    anim = ecs.create_component(entity, components.AnimationComponent, {
        "anim_name": "player_ship"
    })


def create_turret(game_services):
    raise NotImplementedError("Not done yet")


def create_laser_weapon(game_services):
    raise NotImplementedError("Not done yet")


def add_turrets(entity, turret_specs):
    raise NotImplementedError("Not done yet.")


def add_thrusters(entity, thruster_specs):
    ecs = entity.ecs()
    thrusters = ecs.get_component(components.Thrusters)
    assert thrusters is not None
    for spec in thruster_specs:
        thruster_ent = ecs.create_entity()
        thruster_ent.name = "Thruster"
        thruster = ecs.create_component(thruster_ent, components.Thruster, {
            "position": spec.position,
            "orientation": spec.orientation,
            "max_thrust": spec.max_thrust
        })
        thruster.attached_to.entity = entity
        thrusters.thrusters.add_ref_to(thruster_ent)


def standard_thruster_layout(w, h, thrust):
    lateral_thrust = thrust/10.0
    backward_thrust = thrust/5.0
    layout = [
        ((-w/2, -h/2), (1, 0), lateral_thrust),
        ((-w/2, h/2), (1, 0), lateral_thrust),
        ((w/2, -h/2), (-1, 0), lateral_thrust),
        ((w/2, h/2), (-1, 0), lateral_thrust),
        ((0, -h/2), (0, 1), backward_thrust),
        ((0, h/2), (0, -1), thrust)
    ]
    return [ ThrusterSpec(position=l[0],
                          orientation=l[1],
                          max_thrust=l[2]) for l in layout ]