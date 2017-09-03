from ecs import ComponentSystem
from behaviours import *


def towards(e1, e2):
    """ Get a direction from one entity to another. """
    b1 = e1.get_component(Body)
    b2 = e2.get_component(Body)
    if b1 is None or b2 is None:
        return Vec2d(0, 0)
    return b2.position - b1.position


def on_same_team(self, e1, e2):
    """ Are two entities friendly towards one another? """
    t1 = e1.get_component(Team)
    t2 = e2.get_component(Team)

    # If either or both not got team component, then on same team.
    if t1 is None != t2 is None:
        return True

    # If both have team component but either not on a team, then on same team.
    if t1.__team == None or t2.__team == None:
        return True

    # Otherwise on same team if teams match.
    return t1.__team == t2.__team


def consume_power(self, e, amount):
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
        hitpoints.receive_damage(damage)
        hitpoints.hp -= amount

        # If the entities HP is below zero then it must die!
        if hitpoints.hp <= 0:

            # Make the entity explode!
            explodes = entity.get_component(ExplodesOnDeath)
            body = entity.get_component(Body)
            if explodes is not None and body is not None:

                # Create the explosion.
                explosion = entity.ecs().create_entity(explodes.config["explosion_config"])
                explosion_body = explosion.get_component(Body)
                explosion_body.position = body.position
                explosion_body.velocity=body.velocity

                # Shake the camera.
                camera = entity.game_services.get_camera()
                shake_factor = explodes.config.get_or_default("shake_factor", 1)
                camera.apply_shake(shake_factor, body.position)

                # Play a sound.
                sound = explodes.config.get_or_none("sound")
                if sound is not None:
                    camera.play_sound(body, sound)

            # Ok, kill the entity.
            entity.kill()


class FollowsTrackedSystem(ComponentSystem):
    """ Updates entities that follow other entities around. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [FollowsTracked, Tracking, Body])

    def update(self, dt):
        """ Update the followers. """

        for entity in self.entities():

            # If it's not tracking anything then don't do anything.
            tracked_entity = entity.get_component(Tracking).get_tracked()
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
            target_dist = self.config["desired_distance_to_player"]

            # distality is a mapping of distance onto the interval [0,1) to
            # interpolate between two behaviours
            distality = 1 - 2 ** ( - displacement.length / target_dist )
            direction = ( 1 - distality ) * rvel.normalized() + distality * displacement.normalized()

            # Determine the fraction of our thrust to apply. This is governed by
            # how far away the target is, and how far away we want to be.
            frac = min(max(displacement.length / target_dist, rvel.length/200), 1)

            # Apply force in the interpolated direction.
            thrust = this_body.mass * self.config["acceleration"]
            force = frac * thrust * direction
            this_body.force = force


class ShootsAtTrackedSystem(ComponentSystem):
    """ Updates entities that shoot at other entities. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init(self, [ShootsAtTracked, Body, Weapon, Tracking])

    def update(self, dt):
        """ Update the shooters. """

        for entity in self.entities():

            # Get components.
            shooter = entity.get_component(ShootsAtTracked)
            body = entity.get_component(Body)
            gun = entity.get_component(Weapon)
            tracking = entity.get_component(Tracking)

            # Get the tracked body.
            tracked = tracking.tracked.entity
            if tracked is None:
                return
            tracked_body = tracked.get_component(Body)

            # Point at the object we're tracking. Note that in future it would be
            # good for this to be physically simulated, but for now we just hack
            # it in...
            direction = (tracked_body.position - body.position).normalized()
            body.orientation = 90 + direction.angle_degrees

            # Shoot at the object we're tracking.
            if not gun.shooting:
                if not shooter.can_shoot and shooter.fire_timer.tick(dt):
                    shooter.fire_timer.reset()
                    shooter.can_shoot = True
                if shooter.can_shoot:
                    (hit_body, hit_point, hit_normal) = body.hit_scan()
                    if hit_body == tracked_body:
                        shooter.can_shoot = False
                        gun.shooting_at = DirectionProviderBody(entity, tracked)
            else:
                if shooter.burst_timer.tick(dt):
                    shooter.burst_timer.reset()
                    gun.shooting_at = None


class WeaponSystem(ComponentSystem):
    """ Updates entities that shoot bullets. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Weapon, Body])

    def update(self, dt):
        """ Update the guns. """
        for entity in self.entities():
            weapon = entity.get_component(Weapon)
            if weapon.owner.entity is None:
                entity.kill()
                continue
            if weapon.shot_timer > 0:
                weapon.shot_timer -= dt
            if weapon.shooting:
                if weapon.weapon_type == "projectile_thrower":
                    self.shoot_bullet(weapon, dt)
                elif self.weapon_type == "beam":
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
            body = weapon.owner.entity.get_component(Body)
            (hit_body, weapon.impact_point, weapon.impact_normal) = body.hit_scan(
                Vec2d(0, 0),
                Vec2d(0, -1),
                weapon.config["range"],
                weapon.config["radius"]
            )
            if hit_body is not None:
                apply_damage_to_entity(weapon.config["damage"]*dt, hit_body.entity)

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
            weapon.shot_timer += 1.0/self.config["shots_per_second"]

            # Can't spawn bullets if there's nowhere to put them!
            if body is None:
                return

            # Position the bullet somewhere sensible.
            separation = body.size*2
            bullet_position = Vec2d(body.position) + shooting_at_dir * separation

            # Work out the muzzle velocity.
            muzzle_velocity = shooting_at_dir * weapon.config["bullet_speed"]
            spread = weapon.config["spread"]
            muzzle_velocity.rotate_degrees(random.random() * spread - spread)
            bullet_velocity = body.velocity+muzzle_velocity

            # Play a sound.
            shot_sound = weapon.config.get_or_none("shot_sound")
            if shot_sound is not None:
                weapon.entity.game_services.get_camera().play_sound(body, shot_sound)

            # Create the bullet.
            bullet_entity = weapon.entity.ecs().create_entity(weapon.config["bullet_config"])
            body = bullet_entity.get_component(Body)
            if body is not None:
                body.position = bullet_position
                body.velocity = bullet_velocity
                body.orientation = shooting_at_dir.normalized().get_angle_degrees()+90
            team = bullet_entity.get_component(Team)
            if team is not None:
                team.team = weapon.owner.entity.get_component(Team).team


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
                self_team = entity.get_component(Team) # optional
                def f(body):
                    team = body.entity.get_component(Team)
                    if self_team is None or team is None:
                        return False
                    return not team.on_same_team(self_team)
                closest = self.entity.ecs().get_system(Physics).closest_body_with(
                    self_body.position,
                    f
                )
                if closest:
                    tracking.tracked.entity = closest.entity


class LaunchesFightersSystem(ComponentSystem):
    """ Updates entities that launch fighters. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [LaunchesFighers, Body, Tracking, Team])

    def update(self, dt):
        """ Updates the carriers. """
        for entity in self.entities():
            launcher = entity.get_component(LaunchesFighters)
            body = entity.get_component(Body)
            tracking = entity.get_component(Tracking)
            team = entity.get_component(Team)
            if launcher.spawn_timer.tick(dt):
                launcher.spawn_timer.reset()
                for i in range(launcher.config["num_fighters"]):
                    direction = towards(entity, tracking.tracked.entity)
                    spread = launcher.config["takeoff_spread"]
                    direction.rotate_degrees(spread*random.random()-spread/2.0)

                    # Launch!
                    child = entity.ecs().create_entity(launcher.config["fighter_config"])
                    child_team = child.get_component(Team)
                    if child_team is not None:
                        child_team.team = team.get_team(),
                    child_body = child.get_component(Body)
                    if child_body is not None:
                        child_body.position=body.position
                        child_body.velocity=body.velocity + direction * launcher.config["takeoff_speed"]


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
                text.offs += text.scroll_speed * dt
                text.offs = text.offs % (text.warning.get_width()+text.padding)


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
                body = attached.get_component(Body)
                body.apply_force_at_local_point(thruster.amount * thruster.direction, thruster.position)


class ThrustersSystem(ComponentSystem):
    """ Update entities with thruster based movement. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Body, Thrusters])

    def on_component_add(self, component):
        """ When thrusters are added to an entity we need to create the actual
        thrusters themselves, which are specified in the config. """
        thruster_cfgs = component.config.get_or_default("thrusters", [])
        for cfg in thruster_cfgs:
            thruster_ent = component.entity.ecs().create_entity()
            thruster = Thruster(thruster_ent, self.game_services, cfg)
            thruster.attached_to.entity = component.entity
            thruster_ent.add_component(thruster)

    def update(self, dt):
        """ Update the entities. """
        for entity in self.entities():
            body = entity.get_component(Body)
            thrusters = entity.get_component(Thrusters)

            # Counteract excessive spin when an input turn direction has not
            # been given.
            turn = thrusters.turn
            if turn == 0 and self.__direction.x == 0:
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
                thrust = float(thrusts[i])
                resultant_force += self.__thrusters[i].force_with_thrust(thrust)
                resultant_moment += self.__thrusters[i].moment_with_thrust(thrust)

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
        thrust_bounds = [(0, thruster.entity.get_component(Thruster).max_thrust) for thruster in thrusters.thrusters]

        # Optimise the thruster values.
        return scipy.optimize.minimize(f, thrusts, method="TNC", bounds=thrust_bounds)

    def fire_correct_thrusters(self, thrusters, direction, torque):
        """ Perform logic to determine what engines are firing based on the
        desired direction. Automatically counteract spin. """

        # By default the engines should be off.
        for ref in thrusters.thrusters:
            thruster = ref.entity.get_component(Thruster)
            thruster.thrust = 0

        # Come up with a dictionary key.
        key = (direction.x, direction.y, torque)

        # Ensure a configuration exists for this input.
        if not key in thrusters.thruster_configurations:
            thrusters.thruster_configurations[key] = \
                self.compute_correct_thrusters(thrusters, direction, torque)

        # Get the cached configuration and set the thrust.
        result = thrusters.thruster_configurations[key]
        for i in range(0, len(result.x)):
            thruster = thrusters.thrusters[i].entity.get_component(Thruster)
            thruster.thrust = float(result.x[i])


class WaveSpawnerSystem(ComponentSystem):
    """ Spawns waves of enemies. """

    def __init__(self):
        ComponentSystem.__init__(self, [])
        self.wave = 1
        self.spawned = []
        self.message = None
        self.done = False
        self.endgame_timer = Timer(15)

    def update(self, dt):
        """ Update the spawner. """

        # Check for end condition and show game ending message if so.
        if self.done:
            if self.endgame_timer.tick():
                self.game_services.end_game()
        elif self.player_is_dead() or self.max_waves():
            self.done = True
            txt = "GAME OVER"
            if self.max_waves():
                txt = "VICTORY"
            message = self.game_services.get_entity_manager().create_entity("endgame_message.txt", text=txt)

        # If the wave is dead and we're not yet preparing (which displays a timed message) then
        # start preparing a wave.
        if self.wave_is_dead() and self.message is None:
            self.prepare_for_wave()

        # If we're prepared to spawn i.e. the wave is dead and the message has gone, spawn a wave!
        if self.prepared_to_spawn():
            self.spawn_wave()

    def player_is_dead(self):
        """ Check whether the player is dead. """
        player = self.game_services.get_player()
        return player.is_garbage

    def spawn_wave(self):
        """ Spawn a wave of enemies, each one harder than the last."""
        player = self.game_services.get_player()
        player_body = player.get_component(Body)
        self.wave += 1
        for i in range(self.wave-1):
            enemy_type = random.choice(("enemies/destroyer.txt",
                                        "enemies/carrier.txt"))
            rnd = random.random()
            x = 1 - rnd*2
            y = 1 - (1-rnd)*2
            enemy_position = player_body.position + Vec2d(x, y)*500
            self.spawned.append(
                self.game_services.get_entity_manager().create_entity(
                    enemy_type,
                    position=enemy_position,
                    team="enemy"
                )
            )

    def wave_is_dead(self):
        """ Has the last wave been wiped out? """
        self.spawned = list( filter(lambda x: not x.is_garbage, self.spawned) )
        return len(self.spawned) == 0

    def prepare_for_wave(self):
        """ Prepare for a wave. """
        self.message = self.game_services.entity_manager().create_entity(
            "update_message.txt",
            text="WAVE %s PREPARING" % self.wave
        )

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
            sound = self.entity.game_services.get_resource_loader().load_sound(sound)
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
            turret = entity.get_component(Turret)
            if turret.attached_to is None:
                entity.kill()


class TurretsSystem(ComponentSystem):
    """ Manages entities that have a set of turrets attached to them. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Turrets])

    def update(self, dt):
        """ Update the system. """
        for entity in self.entities():
            turrets = entity.get_component(Turrets)
            for turret in turrets.turrets:
                if turret.entity is None:
                    turrets.turrets.remove(turret)

    def on_component_add(self, component):
        """ When the turrets component is added we need to create the turrets
        themselves which are specified in the config"""

        # The component entity needs to have a Body or this won't work.
        body = component.entity.get_component(Body)
        assert body is not None

        # Get the team.
        team = component.entity.get_component(Team)

        # Load the turrets.
        turret_cfgs = config.get_or_default("turrets", [])
        for cfg in turret_cfgs:

            # Load the weapon fitted to the turret.
            weapon_config = self.game_services.resource_loader().load_config(cfg["weapon_config"])

            # Create the turret entity.
            turret_entity = component.entity.ecs().create_entity(cfg)

            # Get the turret component and attach the weapon entity.
            turret = turret_entity.get_component(Turret)
            assert turret is not None
            turret.weapon.entity = component.entity.ecs().create_entity(weapon_config)
            weapon = turret.weapon.entity.get_component(Weapon)
            assert weapon is not None
            weapon.owner = turret_entity

            # Add the backreference and add to our list of turrets.
            turret.attached_to.entity = component.entity
            component.turrets.append(EntityRef(turret_entity, Turret))

            # Set the turret's team.
            turret_team = turret_entity.get_component(Team)
            if turret_team is not None and team is not None:
                turret_team.team = team.team

            # Pin the bodies together.
            turret_body = turret_entity.get_component(Body)
            point = body.local_to_world(turret.position)
            turret_body.position = point
            turret_body.velocity = body.velocity
            turret_body.pin_to(body)
