:- style_check(-discontiguous).
object(_,_) :- fail.
object_color(_,_,_) :- fail.
adjacent(_,_,_) :- fail.
red(red).
blue(blue).
green(green).
yellow(yellow).
object(compositional_v4_p4,red_obj).
object(compositional_v4_p4,blue_obj).
object(compositional_v4_p4,other).
object_color(compositional_v4_p4,red_obj,red).
object_color(compositional_v4_p4,blue_obj,blue).
object_color(compositional_v4_p4,other,green).
adjacent(compositional_v4_p4,red_obj,blue_obj).
adjacent(compositional_v4_p4,blue_obj,red_obj).
object(compositional_v0_p2,red_obj).
object(compositional_v0_p2,blue_obj).
object(compositional_v0_p2,other).
object_color(compositional_v0_p2,red_obj,green).
object_color(compositional_v0_p2,blue_obj,blue).
object_color(compositional_v0_p2,other,red).
adjacent(compositional_v0_p2,red_obj,other).
adjacent(compositional_v0_p2,other,red_obj).
