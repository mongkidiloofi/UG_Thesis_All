time(0..8).
state_at(compositional_v11_p0,0).
1 { action(left,T); action(right,T) } 1 :- time(T), T < 8, not finished(T).
state_at(N,T+1) :- state_at(S,T), action(A,T), transition(S,A,N), T < 8.
goal_reached(T) :- state_at(S,T), goal(S).
finished(T) :- time(T), goal_reached(G), T >= G.
:- not goal_reached(_).
#minimize { 1,T,A : action(A,T) }.
#show action/2.
#show state_at/2.
red(red).
blue(blue).
green(green).
yellow(yellow).
object(compositional_v11_p0,red_obj).
object(compositional_v11_p0,blue_obj).
object(compositional_v11_p0,other).
object_color(compositional_v11_p0,red_obj,red).
object_color(compositional_v11_p0,blue_obj,green).
object_color(compositional_v11_p0,other,blue).
adjacent(compositional_v11_p0,red_obj,blue_obj).
adjacent(compositional_v11_p0,blue_obj,red_obj).
object(compositional_v11_p1,red_obj).
object(compositional_v11_p1,blue_obj).
object(compositional_v11_p1,other).
object_color(compositional_v11_p1,red_obj,green).
object_color(compositional_v11_p1,blue_obj,blue).
object_color(compositional_v11_p1,other,red).
adjacent(compositional_v11_p1,red_obj,other).
adjacent(compositional_v11_p1,other,red_obj).
object(compositional_v11_p2,red_obj).
object(compositional_v11_p2,blue_obj).
object(compositional_v11_p2,other).
object_color(compositional_v11_p2,red_obj,green).
object_color(compositional_v11_p2,blue_obj,blue).
object_color(compositional_v11_p2,other,red).
adjacent(compositional_v11_p2,red_obj,other).
adjacent(compositional_v11_p2,other,red_obj).
object(compositional_v11_p3,red_obj).
object(compositional_v11_p3,blue_obj).
object(compositional_v11_p3,other).
object_color(compositional_v11_p3,red_obj,red).
object_color(compositional_v11_p3,blue_obj,green).
object_color(compositional_v11_p3,other,blue).
adjacent(compositional_v11_p3,red_obj,blue_obj).
adjacent(compositional_v11_p3,blue_obj,red_obj).
object(compositional_v11_p4,red_obj).
object(compositional_v11_p4,blue_obj).
object(compositional_v11_p4,other).
object_color(compositional_v11_p4,red_obj,red).
object_color(compositional_v11_p4,blue_obj,blue).
object_color(compositional_v11_p4,other,green).
adjacent(compositional_v11_p4,red_obj,blue_obj).
adjacent(compositional_v11_p4,blue_obj,red_obj).
object(compositional_v11_p5,red_obj).
object(compositional_v11_p5,blue_obj).
object(compositional_v11_p5,other).
object_color(compositional_v11_p5,red_obj,green).
object_color(compositional_v11_p5,blue_obj,blue).
object_color(compositional_v11_p5,other,red).
adjacent(compositional_v11_p5,red_obj,other).
adjacent(compositional_v11_p5,other,red_obj).
object(compositional_v11_p6,red_obj).
object(compositional_v11_p6,blue_obj).
object(compositional_v11_p6,other).
object_color(compositional_v11_p6,red_obj,red).
object_color(compositional_v11_p6,blue_obj,green).
object_color(compositional_v11_p6,other,blue).
adjacent(compositional_v11_p6,red_obj,blue_obj).
adjacent(compositional_v11_p6,blue_obj,red_obj).
transition(compositional_v11_p0,left,compositional_v11_p0).
transition(compositional_v11_p0,right,compositional_v11_p1).
transition(compositional_v11_p1,left,compositional_v11_p0).
transition(compositional_v11_p1,right,compositional_v11_p2).
transition(compositional_v11_p2,left,compositional_v11_p1).
transition(compositional_v11_p2,right,compositional_v11_p3).
transition(compositional_v11_p3,left,compositional_v11_p2).
transition(compositional_v11_p3,right,compositional_v11_p4).
transition(compositional_v11_p4,left,compositional_v11_p3).
transition(compositional_v11_p4,right,compositional_v11_p5).
transition(compositional_v11_p5,left,compositional_v11_p4).
transition(compositional_v11_p5,right,compositional_v11_p6).
transition(compositional_v11_p6,left,compositional_v11_p5).
transition(compositional_v11_p6,right,compositional_v11_p6).
goal(A):- adjacent(A,D,B),object_color(A,B,C),blue(C),adjacent(A,B,D).
