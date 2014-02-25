/* comquat.c - COMplex numbers and QUATernions  */
/* gcc -W -pedantic -Wall -DTESTcomquat -o comquat comquat.c */

/* ------------------------------------------------------------------------
 
This file is part of the Helios bundle.

Thomas Knudsen  2013-06-28
    2014-02-11  comp renamed komp, c prefix changed to k (for C99 compatibility)
                Name intentionally /not/ changed to komquat.

****************************************************************
Copyright (c) 2013-2014 Thomas Knudsen

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


#ifndef __COMQUAT_H
#define __COMQUAT_H

#include <stdio.h>
#include <math.h>
#include <assert.h>


typedef struct {double w, r, g, b, x, y, z, i, j, k;}  deca;  /* whatever */
typedef struct {double    w, r, g, x, y, z, i, j, k;}  nona;  /* whatever */
typedef struct {double       w, r, x, y, z, i, j, k;}  octa;  /* whatever */
typedef struct {double          w, x, y, z, i, j, k;}  sept;  /* whatever */
typedef struct {double             x, y, z, i, j, k;}  hexa;  /* whatever */
typedef struct {double                x, y, i, j, k;}  pent;  /* whatever */
typedef struct {double                   r, i, j, k;}  quat;  /* quaternion */
typedef struct {double                      x, y, z;}  trip;  /* triplet */
typedef struct {double                         x, y;}  komp;  /* complex */


#ifdef __STACK_H
stackable(komp);
stackable(trip);
stackable(quat);
stackable(pent);
stackable(hexa);
stackable(sept);
stackable(octa);
stackable(nona);
stackable(deca);
#endif


#ifdef __GNUC__
#ifndef INLINE
#define INLINE
#endif
#endif
#ifndef inline
#ifdef INLINE
#define inline inline
#else
#define inline
#endif
#endif

komp kompify (double x, double y) {komp xy; xy.x=x; xy.y=y; return xy;}
trip tripify (double x, double y, double z) {trip xyz; xyz.x = x; xyz.y=y; xyz.z=z; return xyz;}
quat quatify (double r, double i, double j, double k) {quat rijk; rijk.r=r; rijk.i = i; rijk.j=j; rijk.k=k; return rijk;}
pent pentify (double x, double y, double i, double j, double k) {pent p; p.x=x; p.y=y; p.i = i; p.j=j; p.k=k; return p;}

hexa hexaify (double x, double y, double z, double i, double j, double k) {
    hexa p;
    p.x = x;    p.y = y;    p.z = z;
    p.i = i;    p.j = j;    p.k = k;
    return p;
}
sept septify (double w, double x, double y, double z, double i, double j, double k) {
    sept p;
    p.w = w;
    p.x = x;    p.y = y;    p.z = z;
    p.i = i;    p.j = j;    p.k = k;
    return p;
}
octa octaify (double w, double r, double x, double y, double z, double i, double j, double k) {
    octa p;
    p.w = w;    p.r = r;
    p.x = x;    p.y = y;    p.z = z;
    p.i = i;    p.j = j;    p.k = k;
    return p;
}
nona nonaify (double w, double r, double g, double x, double y, double z, double i, double j, double k) {
    nona p;
    p.w = w;    p.r = r;    p.g = g;
    p.x = x;    p.y = y;    p.z = z;
    p.i = i;    p.j = j;    p.k = k;
    return p;
}
deca decaify (double w, double r, double g, double b, double x, double y, double z, double i, double j, double k) {
    deca p;
    p.w = w;    p.r = r;    p.g = g;   p.b = b;
    p.x = x;    p.y = y;    p.z = z;
    p.i = i;    p.j = j;    p.k = k;
    return p;
}



/* quaternion algebra - following http://en.wikipedia.org/wiki/Quaternion */
/* substituting (r,i,j,k) for (a,b,c,d) */


/* conjugation */
inline quat qconj (quat q) {
	q.i = -q.i;
	q.j = -q.j;
	q.k = -q.k;
	return q;
}


/* addition */
inline quat qadd (quat q, quat p) {
	q.r += p.r;
	q.i += p.i;
	q.j += p.j;
	q.k += p.k;
	return q;
}


/* subtraction */
inline quat qsub (quat q, quat p) {
	q.r -= p.r;
	q.i -= p.i;
	q.j -= p.j;
	q.k -= p.k;
	return q;
}


/* negation */
inline quat qneg (quat q) {
	q.r = -q.r;
	q.i = -q.i;
	q.j = -q.j;
	q.k = -q.k;
	return q;
}


/* multiplication */
inline quat qmul (quat q, quat p) {
    quat r;
    r.r = q.r*p.r - q.i*p.i - q.j*p.j - q.k*p.k;
    r.i = q.r*p.i + q.i*p.r + q.j*p.k - q.k*p.j;
    r.j = q.r*p.j - q.i*p.k + q.j*p.r + q.k*p.i;
    r.k = q.r*p.k + q.i*p.j - q.j*p.i + q.k*p.r;
	return r;
}


/* multiplication by a scalar */
inline quat qscale (quat q, double s) {
	q.r *= s;
	q.i *= s;
	q.j *= s;
	q.k *= s;
	return q;
}

/* addition by a scalar */
inline quat qoffset (quat q, double s) {
	q.r += s;
	q.i += s;
	q.j += s;
	q.k += s;
	return q;
}


/* reciprocal (inverse) */
inline quat qinv (quat q){
	double L = q.r*q.r + q.i*q.i + q.j*q.j + q.k*q.k;
	q.r =  q.r / L;
	q.i = -q.i / L;
	q.j = -q.j / L;
	q.k = -q.k / L;
	return q;
}

/* division: q/p */
inline quat qdiv (quat q, quat p) {
    return qmul(q, qinv (p));    
}



/* norm (length) */
inline double qlen (quat q){
	return sqrt (q.r*q.r + q.i*q.i + q.j*q.j + q.k*q.k);
}

/* "rms" difference */
inline double qdist (quat q, quat p) {
    return qlen (qsub(q, p));
}

inline quat qunit (quat q) {
    double L = qlen (q);
    q.r /= L;
    q.i /= L;
    q.j /= L;
    q.k /= L;
    return q;
}

inline quat qexp (quat q) {
    double aexp, vnorm;
    
    aexp  =  exp(q.r);
    vnorm =  sqrt (q.i*q.i + q.j*q.j + q.k*q.k);
    
    /* assume optimizer takes care of invariant sin() and constant folding */
    q.r = aexp * cos (vnorm);
    q.i = aexp * q.i / vnorm * sin(vnorm);
    q.j = aexp * q.j / vnorm * sin(vnorm);
    q.k = aexp * q.k / vnorm * sin(vnorm);
    
    return q;
}

inline quat qlog (quat q) {
    double qnorm, vnorm, scale;
    
    qnorm = qlen (q);
    vnorm = sqrt (q.i*q.i + q.j*q.j + q.k*q.k);

    scale = acos (q.r/qnorm) / vnorm;

    q.r  =   log (qnorm);
    q.i  *=  scale;
    q.j  *=  scale;
    q.k  *=  scale;
            
    return q;
}




komp kconj (komp p) {
    p.y = -p.y;
    return p;    
}

komp kneg (komp p) {
    p.x = -p.x;
    p.y = -p.y;
    return p;
}

komp kscale (komp p, double s) {
    p.x *= s;
    p.y *= s;
    return p;    
}

komp koffset (komp p, double s) {
    p.x += s;
    p.y += s;
    return p;    
}

komp kadd (komp p, komp q) {
    p.x += q.x;
    p.y += q.y;
    return p;    
}

komp ksub (komp p, komp q) {
    p.x -= q.x;
    p.y -= q.y;
    return p;    
}

komp kmul (komp p, komp q) {
    komp r;
    r.x = p.x*q.x - p.y*q.y;
    r.y = p.y*q.x + p.x*q.y;
    return r;
}

komp kdiv (komp p, komp q) {
    komp r;
    double l = hypot (q.x, q.y);
    r.x = (p.x*q.x + p.y*q.y) / l;
    r.y = (p.y*q.x - p.x*q.y) / l;
    return r;
}

inline double klen (komp p) {
    return hypot (p.x, p.y); 
}
inline double kang (komp p) {
    return atan2 (p.y, p.x); 
}

inline komp kroot (komp p) {
    komp r;
    if (p.y==0)
        return p.x = sqrt (p.x), p;
    
    r.x = sqrt (( p.x + klen (p)) / 2);
    r.y = sqrt ((-p.x + klen (p)) / 2);
    if (p.y < 0)
        r.y = -r.y;
    return r;
}


#endif  /* __COMQUAT_H */


#ifdef TESTcomquat
#define	EPS0	1.387778780781445675529539585113525e-17	/* 2^-56 */
#define	EPS1	2e-17
#define	EPS2	1e-14
	

int main (void) {
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

    /* some more generic tests */
    assert (sizeof(deca)==10*sizeof(double));
#define val(comquat, index) index[(double *) &comquat]
    val(a,3) = 42;
    assert (42==val(a,3));
    assert (42==a.k);
    
    
    return 0;


}
#endif  /* TESTcomquat */

/*
 * 
 * 

Trekantsinterpolation

http://www.gamedev.net/topic/380061-solve-triangle-interpolation-linear-equations/

how about something like this

A*x0 + B*y0 + C = z0
A*x1 + B*y1 + C = z1
A*x2 + B*y2 + C = z2

i substract 2 and 3 row from 1

A*(x0-x1) + B*(y0-y1) = z0-z1
A*(x0-x2) + B*(y0-y2) = z0-z2

now let
 
P=x0-x1 Q=y0-y1
R=x0-x2 S=y0-y2
T=z0-z1 U=z0-z2

A*P+B*Q=T
A*R+B*S=U

det=P*S-R*Q

idet=1/det
A=(T*S-U*Q)*idet
B=(P*U-R*T)*idet
C=z0-A*x0-B*x0

14 muls 1 div.. shoud be quite fast

Cubic Interpolation
Instead of weighting by distance, d, weight by:

1 – 3d**2 + 2|d|**3

Smooth, Symmetric




 * 
 * 
 * 
 * 
 * 
 */




/* Plan 9  over at
 * http://swtch.com/usr/local/plan9/src/libgeometry/quaternion.c
 * 
 * has a similar:
 * 
 * Quaternion arithmetic:
 *	qadd(q, r)	returns q+r
 *	qsub(q, r)	returns q-r
 *	qneg(q)		returns -q
 *	qmul(q, r)	returns q*r
 *	qdiv(q, r)	returns q/r, can divide check.
 *	qinv(q)		returns 1/q, can divide check.
 *	double qlen(p)	returns modulus of p
 *	qunit(q)	returns a unit quaternion parallel to q
 * The following only work on unit quaternions and rotation matrices:
 *	slerp(q, r, a)	returns q*(r*q^-1)^a
 *	qmid(q, r)	slerp(q, r, .5) 
 *	qsqrt(q)	qmid(q, (Quaternion){1,0,0,0})
 *	qtom(m, q)	converts a unit quaternion q into a rotation matrix m
 *	mtoq(m)		returns a quaternion equivalent to a rotation matrix m
 */
