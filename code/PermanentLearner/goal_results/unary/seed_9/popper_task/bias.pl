head_pred(goal,1).
body_pred(object,2).
body_pred(color,3).
body_pred(adjacent,3).
body_pred(red,1).
body_pred(blue,1).
body_pred(green,1).
body_pred(yellow,1).

type(goal,(state,)).
type(object,(state,obj)).
type(color,(state,obj,colour)).
type(adjacent,(state,obj,obj)).
type(red,(colour,)).
type(blue,(colour,)).
type(green,(colour,)).
type(yellow,(colour,)).

direction(goal,(in,)).
direction(object,(in,out)).
direction(color,(in,in,out)).
direction(adjacent,(in,out,out)).
direction(red,(in,)).
direction(blue,(in,)).
direction(green,(in,)).
direction(yellow,(in,)).

constant(red,colour).
constant(blue,colour).
constant(green,colour).
constant(yellow,colour).

max_body(3).
max_vars(4).
max_clauses(1).
