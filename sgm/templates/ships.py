from sgm import components as components
from sgm.templates.explosions import create_big_explosion
from sgm.templates.thrusters import add_thrusters, standard_thruster_layout
from sgm.templates.turrets import add_turrets, TurretSpec, create_turret
from sgm.templates.weapons import create_laser_weapon, \
    create_green_blaster_weapon


def add_power(entity, **kwargs):
    ecs = entity.game_services.get_entity_manager()
    power = ecs.create_component(entity, components.Power)
    power.capacity = kwargs["capacity"]
    power.recharge_rate = kwargs["recharge_rate"]


def add_shields(entity, **kwargs):
    ecs = entity.game_services.get_entity_manager()
    shields = ecs.create_component(entity, components.Shields)
    shields.hp = kwargs["hp"]
    shields.recharge_rate = kwargs["recharge_rate"]


def add_ship_components(entity, **kwargs):
    ecs = entity.game_services.get_entity_manager()

    body = ecs.create_component(entity, components.Body)
    body.mass = kwargs["mass"]
    body.size = kwargs["size"]

    explodes = ecs.create_component(entity, components.ExplodesOnDeath)
    explodes.explosion_template = create_big_explosion

    hp = ecs.create_component(entity, components.Hitpoints)
    hp.hp = kwargs["hp"]

    anim = ecs.create_component(entity, components.AnimationComponent)
    anim.anim_name = kwargs["anim_name"]


def create_player(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    player = ecs.create_component(entity, components.Player)
    add_ship_components(entity, mass=100, size=35, hp=50, anim_name="player_ship")
    add_power(entity, capacity=100, recharge_rate=10)
    add_shields(entity, hp=5, recharge_rate=2)
    turrets = ecs.create_component(entity, components.Turrets)
    add_turrets(
        entity,
        [
            TurretSpec(weapon_template=create_laser_weapon,
                       turret_template=create_turret,
                       position=(-20, 0)),
            TurretSpec(weapon_template=create_laser_weapon,
                       turret_template=create_turret,
                       position=(20, 0))
        ]
    )
    thrusters = ecs.create_component(entity, components.Thrusters)
    add_thrusters(
        entity,
        standard_thruster_layout(40, 40, 50000)
    )


def create_fighter(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    add_ship_components(mass=100, size=20, hp=1, anim_name="enemy_fighter")
    team = ecs.create_component(entity, components.Team, {
        "team": "enemy"
    })
    tracking = ecs.create_component(entity, components.Tracking, {})
    follows = ecs.create_component(entity, components.FollowsTracked, {
        "acceleration": 1000,
        "desired_distance_to_player": 500
    })
    turrets = ecs.create_component(entity, components.Turrets)
    add_turrets(
        entity,
        [
            TurretSpec(weapon_template=create_green_blaster_weapon,
                       turret_template=create_turret,
                       position=(0, -20))
        ]
    )
    thrusters = ecs.create_component(entity, components.Thrusters)
    add_thrusters(
        entity,
        standard_thruster_layout(40, 40, 50000)
    )
    return entity


def create_carrier(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    body = ecs.create_component(entity, components.Body, {
        "mass": 100,
        "size": 100
    })
    team = ecs.create_component(entity, components.Team, {
        "team": "enemy"
    })
    eod = ecs.create_component(entity, components.ExplodesOnDeath, {
        "explosion_template": create_big_explosion,
        "sound": "boom1.wav"
    })
    tracking = ecs.create_component(entity, components.Tracking, {})
    follows = ecs.create_component(entity, components.FollowsTracked, {
        "acceleration": 1000,
        "desired_distance_to_player": 500
    })
    hp = ecs.create_component(entity, components.Hitpoints, {
        "hp": 100
    })
    anim = ecs.create_component(entity, components.AnimationComponent, {
        "anim_name": "carrier-closed"
    })
    thrusters = ecs.create_component(entity, components.Thrusters)
    add_thrusters(
        entity,
        standard_thruster_layout(40, 40, 50000)
    )
    fighters = ecs.create_component(entity, components.LaunchesFighters, {
        "fighter_template": create_fighter,
        "num_fighters": 2,
        "spawn_period": 10,
        "takeoff_speed": 700,
        "takeoff_spread": 30
    })
    power = ecs.create_component(entity, components.Power, {
        "capacity": 100,
        "recharge_rate": 10
    })
    shields = ecs.create_component(entity, components.Shields, {
        "hp": 50,
        "recharge_rate": 10
    })
    return entity


def create_destroyer(game_services):
    ecs = game_services.get_entity_manager()
    entity = ecs.create_entity()
    body = ecs.create_component(entity, components.Body, {
        "mass": 100,
        "size": 40
    })
    team = ecs.create_component(entity, components.Team, {
        "team": "enemy"
    })
    eod = ecs.create_component(entity, components.ExplodesOnDeath, {
        "explosion_template": create_big_explosion,
        "sound": "boom1.wav"
    })
    tracking = ecs.create_component(entity, components.Tracking, {})
    follows = ecs.create_component(entity, components.FollowsTracked, {
        "acceleration": 1000,
        "desired_distance_to_player": 500
    })
    hp = ecs.create_component(entity, components.Hitpoints, {
        "hp": 40
    })
    anim = ecs.create_component(entity, components.AnimationComponent, {
        "anim_name": "enemy_destroyer"
    })
    turrets = ecs.create_component(entity, components.Turrets)
    add_turrets(
        entity,
        [
            TurretSpec(weapon_template=create_green_blaster_weapon,
                       turret_template=create_turret,
                       position=(-15, 0)),
            TurretSpec(weapon_template=create_green_blaster_weapon,
                       turret_template=create_turret,
                       position=(15, 0))
        ]
    )
    thrusters = ecs.create_component(entity, components.Thrusters)
    add_thrusters(
        entity,
        standard_thruster_layout(40, 40, 50000)
    )
    fighters = ecs.create_component(entity, components.LaunchesFighters, {
        "fighter_template": create_fighter,
        "num_fighters": 2,
        "spawn_period": 10,
        "takeoff_speed": 700,
        "takeoff_spread": 30
    })
    power = ecs.create_component(entity, components.Power, {
        "capacity": 100,
        "recharge_rate": 10
    })
    shields = ecs.create_component(entity, components.Shields, {
        "hp": 50,
        "recharge_rate": 50
    })
    return entity