/***********************************************************************

Bounding box algebra

This file is part of the Helios system.
Based on roi.h from the BooGIE system

Interval endpoint definitions (closed/open) are selected in
accordace with the intentions behind "Det Danske Kvadratnet",
i.e. left and lower limits are part of the bbox, right and
upper are not (see comments below).

Thomas Knudsen 1994-2014

****************************************************************
Copyright (c) 1994-2014 Thomas Knudsen
Copyright (c) 2014, Danish Geodata Agency, <gst@gst.dk>

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

***********************************************************************/

#ifndef __BBOX_H
#define __BBOX_H


#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <float.h>
#include <limits.h>
#include <ctype.h>

/**********************************************************************/
typedef struct bbox { double n, e, s, w; } bbox;
/***********************************************************************
    The bounding box type "bbox". If the stack.h header library is
    loaded prior to loading bbox.h, bbox becomes stackable.
***********************************************************************/
#ifdef __STACK_H
stackable (bbox);
#endif


/**********************************************************************/
const bbox nowhere = {0,0,0,0};
const bbox everywhere = {HUGE_VAL, HUGE_VAL, -HUGE_VAL, -HUGE_VAL};
/***********************************************************************
    Two constants facilitating clear communication about special
    cases. "nowhere" and "everywhere" are the bbox parallels of
    the limits.h constants such as INT_MIN, INT_MAX etc.
***********************************************************************/



/**********************************************************************/
#define inrange(x0,x,x1) ((x0<=x) && (x < x1))
#define min2(x,y) ((x < y)? x: y)
#define max2(x,y) ((x > y)? x: y)
/***********************************************************************
    A few macros simplifying the implementation of the intersection and
    union functions.

    The open/closed combinations of the interval definition used in
    inrange (x0, x, x1) have been selected in order to fit the
    intentions behind the "Det Danske Kvadratnet".
    (Ravnkjaer Larsen, pers comm, 2014-03-27)
***********************************************************************/



/**********************************************************************/
int bboxes_intersect(bbox A, bbox B) {
/***********************************************************************
    Determine whether or not two bboxes intersect.
    Returns non-zero if they intersect, 0 if not.
***********************************************************************/
    int xoverlap, yoverlap;
    xoverlap = inrange(B.w, A.w, B.e) ||  inrange(A.w, B.w, A.e);
    yoverlap = inrange(B.s, A.s, B.n) ||  inrange(A.s, B.s, A.n);
    return xoverlap && yoverlap;
}


/**********************************************************************/
bbox bbox_intersection (bbox A, bbox B) {
/***********************************************************************
    Given that bboxes A and B intersect, return a bbox of their
    intersection. If no intersection, return the constant "nowhere"
***********************************************************************/
    bbox C;
    if (!bboxes_intersect (A, B))
        return nowhere;
    C.n = min2(A.n, B.n);
    C.s = max2(A.s, B.s);
    C.e = min2(A.e, B.e);
    C.w = max2(A.w, B.w);
    return C;
}


/**********************************************************************/
bbox bbox_union (bbox A, bbox B) {
/***********************************************************************
    Returns the minimum bbox exactly covering A and B
***********************************************************************/
    bbox C;
    C.n = max2(A.n, B.n);
    C.s = min2(A.s, B.s);
    C.e = max2(A.e, B.e);
    C.w = min2(A.w, B.w);
    return C;
}


/**********************************************************************/
int bbox_identical (bbox A, bbox B) {
/***********************************************************************
    Returns 1 if A and B are  identical, 0 otherwise
***********************************************************************/
    if (A.n != B.n) return 0;
    if (A.e != B.e) return 0;
    if (A.s != B.s) return 0;
    if (A.w != B.w) return 0;
    return 1;
}


/**********************************************************************/
int point_in_bbox (bbox b, double x, double y) {
/***********************************************************************
    Determine whether the point x,y falls within the bounding box b.
    Returns 1 if inside, 0 if outside.
    
    Note however, that interval endpoint definitions are selected in
    accordance with the intentions behind "Det Danske Kvadratnet"
    (Ravnkjaer Larsen, pers comm, 2014-03-27)
***********************************************************************/

    if (x  <  b.w)  return 0;
    if (x  >= b.e)  return 0;
    if (y  <  b.s)  return 0;
    if (y  >= b.n)  return 0;
    return 1;
}


/**********************************************************************/
int bbox_print (FILE *f, bbox b) {
/***********************************************************************
    Print a n/e/s/w representation of b to stream f.
    Mostly a debugging/documentation aid.
***********************************************************************/
    return fprintf (f, "%.1f/%.1f/%.1f/%.1f\n", b.n, b.e, b.s, b.w);
}
#endif    /* __BBOX_H */
