/***********************************************************************

                         D V R 9 0

************************************************************************

    Semantic patching of las/laz files:
        - change ellipsoidal heights to DVR90 (orthometric)
        (other tidbits earlier handled by DVR90etc.c moved to haystack.c)

    Thomas Knudsen, Danish Geodata Agency, 2015-06-17

    Compile:
    E:\Documents\2015\Projects\gstdhmqc\DVR90\gstdhmqc\src\etc>gcc -Wall -O2 -pedantic -Wno-overlength-strings -Wno-long-long -Wno-format -o DVR90 -I e:\Documents\2015\Projects\helios\plain\helios\include DVR90.c

    Run:
    E:\Documents\2015\Projects\haystack-test>..\gstdhmqc\DVR90\gstdhmqc\src\etc\DVR90.exe -o a.laz -N e:\sspplash\dkgeoid13b.utm32 d:1km_6173_728.laz

***********************************************************************/
#define SSPPLASH_LEVEL FULL
#define VERBOSITY E.verbosity
#ifdef TESTDVR90
#include "../../../../../helios/plain/helios/include/sspplash.h"
#else
#include "sspplash.h"
#endif


/* These are empty */
sspplash_nop (preheader);
sspplash_nop (prevlr);
sspplash_nop (prerecord);
sspplash_nop (preevlr);
sspplash_nop (preclose);

int removed = 0;
FILE      *DVR90_log;

ASTA *asta_h = 0, *asta_H = 0, *asta_N = 0;

ADDRECORD {skip;}

BEGIN {
/*    DVR90_log = fopen ("DVR90.log", "a+t");
    nuncius_logfile (DVR90_log, 0); */



    asta_h = asta_alloc ();
    asta_H = asta_alloc ();
    asta_N = asta_alloc ();


    /* Check that we really are using dkgeoid13b for DVR90 transformations */

    /* Amager Strand */
    assert (0.001 > fabs (N(729000, 6173000) - 35.9902));
    /* West of Blaavand */
    assert (0.001 > fabs (N(400000, 6173000) - 40.7868));
    /* Jutland,  around Hobro */
    assert (0.001 > fabs (N(500000, 6273000) - 39.4078));
    /* Funen,  around  */
    assert (0.001 > fabs (N(575000, 6130000) - 39.9581));
    /* Zeeland,  around  */
    assert (0.001 > fabs (N(700000, 6140000) - 36.8445));
    /* Bornholm,  around  */
    assert (0.001 > fabs (N(875000, 6135000) - 34.5805));
    automatic;
}
VLR   {automatic;}
EVLR  {automatic;}


HEADER {
    automatic;
}


RECORD {
    double geoid_undulation;

    geoid_undulation = N (easting, northing);

    if (HUGE_VAL==geoid_undulation) {
        removed++;
        next;
    }

    oheight = height - geoid_undulation;
    asta (asta_H, oheight);
    asta (asta_N, geoid_undulation);
    asta (asta_h, height);


    if (E.records_read==1)
        nuncius (INFO, "Test point %s: %15.2f %15.2f %7.2f %7.2f %7.3f\n", I.name, I.rec.x, I.rec.y, I.rec.z, O.rec.z, N(I.rec.x, I.rec.y));

    patch;
}


END {
    if (E.verbosity > 1) {
        asta_info_header (stdout, "Item", 12);
        asta_info (asta_H, stdout, "Geophysical", 12, 3);
        asta_info (asta_N, stdout, "Geoid",       12, 3);
        asta_info (asta_h, stdout, "Geometrical", 12, 3);
    }
    patch;
}
