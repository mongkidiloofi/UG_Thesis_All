:- clause(C), #count{V : var_type(C,V,example)} != 1.
body_pred(absentpixel,3).
body_pred(current,3).
body_pred(opposite,2).
head_pred(nextpixel,3).
max_body(3).
max_vars(4).
type(absentpixel,(example,coord,coord)).
type(current,(example,coord,coord)).
type(nextpixel,(example,coord,coord)).
type(opposite,(coord,coord)).
