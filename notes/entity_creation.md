Entity Creation
===============

Components used to have a setup() method that got called during
creation, this meant you could pass down e.g. a position or team
and components would pull in those values at creation time.

I've since removed that and just had the calling code set whatever
properties, thinking that would be simpler.

However, there is a problem in that certain values get propagated
to 'child' entities during creation, but we no longer have a formal
concept of a 'child' entity; it's all ad hoc based on how systems
interpret the ownership of references.

This means that you can't just e.g. set an entity's team after
creating it since it might already have created children based
on its default team in the config (which could be null).

Note sure of the best solution:
  - Reintroduce setup() to specify everything at creation-time.
  - Reintroduce formal parent-child relationship and make team
    logic aware of this.
  - Do ad hoc parent-child inside team component and make code
    aware of this.
  - ???

I've 'fixed' it with a hack for now - enemies default to the
'enemy' team so it all appears to work!

Could have

     class Compound(Component):
       def __init__(self, entity, game_services, config):
         Component.__init__(self, entity, game_services, config)
         self.parent = EntityRef(Compound)
         self.children = EntityRefList(Compound)
         
to associate entities that are part of the same whole.
