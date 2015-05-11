/***********************************************************************

                     H  A  Y  S  T  A  C  K

************************************************************************

    Semantic patching of las/laz files:
        - remove and add points

    Thomas Knudsen, Danish Geodata Agency, 2015-05-11

***********************************************************************/
#define SSPPLASH_LEVEL FULL
#define VERBOSITY E.verbosity
#define SSPPLASH_EXTRA_OPTIONS "r:a:"

#include "../helios/include/sspplash.h"
#include "../helios/include/stack.h"
#include "../helios/include/spain.h"

/* These are empty */
enum sspplash_action preheader (void) {automatic;}
enum sspplash_action prevlr    (void) {automatic;}
enum sspplash_action prerecord (void) {automatic;}
enum sspplash_action preevlr   (void) {automatic;}
enum sspplash_action preclose  (void) {automatic;}


FILE  *add     = 0;
size_t added   = 0;
size_t removed = 0;


typedef struct {
    double x, y, z;
    int cls, strip;
} needle;
stackable (needle);
stack(needle) needles; /* a stack of needles to search for */


BEGIN {
    FILE *f;
    set_logfile ("haystack.log");


    /*
     *    Read needles to remove into the needlestack
     *
     */

    if (0==E.args['r'])
        nuncius (FAIL, "Remove file name (option '-r') not specified - bye\n");
    f = fopen (E.args['r'], "rb");
    if (0==f)
        nuncius (FAIL, "Cannot open remove file '%s' - bye\n", E.args['r']);

    stack_alloc (needles, 10000);
    do {
        needle rec;
        fread (&rec.x,     sizeof (rec.x),     1, f);
        fread (&rec.y,     sizeof (rec.y),     1, f);
        fread (&rec.z,     sizeof (rec.z),     1, f);
        fread (&rec.cls,   sizeof (rec.cls),   1, f);
        fread (&rec.strip, sizeof (rec.strip), 1, f);
        push (needles, rec);
    } while (!feof(f));
    (void) pop (needles); /* because last item was read past EOF */

    nuncius (INFO, "Read %d needles\n", depth(needles));

    if (0==E.args['a'])
        nuncius (FAIL, "Add file name (option '-a') not specified - bye\n");
    add = fopen (E.args['a'], "rb");

    automatic;
}
VLR   {automatic;}
EVLR  {automatic;}


HEADER {
    automatic;
}



ADDRECORD {
    needle rec;
    fread (&rec.x,     sizeof (rec.x),     1, add);
    fread (&rec.y,     sizeof (rec.y),     1, add);
    fread (&rec.z,     sizeof (rec.z),     1, add);
    fread (&rec.cls,   sizeof (rec.cls),   1, add);
    fread (&rec.strip, sizeof (rec.strip), 1, add);

    if (feof(add)) {
        nuncius (INFO, "Added %d points\n", (int) added);
        fclose (add);
        skip;
    }

    /* Build output record */
    O.rec.x = rec.x;
    O.rec.y = rec.y;
    O.rec.z = rec.z;
    O.rec.point_source_id = rec.strip;

    /* This information is common to all added points: the "added point fingerprint" */
    O.rec.intensity = 0;
    O.rec.return_number = 1;
    O.rec.number_of_returns = 1;
    O.rec.synthetic = 1;
    O.rec.classification = 2;
    O.rec.gps_time = -123456789; /* 2007-10-16T04:13:17 */

    added++;
    patch;
}





RECORD {
    int found = 0;
    needle *curr;
    if (las_record_number (&I.internals)==2000)
        nuncius (INFO, "Test point %s: %15.2f %15.2f %7.2f %7.2f %7.3f\n\n", I.name, I.rec.x, I.rec.y, I.rec.z, O.rec.z, 10101.01/*N(I.rec.x, I.rec.y)*/);

    foreach (curr, needles) {
/*        if ((unsigned) curr->cls != I.rec.classification)
            continue;
        if ((unsigned) curr->strip != I.rec.point_source_id)
            continue;*/
        if (0.01 < fabs(curr->x - easting))
            continue;
        if (0.01 < fabs(curr->y - northing))
            continue;
        if (0.01 < fabs(curr->z - height))
            continue;
        found = 1;
    }
    if (found) {
        removed++;
        skip;
    }

    patch;
}


END {
    if (removed > 0)
        nuncius (INFO, "Removed %d points from %s", removed, I.name);
    patch;
}
