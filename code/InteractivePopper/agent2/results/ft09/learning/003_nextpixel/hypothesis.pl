nextpixel(V0,V1,V2):- absentpixel(V0,V1,V2),local_click(V0).
nextpixel(V0,V1,V2):- entered_lacks9(V0),current(V0,V1,V2).
