/*
 *    Test program for the sLASh LAS file reader.
 *
 *    Compilation
 *       gcc -pedantic -Wall -Wno-long-long -I</path(to/slash.h> -o slashdump -O2 /path/to/slashdump.c
 *
 *    Thomas Knudsen, thokn@gst.dk, 2013-06-13
 *    2013-07-06 Redone for silas->slash update


****************************************************************
Copyright (c) 2013, Danish Geodata Agency, <gst@gst.dk>

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
****************************************************************

 *
 */


#ifdef NO_MAIN_REMAINS
#define main(argc, argv) slashdump_main (argc, argv)
#endif

#include "../include/slash.h"
#include "../include/asta.h"
#include "../include/stack.h"
#include "../include/comquat.h"
#include "../include/roipoly.h"

const char slashdump_helptext[] = {
"Syntax: slashdump [-o OUTFILE] [-r ROIFILE] [-O METADATAFILE] [-j JOURNALFILE] LASFILE...\n\n"

"Read las file(s) LASFILE.... Dump las header and histogram to stderr or,\n"
"to METADATAFILE if specified\n"
"dump x/y/z coordinates to stdout, or to OUTFILE if specified\n\n"

"If optional ROIFILE is given, ignore points outside ROI polygon\n\n"

"If optional JOURNALFILE is given, duplicate all output there\n"
};

/* This is probably too cute for real men - but still horribly useful */
#include <getopt.h>
#define  decode(optstr, optchar, argc, argv) \
    while ((optchar = getopt (argc, argv, optstr))!=-1) switch (optchar)


void close_all_outfiles (FILE *fout, FILE *fmet) {
    if ( (0!=fout) && (stdout!=fout) && (stderr!=fout) )
        fclose (fout);
    if ( (0!=fmet) && (stdout!=fmet) && (stderr!=fmet) )
        fclose (fmet);
}


int main (int argc, char **argv) {
    LAS *h = 0;
    ASTA *stat_x = 0, *stat_y = 0, *stat_z = 0;
    size_t histogram[256];

    /* by default data output goes to stdout */
    char *fnout =  dash;
    FILE *fout  = stdout;

    /* by default, metadata output goes to stderr */
    char *fnmet    =  dash;
    FILE *fmet     =  stderr;

    /* if requested, all output is copied to the journal */
    char *fnjou    =  dash;
    
    /* region-of-interest file name */
    char *fnroi    = 0;
    comp_stack *region = 0;
    
    /* input file handling */
    int fileindex;
    char *fnin;

    int optchar = 0;
    int status = 1;
    int i = 0, n = 0;
    int x_decimals = 2, y_decimals = 2, z_decimals = 3;

    status = 1;
    decode ("j:o:O:vhr:", optchar, argc, argv) {

        case 'o': /* data output file name */
            fnout = optarg;
            fout  = fopen(fnout, "wt");
            if (0==fout) {
                close_all_outfiles (fout, fmet);
                return inform (0, status, stderr, "Cannot open output file %s - bye\n", fnout);
            }
            break;

        case 'O': /* metadata output file name */
            fnmet = optarg;
            fmet  = fopen(fnmet, "wt");
            if (0==fmet) {
                close_all_outfiles (fout, fmet);
                return inform (0, status, stderr, "Cannot open metadata file %s - bye\n", fnmet);
            }
            break;

        case 'j': /* journal file name */
            fnjou = optarg;
            set_journal (fnjou, "wt", 0);
            break;

        case 'r': /* roi file name */
            fnroi = optarg;
            region = roi_read (fnroi);
            if (0==region)
                return inform (0, status, stderr, "Couldn't read ROIfile '%s' - bye!\n", fnroi);
            break;

        case 'v': /* verbosity */
            increment_verbosity_level ();
            break;

        case 'h': /* print help message to stdout */
            close_all_outfiles (fout, fmet);
            return inform (0, 0, stdout, slashdump_helptext);
        
        default:  /* unknown option */
            close_all_outfiles (fout, fmet);
            return inform (0, status, stderr, "Unknown option: '%c' - bye!\n", optchar);
    }



    
    /* allocate memory for statistics */
    stat_x = asta_alloc ();
    stat_y = asta_alloc ();
    stat_z = asta_alloc ();
    if (!stat_x || !stat_y || !stat_z)
        goto cleanup;

    for (i=0; i<256; i++)
        histogram[i] = 0;


    if (optind >= argc)
        fnin = dash;

    /* TODO: make fnin = dash work - here and in las_open */
    for (fileindex = optind; fileindex < argc; fileindex++) {
        fnin = argv[fileindex];

        h = las_open (fnin, "rb");
        status = 3;

        if (0==h)
            goto cleanup;


        status = 4;
        las_header_display (fmet, h);


        /* loop over all records */
        while  (las_read (h))  {
            double x, y;
            n++;
            x = las_x (h);
            y = las_y (h);
            if (0==point_in_polygon(region, compify(x, y)))
                continue;
            las_record_display (fout, h);
            asta (stat_x, x);
            asta (stat_y, y);
            asta (stat_z, las_z (h));
        }
        for (i=0; i<256; i++)
            histogram[i] += h->class_histogram[i];

        /* need to store these for pasta_inform, below */
        x_decimals = -log10(h->x_scale) + 0.5;
        y_decimals = -log10(h->y_scale) + 0.5;
        z_decimals = -log10(h->z_scale) + 0.5;
        
        las_close (h);
        h = 0;

    }

    fprintf (fmet, "records read = %d\n", n);

    if (n) {
        asta_info (stat_x, fmet, "x: ", 3, x_decimals);
        asta_info (stat_y, fmet, "y: ", 3, y_decimals);
        asta_info (stat_z, fmet, "z: ", 3, z_decimals);

        for (i=0; i<256; i++)
            if (histogram[i])
                fprintf (fmet, "h[%3.3d] = %d\n", i, (int) histogram[i]);

        status = 0;
    }
    /* the free/close functions have been designed to ignore calls with */
    /* null pointer arguments. With properly initialized identifiers,   */
    /* this makes the clean up code very simple                         */
    cleanup:
    stack_free (region);
    asta_free (stat_z);
    asta_free (stat_y);
    asta_free (stat_x);
    return status;
}
