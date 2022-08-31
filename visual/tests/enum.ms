

typedef enum {
    A1,
    A2,
    A3,
    A4
} Paper;

function Paper permute(Paper a);
    Paper x;
    if (a == A1) x = A2;
    else if (a == A2) x = A1;
    else if (a == A3) x = A4;
    else x = A3; /*a = A4*/
    return x;
endfunction