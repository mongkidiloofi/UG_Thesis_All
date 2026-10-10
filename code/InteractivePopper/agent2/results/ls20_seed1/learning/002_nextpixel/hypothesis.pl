nextpixel(V0,V1,V2):- entered_has1(V0),opposite(V2,V3),current(V0,V1,V3).
nextpixel(V0,V1,V2):- entered_lacks1(V0),current(V0,V1,V2).
