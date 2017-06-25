Data Model
============

We currently use a crude 'entity system' to compose game objects out of 
simple behaviours.  However the system at present is not very structured,
it's not obvious how to express complex relationships and doesn't always
behave intuitively.  Additionally since it there isn't much structure
imposed on the data it's not clear how e.g. load/save would be implemented,
for instance.

Possible reasons for these difficulties:
* The entity system is insufficiently pure (components strictly
  data, all processing done on queries of the game database)
* The entity system is trying to do too much, there should be fewer
  components and within the systems should be more traditional OOP.
* We simply don't have enough regularity to our data, perhaps we could
  make what we have more consistent and it would be sufficient.

Probably best to work through a concrete example to get an idea of how
it should be represented.

A spaceship has
* Modules, that bestow upon it particular properties and bonuses. Modules
  come in different types e.g. turrets, thrusters.  Modules go in sockets,
  a socket might be limited to modules of a particular type.  Some sockets
  might be compulsory, a ship won't be valid without a module in them.
  e.g. crew quarters, bulkheads, armour, turrets, thrusters...
* Turret sockets, that can be fitted with particular weapon turrets.
  A turret socket can be either rotary or coaxial. A rotary turret
  socket has a angular range in which it can rotate.
  Turret sockets might be e.g. small, medium, large.
* Thrusters, that allow it to move.
* A hull, providing module slots and baseline stats e.g. hp, mass...

Turrets might either be under direct control or fire autonomously.

A ship might need:
* 5 thrusters (1 main, 1 reverse, 4 for lateral movement / turning)
* 1+ turret slots
* power generator
* shield generator
* ...

As well as provide certain qualities (shields) a module might affect
the stats of another module (+10% shield strength).

Can a ship have multiple shield generators? This would mean a ship
with 1+ shield generators has the 'shielded' property, and adding
more shield generators perhaps adds to the shield capacity.

What does all this mean for the data model?  Obviously a 'shield generator'
module doesn't correspond to our 'shielded' ECS component - but having 1
or more generator module clearly bestows that component.

Perhaps this is all reconcilable with our current model. Modules are managed
by a 'Modules' component, and adding/removing modules adds/removes behaviour
components as necessary. This is going to run into problems though, since we've
got components creating and managing other components. What if a 'Shields'
component is added to an entity from a different source? Will the two systems
fight with one another? (Maybe for instance a buff adds the 'shielded' property)

Is there a better way of expressing and managing all this?

Would it be helpful to try to model this in OOP terms and see if a representation
using our entities and components presents itself?

     Ship               Hull            Module
     Module slot        Module type     Thruster
     Turret             Turret slot     Shield Generator
     Power Generator    Attribute       Modifier
     Hitpoints          Shields         Power
     AttributeSet
     

                     <>------ AttributeSet
    Ship <>---- Hull <>------ ModuleSlot <-- SystemSlot <>-- System -----> Module
                                         <-- TurretSlot <>-- Turret ----->
                                         <-- ThrusterSlot <>-- Thruster ->
                                     
![some uml](http://www.plantuml.com/plantuml/proxy?src=https://raw.githubusercontent.com/nathanwoodward/space_game/master/notes/ship.puml)

In the above diagram, the structure defines a ship *design*, which can be applied to
an actual ship entity to create the components necessary to represent it. That's a bit
of a handwave though. What if the design has only changed slightly, we presumably want
it to keep its damage etc. Can you reverse engineer a design from a ship entity? It
doesn't sound very robust. Probably don't want to go this route? However the relationships
between the components of the design sound plausible.
