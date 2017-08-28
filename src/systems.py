

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
        power_consumed = consume_power(weapon.entity, weapon.config["power_usage"] * dt)
        if power_consumed == 0:
            weapon.shooting_at = None
        else:
            body = weapon.entity.get_component(Body)
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
            body = weapon.entity.get_component(Body)
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
                team.team = weapon.entity.get_component(Team).team


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
                body.apply_force(thruster.position, thruster.amount * thruster.direction)


class ThrustersSystem(ComponentSystem):
    """ Update entities with thruster based movement. """

    def __init__(self):
        """ Constructor. """
        ComponentSystem.__init__(self, [Body, Thrusters])

    def on_component_add(self, component):
        """ When thrusters are added to an entity we need to create the actual
        thrusters themselves, which are specified in the config. """

        # I lied; they're hard coded for now.
        body = component.entity.get_component(Body)
        body.add_thruster(Thruster(Vec2d(-20, -20), Vec2d( 1,  0),
                                   component.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d(-20,  20), Vec2d( 1,  0),
                                   component.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d( 20, -20), Vec2d(-1,  0),
                                   component.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d( 20,  20), Vec2d(-1,  0),
                                   component.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d(  0, -20), Vec2d( 0,  1),
                                   component.config["max_thrust"] / 4))
        body.add_thruster(Thruster(Vec2d(  0,  20), Vec2d( 0, -1),
                                   component.config["max_thrust"]    ))

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
            body.fire_correct_thrusters(thrusters.direction, turn)


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

class TurretsSystem(ComponentSystem):
    def __init__(self):
        ComponentSystem.__init__(self, [Turrets])

    def on_component_add(self, component):
        """ When the turrets component is added we need to create the turrets
        themselves which are specified in the config"""
        hardpoints = config.get_or_default("hardpoints", [])
        for hp in hardpoints:
            if not "x" in hp or not "y" in hp:
                continue
            self.__hardpoints.append(HardPoint(Vec2d(hp["x"], hp["y"])))
            weapon_config = "enemies/turret.txt"
            if "weapon_config" in hp:
                weapon_config = hp["weapon_config"]
                entity = self.entity.ecs().create_entity(weapon_config,
                                                         parent=self.entity,
                                                         team=self.entity.get_component(Team).get_team())
                self.__hardpoints[hardpoint_index].set_turret(entity, self.entity.get_component(Body))

    def pin_turret(...):
        # If a new weapon has been added then pin it to our body.
        weapon_body = self.__weapon.get_component(Body)
        point = body_to_add_to.local_to_world(self.__position)
        weapon_body.position = point
        weapon_body.velocity = body_to_add_to.velocity
        weapon_body.pin_to(body_to_add_to)
