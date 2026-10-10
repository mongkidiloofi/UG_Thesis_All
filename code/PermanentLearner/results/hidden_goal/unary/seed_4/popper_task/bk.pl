:- style_check(-discontiguous).
object(_,_) :- fail.
object_color(_,_,_) :- fail.
adjacent(_,_,_) :- fail.
red(red).
blue(blue).
green(green).
yellow(yellow).
object(unary_v1_p4,token).
object(unary_v1_p4,marker).
object_color(unary_v1_p4,token,red).
object_color(unary_v1_p4,marker,green).
object(unary_v3_p1,token).
object(unary_v3_p1,marker).
object_color(unary_v3_p1,token,red).
object_color(unary_v3_p1,marker,green).
object(unary_v2_p4,token).
object(unary_v2_p4,marker).
object_color(unary_v2_p4,token,blue).
object_color(unary_v2_p4,marker,green).
