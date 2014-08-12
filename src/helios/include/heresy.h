/***********************************************************************

                       H  E  R  E  S  Y  .  H

***********************************************************************

heresy.h is a header file, defining a number of macros that, according
to the canonical scriptures (and common practices) of C-orthodoxy are
considered horribly heretic.
 
K&R [1], the revelation of C, demonstrated a beautiful coding style,
equally useful for pedagogical purposes and practical programming.

This style has since then represented the "C way of doing things".
Meaning e.g. using the preprocessor sparsely, mostly for including
headers and defining constants.
 
In the early days of C, however, it was common to use the preprocessor
as a "language extender and chameleonizer". Most notably, Stephen
Bourne, when writing the Unix Bourne Shell, augmented C with a number
of esoteric macros, making the language resemble ALGOL68 (actually,
according to Landon Curt Noll [2], the Bourne Shell code provided the
inspiration for IOCCC, the International Obfuscated C Code Contest).

While you can certainly use the preprocessor for obfuscation, and while
doing this is certainly a highly enjoyable game, the preprocessor may
also have more merit than C orthodoxy allows it. Had we had a culture
of experimenting with language additions and corrections through playful
(mis)use of the preprocessor, I'm sure the committees behind the
C standards following the original C89, would have had a much larger
gamut of well tested suggestions for improvement.

With this in mind (and 25 years too late), I hereby present 'heresy.h',
a little collection of heretic C amendments


[1] Brian W. Kernighan and Dennis M. Ritchie:
    The C Programming Language
    Englewood Cliffs, New Jersey, Prentice Hall, Inc.
    228 pp, 1978

[2] The International Obfuscated C Code Contest:
    The IOCCC FAQ,
    http://www.ioccc.org/faq.html

***********************************************************************

Copyright (c) 1998-2014, Thomas Knudsen <knudsen.thomas@gmail.com>

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

***********************************************************************/



/***********************************************************************
 repair  -  make Windows less painful
************************************************************************

While POSIX certainly comes with its specific pains, they are in
general dwarfed by the pains inflicted by the Windows platforms.

This section tries to repair some of the maldecisions taken by
the geniuses in Redmond.

While not exactly fitting under the "heresy" headline, this material
fits here in the sense that it fills in gaps and repair stupidities.

***********************************************************************/
#ifdef _WIN32

/* TODO: write long warning about how this may affect your general health and abilities.
 * (short form: be sure to define this before ANY system headers are included, i.e. preferably on the compiler command line) */
#ifndef _FILE_OFFSET_BITS
#define _FILE_OFFSET_BITS 64
#endif
#define I64FMT "%I64d"
#ifdef __MINGW32__
#  define fseeko fseeko64
#  define ftello ftello64
#else
/* In Redmond they do their utmost in order to stay incompatible with everyone else */
#  define fseeko _fseeki64
#  define ftello _ftelli64
#define _USE_MATH_DEFINES
#define isnan(x) _isnan(x)
#define isinf(x) (!_finite(x))
#endif

#else /* not _WIN32*/
#define I64FMT "%lld"
#endif


/***********************************************************************
 stdinc  -  include all commonly used headers
************************************************************************

Tha Plan 9 OS (http://plan9.bell-labs.com/plan9/), insists that
"headers follow libraries", i.e. one header for each library.

libc - the C standard library - with its Unix heritage does not
follow this practise (although a "libc.h" header is actually found
on some systems).

Heresy does a partial repair of this by including a number of the
most commonly used header files for libc (and libm) below

***********************************************************************/

#include <stdio.h>     /* e.g. FILE, fopen(), printf()            */
#include <stdlib.h>    /* e.g. malloc()/calloc()/realloc()/free() */
#include <stddef.h>    /* e.g. offsetof macro                     */
#include <stdarg.h>    /* e.g. va_list, va_start                  */
#include <string.h>    /* e.g. memcpy()                           */
#include <math.h>      /* e.g. log10(), sinh(), HUGE_VAL          */
#include <float.h>     /* e.g. DBL_MAX, FLT_MIN                   */
#include <limits.h>    /* e.g. INT_MAX, LONG_MIN                  */
#include <ctype.h>     /* e.g. isspace()                          */
#include <time.h>      /* e.g. struct tm                          */
#include <errno.h>
#include <assert.h>

/* TODO: ifdef helios include remaining helios headers.
 * Requires conditional compilation of their built-in Windows repair */


/***********************************************************************
 decode  -  a worse/better getopt than getopt?
************************************************************************

This is probably too cute for real men - but has been very useful
to me since 1999

usage:

#include <heresy.h>
int main(int argc, char **argv) {
    int optchar    = 0;
    int verbostity = 0;
    char help[] = {"Help goes here..."};
    FILE *out = 0;

    decode ("o:vh", optchar, argc, argv) {
    case 'o':                // output file
        out  = fopen(optarg, "w");
        if (0!=out)
            break;
        fprintf (stderr, "Cannot open output file %s\n", optarg);
        return EXIT_FAILURE;
    case 'h':                // help
        puts (help);
        return EXIT_SUCCESS;
    case 'v':                // verbosity
        verbosity++;
        break;
    default:
        fprintf (stderr, "Unknown option - %c\n", optchar);
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}

***********************************************************************/
#include <getopt.h>
#define  decode(optstr, optchar, argc, argv) \
    while ((optchar = getopt (argc, argv, optstr))!=-1) switch (optchar)



/***********************************************************************
 loop  -  infinite loop, exit with "break"
************************************************************************

This one is inspired by the loop/exit/endloop construction of
RC Comal, running e.g. on the RC700 series microcomputers (approx 1983)

loop {
    do_interesting_stuff ();
    if (done)
        break;
    do_rest ();
}

***********************************************************************/
#define loop      for (;;)


/***********************************************************************
 unless, until  -  inverted conditionals
************************************************************************

Sometimes a condition is mentally easier to grasp if stated inversely.
In natural language, we stress the common case by saying either

"do this unless that" (when 'that' is unlikely) or
"if (that) then do this" (if that is most likely).

until/unless implements this kind of "inverted conditionals".
They are inspired by the Perl commands with the same names.

***********************************************************************/
#define until(x)  while (!(x))
#define unless(x) if (!(x))


/***********************************************************************
 nelem  -  number of elements in an array
************************************************************************

This one is well known, but slightly dangerous due to the close
syntactical relation between pointers and arrays in C:

int n;
double *p;
double a[100];
p = calloc (100, sizeof(double));

n = nelem (a);  // n==100
n = nelem (p);  // Oops!

***********************************************************************/
#define	nelem(x)	(sizeof(x) / sizeof((x)[0]))


/***********************************************************************
 tic/toc  -  timing
************************************************************************

These are inspired by Matlab. Formally, the clock() call used measures
CPU time, not wall clock time. Do not, however, expect very high
accuracy.

double timer t;
t = tic();
do_interesting_stuff();
t = toc(t);
printf ("Doing interesting stuff took %f seconds\n", t);
t = tic();
do_more_interesting_stuff();
TOC("Doing more interesting stuff took: ", t);

***********************************************************************/
#define	tic(t)	 (((double)clock()) / CLOCKS_PER_SEC)
#define toc(t)	 (tic() - t)
#define TOC(s,t) printf (s "%.2f s\n", toc(t))

