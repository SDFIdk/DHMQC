Helios - HEader LIbraries On Steroids
=====================================

A collection of compact header libraries and simple demo programs in (mostly) plain C89.

- Asta   *A*ccumulation of *STA*tistics
- stack  stack template library
- sLASh  LAS LiDAR data reader library
- comquat *com*plex numbers, triplets, *quat*ernions, etc. ad 10

Not yet any polished documentation, but see the source code in include/ for 
comments and demo test code.

Asta
--------------

*A*ccumulation of *STA*tistics

    ASTA *a;
    size_t i, n=1e7;
    long double dt;   
    dt = 2*M_PI/(n-1);

    a = asta_alloc ();
    for (i = 0; i < n; i++)
        asta (a, (i*dt)-M_PIl);
    asta_info (a, stdout, "linesum", 20, 12);
    asta_free (a);



stack
-----

    stack(double) *dst;
    int i;


    dst = stack_alloc (dst, 15);
    push (dst, 444);
    printf ("top = %f\n", top(dst));

    /* push will block if errlev!=0 */
    dst->errlev = 444;
    push (dst, 555);
    printf ("top = %f\n", top(dst));
    dst->errlev = 0;
    push (dst, 555);
    printf ("top = %f\n", top(dst));




sLASh
-----

    /* -- Main API ---------------------------------------------------- */
    LAS          *las_open (const char *filename, const char *mode) ;
    void          las_close (LAS *h) ;
    inline int    las_seek (LAS *h, size_t pos, int whence) ;
    inline size_t las_read (LAS *h) ;



comquat
-------
**Com**plex numbers and **Quat**ernions

    #define	 EPS2  1e-14
    quat a = {0,1,2,3}, b = {2,1,3,4};

    /* check some quaternion identities */
    
    /* b == log (exp (b)) */
    assert (qdist (b, qexp(qlog(b))) < EPS2);

    /* b == Ub * |b| */
    assert (qdist (b, qscale (qunit (b), qlen(b))) < EPS2);
    
    /* |q| = sqrt (qq*) */
    assert (fabs (qlen(b) - sqrt (qmul(b, qconj(b)).r)) < EPS2);

    /* |qp| == |q||p| */
    assert (fabs ( qlen (qmul (a,b)) - qlen (a)*qlen (b) ) < EPS2 );

    /* q^-1 == q* / |q|^2 */
    assert (qdist (qinv(b), qscale(qconj(b), pow(qlen(b),-2)) ) < EPS2);


Licence
-------


Copyright (c) 1991--2014, Thomas Knudsen  <knudsen.thomas@gmail.com>  
Copyright (c) 2013--2014, Danish Geodata Agency <gst@gst.dk>

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
