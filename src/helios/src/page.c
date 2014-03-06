/*********************************************************************
page - read LAS files, write ESRI ascii grid

    gcc -W -Wall -Wextra -Wno-long-long -pedantic -O2 -o page page.c

This file is part of the Helios bundle.

PAGE: Page Ain't Geogrid Either!

The name refers to the fact that PAGE is the successor to PINGPONG,
and "PINGPONG Is Not Geogrid: PINGPONG's an Ordinary New Gridder".

In the geodetic community, Geogrid is a famous gridding program by
Rene Forsberg. Geogrid is not in any way related to neither Page
nor Pingpong.
*********************************************************************
Copyright (c) 2013-2014, Thomas Knudsen <knudsen.thomas@gmail.com>
Copyright (c) 2013-2014, Danish Geodata Agency, <gst@gst.dk>

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
********************************************************************/
#define _USE_MATH_DEFINES
#include <math.h>
#include <assert.h>

#include "../include/stack.h"
#include "../include/comquat.h"
#include "../include/asta.h"
#include "../include/slash.h"
#include "../include/esrigrid.h"

/* This is probably too cute for real men - but still horribly useful */
#include <getopt.h>
#define  decode(optstr, optchar, argc, argv) \
    while ((optchar = getopt (argc, argv, optstr))!=-1) switch (optchar)


const char page_helptext[] = {
"Syntax: page [-o OUTFILE] [-g GRIDDESC] [-F FILTER][-p PREDICTOR] LASFILE...\n\n"

"Read las file(s) LASFILE.... write gridded values to OUTFILE.\n"
};


#ifdef NO_MAIN_REMAINS
#define main(argc, argv) page_main (argc, argv)
#endif




/***********************************************************************/
const quat *search_easting(double key, const quat *base, size_t nitems) {
/************************************************************************
  Locate the first element of array BASE, with an easting larger than
  KEY - i.e. skip points too far westward of region of interest.
************************************************************************/
    size_t i = -1;
    while (++i < nitems)
        if (key < base[i].i)
            return base + i;
    return 0;
}

/***********************************************************************/
const trip *search_northing(double key, const trip *base, size_t nitems) {
/************************************************************************
  Locate the first element of array BASE, with a northing less than
  KEY - i.e. skip points too far northward of region of interest.
************************************************************************/
    size_t i = -1;
    while (++i < nitems)
        if (key > base[i].y)
            return base + i;
    return 0;
}


/***********************************************************************
  comparator functions for C stdlib qsort ()
************************************************************************/
int compare_trip_northing_negated (const void  *a, const void *b ) {
/***********************************************************************/
   if (((const trip *) a)->y < ((const trip *)b)->y)
       return 1;
   if (((const trip *) a)->y > ((const trip *)b)->y)
       return -1;
   return 0;
}
/***********************************************************************/
int compare_quat_easting (const void  *a, const void *b ) {
/***********************************************************************/
   if (((const trip *) a)->y > ((const trip *)b)->y)
       return 1;
   if (((const trip *) a)->y < ((const trip *)b)->y)
       return -1;
   return 0;
}








/***********************************************************************/
enum predictor {
    PREDICTOR_NONE = 0, PREDICTOR_NEAREST,    PREDICTOR_INVDIST,
    PREDICTOR_DENSITY,  PREDICTOR_DISTANCE,   PREDICTOR_BOXDENSITY
};
/***********************************************************************/



/***********************************************************************/
quat predict (double northing, double easting, const quat *left, const quat *right, quat predpar, double nodata_value) {
/************************************************************************
  This is where the fun starts... compute the height at (N,E) from the
  scattered height observations bracketed by LEFT and RIGHT
************************************************************************/
    quat *q, result;
    double min = DBL_MAX, znn = 0, radius = predpar.j, wsum = 0, sumw = 0;
    double area = (M_PI*radius*radius);
    size_t n = 0;
    enum predictor method = floor(predpar.i+0.5);

    result.i = nodata_value;
    result.j = nodata_value;
    result.k = nodata_value;
    result.r = nodata_value;

    if (left>=right)
        return result;
        
    if (PREDICTOR_BOXDENSITY==method) {
        result.r = (right - left) / (4*radius*radius);
        return result;
    }
    znn = left->k;


    /* compute distances from grid point to all relevant observations */
    for (q = (quat *) left; q < right; q++) {
        double d = hypot (easting - q->i, northing - q->j);

        /* q->r = d; not needed yet */

        /* nearest neighbour (so far) */
        if (min > d) {
            min = d;
            znn = q->k;
        }

        if (d < radius) {
            n++;
            if (PREDICTOR_INVDIST==method) {
                /* the power==0 check avoids pow(0,0) i.e. NaN */
                double w;

                /* an observation on the spot? use it directly    */
                /* (also avoids the pow(0,-n) -> +/-INF problem)  */
                if (d < radius/1000) {
                    wsum = q->k;
                    sumw = 1;
                    break;
                }

                /* the power==0 check avoids pow(0,0) i.e. NaN */
                w = (predpar.k==0? 1: pow(d, -predpar.k));
                wsum += w*q->k;
                sumw += w;
            }
        }
    }

    if (min < radius) {
        result.i = znn;        /* nearest neighbour (nn) estimator */
        result.j = min;        /* dist. to nn */
    }
    if (0!=n)
        result.k = n / area;   /* density */

    switch (method) {
        case PREDICTOR_DISTANCE:
            result.r = result.j;
            break;
        case PREDICTOR_DENSITY:
            result.r = result.k;
            break;
        case PREDICTOR_INVDIST:
            result.r = (sumw != 0)? wsum / sumw : nodata_value;
            break;
        default:
            result.r = znn;
    }
    return result;
}





char testfile[] = {"d:/Geodata/Oksbol-2013/1km_6170_451.las"};
char testgrid[] = {"G/6170000.5/451000.5/1000/1000/1/9999"};

int main (int argc, char *argv[]) {
    FILE           *out = 0;
    ASTA           *raw_stats = 0, *grid_stats = 0;
    ESRIGRID       *g = 0;
    LAS_FILTER     *filter = 0;
    stack(trip)     all_points;
    stack(quat)     row_points;
    trip           *t;
    size_t          row, col;
    double          search_radius = 2.0;
    const trip     *haystack, *sentinel;


    /* input file handling */
    int fileindex;
    char dash[] = {"-"};
    char *fnout = dash;

    int optchar     = 0;
    int status      = 1;
    int bogusreturn = 0;
    int verbosity   = 0;
    
    quat predpar = {PREDICTOR_NEAREST, DBL_MAX, 2, 2}; /* TODO: more sane way of setting default radius (congruent with grid interval) */

    decode ("o:g:p:F:b:vh", optchar, argc, argv) {

        case 'o': /* data output file name */
            fnout = optarg;
            out  = fopen(fnout, "wt");
            if (0!=out)
                break;
            fprintf (stderr, "Cannot open output file %s - bye\n", fnout);
            return status;

        case 'g': /* grid parameters */
            g = parse_grid_opt (optarg);
            if (0!=g)
                break;
            fprintf (stderr, "Bad grid descriptor %s - bye\n", optarg);
            return status;

        case 'p': /* predictor */
            /* Nearest neighbour */
            if (0==strncmp("nn:", optarg, 3)) {
                double radius;
                int n = sscanf (optarg, "nn:%lf", &radius);
                if (1!=n) {
                    fprintf (stderr, "Bad arg for predictor nn: '%s' - bye!\n", optarg+3);
                    return status;
                }
                predpar.i = PREDICTOR_NEAREST;
                predpar.j = radius;
                break;
            }

            /* Inverse distance */
            if (0==strncmp("id:", optarg, 3)) {
                double radius, power;
                int n = sscanf (optarg, "id:%lf/%lf", &radius, &power);
                if (2!=n) {
                    fprintf (stderr, "Bad arg for predictor id: '%s' - bye!\n", optarg+3);
                    return status;
                }
                predpar.i = PREDICTOR_INVDIST;
                predpar.j = radius;
                predpar.k = power;
                break;
            }

            /* Density */
            if (0==strncmp("density:", optarg, 8)) {
                double radius;
                int n = sscanf (optarg, "density:%lf", &radius);
                if (1!=n) {
                    fprintf (stderr, "Bad arg for predictor density: '%s' - bye!\n", optarg+8);
                    return status;
                }
                predpar.i = PREDICTOR_DENSITY;
                predpar.j = radius;
                break;
            }

            /* Distance */
            if (0==strncmp("distance:", optarg, 9)) {
                double radius;
                int n = sscanf (optarg, "distance:%lf", &radius);
                if (1!=n) {
                    fprintf (stderr, "Bad arg for predictor distance: '%s' - bye!\n", optarg+9);
                    return status;
                }
                predpar.i = PREDICTOR_DISTANCE;
                predpar.j = radius;
                break;
            }

            /* Box density */
            if (0==strncmp("boxdensity:", optarg, 11)) {
                double radius;
                int n = sscanf (optarg, "boxdensity:%lf", &radius);
                if (1!=n) {
                    fprintf (stderr, "Bad arg for predictor boxdensity: '%s' - bye!\n", optarg+11);
                    return status;
                }
                predpar.i = PREDICTOR_BOXDENSITY;
                predpar.j = radius;
                break;
            }

            fprintf (stderr, "Unknown predictor: '%s' - bye!\n", optarg);
            return status;

        case 'F': /* filter parameters */
            if (0==filter)
                filter = las_filter_alloc ();
            if (0==filter)
                return status;
            if (0==las_filter_decode (filter, optarg))
                break;
            fprintf (stderr, "Bad filter descriptor %s - bye\n", optarg);
            return status;
            
        case 'b': /* bogus - communicate via return code */
            if (0==strcmp (optarg, "decimin"))
                bogusreturn = 10;
            break;

        case 'v': /* verbosity */
            verbosity++;
            break;

        case 'h': /* print help message to stdout */
            if (out)
                fclose (out);
            return (fprintf (stdout, page_helptext), 0);

        default:  /* unknown option */
            if (out)
                fclose (out);
            fprintf (stderr, "Unknown option: '%c' - bye!\n", optchar);
            return status;
    }
    search_radius = predpar.j;

    if (optind >= argc) {
        fprintf (stderr, "Error: must specify at least 1 input file - bye!\n");
        return status;
    }
    
    if (0 == g) {
        fprintf (stderr, "Error: must specify at grid parameters (option -g) - bye!\n");
        return status;
    }

    /* This is the storage for the ENTIRE point cloud */
    stack_alloc (all_points, 1000000);
    assert (0!=all_points);

    /*
    This is the storage for the more limited part of the point
    cloud relevant for a single grid row.
    Here we need a bit of workspace, and hence expand from
    a stack of trips to a stack of quats.
     */
    stack_alloc (row_points, 100000);
    assert (0!=row_points);


    /* Read input files */
    for (fileindex = optind; fileindex < argc; fileindex++) {
        LAS *in = 0;
        char *fnin = argv[fileindex];
        if (verbosity > 1)
            fprintf (stderr, "Reading from '%s'\n", fnin);
        in = las_open (fnin, "rb");
        assert (0!=in);
        if (verbosity > 2)
            las_header_display (in, stderr);
        if (filter)
            in->filter = filter;

        /* read the input data - TODO: use dispatch table */
        while  (las_read (in))
            push(all_points, tripify (las_x (in), las_y (in), las_z (in)));
        if (verbosity > 3)
           fprintf (stderr, "done reading \"%s\"\n", fnin);
        las_close (in);
    }
    raw_stats = asta_alloc ();
    assert (0!=raw_stats);
    for (t = begin (all_points);  t != end (all_points); t++)
        asta (raw_stats, t->z);
    asta_info (raw_stats, stderr, "raw_stats", 2, 10);

    /* Sort everything into descending order by northing */
    stack_sort (all_points, compare_trip_northing_negated);
    asta_reset (raw_stats);
    for (t = begin (all_points);  t != end (all_points); t++)
        asta (raw_stats, t->z);
    asta_info (raw_stats, stderr, "raw_stats", 2, 10);

    /* initialize output grid file */
    if (dash==fnout)
        out = stdout;
    else
        out = fopen (fnout, "wt");
    assert (0!=out);
    write_esrigrid_header (out, g);
    if (verbosity > 2)
        write_esrigrid_header (stdout, g);

    /* initialize grid relevant state variables */
    haystack = begin (all_points);
    sentinel = end (all_points);
    grid_stats = asta_alloc ();


    /* Generate grid, row-by-row */
    for (row = 0; row < (size_t)g->nrows; row++) {
        double northing = g->yllcenter + (g->nrows - row - 1) * g->cellsize;
        double upper_northing = northing + search_radius;
        double lower_northing = northing - search_radius;
        const trip *first, *last, *curr;
        const quat *hay, *row_sentinel;
        size_t nelem = ptop(all_points) - haystack + 1;

        /* Locate first and last point with northings within the search radius for this row */
        first = search_northing(upper_northing, haystack, nelem);
        if (0==first)
            first = haystack;
        nelem = sentinel - haystack;
        last  = search_northing(lower_northing, first, nelem);
        if (0==last)
            last = sentinel;

        /* Copy the relevant parts to the row_points stack */
        depth (row_points) = 0;
        for (curr = first; curr < last; curr++)
            push (row_points, quatify (0, curr->x, curr->y, curr->z));
        row_sentinel = end (row_points);

        hay = begin (row_points);
        qsort ((void *) hay, depth(row_points), sizeof (quat), compare_quat_easting);

        for (col = 0; col < (size_t)g->ncols; col++) {
            double easting = g->xllcenter + col * g->cellsize;
            double right_easting = easting + search_radius;
            double left_easting  = easting - search_radius;
            const quat *left, *right;
            quat result;

            nelem = row_sentinel - hay;

            /* Locate data points forming left and right bracket for the search radius of current column */
            left = search_easting(left_easting, hay, nelem);

            if (0==left)
                left = hay;
            nelem -= (left - hay);
            nelem = row_sentinel - left;
            right = search_easting(right_easting, left, nelem);
            if (0==right)
                right = row_sentinel;

            result = predict (northing, easting, left, right, predpar, g->nodata_value);
            fprintf (out, " %5.2f", result.r);
            if (result.r != g->nodata_value)
                asta (grid_stats, result.r);
            hay = left;
        }
        fprintf (out, "\n");

        haystack = first;
        nelem = sentinel - haystack;

        if (verbosity > 2) {
            fprintf (stderr, "[northing: %.2f done, using %d points. %d rows to go. %d points left]     \r",
                         northing, (int) (last-first), (int)(g->nrows-row-1), (int)nelem);
            fflush (stderr);
        }
    }

    if (stdout!=out)
        fclose(out);
    
    stack_free (row_points);
    stack_free (all_points);
    las_filter_free (filter);

    if (verbosity > 1) {
        fprintf (stderr, "\n");
        asta_info (raw_stats,  stdout, "raw data    ", 10, 2);
        asta_info (grid_stats, stdout, "gridded data", 10, 2);
    }
    
    /* handle special case of communicating through process status */
    switch (bogusreturn) {
        case 10:
            status = 10 * asta_min (grid_stats);
            break;
        default:
            status = 0;
    }
    
    asta_free (raw_stats);
    asta_free (grid_stats);
    
    return status;
}
