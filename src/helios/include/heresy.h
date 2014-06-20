/***********************************************************************

                       H  E  R  E  S  Y  .  H

***********************************************************************

A header file, defining a number of macros that, according to the
canonical scriptures (and common practices) of C-orthodoxy are
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

/* This is probably too cute for real men - but still horribly useful */
#include <getopt.h>
#define  decode(optstr, optchar, argc, argv) \
    while ((optchar = getopt (argc, argv, optstr))!=-1) switch (optchar)

#define loop      for (;;)
#define until(x)  while (!(x))
#define unless(x) if (!(x))
