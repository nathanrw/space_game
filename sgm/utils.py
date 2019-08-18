from pymunk import Vec2d

from sgm import components as components
from sgm.components import Body, Team, Power


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


def setup_team(e1, e2):
    """ Put one entity under the team leadership of another. """
    t1 = e1.get_component(components.Team)
    t2 = e2.get_component(components.Team)
    if t1 is not None and t2 is not None:
        t2.parent.entity = e1