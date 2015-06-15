/***********************************************************************

                         D V R 9 0

************************************************************************

    Semantic patching of las/laz files:
        - change ellipsoidal heights to DVR90 (orthometric)
        (other tidbits earlier handled by DVR90etc.c moved to haystack.c)

    Thomas Knudsen, Danish Geodata Agency, 2015-06-04

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


ADDRECORD {skip;}

BEGIN {
/*    DVR90_log = fopen ("DVR90.log", "a+t");
    nuncius_logfile (DVR90_log, 0); */

    /* Check that we are using dkgeoid13b for DVR90 transformations */

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

    if (E.records_read==2000)
        nuncius (NOTE, "Test point %s: %15.2f %15.2f %7.2f %7.2f %7.3f", I.name, I.rec.x, I.rec.y, I.rec.z, O.rec.z, N(I.rec.x, I.rec.y));

    patch;
}


END {
    if (removed > 0)
        nuncius (WARN, "Removed %d out-of-bbox points from %s", removed, I.name);
    patch;
}
