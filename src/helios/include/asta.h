/****************************************************************************
                         A S T A

    ASTA (Accumulation of STAtistics is basically a reimplementation
    of the BASTA (BAsic STAtistics) functionality which, following
    earlier ideas, were implemented as part of the BUSSTOP system,
    approx. 1995. But ASTA uses a more roundoff resistant algorithm,
    and the APIs differ.
    
    ASTA is a tiny package for handling and computing fundamental
    internal statistics of a data set.

    ASTA is based on sequential updating in a *single* pass through
    the data set (i.e. "online accumulation").
    
    Online accumulation is evidently prone to overflows and hence
    not the most precise way of computing the moments of a distribution.
    But it means that ASTA is very useful for handling piped data.

    The precision problem is to some extent offset by using very wide
    data types (long long and long double), and fairly roundoff
    resistant algorithms.
    
    This version excludes earlier functionality for histogram handling.

    Thomas Knudsen,
        Copenhagen,   1991
            Early attempt written in awk - a suggestion for
            use with the Gravsoft Package.
        Vejby Strand, 1993
            ufincs.c (part of my MSc thesis work)
        Roskilde, Copenhagen, Vejby Strand, Spentrup, 1995
            BaSta becomes the first app of the BUSSTOP system
        Halifax,      1999-02
            Rewritten as library.
        Hannover,     2007-05-31
            Reconstructed from 1995 code while working on early LAS data.
        Copenhagen,   2011-01-17
            "PASTA" - First version with the more precise algorithms.
            Following a description in Wikipedia [1]
        Copenhagen,   2011-08-05
            Ignore NaN, Inf & DBL_MAX.
        Copenhagen,   2013-06
            Implement more advanced precise algorithms (cf. [1]-[4]).
            Now supports skewness and kurtosis.
        Copenhagen,   2013-07-02
            Moved to file asta.h
        Sundbyøster,  2013-11-04
            Now part of the Helios bundle
    
    The "precise, online" algorithms are described in e.g.
    
    [1] http://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
    [2] http://www.johndcook.com/skewness_kurtosis.html
    [3] http://www.johndcook.com/standard_deviation.html
    [4] http://lingpipe-blog.com/2009/03/19/computing-sample-mean-variance-online-one-pass/

    A nice extension also from John D. Cook:
        Computing the linear regression in a single pass:

    [5] http://www.johndcook.com/running_regression.html

****************************************************************************/


/****************************************************************
Copyright (c) 1991-2014, Thomas Knudsen <knudsen.thomas@gmail.com>
Copyright (c) 2013,      Danish Geodata Agency, <gst@gst.dk>

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
****************************************************************/




#ifndef __ASTA_H
#define __ASTA_H


#include <stdio.h>
#include <float.h>  /* for DBL_MAX */
#include <stdlib.h> /* for calloc  */
#include <math.h>   /* for sqrt    */

/********************************************************************/
struct ASTA {
    long double M1, M2, M3, M4;
    size_t      n;
    double      min, max;
};
/********************************************************************/
typedef struct ASTA ASTA;
#ifdef __STACK_H
stackable_pointer_to(ASTA);
#endif
/********************************************************************/


/********************************************************************/
ASTA *asta_reset (ASTA *p) {
/********************************************************************/
    if (0==p)
        return 0;

    p->n = 0;
    p->M1 = 0;
    p->M2 = 0;
    p->M3 = 0;
    p->M4 = 0;

    p->min   =   DBL_MAX;
    p->max   =  -DBL_MAX;
    return p;
}

/********************************************************************/
inline ASTA *asta_alloc (void) {
/********************************************************************/
    ASTA *p;
    p = calloc(1, sizeof(ASTA));
    if (0==p)
        return 0;
    return asta_reset (p);
}

#define asta_free(p) free(p)



/* the accumulator function */
/********************************************************************/
inline size_t  asta (ASTA *p, double v) {
/********************************************************************/
    long double delta, delta_n, delta_n2, term1;

    size_t n1 = p->n;

    /* ignore invalid data */
	if (isnan(v))
        return p->n;
	if (isinf(v))
        return p->n;
	if (DBL_MAX==v)
        return p->n;


    p->n++;
    delta    =  v - p->M1;
    delta_n  =  delta / p->n;
    delta_n2 =  delta_n * delta_n;
    term1    =  delta * delta_n * n1;
    p->M1   +=  delta_n;
    p->M4   +=  term1 * delta_n2 * (p->n*p->n - 3*p->n + 3) + 6 * delta_n2 * p->M2 - 4 * delta_n * p->M3;
    p->M3   +=  term1 * delta_n * (p->n - 2) - 3 * delta_n * p->M2;
    p->M2   +=  term1;


    /* update extrema */
    if (v < p->min)
        p->min = v;
    if (v > p->max)
        p->max = v;

    return p->n;
}



/********************************************************************/
#define asta_var(p)  ((double)(((p)->n < 2)? 0: (p)->M2 / ((p)->n - 1)))
#define asta_sd(p)   ((double)(((p)->n < 2)? 0: sqrt((p)->M2 / ((p)->n - 1))))
#define asta_skew(p) ((double)(sqrt((p)->n) * (p)->M3/ pow((p)->M2, 1.5))
#define asta_kurt(p) ((double)((p)->n * (p)->M4 / ((p)->M2*(p)->M2) - 3.0))

#define asta_min(p)  ((double)((p)->min))
#define asta_mean(p) ((double)((p)->M1))
#define asta_max(p)  ((double)((p)->max))
#define asta_n(p)    ((double)((p)->n))
/********************************************************************/










void asta_accumulate (ASTA *accumulator, const ASTA *contribution) {
    ASTA combined;
    
    double delta  = contribution->M1 - accumulator->M1;
    double delta2 = delta*delta;
    double delta3 = delta*delta2;
    double delta4 = delta2*delta2;

    combined.min = accumulator->min < contribution->min ? accumulator->min: contribution->min;
    combined.max = accumulator->max > contribution->max ? accumulator->max: contribution->max;
    
    combined.n  = accumulator->n + contribution->n;
    
    combined.M1 = (accumulator->n*accumulator->M1 + contribution->n*contribution->M1) / combined.n;
    
    combined.M2 = accumulator->M2 + contribution->M2 + 
                  delta2 * accumulator->n * contribution->n / combined.n;
    
    combined.M3 = accumulator->M3 + contribution->M3 + 
                  delta3 * accumulator->n * contribution->n * (accumulator->n - contribution->n)/(combined.n*combined.n);
    combined.M3 += 3.0*delta * (accumulator->n*contribution->M2 - contribution->n*accumulator->M2) / combined.n;
    
    combined.M4 = accumulator->M4  + 
                  contribution->M4 +
                  delta4*accumulator->n*contribution->n * (accumulator->n*accumulator->n - accumulator->n*contribution->n + contribution->n*contribution->n) /
                      (combined.n*combined.n*combined.n);
    combined.M4 += 6.0*delta2 * (accumulator->n*accumulator->n*contribution->M2 + contribution->n*contribution->n*accumulator->M2)/(combined.n*combined.n) +
                   4.0*delta*(accumulator->n*contribution->M3 - contribution->n*accumulator->M3) / combined.n;
    
    *accumulator = combined;
    return;
}













/********************************************************************/
#define asta_info(p, stream, message, width, precision)              \
    (p)->n < 2? fprintf (stream, "0 0 0 0 0\n"):                     \
    fprintf (stream, "%*s %10ld  %10.*f  %10.*f  %10.*f  %10.*f\n",  \
            (int)(width), message,                                   \
            (long) (p)->n,                                           \
            (int)(precision), asta_min(p),                           \
            (int)(precision), asta_mean(p),                          \
            (int)(precision), asta_max(p),                           \
            (int)(precision), asta_sd(p)      )
/********************************************************************/

#endif /* __ASTA_H */



#ifdef TESTasta

#ifndef M_PIl
/* The constant Pi in high precision */
#define M_PIl 3.1415926535897932384626433832795029L
#endif

int main (void) {
    ASTA *a;
    size_t i, n=1e7;
    long double dt;   
    dt = 2*M_PIl/(n-1);

    a = asta_alloc ();
    for (i = 0; i < n; i++)
        asta (a, (i*dt)-M_PIl);
    asta_info (a, stdout, "linesum", 20, 12);

    asta_reset (a);
    for (i = 0; i < n; i++) {
        if (0==i%10000)
            fprintf (stderr, "%20.12f %20.12f %20.12f\n", (double)(i*dt), (double)(a->M1), (double)sin(i*dt));
        asta (a, sin (i*dt));
    }
    asta_info (a, stdout, "sinelinesum", 20, 12);

    asta_reset (a);
    for (i = 0; i < n; i++)
        asta (a, sin (i*dt) + (i*dt) - M_PIl);
    asta_info (a, stdout, "sinelinesum", 20, 12);

    asta_reset (a);
    for (i = 0; i < 10001; i++)
        asta (a, i);
    asta_info (a, stdout, "0..10.000", 20, 12);
    return 0;
}
#endif
