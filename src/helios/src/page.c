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

testfile: d:/Geodata/Oksbol-2013/1km_6170_451.las
testgrid G/6170000.5/451000.5/1000/1000/1/9999
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

#include "../include/slash.h"
#include "../include/stack.h"
#include "../include/almanak.h"
#include "../include/comquat.h"
#include "../include/asta.h"
#include "../include/esrigrid.h"
#include "../include/bbox.h"

#include <math.h>
#include <assert.h>

/* This is probably too cute for real men - but still horribly useful */
#include <getopt.h>
#define  decode(optstr, optchar, argc, argv) \
    while ((optchar = getopt (argc, argv, optstr))!=-1) switch (optchar)


const char page_helptext[] = {
"Syntax: page [-o OUTFILE] [-g GRIDDESC] [-S SELECTOR][-p PREDICTOR] LASFILE...\n\n"
"Read las file(s) LASFILE..., write gridded values to OUTFILE.\n"
"\n"
"Examples:\n"
"    page -vvvo foo.asc -g G/6170000.5/451000.5/1000/1000/1/9999 -p id:1/2 1km_6170_451.las\n"
"    e:page -vvvo solar_height.asc -g G/6139050/640050/10/10/100/9999 -p solar_elevation:38.8/55/9 pre_1km_6139_640.las"
};


/***********************************************************************/
const quat *search_easting (stack (quat) haystack, const quat *base, double needle) {
/************************************************************************
  Locate the first element of array BASE, with an easting larger than
  NEEDLE - i.e. skip points too far westward of region of interest.
************************************************************************/
    const quat *t;
    for (t = base; t != end(haystack); t++)
        if (needle < t->i)
            return t;
    return end(haystack); /* sentinel */
}

/***********************************************************************/
const trip *search_northing (stack (trip) haystack, const trip *base, double needle) {
/************************************************************************
  Locate the first element of array BASE, with a northing less than
  NEEDLE - i.e. skip points too far northward of region of interest.
************************************************************************/
    const trip *t;
    for (t = base; t != end(haystack); t++)
        if (needle > t->y)
            return t;
    return end(haystack); /* sentinel */
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
    PREDICTOR_DENSITY,  PREDICTOR_DISTANCE,   PREDICTOR_BOXDENSITY,
    PREDICTOR_MAX_SOLAR_ELEVATION
};
/***********************************************************************/


/***********************************************************************/
quat predict (double northing, double easting, const quat *left, const quat *right, quat predpar, double nodata_value) {
/************************************************************************
  This is where the fun starts... compute the height at (N,E) from the
  scattered height observations bracketed by LEFT and RIGHT.
  Returns a quat, with
  * predict.i: value of nearest neighbour
  * predict.j: distance to nearest neighbour
  * predict.k: point density (if != 0)
  * predict.r: estimate according to arg predpar
************************************************************************/
    quat *q, result;
    double min = DBL_MAX, znn = 0, radius = predpar.j, wsum = 0, sumw = 0;
    double area = (M_PI*radius*radius);
    size_t n = 0;
    enum predictor method = floor(predpar.r+0.5);

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
    

    /* in this case q.k (z) is really a las_gps_time */
    if (PREDICTOR_MAX_SOLAR_ELEVATION==method) {
        double max_so_far = 0, previous_time = -HUGE_VAL;
        result.r = 0;
        errno = 0;
        for (q = (quat *) left; q < right; q++) {
            double e;
            double d = fabs (previous_time - q->k);

            /* ignore tiny time differences - in effect check only once per flight strip */
            if (d < 100)
                continue;
            e = solar_elevation (predpar.j, predpar.k, q->k, EPOCH_MODIFIED_GPS);
            previous_time = q->k;
            if (e > max_so_far)
                max_so_far = e;
            if ((e > predpar.i) && (predpar.i < 90))
                return result.r = 1, result;
            errno = 0;
        }
        result.r = (predpar.i < 90)? 0: max_so_far;
        return result;
    }

    znn = left->k;

    /* compute distances from grid point to all relevant observations */
    for (q = (quat *) left; q < right; q++) {
        double d = hypot (easting - q->i, northing - q->j);

        /* q->r = d; not needed yet (needed for quadrant search and kriging) */

        /* nearest neighbour (so far) */
        if (min > d) {
            min = d;
            znn = q->k;
        }

        if (d < radius) {
            n++;
            if (PREDICTOR_INVDIST==method) {
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


struct indata_state {
    int argc;
    char **argv;
    stack (bbox) bounding_box;
    bbox current_roi;
    ASTA *raw_stats;
    LAS_SELECTOR *select;
    size_t preload_rows;
    const trip *first;
    double search_radius;
};



/**********************************************************************/
void setup_bounding_boxes (struct indata_state *files, int verbosity) {
/***********************************************************************
    Read bounding boxes from input files
***********************************************************************/
    int i;
    for (i = 0; i < files->argc; i++) {
        bbox b;
        LAS *in = 0;
        char *fnin = files->argv[i];
        if (verbosity > 2)
            fprintf (stderr, "Reading bounding box from '%s'\n", fnin);

        in = las_open (fnin, "rb");
        assert (0!=in);

        b.n = in->y_max;
        b.s = in->y_min;
        b.w = in->x_min;
        b.e = in->x_max;
        push (files->bounding_box, b);
        if (verbosity > 3)
            fprintf (stderr, "    %.1f/%.1f/%.1f/%.1f\n", b.n, b.w, b.s, b.e);
        las_close (in);
    }
}


/********************************************************************************************/
int imbibe_data (struct indata_state *files, int verbosity, stack(trip) all_points, bbox roi, quat predpar) {
/*********************************************************************************************
    Read input files
*********************************************************************************************/
    int fileindex;
    bbox partial_roi = roi;

    /* we need to remove the already read part from the roi in order to get valid input stats */
    if (!bbox_identical (nowhere, files->current_roi)) {
        const trip *p = all_points->data;
        partial_roi.n = files->current_roi.s;
        /* also remove superfluous data */
        p = search_northing (all_points, p, partial_roi.n + files->search_radius);
        printf ("erasing %ld points\n", (long)(p-all_points->data));
        memmove (all_points->data, p, (end(all_points)-p));
        depth (all_points) -= (p-all_points->data);
        /*erase (all_points, 0ULL, (p-all_points->data));*/
    }

    for (fileindex = 0; fileindex < files->argc; fileindex++) {
        LAS *in = 0;
        char *fnin = files->argv[fileindex];
        if (!bboxes_intersect (partial_roi, element(files->bounding_box, fileindex)))
            continue;
        if (verbosity > 1)
            fprintf (stderr, "Reading from '%s'\n", fnin);
        in = las_open (fnin, "rb");
        assert (0!=in);
        if (verbosity > 2)
            las_header_display (in, stderr);
        if (files->select)
            in->select = files->select;

        /* read the input data */
        while  (las_read (in)) {
            trip p = tripify (las_x (in), las_y (in), las_z (in));
            if (!point_in_bbox (partial_roi, p.x, p.y))
                continue;
            if (PREDICTOR_MAX_SOLAR_ELEVATION==predpar.r)
                p.z = las_gps_time (in);
            push(all_points, p);
            asta (files->raw_stats, p.z);
        }
        if (verbosity > 3)
           fprintf (stderr, "done reading \"%s\"\n", fnin);
        las_close (in);
    }
    /* Sort everything into descending order by northing */
    stack_sort (all_points, compare_trip_northing_negated);
    files->current_roi = roi;
    return 0;
}


/********************************************************************************************/
int row_prepare (stack(trip) all_points, stack(quat) row_points, struct indata_state *files, ESRIGRID *g, quat predpar, int verbosity, size_t row, double search_radius) {
/*********************************************************************************************
    Extract the part of the point cloud relevant for the current grid row.
    Sort west-east, so it is ready for columnwise prediction.
*********************************************************************************************/
    double northing = g->yllcenter + (g->nrows - row - 1) * g->cellsize;
    const trip *first, *last, *curr;
    bbox roi;

    if (0==row)
        setup_bounding_boxes (files, verbosity);

    if (0==(row%files->preload_rows)) {
        /* carefull here: mixing signed and unsigned in subtractions */
        int upper_row = ((int) g->nrows - 1 - (int) row);
        int lower_row = ((int) g->nrows - 1 - (int) row - (int) files->preload_rows);
        /* the roi is the lookahead region buffered by the search radius */
        roi.n = g->yllcenter + upper_row * g->cellsize + search_radius;
        roi.s = g->yllcenter + lower_row * g->cellsize - search_radius;
        roi.w = g->xllcenter - search_radius;
        roi.e = g->xllcenter + (g->ncols - 1) * g->cellsize + search_radius;
        printf ("(Re)initializing at row %lu ", (unsigned long) row); bbox_print (stdout, roi);
        imbibe_data (files, verbosity, all_points, roi, predpar);
        files->first = begin (all_points);
    }

    /* Locate first and last point with northings within the search radius for this row */
    first = search_northing(all_points, files->first, northing + search_radius);
    last  = search_northing(all_points, first, northing - search_radius);
    files->first = first;

    /* Copy the relevant parts to the row_points stack */
    depth (row_points) = 0;
    for (curr = first; curr != last; curr++)
        push (row_points, quatify (0, curr->x, curr->y, curr->z));
    qsort ((void *) begin (row_points), depth(row_points), sizeof (quat), compare_quat_easting);
    return 0;
}



int main (int argc, char *argv[]) {
    FILE           *out = 0;
    ASTA           *raw_stats = 0, *grid_stats = 0;
    ESRIGRID       *g = 0;
    LAS_SELECTOR   *select = 0;
    stack(trip)     all_points;
    stack(quat)     row_points;
    size_t          row, col;
    unsigned long   preload_rows = 0;
    double          search_radius = 2.0;
    struct indata_state  files;

    /* input file handling */
    char dash[] = {"-"};
    char *fnout = dash;

    int optchar     = 0;
    int status      = 1;
    int verbosity   = 0;

    quat predpar = {PREDICTOR_NEAREST, DBL_MAX, 2, 2}; /* TODO: more sane way of setting default radius (congruent with grid interval) */

    decode ("o:g:p:P:S:vh", optchar, argc, argv) {
        int n;
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
                predpar.r = PREDICTOR_NEAREST;
                predpar.i = PREDICTOR_NEAREST;
                predpar.j = radius;
                break;
            }

            /* Inverse distance */
            if (0==strncmp("id:", optarg, 3)) {
                double radius, power;
                n = sscanf (optarg, "id:%lf/%lf", &radius, &power);
                if (2!=n) {
                    fprintf (stderr, "Bad arg for predictor id: '%s' - bye!\n", optarg+3);
                    return status;
                }
                predpar.r = PREDICTOR_INVDIST;
                predpar.i = PREDICTOR_INVDIST;
                predpar.j = radius;
                predpar.k = power;
                break;
            }

            /* Density */
            if (0==strncmp("density:", optarg, 8)) {
                double radius;
                n = sscanf (optarg, "density:%lf", &radius);
                if (1!=n) {
                    fprintf (stderr, "Bad arg for predictor density: '%s' - bye!\n", optarg+8);
                    return status;
                }
                predpar.r = PREDICTOR_DENSITY;
                predpar.i = PREDICTOR_DENSITY;
                predpar.j = radius;
                break;
            }

            /* Distance */
            if (0==strncmp("distance:", optarg, 9)) {
                double radius;
                n = sscanf (optarg, "distance:%lf", &radius);
                if (1!=n) {
                    fprintf (stderr, "Bad arg for predictor distance: '%s' - bye!\n", optarg+9);
                    return status;
                }
                predpar.r = PREDICTOR_DISTANCE;
                predpar.i = PREDICTOR_DISTANCE;
                predpar.j = radius;
                break;
            }

            /* Box density */
            if (0==strncmp("boxdensity:", optarg, 11)) {
                double radius;
                n = sscanf (optarg, "boxdensity:%lf", &radius);
                if (1!=n) {
                    fprintf (stderr, "Bad arg for predictor boxdensity: '%s' - bye!\n", optarg+11);
                    return status;
                }
                predpar.r = PREDICTOR_BOXDENSITY;
                predpar.i = PREDICTOR_BOXDENSITY;
                predpar.j = radius;
                break;
            }

            /* Solar maximum elevation */
            if (0==strncmp("solar_elevation:", optarg, 16)) {
                double limit, latitude, longitude;
                n = sscanf (optarg, "solar_elevation:%lf/%lf/%lf", &limit, &latitude, &longitude);
                if (3!=n) {
                    fprintf (stderr, "Bad arg for predictor solar_elevation: '%s' - bye!\n", optarg+16);
                    return status;
                }
                predpar.r = PREDICTOR_MAX_SOLAR_ELEVATION;
                predpar.i = limit;
                predpar.j = latitude;
                predpar.k = longitude;
                break;
            }

            fprintf (stderr, "Unknown predictor: '%s' - bye!\n", optarg);
            return status;

        case 'P': /* preload lines */
            n = sscanf (optarg, "%lu", &preload_rows);
            if (1==n)
                break;
            fprintf (stderr, "Bad argunemt for preload rows (-P): %s - bye\n", optarg);
            return status;

        case 'S': /* selector parameters */
            if (0==select)
                select = las_selector_alloc ();
            if (0==select)
                return status;
            if (0==las_selector_decode (select, optarg))
                break;
            fprintf (stderr, "Bad selector %s - bye\n", optarg);
            return status;

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
    if (PREDICTOR_MAX_SOLAR_ELEVATION==predpar.r)
        search_radius = g->cellsize/2;

    if (optind >= argc) {
        fprintf (stderr, "Error: must specify at least 1 input file - bye!\n");
        return status;
    }

    if (0==g) {
        fprintf (stderr, "Error: must specify grid parameters (option -g) - bye!\n");
        return status;
    }

    raw_stats = asta_alloc ();
    assert (0!=raw_stats);

    files.argv = argv + optind;
    files.argc = argc - optind;
    files.raw_stats = raw_stats;
    files.select = select;
    files.preload_rows = preload_rows? preload_rows: (size_t) g->nrows;
    files.current_roi = nowhere;
    stack_alloc (files.bounding_box, files.argc);
    files.search_radius = search_radius;
    
    /* This is the storage for the ENTIRE point cloud (grows as needed) */
    stack_alloc (all_points, 1000000);
    assert (0!=all_points);

    /*
     *    This is the storage for the more limited part of the point
     *    cloud relevant for a single grid row.
     *    Here we may need a bit of workspace, and hence expand from
     *    a stack of trips to a stack of quats.
     */
    stack_alloc (row_points, 100000);
    assert (0!=row_points);


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
    grid_stats = asta_alloc ();


    /* Generate grid, row-by-row */
    for (row = 0; row < (size_t)g->nrows; row++) {
        const quat *left, *right;

        row_prepare (all_points, row_points, &files, g, predpar, verbosity, row, search_radius);
        left =  begin (row_points);

        for (col = 0; col < (size_t)g->ncols; col++) {
            double northing = g->yllcenter + (g->nrows - row - 1) * g->cellsize;
            double easting  = g->xllcenter + col * g->cellsize;
            quat result;

            /* Data brackets for current column */
            left  = search_easting(row_points, left, easting - search_radius);
            right = search_easting(row_points, left, easting + search_radius);

            result = predict (northing, easting, left, right, predpar, g->nodata_value);
            /* write {0,1} indicator cases in compact notation */
            if ((0==result.r) || (1==result.r))
                fprintf (out, " %1.0f", result.r);
            else
                fprintf (out, " %5.2f", result.r);
            if (result.r != g->nodata_value)
                asta (grid_stats, result.r);
        }
        fprintf (out, "\n");

        if (verbosity > 2) {
            fprintf (stderr, "[row: %4.4d done, using %6.6d points. %d rows to go. %d points left]     \r",
                         (int)row, (int) depth (row_points), (int)(g->nrows-row-1), (int) (end(all_points)-files.first));
            fflush (stderr);
        }
    }

    if (stdout!=out)
        fclose(out);

    stack_free (row_points);
    stack_free (all_points);
    stack_free (files.bounding_box);
    las_selector_free (select);

    if (verbosity > 1) {
        fprintf (stderr, "\n");
        asta_info (raw_stats,  stdout, "raw data    ", 10, 2);
        asta_info (grid_stats, stdout, "gridded data", 10, 2);
    }
    asta_free (raw_stats);
    asta_free (grid_stats);

    return 0;
}
