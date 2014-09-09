#include "../include/slash.h"

/* geomide: Fast check for GEOMetrical IDEntity of two files */

int main (int argc, char **argv) {
    LAS *h0, *h1;
    size_t r = 0, read = 10, skip = 0;
    char *p;

    if (1==argc)
        return printf("syntax: geomide file1 file2 [nunber of points to skip] [number of data to read]\nCHeck GEOMetric IDEntity\ndefault: skip 0, read 10"),0;

    assert (argc >= 3);

    /* open las file for reading */
    h0 = las_open (argv[1], "rb");
    assert (h0!=0);
    h1 = las_open (argv[2], "rb");
    assert (h0!=0);

    if (argc > 3)
        skip = atoll (argv[3]);
    if (argc > 4)
        read = atoll (argv[4]);
    p = strrchr (argv[2], '\\');
    if (0==p)
        p = strrchr (argv[2], '/');
    if (0==p)
        p = argv[2];


    /* show general information
    las_header_display (h, stdout);
    las_vlr_interpret_all (h, stdout);  */
    if (0==read)
        return 0;

/*
    if (h0->number_of_point_records != h1->number_of_point_records)
        return printf ("diff in header file %s. records: %lu vs. %lu\n", p, (unsigned long) h0->number_of_point_records, (unsigned long)  h1->number_of_point_records);
*/

    /* skip first records */
    if (0!=skip) {
        las_seek (h0, skip, SEEK_SET);
        las_seek (h1, skip, SEEK_SET);
    }

    /* loop over remaining records - extract data */
    while  (las_read (h0) && las_read (h1))  {
        if (r >= read)
            exit (0);
        r++;
        if (las_gps_time (h0) != las_gps_time (h1)) break;
        if (fabs(las_x (h1) - las_x (h0)) > 0.0055) break;
        if (fabs(las_y (h1) - las_y (h0)) > 0.0055) break;
        if (fabs(las_z (h1) - las_z (h0)) > 0.0055) break;
    }

    printf ("x: %.2f dx: %.3f, dt: %lg\n", las_x (h0), las_x (h0) - las_x (h1), las_gps_time (h0)-las_gps_time (h1));
    printf ("diff in rec %lu file %s\n", (unsigned long) (r-1 + skip), p);

    las_close (h0);
    las_close (h1);
    return 0;
}
