% Learned theory snapshot; supply observation facts to query it.
% Registered observed region (9, 52, 36, 6)
nextpixel_region0(V0,V1,V2):- absentpixel(V0,V1,V2),local_click(V0).
nextpixel_region0(V0,V1,V2):- no_local_click(V0),current(V0,V1,V2).

% Registered observed region (9, 36, 52, 6)

