% Learned theory snapshot; supply observation facts to query it.
advances(V0):- equal_c3(V0).
advances(V0):- unequal_c3(V0),lacks_c4(V0).

changes(V0):- equal_c5(V0).
changes(V0):- lacks_c9(V0).

progress(V0):- equal_c5(V0).

% Registered observed region (9, 3, 55, 6)
nextpixel_region0(V0,V1,V2):- current(V0,V3,V1),opposite(V2,V3),entered_has1(V0).
nextpixel_region0(V0,V1,V2):- entered_lacks1(V0),current(V0,V1,V2).

% Registered observed region (5, 1, 53, 10)
nextpixel_region1(V0,V1,V2):- current(V0,V3,V1),opposite(V2,V3),entered_has1(V0).
nextpixel_region1(V0,V1,V2):- entered_lacks1(V0),current(V0,V1,V2).

