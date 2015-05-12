/***********************************************************************

                     H  A  Y  S  T  A  C  K

************************************************************************

    Semantic patching of las/laz files:
        - remove and add points

    Thomas Knudsen, Danish Geodata Agency, 2015-05-11

***********************************************************************/
#define SSPPLASH_LEVEL FULL
#define VERBOSITY E.verbosity
#define SSPPLASH_EXTRA_OPTIONS "w:a:"


#ifdef TESThaystack
#include "../../../helios/include/sspplash.h"
#include "../../../helios/include/stack.h"
#include "../../../helios/include/spain.h"
#else
#include "sspplash.h"
#include "stack.h"
#include "spain.h"
#endif


/* These are empty */
enum sspplash_action preheader (void) {automatic;}
enum sspplash_action prevlr    (void) {automatic;}
enum sspplash_action prerecord (void) {automatic;}
enum sspplash_action preevlr   (void) {automatic;}
enum sspplash_action preclose  (void) {automatic;}


FILE  *add     = 0;
size_t added   = 0;
size_t removed = 0;



/***********************************************************************
                             N E E D L E
************************************************************************
Basically, haystack searces for needles in a haystack, where the needles
represent either points to add or points to withheld.

The needle object, the stack of needles (which could have been called the
pincushion), and the reader read_needle() handles everything need(l)ed
here...
***********************************************************************/
typedef struct {
    double x, y, z;
    int cls, strip;
} needle;
stackable (needle);
stack(needle) needles; /* a stack of needles to search for */

needle read_needle (FILE *f) {
    needle rec;
    double cls;
    double strip;

    fread (&rec.x,     sizeof (rec.x),   1, f);
    fread (&rec.y,     sizeof (rec.y),   1, f);
    fread (&rec.z,     sizeof (rec.z),   1, f);
    fread (&cls,       sizeof (cls),     1, f);
    fread (&strip,     sizeof (strip),   1, f);
    rec.cls   =  cls   + 0.5;
    rec.strip =  strip + 0.5;
    return rec;
}


BEGIN {
    FILE *f;
    set_logfile ("haystack.log");

    /* Force GPS time flag to indicate modified GPS time */
    O.hdr.global_encoding |= 1;


    /* Read points to withhold into the needlestack */
    if (0==E.args['w'])
        nuncius (FAIL, "Withhold point file name (option '-w') not specified - bye\n");
    f = fopen (E.args['w'], "rb");
    if (0==f)
        nuncius (FAIL, "Cannot open withhold point file '%s' - bye\n", E.args['w']);

    stack_alloc (needles, 10000);
    while (!feof(f))
        push (needles, read_needle(f));
    (void) pop (needles); /* because last item was read past EOF */

    if (stack_invalid (needles))
        nuncius (FAIL, "Error reading file '%s' - bye\n", E.args['r']);
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


/**********************************************************************/
ADDRECORD {
/***********************************************************************

    Immediately before starting to read the point records, the sspplash
    event loop calls this section, querying whether it wants to add
    extra point records to the output file.

    If the ADDRECORD section replies with a "patch" signal, the event
    loop assumes that whatever is present in O.rec should be written
    to the output file, and the ADDRECORD section called again.

    In case of any other reply, the event loop assumes ADDRECORD has
    finished adding new points, and continues to handle the PRERECORD
    section.

***********************************************************************/
    needle rec;

    rec = read_needle (add);

    /* Done? */
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
        if ((unsigned) curr->strip != I.rec.point_source_id)
            continue;
        if ((unsigned) curr->cls != I.rec.classification)
            continue;
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
        O.rec.withheld = 1;
    }

    /* Repair class 32 specification bug */
    if (I.rec.synthetic && (0==I.rec.classification)) {
        O.rec.synthetic = 0;
        O.rec.classification = 31;
    }

    patch;
}


END {
    if (removed > 0)
        nuncius (INFO, "Withheld %d points from %s", removed, I.name);
    patch;
}
