:- style_check(-discontiguous).
object(_,_) :- fail.
object_color(_,_,_) :- fail.
adjacent(_,_,_) :- fail.
red(red).
blue(blue).
green(green).
yellow(yellow).
object(relational_v2_p1,left_obj).
object(relational_v2_p1,right_obj).
object(relational_v2_p1,spectator).
object_color(relational_v2_p1,left_obj,red).
object_color(relational_v2_p1,right_obj,red).
object_color(relational_v2_p1,spectator,green).
adjacent(relational_v2_p1,left_obj,spectator).
adjacent(relational_v2_p1,spectator,left_obj).
object(relational_v5_p1,left_obj).
object(relational_v5_p1,right_obj).
object(relational_v5_p1,spectator).
object_color(relational_v5_p1,left_obj,red).
object_color(relational_v5_p1,right_obj,red).
object_color(relational_v5_p1,spectator,green).
adjacent(relational_v5_p1,left_obj,spectator).
adjacent(relational_v5_p1,spectator,left_obj).
object(relational_v5_p0,left_obj).
object(relational_v5_p0,right_obj).
object(relational_v5_p0,spectator).
object_color(relational_v5_p0,left_obj,red).
object_color(relational_v5_p0,right_obj,blue).
object_color(relational_v5_p0,spectator,green).
adjacent(relational_v5_p0,left_obj,right_obj).
adjacent(relational_v5_p0,right_obj,left_obj).
object(relational_v2_p0,left_obj).
object(relational_v2_p0,right_obj).
object(relational_v2_p0,spectator).
object_color(relational_v2_p0,left_obj,red).
object_color(relational_v2_p0,right_obj,red).
object_color(relational_v2_p0,spectator,green).
adjacent(relational_v2_p0,left_obj,right_obj).
adjacent(relational_v2_p0,right_obj,left_obj).
