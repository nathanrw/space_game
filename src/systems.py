"""
System implementations.  Each system governs a particular aspect of the
simulation; for instance, a system exists to advance animations and another
exists to kill certain entities after a timer expires.

A System is registered with the entity manager at the start of the program. It
has an update() method which is called once per frame; update() methods are
invoked in order of system registration.

There is a general 1-1 correspondence between systems and component types, but
this isn't a hard and fast rule - a system might process entities with a
combination of compoent types, and more than one system might process
components of a given type. *Generally*, there will be a single 'main' system
for a given component type, which will be responsible for updating its fields
and doing the bulk of the processing relating to it, but other systems will
query the fields - and may even update them.

Entity relationships are defined in a rather ad hoc manner at present. A 1-1
relationship is modelled as a reference to an entity stored in a particular
component. For example, the 'Tracking' component, which is used to have one
entity 'follow' another, contains an entity reference - the tracked entity.
1-many relationships are similarly ad hoc. The pattern here is for the
'containing' component to store a list of entity references, while the
'contained' components store a back reference to the 'containing' entity. Any
'ownership' semantics are implemented on an ad hoc basis in the corresponding
system. For instance an entity with the 'Thruster' component will kill itself
when the entity it is attached to is killed.

Some rules are implemented as free functions, since they are needed in multiple
places.
"""

from config import Config
from ecs import ComponentSystem
from components import *
from physics import Physics
from direction_providers import *
from renderer import Renderer

import random
import numpy
import scipy.optimize


def towards(e1, e2):
    """ Get a direction from one entity to another. """
    b1 = e1.get_component(Body)
    b2 = e2.get_component(Body)
    if b1 is None or b2 is None:
        return Vec2d(0, 0)
    return b2.position - b1.position


def get_team(e):
    """ Get the team of an entity.  If the entity does not have a team then
    this returns None. """
    assert e is not None
    ret = None
    ct = e.get_component(Team)
    if ct is not None:
        if ct.parent.entity is not None:
            ret = get_team(ct.parent.entity)
        if ret is None:
            ret = ct.team
    return ret


def setup_team(e1, e2):
    """ Put one entity under the team leadership of another. """
    t1 = e1.get_component(Team)
    t2 = e2.get_component(Team)
    if t1 is not None and t2 is not None:
        t2.parent.entity = e1


def on_same_team(e1, e2):
    """ Are two entities friendly towards one another? """
    t1 = get_team(e1)
    t2 = get_team(e2)
    if t1 is None or t2 is None:
        return True
    return t1 == t2


def consume_power(e, amount):
    """ Consume an entity's power. """
    p = e.get_component(Power)
    if p is None:
        return 0
    elif amount <= p.power:
        p.power -= amount
        return amount
    else:
        p.overloaded = True
        return 0

def handle_damage_collision(dmg, hp):
    """ Used to implement the 'damage on contact' behaviour. 
    
    'dmg' is a DamageOnContact component
    
    'hp' is a Hitpoints component.
    """

    # If our entity is about to die we might be about to spawn an
    # explosion. If that's the case it should be travelling at the same
    # speed as the thing we hit. So match velocities before our entity is
    # killed.
    if dmg.config.get_or_default("destroy_on_hit", True):
        b1 = dmg.entity.get_component(Body)
        b2 = hp.entity.get_component(Body)
        if b1 is not None and b2 is not None:
            b1.velocity = b2.velocity
        do_explosion(dmg.entity)
        dmg.entity.kill()

    # Apply the damage.
    apply_damage_to_entity(dmg.config["damage"], hp.entity)


def do_explosion(entity):
    """ If an entity explodes, create the explosion. """
    explodes = entity.get_component(ExplodesOnDeath)
    body = entity.get_component(Body)
    if explodes is not None and body is not None:

        # Create the explosion.
        explosion = entity.ecs().create_entity(
            explodes.config["explosion_config"])
        teleport(explosion, body.position, body.velocity)

        # Shake the camera.
        cs = entity.ecs().get_system(CameraSystem)
        shake_factor = explodes.config.get_or_default("shake_factor", 1)
        cs.apply_shake(shake_factor, body.position)

        # Play a sound.
        sound = explodes.config.get_or_none("sound")
        if sound is not None:
            cs.play_sound(sound, body.position)


def apply_damage_to_entity(damage, entity):
    """ Apply damage to an object we've hit. """

    # Shields can mitigate damage.
    shields = entity.get_component(Shields)
    if shields is not None:
        shields.hp -= damage
        if shields.hp < 0:
            damage = -shields.hp
        else:
            damage = 0

    # Ok, apply the damage.
    hitpoints = entity.get_component(Hitpoints)
    if hitpoints is not None:
        hitpoints.hp -= damage
        if hitpoints.hp <= 0:
            do_explosion(entity)
            entity.kill()


def get_attached_entities(start_entity):
    """ Get the entities attached to the one given. """
    joints_entities = start_entity.ecs().query_include_queued(Joint)
    got = set()
    got.add(start_entity)
    while True:
        new = set()
        for joint_entity in joints_entities:
            joint = joint_entity.get_component(Joint)
            if joint.entity_a.entity is None or \
                            joint.entity_b.entity is None:
                continue
            e1 = joint.entity_a.entity
            e2 = joint.entity_b.entity
            if e1 in got and not e2 in got:
                new.add(e2)
            if e2 in got and not e1 in got:
                new.add(e1)
        if len(new) == 0:
            break
        else:
            got = got | new
    return got


def teleport(entity, to, to_velocity=None, to_orientation=None):
    """ Move an entity to a new position. """

    # Can only teleport a body!
    body = entity.get_component(Body)
    if body is None:
        return

    # Change in position for attached bodies.
    relative_movement = to - body.position
    relative_rotation = None
    if to_orientation is not None:
        relative_rotation = to_orientation - body.orientation
    relative_delta_v = None
    if to_velocity is not None:
        relative_delta_v = to_velocity - body.velocity

    # Move each attached entity the same distance and apply the same change
    # in orientation.
    to_move = get_attached_entities(entity)
    for attached_entity in to_move:
        attached_body = attached_entity.get_component(Body)
        attached_body.position += relative_movement
        if relative_delta_v is not None:
            attached_body.velocity += relative_delta_v
        if relative_rotation is not None:
            attached_body.orientation += relative_rotation


def local_to_world(entity, local_point):
    """ Convert a point in entity local coordinates to world space. """
    physics = entity.ecs().get_system(Physics)
    return physics.local_to_world(entity, local_point)


def world_to_local(entity, world_point):
    """ Convert a point in world space to entity local coordinates. """
    physics = entity.ecs().get_system(Physics)
    return physics.world_to_local(entity, world_point)


def hit_scan(
        from_entity,
        local_origin=Vec2d(0,0),
        local_direction=Vec2d(0,-1),
        distance=1000,
        radius=1,
        filter_func=lambda x: True
):
    """ Do a hit scan from an entity. """
    aug_filter = lambda x: x != from_entity and not x in get_attached_entities(from_entity)
    physics = from_entity.ecs().get_system(Physics)
    return physics.hit_scan(from_entity, local_origin, local_direction,
                            distance, radius, aug_filter)


class FollowsTrackedSystem(ComponentSystem):
    """ Updates entities that follow other entities around. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [FollowsTracked, Tracking, Body])

    def update(self, dt):
        """ Update the followers. """

        for entity in self.entities():

            # If it's not tracking anything then don't do anything.
            tracked_entity = entity.get_component(Tracking).tracked.entity
            if tracked_entity is None:
                continue

            # Get the pair of bodies.
            this_body = entity.get_component(Body)
            that_body = tracked_entity.get_component(Body)
            assert this_body is not None
            assert that_body is not None

            # There is more than one way to follow...
            follows = entity.get_component(FollowsTracked)
            if follows.follow_type == "instant":
                this_body.position = that_body.position
                continue

            displacement = that_body.position - this_body.position
            rvel = that_body.velocity - this_body.velocity
            target_dist = follows.config["desired_distance_to_player"]

            # distality is a mapping of distance onto the interval [0,1) to
            # interpolate between two components
            distality = 1 - 2 ** ( - displacement.length / target_dist )
            direction = ( 1 - distality ) * rvel.normalized() + distality * displacement.normalized()

            # Determine the fraction of our thrust to apply. This is governed by
            # how far away the target is, and how far away we want to be.
            frac = min(max(displacement.length / target_dist, rvel.length/200), 1)


            # Apply force in the interpolated direction.
            thrust = this_body.mass * follows.config["acceleration"]
            force = frac * thrust * direction
            physics = self.game_services.get_entity_manager().get_system(Physics)
            physics.apply_force_at_local_point(
                entity,
                force,
                Vec2d(0, 0)
            )


class WeaponSystem(ComponentSystem):
    """ Updates entities that shoot bullets. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Weapon])

    def update(self, dt):
        """ Update the guns. """
        for entity in self.entities():
            weapon = entity.get_component(Weapon)
            if weapon.owner.entity is None:
                entity.kill()
                continue
            if weapon.shot_timer > 0:
                weapon.shot_timer -= dt
            if weapon.shooting_at is not None:
                if weapon.weapon_type == "projectile_thrower":
                    self.shoot_bullet(weapon, dt)
                elif weapon.weapon_type == "beam":
                    self.shoot_beam(weapon, dt)
                else:
                    # Unknown weapon style.
                    pass

    def shoot_beam(self, weapon, dt):
        """ Shoot a beam. """
        power_consumed = consume_power(weapon.owner.entity, weapon.config["power_usage"] * dt)
        if power_consumed == 0:
            weapon.shooting_at = None
        else:
            (hit_entity, weapon.impact_point, weapon.impact_normal) = hit_scan(
                weapon.owner.entity,
                Vec2d(0, 0),
                Vec2d(0, -1),
                weapon.config["range"],
                weapon.config["radius"]
            )
            if hit_entity is not None:
                apply_damage_to_entity(weapon.config["damage"]*dt, hit_entity)

    def shoot_bullet(self, weapon, dt):
        """ Shoot a bullet, for projectile thrower type weapons. """

        # If it's time, shoot a bullet and rest the timer. Note that
        # we can shoot more than one bullet in a time step if we have
        # a high enough rate of fire.
        while weapon.shot_timer <= 0:

            # These will be the same for each shot, so get them here...
            body = weapon.owner.entity.get_component(Body)
            shooting_at_dir = weapon.shooting_at.direction()

            # Update the timer.
            weapon.shot_timer += 1.0/weapon.config["shots_per_second"]

            # Can't spawn bullets if there's nowhere to put them!
            if body is None:
                return

            # Position the bullet somewhere sensible.
            separation = body.size*4
            bullet_position = Vec2d(body.position) + shooting_at_dir * separation

            # Work out the muzzle velocity.
            muzzle_velocity = shooting_at_dir * weapon.config["bullet_speed"]
            spread = weapon.config["spread"]
            muzzle_velocity.rotate_degrees(random.random() * spread - spread)
            bullet_velocity = body.velocity+muzzle_velocity

            # Play a sound.
            shot_sound = weapon.config.get_or_none("shot_sound")
            if shot_sound is not None:
                cs = self.game_services.get_entity_manager().get_system(CameraSystem)
                cs.play_sound(shot_sound, body.position)

            # Create the bullet.
            bullet_entity = weapon.entity.ecs().create_entity(weapon.config["bullet_config"])

            # Set the position.
            bullet_orientation = shooting_at_dir.normalized().get_angle_degrees()+90
            teleport(bullet_entity, bullet_position, bullet_velocity, bullet_orientation)

            # Set the team.
            setup_team(weapon.owner.entity, bullet_entity)


class TrackingSystem(ComponentSystem):
    """ Update entities that track other entities. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Tracking, Body])

    def update(self, dt):
        """ Update the trackers. """
        for entity in self.entities():
            self_body = entity.get_component(Body)
            tracking = entity.get_component(Tracking)
            if tracking.tracked.entity is None and tracking.track_type == "team":
                def f(body):
                    return not on_same_team(entity, body.entity)
                closest = entity.ecs().get_system(Physics).closest_body_with(
                    self_body.position,
                    f
                )
                if closest is not None:
                    tracking.tracked.entity = closest.entity


class LaunchesFightersSystem(ComponentSystem):
    """ Updates entities that launch fighters. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [LaunchesFighters])

    def update(self, dt):
        """ Updates the carriers. """
        for entity in self.entities():
            launcher = entity.get_component(LaunchesFighters)
            body = entity.get_component(Body)
            if body is None:
                continue
            if len(launcher.launched) == 0 and launcher.spawn_timer.tick(dt):
                launcher.spawn_timer.reset()
                for i in range(launcher.config["num_fighters"]):
                    direction = Vec2d(0, 1)
                    spread = launcher.config["takeoff_spread"]
                    direction.rotate_degrees(spread*random.random()-spread/2.0)

                    # Launch!
                    child = entity.ecs().create_entity(launcher.config["fighter_config"])
                    launcher.launched.add_ref_to(child)
                    setup_team(entity, child)
                    teleport(child,
                             body.position + (body.size + 10) * direction,
                             body.velocity + direction * launcher.config["takeoff_spread"])


class KillOnTimerSystem(ComponentSystem):
    """ Updates entities that die after a timer. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [KillOnTimer])

    def update(self, dt):
        """ Update the entities. """
        for entity in self.entities():
            c = entity.get_component(KillOnTimer)
            if c.lifetime.tick(dt):
                entity.kill()


class PowerSystem(ComponentSystem):
    """ Updates entities that store / produce power. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Power])

    def update(self, dt):
        """ Update the entities."""
        for e in self.entities():
            power = e.get_component(Power)
            if power.overloaded:
                if power.overload_timer.tick(dt):
                    power.overloaded = False
                    power.overload_timer.reset()
            else:
                power.power = min(power.capacity, power.power + power.recharge_rate * dt)


class ShieldSystem(ComponentSystem):
    """ Updates entities with shields. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Shields])

    def update(self, dt):
        """ Update the shields. """
        for e in self.entities():
            shields = e.get_component(Shields)
            power = e.get_component(Power)
            if power is None:
                shields.hp = 0
            else:
                if shields.overloaded:
                    if shields.overload_timer.tick(dt):
                        shields.overloaded = False
                        shields.overload_timer.reset()
                else:
                    recharge_amount = min(shields.max_hp - shields.hp, shields.recharge_rate * dt)
                    shields.hp = min(shields.max_hp, shields.hp + consume_power(e, recharge_amount))


class TextSystem(ComponentSystem):
    """ Updates entities with scrolling text. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Text])

    def update(self, dt):
        """ Update the entities. """
        for e in self.entities():
            text = e.get_component(Text)
            if text.blink:
                if text.blink_timer.tick(dt):
                    text.blink_timer.reset()
                    text.visible = not text.visible
            if text.warning is not None:
                text.offset += text.scroll_speed * dt
                text.offset = text.offset % (text.warning.get_width()+text.padding)


class AnimSystem(ComponentSystem):
    """ Updates entities with animations. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [AnimationComponent])

    def update(self, dt):
        """ Update the animations. """
        for e in self.entities():
            c = e.get_component(AnimationComponent)
            if c.anim.tick(dt):
                if c.config.get_or_default("kill_on_finish", 0):
                    e.kill()
                else:
                    c.anim.reset()


class ThrusterSystem(ComponentSystem):
    """ Updates entities that are thrusters. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Thruster])

    def update(self, dt):
        """ Update the thrusters. """
        for entity in self.entities():
            thruster = entity.get_component(Thruster)
            attached = thruster.attached_to.entity
            if attached is None:
                entity.kill()
            else:
                physics = self.game_services.get_entity_manager().get_system(Physics)
                physics.apply_force_at_local_point(
                    attached,
                    thruster.thrust * thruster.direction,
                    thruster.position
                )


class ThrustersSystem(ComponentSystem):
    """ Update entities with thruster based movement. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Body, Thrusters])

    def on_component_add(self, component):
        """ When thrusters are added to an entity we need to create the actual
        thrusters themselves, which are specified in the config. """
        if component.__class__ == Thrusters:
            thruster_cfgs = component.config.get_or_default("thrusters", [])
            for cfg in thruster_cfgs:
                thruster_ent = component.entity.ecs().create_entity()
                thruster = Thruster(thruster_ent, self.game_services, cfg)
                thruster.attached_to.entity = component.entity
                thruster_ent.add_component(thruster)
                thruster_ent.name = "Thruster"
                component.thrusters.add_ref_to(thruster_ent)

    def update(self, dt):
        """ Update the entities. """
        for entity in self.entities():
            body = entity.get_component(Body)
            thrusters = entity.get_component(Thrusters)

            # Counteract excessive spin when an input turn direction has not
            # been given.
            turn = thrusters.turn
            if turn == 0 and thrusters.direction.x == 0:
                excessive_spin = 10
                if body.angular_velocity > excessive_spin:
                    turn = -1
                elif body.angular_velocity < -excessive_spin:
                    turn = 1

            # Fire thrusters to achieve desired spin and direction.
            self.fire_correct_thrusters(thrusters, thrusters.direction, turn)

    def compute_correct_thrusters(self, thrusters, direction, turn):
        """ Perform logic to determine what engines are firing based on the
        desired direction. Automatically counteract spin. We cope with an
        arbitrary configuration of thrusters through use of a mathematical
        optimisation algorithm (scipy.optimize.minimize.)

        Variables: t0, t1, t2, ...
        Function: g . f where
                  f(t0, t1, t2, ...) -> (acceleration, moment)
                  g(acceleration, moment) -> distance from desired (accel, moment)
        Constraint: t0min <= t0 <= t0max, ...

        Note: there may be a better way of solving this problem, I
        don't know. I will try to state the problem clearly here so
        that a better solution might present itself:

        Note: notation a little odd in the following:

        We have a set of N thrusters, (Tn, Dn, Pn, TMAXn), where "Tn" is
        the thruster's current (scalar) thrust, Pn is its position,
        and FMAXn is the maximum thrust it can exert. Dn is the direction
        of thrust, so the force currently being exerted, Fn, is Tn*Dn.

        The acceleration due to a given thruster:

            An = m * Fn

        where m is the mass of the body.

        The centre of mass is the origin O.

        The torque due to a given thruster is therefore

            Qn = |Pn| * norm(orth(Pn)) * Fn.

        The resultant force on the body, F', is F0+F1+...+Fn

        The resultant torque on the body, Q', is Q0+Q1+...+Qn

        The following constraints are in effect:

            T0 >= 0, T1 >= 0, ..., Tn >= 0

            T0 <= TMAX0, T1 <= TMAX1, Tn <= TMAXn

        In my implementation here, the vector T0..n is the input array for a
        function to be minimised.

        Note that this function is very slow. Some sort of caching scheme will be
        a must - and it would be good to share identical configurations between
        entities.

        I don't know whether there is an analytical solution to this problem.

        """

        def f(thrusts):
            """ Objective function. Determine the resultant force and torque on
            the body, and then apply heuristics (absolute guesswork!!) to determine
            the fitness. We can then use a minimisation algorithm to optimise the
            thruster configuration. """

            # Calculate the resultant force and moment from applying all thrusters.
            resultant_force = Vec2d(0, 0);
            resultant_moment = 0
            for i in range(0, len(thrusts)):
                thruster = thrusters.thrusters[i].get_component(Thruster)
                thrust = float(thrusts[i])
                force = thruster.direction * thrust
                resultant_force += force
                resultant_moment += thruster.position.length * thruster.position.perpendicular_normal().dot(force)

            # We want to maximise the force in the direction in which we want to
            # be thrusting.
            force_objective = direction.normalized().dot(resultant_force)

            # We want to maximise the torque in the direction we want.
            moment_objective = numpy.sign(turn) * resultant_moment

            # We negate the values because we want to *minimise*
            return -force_objective - moment_objective

        # Initial array of values.
        thrusts = numpy.zeros(len(thrusters.thrusters))

        # Thrust bounds.
        thrust_bounds = [(0, thruster.get_component(Thruster).max_thrust) for thruster in thrusters.thrusters]

        # Optimise the thruster values.
        return scipy.optimize.minimize(f, thrusts, method="TNC", bounds=thrust_bounds)

    def fire_correct_thrusters(self, thrusters, direction, torque):
        """ Perform logic to determine what engines are firing based on the
        desired direction. Automatically counteract spin. """

        # If no thrusters to fire then don't bother!
        if len(thrusters.thrusters) == 0:
            return

        # By default the engines should be off.
        for entity in thrusters.thrusters:
            thruster = entity.get_component(Thruster)
            thruster.thrust = 0

        # Come up with a dictionary key.
        key = (direction.x, direction.y, torque, len(thrusters.thrusters))

        # Ensure a configuration exists for this input.
        if not key in thrusters.thruster_configurations:
            thrusters.thruster_configurations[key] = \
                self.compute_correct_thrusters(thrusters, direction, torque)

        # Get the cached configuration and set the thrust.
        result = thrusters.thruster_configurations[key]
        for i in range(0, len(result.x)):
            thruster = thrusters.thrusters[i].get_component(Thruster)
            thruster.thrust = float(result.x[i])


class WaveSpawnerSystem(ComponentSystem):
    """ Spawns waves of enemies. """

    def __init__(self):
        ComponentSystem.__init__(self, [])
        self.wave = 1
        self.spawned = EntityRefList()
        self.message = None
        self.done = False
        self.endgame_timer = Timer(15)

    def update(self, dt):
        """ Update the spawner. """

        # Check for end condition and show game ending message if so.
        if self.done:
            if self.endgame_timer.tick(dt):
                self.game_services.end_game()
        elif self.player_is_dead() or self.max_waves():
            self.done = True
            txt = "GAME OVER"
            if self.max_waves():
                txt = "VICTORY"
            message = self.game_services.get_entity_manager().create_entity("endgame_message.txt")
            message.get_component(Text).text = txt

        # If the wave is dead and we're not yet preparing (which displays a timed message) then
        # start preparing a wave.
        if self.wave_is_dead() and self.message is None:
            self.prepare_for_wave()

        # If we're prepared to spawn i.e. the wave is dead and the message has gone, spawn a wave!
        if self.prepared_to_spawn():
            self.spawn_wave()

    def player_is_dead(self):
        """ Check whether the player is dead. """
        players = self.game_services.get_entity_manager().query(Player)
        return len(players) == 0

    def spawn_wave(self):
        """ Spawn a wave of enemies, each one harder than the last."""
        players = self.game_services.get_entity_manager().query(Player)
        if len(players) == 0:
            return
        player = players[0]
        player_body = player.get_component(Body)
        self.wave += 1
        for i in range(self.wave-1):
            enemy_type = random.choice(("enemies/destroyer.txt",
                                        "enemies/carrier.txt"))
            rnd = random.random()
            x = 1 - rnd*2
            y = 1 - (1-rnd)*2
            enemy_position = player_body.position + Vec2d(x, y)*500
            entity = self.game_services.get_entity_manager().create_entity(enemy_type)
            entity.get_component(Team).team = "enemy"
            teleport(entity, enemy_position)
            self.spawned.add_ref_to(entity)

    def wave_is_dead(self):
        """ Has the last wave been wiped out? """
        return len(self.spawned) == 0

    def prepare_for_wave(self):
        """ Prepare for a wave. """
        self.message = self.game_services.get_entity_manager().create_entity("update_message.txt")
        self.message.get_component(Text).text = "WAVE %s PREPARING" % self.wave

    def prepared_to_spawn(self):
        """ Check whether the wave is ready. """
        if self.message is None or not self.wave_is_dead():
            return False
        if self.message.is_garbage:
            self.message = None
            return True
        return False

    def max_waves(self):
        """ Check whether the player has beaten enough waves. """
        return self.wave == 10


class CameraSystem(ComponentSystem):
    """ Manages cameras."""

    def __init__(self):
        """ Initialise the system. """
        ComponentSystem.__init__(self, [Camera, Body])

    def apply_shake(self, shake_factor, position):
        """ Apply a screen shake effect. """
        for camera_ent in self.entities():
            camera = camera_ent.get_component(Camera)
            body = camera_ent.get_component(Body)
            displacement = body.position - position
            distance = displacement.length
            max_dist = camera.screen_diagonal * 2
            amount = max(shake_factor * (1.0 - distance/max_dist), 0)
            camera.shake = min(camera.shake+amount, camera.max_shake)

    def play_sound(self, sound, position):
        """ Play a sound at a position. """
        entities = self.entities()
        if len(entities) > 0:
            sound = self.game_services.get_resource_loader().load_sound(sound)
            camera_position = entities[0].get_component(Body).position
            sound.play_positional(position - camera_position)

    def update(self, dt):
        """ Update the cameras. """
        for camera_ent in self.entities():
            camera = camera_ent.get_component(Camera)
            if camera.shake > 0:
                camera.shake -= dt * camera.damping_factor
            if camera.shake < 0:
                camera.shake = 0
            camera.vertical_shake = (1-2*random.random()) * camera.shake
            camera.horizontal_shake = (1-2*random.random()) * camera.shake


class TurretSystem(ComponentSystem):
    """ Manage entities that are turrets. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Turret])

    def update(self, dt):
        """ Update the system. """
        for entity in self.entities():

            # Kill detached turrets
            turret = entity.get_component(Turret)
            if turret.attached_to.entity is None:
                entity.kill()
                continue

            # Get body
            body = entity.get_component(Body)
            if body is None:
                continue

            # Get the weapon
            gun_ent = turret.weapon.entity
            if gun_ent is None:
                continue
            gun = gun_ent.get_component(Weapon)

            attached_body = turret.attached_to.entity.get_component(Body)
            if attached_body is None:
                continue

            # Get the tracked body.  Note the special case for the player. This
            # could be made more elegant!
            shooting_at = turret.shooting_at
            if shooting_at is None and turret.attached_to.entity.get_component(Player) is None:
                # Get tracked entity.
                tracking = entity.get_component(Tracking)
                if tracking is not None:
                    tracked = tracking.tracked.entity
                    if tracked is not None:
                        shooting_at = DirectionProviderBody(entity, tracked)
            if shooting_at is not None:
                body.orientation = 90 + shooting_at.direction().angle_degrees
            body.angular_velocity = 0

            # Stop the gun if we've stopped shooting
            if shooting_at is None and gun.shooting_at is not None:
                gun.shooting_at = None

            # Shoot at the object we're tracking.
            if gun.shooting_at is None:
                if not turret.can_shoot and turret.fire_timer.tick(dt):
                    turret.fire_timer.reset()
                    turret.can_shoot = True
                if turret.can_shoot:
                    (hit_entity, hit_point, hit_normal) = hit_scan(entity)
                    if hit_entity is None or not on_same_team(entity, hit_entity):
                        turret.can_shoot = False
                        gun.shooting_at = shooting_at
            else:
                if turret.burst_timer.tick(dt):
                    turret.burst_timer.reset()
                    gun.shooting_at = None


class TurretsSystem(ComponentSystem):
    """ Manages entities that have a set of turrets attached to them. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Turrets])

    def update(self, dt):
        """ Update the system. """
        pass

    def on_component_add(self, component):
        """ When the turrets component is added we need to create the turrets
        themselves which are specified in the config"""

        # The component entity needs to have a Body or this won't work.
        body = component.entity.get_component(Body)
        assert body is not None

        # Load the turrets.
        turret_cfgs = component.config.get_or_default("turrets", [])
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
            turret.position = Vec2d(cfg.get_or_default("position", (0, 0)))
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

            # Match position and velocity.
            turret_body = turret_entity.get_component(Body)
            turret_body.position = local_to_world(body.entity, turret.position)
            turret_body.velocity = body.velocity

            # Pin the bodies together.
            joint_entity = component.entity.ecs().create_entity()
            joint = Joint(joint_entity, self.game_services, Config())
            joint.entity_a.entity = component.entity
            joint.entity_a_local_point = turret.position
            joint.entity_b.entity = turret_entity
            joint.entity_b_local_point = Vec2d(0, 0)
            joint_entity.add_component(joint)

            
class SolarSystem(ComponentSystem):
    """ Manages the procession of the celestial spheres. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [CelestialBody])

    def update(self, dt):
        """ Update the system. """
        for entity in self.entities():
            celestial_body = entity.get_component(CelestialBody)
            celestial_body.parameter += dt