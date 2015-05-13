/***********************************************************************

                     H  A  Y  S  T  A  C  K

************************************************************************

    Repair minor bugs and annoyanvces in delivery level DHM2014 data
    by semantic patching of las/laz files

    - Apply the withheld flag to points externally determined to
      be noise/migrating birds/power lines/haystacks

    - Add additional points supposedly repairing data holes by fill
      in from DHM 2007

    - Repair the specification blunder requiring surface points in
      the overlap zone to be classified as class 32, which results
      in overflow to 00000 and carry-setting of the "synthetic" flag.

      Modified by resetting the flag and reclass to class 31 (11111).

    - Repair mistaken GPS time flag to properly signal modified GPS time

    Thomas Knudsen, Danish Geodata Agency, 2015-05

********************************************************************
Copyright (c) 2015, Danish Geodata Agency, <gst@gst.dk>

Permission to use, copy, modify, and/or distribute this
software for any purpose with or without fee is hereby granted,
provided that the above copyright notice and this permission
notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL
WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL
THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
***********************************************************************/
#define SSPPLASH_LEVEL FULL
#define VERBOSITY E.verbosity
#define SSPPLASH_EXTRA_OPTIONS "w:a:"

#define SSPPLASH_HELP_MSG \
    "\n"\
    "syntax:  %s [-h] -o OUTFILE [-w WITHHOLDFILE] [-a ADDFILE] [-v] INFILE\n\n" \
    "Perform pointwise perturbations phor preparation of DHM2015 data.\n\n"\
    "The arguments to the -w and -a options are assumed to be point files\n"\
    "in the celebrated 'permuted milks' (= simlk) format.\n"


#ifdef TESThaystack
#include "../../../helios/include/sspplash.h"
#include "../../../helios/include/stack.h"
#include "../../../helios/include/spain.h"
#else
#include "sspplash.h"
#include "stack.h"
#endif


/* These are empty */
sspplash_nop (preheader);
sspplash_nop (prevlr);
sspplash_nop (prerecord);
sspplash_nop (preevlr);
sspplash_nop (preclose);

FILE  *add     = 0;
size_t added   = 0;
size_t removed = 0;



/***********************************************************************
                             N E E D L E
************************************************************************
Basically, haystack searces for needles in a haystack, where the needles
represent either points to add or points to withhold.

The needle object, the stack of needles (which could have been called the
pincushion), and the reader read_needle() handles everything need(l)ed
here...
***********************************************************************/
typedef struct {
    double x, y, z;
    unsigned long long cls, strip;
} needle;
stackable (needle);
stack(needle) needles; /* a stack of needles to search for */

needle read_needle (FILE *f) {
    needle rec;
    double cls;
    double strip;

    fread (&rec.x,     sizeof (rec.x),   1,  f);
    fread (&rec.y,     sizeof (rec.y),   1,  f);
    fread (&rec.z,     sizeof (rec.z),   1,  f);
    fread (&cls,       sizeof (cls),     1,  f);
    fread (&strip,     sizeof (strip),   1,  f);

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
    stack_alloc (needles, 10000);
    if (stack_invalid (needles))
        nuncius (FAIL, "Out of memory - bye\n");

    if (0!=E.args['w']) {
        f = fopen (E.args['w'], "rb");
        if (0==f)
            nuncius (FAIL, "Cannot open withhold point file '%s' - bye\n", E.args['w']);

        while (!feof(f))
            push (needles, read_needle(f));
        (void) pop (needles); /* because last item was read past EOF */

        if (stack_invalid (needles))
            nuncius (FAIL, "Error reading file '%s' - bye\n", E.args['r']);

        nuncius (INFO, "Read %d needles\n", depth(needles));
    }

    if (0!=E.args['a']) {
        add = fopen (E.args['a'], "rb");
        if (0==add)
            nuncius (FAIL, "Cannot open add point file '%s' - bye\n", E.args['a']);
    }

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

    if (0==add)
        skip;

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
        nuncius (INFO, "Test point %s: %15.2f %15.2f %7.2f %7.2f\n\n", I.name, I.rec.x, I.rec.y, I.rec.z, O.rec.z);

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
        O.rec.classification = 18;  /* High Noise */
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
        nuncius (INFO, "Withheld %d points from %s\n", removed, I.name);
    patch;
}
