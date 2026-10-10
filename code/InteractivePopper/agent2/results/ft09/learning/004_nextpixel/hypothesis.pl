nextpixel(V0,V1,V2):- absentpixel(V0,V1,V2),local_click(V0).
nextpixel(V0,V1,V2):- no_local_click(V0),current(V0,V1,V2).
