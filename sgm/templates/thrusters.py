from pymunk import Vec2d

from sgm import components as components


class ThrusterSpec(object):
    def __init__(self, **kwargs):
        self.position = kwargs.get("position", Vec2d(0, 0))
        self.orientation = kwargs.get("orientation", Vec2d(1, 0))
        self.max_thrust = kwargs.get("max_thrust", 0)


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