"""
Definition of planets.
"""


import components
from sge import utils


class PlanetDef(object):
    def __init__(self, **kwargs):
        self.name = kwargs.get("name", "Unknown planet")
        self.radius = kwargs.get("radius", 1000)
        self.orbit_radius = kwargs.get("orbit_radius", 0)
        self.is_star = kwargs.get("is_star", False)
        self.description = kwargs.get("description", "")


SUN_DEF = PlanetDef(
    name="The Sun",
    radius=20000,
    orbit_radius=0,
    is_star=True
)
MERCURY_DEF = PlanetDef(
    name="Mercury",
    radius=1000,
    orbit_radius=100000,
    description= """
The smallest planet. It's really small. It's also very close to the sun, 
so it is very hot. Because there is no atmosphere or magnetic field, you're 
exposed to cosmic radiation. You wouldn't want to live here.
"""
)
VENUS_DEF = PlanetDef(
    name="Venus",
    radius=2000,
    orbit_radius=200000,
    description="""
    A hellhole.
    """
)
EARTH_DEF = PlanetDef(
    name="The Earth",
    radius=5000,
    orbit_radius=400000,
    description="""
    The centre of the universe.
    """
)
MARS_DEF = PlanetDef(
    name="Mars",
    radius=3000,
    orbit_radius=1000000,
    description="""
    A dull, red desert.
    """
)
JUPITER_DEF = PlanetDef(
    name="Jupiter",
    radius=10000,
    orbit_radius=5000000,
    description="""
    A huge gas giant with an extensive system of moons. The Jupiter system is
    full of deadly radiation. You won't survive here without extensive
    protection.
    """
)


def create_planet(entity_manager, planet_def):
    """
    Create a planet or star.
    :planet_def a PlanetDef instance.
    :return: the planet entity
    """
    entity = entity_manager.create_entity()

    # Add star / planet tag
    if planet_def.is_star:
        entity_manager.create_component(entity, components.Star)
    else:
        entity_manager.create_component(entity, components.Planet)

    # Add celestial body component.
    celestial_body = entity_manager.create_component(
        entity,
        components.CelestialBody,
        {"name": planet_def.name}
    )

    # Create physics body. The celestial body system will drive this by
    # setting the velocity, so make it a kinematic body.
    body_data = {
        "size": planet_def.radius,
        "kinematic": True,
        "is_collideable": False
    }
    body = entity_manager.create_component(entity, components.Body, body_data)
    body.position = utils.Vec2d(0, planet_def.orbit_radius)

    # If it's dockable, add the component.
    if planet_def.description != "":
        entity_manager.create_component(
            entity,
            components.Dockable,
            {"title": planet_def.name, "description": planet_def.description}
        )

    return entity