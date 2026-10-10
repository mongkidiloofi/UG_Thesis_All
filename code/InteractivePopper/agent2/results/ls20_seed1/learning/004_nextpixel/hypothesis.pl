nextpixel(V0,V1,V2):- current(V0,V3,V1),opposite(V2,V3),entered_has1(V0).
nextpixel(V0,V1,V2):- entered_lacks1(V0),current(V0,V1,V2).
