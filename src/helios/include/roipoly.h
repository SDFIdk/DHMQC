/* ------------------------------------------------------------------------
  
This file is part of the Helios system.
Based on roi.h from the BooGIE system

Thomas Knudsen 1994-2013

****************************************************************
Copyright (c) 1994-2010 Thomas Knudsen / KMS.
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

--------------------------------------------------------------------------*/

#ifndef __ROIPOLY_H
#define __ROIPOLY_H


#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <float.h>
#include <limits.h>
#include <ctype.h>

#include "stack.h"
#include "comquat.h"


int skip_whitespace_and_comments (FILE *f) {
    int c;
    for (;;) {
        /* skip whitespace */
        do {
            c = getc (f);
        } while ((EOF!=c) && isspace (c));
        if (EOF==c)
            return EOF;
        ungetc (c, f);
        

        /* skip comment lines */
        if ('#'==c) {
            do {
                c = getc (f); 
            } while ((EOF != c) && ('\r' != c) && ('\n' != c));
            if (EOF==c)
                return EOF;
            continue; /* go on and skip more whitespace */
        }
        else
            return 0; /* non-comment following skipped whitespace */
    }
    return 0; /* should not happen */
}



/*********************************************************************/
inline void *roi_read (char *filename) {
/*********************************************************************
    The region-of-interest (roi) is indicated by a polygon, which
    may consist of disjunct parts.
    
    If non-disjunct, the last vertex of the polygon need not
    match the first (i.e. the polygon is automatically closed).
    
    If disjunct, the individual parts must be wrapped in "0 0"
    records, and the last vertex must match the first.
    cf. http://www.ecse.rpi.edu/Homepages/wrf/Research/Short_Notes/pnpoly.html
*********************************************************************/
    comp xy;
    comp_stack *reg;
    size_t fields = 0;
    FILE *f;

    stack_alloc (reg, comp, 15);
    
    if (0==reg)
        return 0;

    f = fopen (filename, "rt");
    if (0==f)
        return 0;

    do {
        if (EOF==skip_whitespace_and_comments (f))
            break;
        /* try to read two numbers. Failure means syntax error or EOF */
        fields = fscanf (f, "%lf%lf", &(xy.x), &(xy.y));
        if (2 != fields)
            break;
        push (reg, xy);
    } while (!feof (f));

    fclose (f);
    
    /* catch the "syntax error" break above */
    if (feof (f))
        return reg;
    stack_free (reg);
    return 0;
}



inline int point_in_polygon (comp_stack *polygon, comp pnt) {
    size_t i,  j,  inside = 0;
    j = depth (polygon) - 1;

    for (i = 0; i < depth (polygon); j = i++)
        if ( (((element (polygon, i)).y>pnt.y) != ((element (polygon, j)).y>pnt.y)) &&
	         (pnt.x < ((element (polygon, j)).x-(element (polygon, i)).x) * (pnt.y-(element (polygon, i)).y) / ((element (polygon, j)).y-(element (polygon, i)).y) + (element (polygon, i)).x) )
            inside = !inside;
    return inside;
}

#endif    /* __ROIPOLY_H */
