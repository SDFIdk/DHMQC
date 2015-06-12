/***********************************************************************

                         D V R 9 0

************************************************************************

    Semantic patching of las/laz files:
        - change ellipsoidal heights to DVR90 (orthometric)
        (other tidbits earlier handled by DVR90etc.c moved to haystack.c)

    Thomas Knudsen, Danish Geodata Agency, 2015-06-04

***********************************************************************/
#define SSPPLASH_LEVEL FULL
#define VERBOSITY E.verbosity
#ifdef TESTDVR90
#include "../../../../helios/include/sspplash.h"
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

    if (las_record_number (&I.internals)==2000)
        nuncius (NOTE, "Test point %s: %15.2f %15.2f %7.2f %7.2f %7.3f", I.name, I.rec.x, I.rec.y, I.rec.z, O.rec.z, N(I.rec.x, I.rec.y));

    patch;
}


END {
    if (removed > 0)
        nuncius (WARN, "Removed %d out-of-bbox points from %s", removed, I.name);
    patch;
}
