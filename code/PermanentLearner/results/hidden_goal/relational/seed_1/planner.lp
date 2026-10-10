time(0..8).
state_at(relational_v11_p0,0).
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
object(relational_v11_p0,left_obj).
object(relational_v11_p0,right_obj).
object(relational_v11_p0,spectator).
object_color(relational_v11_p0,left_obj,red).
object_color(relational_v11_p0,right_obj,blue).
object_color(relational_v11_p0,spectator,green).
adjacent(relational_v11_p0,left_obj,right_obj).
adjacent(relational_v11_p0,right_obj,left_obj).
object(relational_v11_p1,left_obj).
object(relational_v11_p1,right_obj).
object(relational_v11_p1,spectator).
object_color(relational_v11_p1,left_obj,red).
object_color(relational_v11_p1,right_obj,red).
object_color(relational_v11_p1,spectator,green).
adjacent(relational_v11_p1,left_obj,spectator).
adjacent(relational_v11_p1,spectator,left_obj).
object(relational_v11_p2,left_obj).
object(relational_v11_p2,right_obj).
object(relational_v11_p2,spectator).
object_color(relational_v11_p2,left_obj,red).
object_color(relational_v11_p2,right_obj,blue).
object_color(relational_v11_p2,spectator,green).
adjacent(relational_v11_p2,left_obj,right_obj).
adjacent(relational_v11_p2,right_obj,left_obj).
object(relational_v11_p3,left_obj).
object(relational_v11_p3,right_obj).
object(relational_v11_p3,spectator).
object_color(relational_v11_p3,left_obj,red).
object_color(relational_v11_p3,right_obj,red).
object_color(relational_v11_p3,spectator,green).
adjacent(relational_v11_p3,left_obj,spectator).
adjacent(relational_v11_p3,spectator,left_obj).
object(relational_v11_p4,left_obj).
object(relational_v11_p4,right_obj).
object(relational_v11_p4,spectator).
object_color(relational_v11_p4,left_obj,red).
object_color(relational_v11_p4,right_obj,blue).
object_color(relational_v11_p4,spectator,green).
adjacent(relational_v11_p4,left_obj,right_obj).
adjacent(relational_v11_p4,right_obj,left_obj).
object(relational_v11_p5,left_obj).
object(relational_v11_p5,right_obj).
object(relational_v11_p5,spectator).
object_color(relational_v11_p5,left_obj,red).
object_color(relational_v11_p5,right_obj,red).
object_color(relational_v11_p5,spectator,green).
adjacent(relational_v11_p5,left_obj,spectator).
adjacent(relational_v11_p5,spectator,left_obj).
object(relational_v11_p6,left_obj).
object(relational_v11_p6,right_obj).
object(relational_v11_p6,spectator).
object_color(relational_v11_p6,left_obj,red).
object_color(relational_v11_p6,right_obj,red).
object_color(relational_v11_p6,spectator,green).
adjacent(relational_v11_p6,left_obj,right_obj).
adjacent(relational_v11_p6,right_obj,left_obj).
transition(relational_v11_p0,left,relational_v11_p0).
transition(relational_v11_p0,right,relational_v11_p1).
transition(relational_v11_p1,left,relational_v11_p0).
transition(relational_v11_p1,right,relational_v11_p2).
transition(relational_v11_p2,left,relational_v11_p1).
transition(relational_v11_p2,right,relational_v11_p3).
transition(relational_v11_p3,left,relational_v11_p2).
transition(relational_v11_p3,right,relational_v11_p4).
transition(relational_v11_p4,left,relational_v11_p3).
transition(relational_v11_p4,right,relational_v11_p5).
transition(relational_v11_p5,left,relational_v11_p4).
transition(relational_v11_p5,right,relational_v11_p6).
transition(relational_v11_p6,left,relational_v11_p5).
transition(relational_v11_p6,right,relational_v11_p6).
goal(A):- adjacent(A,C,B),object_color(A,C,D),object_color(A,B,D).
