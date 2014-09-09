/***********************************************************************

   R E P A I R - G P S - T I M E - G L O B A L - E N C O D I N G . C

************************************************************************

0. SYNOPSIS

    repair-gps-time-global-encoding LAS_FILE...

Repair global encoding field of one or more .las files by binarey
patching.

WARNING: DO NOT USE THIS UTILITY UNLESS YOU KNOW WHAT YOU DO!!! [2]

--

1. BACKGROUND

In a .las file header, bit 0 of the GLOBAL ENCODING field identifies
how the time stamps in the file are to be interpreted.

There are two varieties:

Flag == 0.
    Time stamps are to be interpreted as GPS week time, i.e. seconds
    since the start of the GPS-week of the observation campaign
    (which must be known from external sources - it is not stored in
    the las file)

Flag == 1.
    Time stamps are to be interpreted as "Adjusted GPS time",
    i.e. seconds since the epoch of the GPS time frame, adjusted by
    subtracting 1 000 000 000 seconds (1e9).
 
See [1] for details.

--

2. PROBLEM

It sometimes happen that a file with time stamps in Adjusted GPS
time is stored with an encoding flag indicating GPS week time.

--

3. SOLUTION

This horribly obnoxious little utility repairs that problem by
pure and dumb binary patching.

2014-09-09 Thomas Knudsen, Danish Geodata Agency, <thokn@gst.dk>

[1] LAS SPECIFICATION VERSION 1.3 – R11 OCTOBER 24, 2010
    Bethesda, Maryland,
    The American Society for Photogrammetry & Remote Sensing
    18 pp.

[2] George Lakoff (1987): Women, Fire, and Dangerous Things
    University of Chicago Press, 632pp., ISBN 0-226-46803-8

***********************************************************************/

#include <stdio.h>
#include <string.h>
#include <assert.h>


int main (int argc, char **argv) {
    unsigned char buf[8];
    FILE *f;
    int i;
    assert (argc>=2);

    for (i = 1; i < argc; i++) {
        f = fopen (argv[i], "r+b");
        assert (f!=0);
        fread (buf, 1, 8, f);
        assert (0==strncmp ((char *)buf, "LASF", 4));
    
        /* do the dirty work in the buffer */
        buf[6] |= ((unsigned char)(1));
    
        rewind (f);
        fwrite (buf, 1, 8, f);
        fclose (f);
        printf ("File #%d:  %s  done.\n", i, argv[i]);
    }
    return 0;
}
