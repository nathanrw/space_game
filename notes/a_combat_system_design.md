A combat system design
======================

This is a sketch of a possible real-time-with-pause combat system for a space
game.

- Game plays out in real time, but commands can be issued while it is paused.

- Movement instructions given by dragging control points on a curve, which
  is limited to the set of positions the ship could be in after the next
  X seconds.  Can also set the position, spin & velocity at the end of the
  movement, which affects the range of possible positions.  This time period
  is called the 'turn period'.

- Can drag a slider to preview the ship's position along the movement curve
  over the turn period.

- Can queue an action to occur at any period along the turn period by using
  the slider and selection the action at that point. The slider will show
  a preview of queued actions.  An action will have a cooldown, cooldowns
  will be shown on the slider too.

- An action can be e.g. fire a turret.  The direction of shooting can be
  specified.

- Actions will be accessed from buttons on the objects that provide them.

- Can have a variety of weapons e.g. grappling hooks.  Firing a hook will
  be an action, if it hits something the grapple latches on and then either
  reeling in or detaching will be actions.  This will be physics based.

       .------------------------------------------------.
       |                                                |
       |                                                |
       |                      __________                |
       |                     /          \               |
       |                                 \              |
       |                    /\            \             |
       |                 __/  \__          |            |
       |                 \W1  W2/          |            |
       |                  |    |           V            |
       |                  | G  |           X--> facing  |
       |                  |    |           |            |
       |                 /______\          v vel        |
       |                                                |
       |                                                |
       |                                                |
       |                                                |
       |                                                |
       |                                                |
       |  [-W2-------------X------------W1-----------]  |
       |                 [||] [>] [>>]                  |
       |                                                |
       '------------------------------------------------'

This will require a clever algorithm for the movement calculations.
