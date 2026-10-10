time(0..8).
state_at(unary_v11_p0,0).
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
object(unary_v11_p0,token).
object(unary_v11_p0,marker).
object_color(unary_v11_p0,token,yellow).
object_color(unary_v11_p0,marker,green).
object(unary_v11_p1,token).
object(unary_v11_p1,marker).
object_color(unary_v11_p1,token,blue).
object_color(unary_v11_p1,marker,green).
object(unary_v11_p2,token).
object(unary_v11_p2,marker).
object_color(unary_v11_p2,token,green).
object_color(unary_v11_p2,marker,green).
object(unary_v11_p3,token).
object(unary_v11_p3,marker).
object_color(unary_v11_p3,token,red).
object_color(unary_v11_p3,marker,green).
object(unary_v11_p4,token).
object(unary_v11_p4,marker).
object_color(unary_v11_p4,token,blue).
object_color(unary_v11_p4,marker,green).
object(unary_v11_p5,token).
object(unary_v11_p5,marker).
object_color(unary_v11_p5,token,green).
object_color(unary_v11_p5,marker,green).
object(unary_v11_p6,token).
object(unary_v11_p6,marker).
object_color(unary_v11_p6,token,yellow).
object_color(unary_v11_p6,marker,green).
transition(unary_v11_p0,left,unary_v11_p0).
transition(unary_v11_p0,right,unary_v11_p1).
transition(unary_v11_p1,left,unary_v11_p0).
transition(unary_v11_p1,right,unary_v11_p2).
transition(unary_v11_p2,left,unary_v11_p1).
transition(unary_v11_p2,right,unary_v11_p3).
transition(unary_v11_p3,left,unary_v11_p2).
transition(unary_v11_p3,right,unary_v11_p4).
transition(unary_v11_p4,left,unary_v11_p3).
transition(unary_v11_p4,right,unary_v11_p5).
transition(unary_v11_p5,left,unary_v11_p4).
transition(unary_v11_p5,right,unary_v11_p6).
transition(unary_v11_p6,left,unary_v11_p5).
transition(unary_v11_p6,right,unary_v11_p6).
goal(A):- object(A,C),object_color(A,C,B),red(B).
