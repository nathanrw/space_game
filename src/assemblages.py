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
    """
        # The component entity needs to have a Body or this won't work.
        body = component.entity.get_component(Body)
        assert body is not None

        # Load the turrets.
        turret_cfgs = component.config.get("turrets", [])
        for cfg in turret_cfgs:

            # Load the weapon fitted to the turret.
            weapon_config = self.game_services.get_resource_loader().load_config_file(cfg["weapon_config"])
            turret_config = self.game_services.get_resource_loader().load_config_file(cfg["turret_config"])

            # Create the turret entity.
            turret_entity = component.entity.ecs().create_entity(turret_config)

            # Get the turret component and attach the weapon entity.
            turret = turret_entity.get_component(Turret)
            assert turret is not None
            turret.weapon.entity = component.entity.ecs().create_entity(weapon_config)
            turret.position = Vec2d(cfg.get("position", (0, 0)))
            weapon = turret.weapon.entity.get_component(Weapon)
            assert weapon is not None
            weapon.owner.entity = turret_entity

            # Set the level so that turrets display on top of ships.
            anim = turret_entity.get_component(AnimationComponent)
            if anim is not None:
                anim.level = Renderer.LEVEL_MID_NEAR

            # Add the backreference and add to our list of turrets.
            turret.attached_to.entity = component.entity
            component.turrets.add_ref_to(turret_entity)

            # Set the turret's team.
            setup_team(component.entity, turret_entity)

            physics = component.entity.ecs().get_system(Physics)

            # Match position and velocity.
            physics.teleport(
                turret_entity,
                to_position=physics.local_to_world(body.entity, turret.position),
                to_velocity=body.velocity
            )

            # Pin the bodies together.
            physics.create_joint(
                component.entity,
                turret.position,
                turret_entity,
                Vec2d(0, 0)
            )
    :param game_services:
    :return:
    """
    raise NotImplementedError("Not done yet")


"""
Weapons:

components:
  src.components.Weapon:
    bullet_config: bullets/green_bullet.txt
    shots_per_second: 4
derive_from: weapons/red_blaster.txt



components:
  src.components.Weapon:
    type: beam
    range: 5000
    radius: 6
    damage: 30
    power_usage: 20




components:
  src.components.Weapon:
    bullet_config: bullets/red_bullet.txt
    bullet_speed: 2000
    shots_per_second: 10
    spread: 10
    shot_sound: 143609__d-w__weapons-synth-blast-03.wav



components:
  src.components.Weapon:
    shots_per_second: 25
derive_from: weapons/red_blaster.txt



components:
  src.components.Weapon:
    bullet_config: bullets/torpedo_bullet.txt
    bullet_speed: 1000
    shots_per_second: 1
    spread: 1
derive_from: weapons/red_blaster.txt





"""


def create_laser_weapon(game_services):
    raise NotImplementedError("Not done yet")


def add_turrets(entity, turret_specs):
    raise NotImplementedError("Not done yet.")



"""
components:
  src.components.DamageOnContact:
    damage: 1
  src.components.ExplodesOnDeath:
    explosion_config: explosions/green_explosion.txt
    sound: 234082__211redman112__lasgun-impact.ogg
  src.components.KillOnTimer:
    lifetime: 2
  src.components.AnimationComponent:
    anim_name: pewpew_green
    brightness: 0.5
  src.physics.Body:
    mass: 1
    size: 3


derive_from: bullets/base_bullet.txt


derive_from: bullets/base_bullet.txt

components:

  # A red laser.
  src.components.AnimationComponent:
    anim_name: pewpew_red

  # A red explosion.
  src.components.ExplodesOnDeath:
    explosion_config: explosions/red_explosion.txt



# A bullet that shoots more bullets!

derive_from: bullets/base_bullet.txt

components:

  # Does more damage than a regular bullet.
  src.components.DamageOnContact:
    damage: 5

  # A torpedo explodes, naturally!
  src.components.ExplodesOnDeath:
    explosion_config: explosions/big_explosion.txt

  # A torpedo has a team (it shoots and follows the opposite team.)
  src.components.Team: {}

  # A torpedo follows a target.
  src.components.Tracking: {}

  # A torpedo seeks out its target.
  src.components.FollowsTracked:
    acceleration: 3000
    desired_distance_to_player: 0.1

  # A torpedo is driven by thrusters.
  src.components.Thrusters:
    max_thrust: 100000

  # A torpedo has a small blaster turrent on board!
  src.components.Turrets:
    hardpoints:
    - weapon_config: enemies/torpedo_turret.txt
      x: 0
      y: 0

  # Make it look like a torpedo
  src.components.AnimationComponent:
    anim_name: rocket
    brightness: 0

  # Set the mass and size.
  src.physics.Body:
    mass: 10
    size: 10

"""


def create_bullet(game_services, **kwargs):
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


"""

Enemies


components:

  src.physics.Body:
    mass: 100
    size: 20

  src.components.Team:
    team: enemy

  src.components.ExplodesOnDeath:
    explosion_config: explosions/big_explosion.txt
    sound: boom1.wav

  src.components.Tracking: {}

  src.components.Hitpoints:
    hp: 1

  src.components.AnimationComponent:
    anim_name: enemy_fighter



derive_from: enemies/base_enemy.txt

components:

  src.components.Thrusters:
    max_thrust: 50000

  src.components.FollowsTracked:
    acceleration: 1000
    desired_distance_to_player: 500




derive_from: enemies/base_flying_enemy.txt

components:

  src.components.Hitpoints:
    hp: 100

  src.components.LaunchesFighters:
    fighter_config: enemies/fighter.txt
    num_fighters: 2
    spawn_period: 10
    takeoff_speed: 700
    takeoff_spread: 30

  src.components.AnimationComponent:
    anim_name: carrier-closed

  src.physics.Body:
    mass: 100
    size: 100

  # The ship is powered.
  src.components.Power:
    capacity: 100
    recharge_rate: 10

  # The ship is shielded.
  src.components.Shields:
    hp: 50
    recharge_rate: 10
    
    
    
    

derive_from: enemies/base_flying_enemy.txt

components:

  src.components.Hitpoints:
    hp: 40

  src.components.Turrets:
    turrets:
      - weapon_config: weapons/green_blaster.txt
        turret_config: enemies/turret.txt
        position: [-15, 0]
      - weapon_config: weapons/green_blaster.txt
        turret_config: enemies/turret.txt
        position: [15, 0]

  src.components.AnimationComponent:
    anim_name: enemy_destroyer

  src.physics.Body:
    mass: 100
    size: 40

  # The ship is powered.
  src.components.Power:
    capacity: 100
    recharge_rate: 10

  # The ship is shielded.
  src.components.Shields:
    hp: 50
    recharge_rate: 50




derive_from: enemies/base_flying_enemy.txt

components:

  # The ship has turrets.
  src.components.Turrets:
    turrets:
      - weapon_config: weapons/green_blaster.txt
        turret_config: enemies/turret.txt
        position: [0, -20]





derive_from: enemies/turret.txt





components:

  src.components.AnimationComponent:
    anim_name: enemy_turret

  src.physics.Body:
    mass: 1
    size: 1

  src.components.Turret: {}

  src.components.Power:
    capacity: 100
    recharge_rate: 10

  src.components.Team: {}

  src.components.Tracking: {}




"""



def create_destroyer(game_services, **kwargs):
    raise NotImplementedError("Not done yet.")

def create_carrier(game_services, **kwargs):
    raise NotImplementedError("Not done yet.")

def create_endgame_message(game_services, **kwargs):
    """
    components:
  src.components.KillOnTimer:
    lifetime: 10
  src.components.Text:
    text: Hello, World!
    font_colour:
      blue: 255
      green: 255
      red: 255
    font_name: res/fonts/nasdaqer/NASDAQER.ttf
    font_size: 62

    :param game_services:
    :param kwargs:
    :return:
    """
    raise NotImplementedError("Not done yet.")

def create_update_message(game_services, **kwargs):
    """
    components:
  src.components.KillOnTimer:
    lifetime: 4
  src.components.Text:
    text: Hello, World!
    blink: 1
    font_colour:
      blue: 255
      green: 255
      red: 255
    font_name: res/fonts/nasdaqer/NASDAQER.ttf
    font_size: 62

    :param game_services:
    :param kwargs:
    :return:
    """
    raise NotImplementedError("Not done yet.")

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