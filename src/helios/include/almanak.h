/*********************************************************************
almanak.h - quick-and-dirty approximation of solar elevation
    gcc -W -pedantic -Wall -Wextra -DTESTalmanak -x c -o almanak almanak.h

This file is part of the Helios bundle.

Warning: quick hack. Crude approximations, not well tested,
not for critical applications

*********************************************************************
Copyright (c) 1994-2014, Thomas Knudsen <knudsen.thomas@gmail.com>
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
********************************************************************/
#ifndef __ALMANAK_H
#define __ALMANAK_H
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

#define _USE_MATH_DEFINES  /* for partial repair of Redmond insanity */
#include <math.h>

#include <errno.h>


/* Handy epoch constants computed using http://www.andrews.edu/~tzs/timeconv/timeconvert.php? */
#define EPOCH_2013             1041033616  /* 2013-01-06T00:00:00 UTC */
#define EPOCH_2014             1072569616  /* 2014-01-06T00:00:00 UTC */
#define EPOCH_2016             1135641616  /* 2016-01-06T00:00:00 UTC */
#define EPOCH_GPS                       0  /* 1980-01-06T00:00:00 UTC */
#define EPOCH_OLD_MODIFIED_GPS  900000000  /* 2008-07-13T15:59:46 UTC */
#define EPOCH_MODIFIED_GPS     1000000000  /* 2011-09-14T01:46:25 UTC */
#define EPOCH_UNIX             -315964800  /* 1970-01-01T00:00:00 UTC */

/* Not used. from http://www.pveducation.org/pvcdrom/properties-of-sunlight/suns-position */
double equation_of_time (double day_of_year) {
    double B = 360*(day_of_year - 81)/365 * M_PI / 180;
    return 9.87 * sin (2*B)  -  7.53 * cos (B) - 1.5 * sin (B);
}

/* very hacky, but from tests in solar_elevation we know we are in 2014-15 */
int day_of_year (double utc, double epoch) {
    /* day of year base 0, i.e. first day of year is day 0 */
    long long t = utc + (epoch - EPOCH_2014);
    return (t / 86400) % 365;
}

double time_of_day (double utc, double epoch) {
    return fmod (utc + (epoch - EPOCH_2014), 86400);
}

double fractional_day_of_year (double utc, double epoch) {
    return day_of_year (utc, epoch) + time_of_day (utc, epoch) / 86400;
}


double solar_declination (double utc, double epoch) {
    double df = fractional_day_of_year (utc, epoch)-81;
    return 23.45*M_PI / 180 * sin (360.0/365*M_PI / 180 * df);
}

double solar_elevation_1 (double latitude, double longitude, double utc, double epoch) {
    double elev = HUGE_VAL, h;
    double delta = solar_declination (utc, epoch);
    if ((utc + epoch < EPOCH_2013)||(utc + epoch > EPOCH_2016))
        return errno = EDOM, HUGE_VAL;
    if ((latitude < -90) || (latitude > 90))
        return errno = EDOM, HUGE_VAL;
    if ((longitude < -180) || (longitude > 180))
        return errno = EDOM, HUGE_VAL;

    /* local hour angle in seconds */
    h = (time_of_day (utc, epoch) + longitude / 15 * 3600 - 43200);
    /* convert to radians */
    h = h / 3600 * 15 * M_PI / 180;

    /* prepare for the trigonometry - convert to radians */
    latitude  *=  (M_PI/180);
    longitude *=  (M_PI/180);

    /* Approx. solar elevation: The angle between the horizon and the centre of the sun's disc */
    elev = asin ( cos (h) * cos (delta) * cos (latitude) + sin (delta) * sin (latitude));

    return elev * 180 / M_PI;
}


/* http://www.esrl.noaa.gov/gmd/grad/solcalc/solareqns.PDF - with trig substitutions by thokn */
double solar_elevation (double latitude, double longitude, double utc, double epoch) {
    double dt    = time_of_day (utc, epoch);
    double gamma = 2*M_PI * (day_of_year (utc, epoch) + (dt-43200)/86400.0) / 365.0;
    double C     = cos (gamma);
    double S     = sin (gamma);
    double declination = 0.006918 - 0.399912*C + 0.070257*S - 0.006758*(C*C-S*S) + 0.000907*(2*C*S) - 0.002697*C*(C*C-3*S*S) + 0.00148*S*(3 - 4*S*S);
    double eqtime = 229.18 * (0.000075 + 0.001868*C - 0.032077*S - 0.014615*(C*C-S*S) - 0.040849*2*C*S);
    double tOffset = eqtime + 4*longitude; /*+ 60*timeZone */
    double tst = dt/60 + tOffset;
    double hour_angle = (tst/4)-180;
    double zenit = 180/M_PI*acos ( sin(latitude*M_PI/180) * sin(declination) + cos (latitude*M_PI/180) * cos(declination) * cos(hour_angle*M_PI/180) );
    return 90-zenit;
}

/* And the solar azimuth (az, clockwise from north) is:
cos(180-az) = (sin(declination) - sin (lat) cos (zenit_angle)) / (cos (lat) sin(zenit_angle)) */


/***********************************************************************
                         U N I T   T E S T S
***********************************************************************/
#ifdef TESTalmanak
#include <assert.h>

/* Test points using info obtained from http://www.torbenhermansen.dk/almanak/almanak.php */

/* The Sun rises in CPH 2014-06-20T02:39 UTC */
#define SUNRISE_CPH_2014_06_20   1087267156
/* The Sun sets in CPH 2014-06-20T19:55 UTC */
#define SUNSET_CPH_2014_06_20    1087329316
/* The Sun reaches an elevation of 58 deg in CPH 2014-06-20T11:17 UTC */
#define SUN_MAX_ELEVATION_CPH_2014_06_20  1087298236  /* unix time 1403263020 */


/* The Sun rises in CPH 2014-03-21T05:17 UTC */
#define SUNRISE_CPH_2014_03_21   1079414236
/* The Sun reaches an elevation of 35 deg in CPH 2014-03-21T11:23 UTC */
#define SUN_MAX_ELEVATION_CPH_2014_03_21  1079436196

int main (void) {
    printf ("*** %d\n", day_of_year (SUNRISE_CPH_2014_06_20, EPOCH_GPS));
    printf ("*** %g\n", time_of_day (SUNRISE_CPH_2014_06_20, EPOCH_GPS));
    printf ("***1-- %g\n", solar_elevation_1 (55.66, 12.55, SUNRISE_CPH_2014_06_20, EPOCH_GPS));
    printf ("***2-- %g\n", solar_elevation (55.66, 12.55, SUNRISE_CPH_2014_06_20, EPOCH_GPS));
    printf ("***1-- %g\n", solar_elevation_1 (55.66, 12.55, SUN_MAX_ELEVATION_CPH_2014_06_20, EPOCH_GPS) - 58);
    printf ("***2-- %g\n", solar_elevation (55.66, 12.55, SUN_MAX_ELEVATION_CPH_2014_06_20, EPOCH_GPS) - 58);
    printf ("***1-- %g\n", solar_elevation_1 (55.66, 12.55, SUNRISE_CPH_2014_03_21, EPOCH_GPS));
    printf ("***2-- %g\n", solar_elevation (55.66, 12.55, SUNRISE_CPH_2014_03_21, EPOCH_GPS));
    printf ("***1-- %g\n", solar_elevation_1 (55.66, 12.55, SUN_MAX_ELEVATION_CPH_2014_03_21, EPOCH_GPS) - 35);
    printf ("***2-- %g\n", solar_elevation (55.66, 12.55, SUN_MAX_ELEVATION_CPH_2014_03_21, EPOCH_GPS) - 35);
    assert (EPOCH_2016-EPOCH_2014 == 2*365*86400);
    assert (time_of_day (SUNRISE_CPH_2014_06_20, EPOCH_GPS) == 60*(39 + 60*2));
    assert (time_of_day (EPOCH_2014, EPOCH_GPS) == 0);
    assert (day_of_year (SUNRISE_CPH_2014_06_20, EPOCH_GPS) == 30*5+1+19);
    assert (day_of_year (EPOCH_2014, EPOCH_GPS) == 0);
    return 0;
}
#endif
#endif
