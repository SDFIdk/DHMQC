/*********************************************************************
esrigrid.h - handle ESRI ascii grid files
    gcc -W -pedantic -Wall -Wextra -DTESTesrigrid -x c -o esrigrid esrigrid.h

This file is part of the Helios bundle.
 
esrigrid.h started its life under the GNU General Public Licence.
The bilin functions as part of the Busstop system (1996-2010),
the remaining parts as part of the BooGIE system (2007-2014).

Needing this for work in a BSD licensed ecosystem, I changed the licence
and moved the material to the Helios bundle on 2014-02-25.

This file is now distributed under the ISC/OpenBSD licence (see below). 

                             Thomas Knudsen, Sundbyøster, 2014-02-25

demo/tests start around line 500
*********************************************************************
Copyright (c) 1996-2014, Thomas Knudsen <knudsen.thomas@gmail.com>

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

/* TODO: unnecessarily complex. Reduction of LOC by a factor of
 * 2-3 probably possible. But it works, so... why bother?
 */

#include <stdio.h>     /*  for printf and friends  */
#include <stdlib.h>    /*  for malloc/free         */
#include <ctype.h>     /*  for isspace()           */
#include <math.h>      /*  for HUGE_VAL            */

typedef struct  ESRIGRID     ESRIGRID;

enum ESRIGRID_TYPE { image = 0, grid = 1 };

struct ESRIGRID {
    enum ESRIGRID_TYPE type;
    long        ncols, nrows;
    double      xllcenter, yllcenter, cellsize, nodata_value;
    double *data;
    size_t data_size;
    int     status;
};





/* skip whitespace and comments - one would believe this could be done in a simpler way ... */
/*****************************************************************************/
void skipws(FILE *f) {
/*****************************************************************************/
    int c = 0, s = 0;

    while (EOF != (c=getc(f))) {
        switch (s) {
        case 0:    if (isspace(c)) { s = ' '; continue; }
                   if ('#'==c)     { s = '#'; continue; }
                   ungetc(c, f);              return;

        case '#':  if (c!='\n')    continue;
                   s = ' ';        continue;

        case ' ':  if (isspace(c))       continue;
                   if ('#'==c) {s = '#'; continue;}
                   ungetc(c, f);         return;

        }
    }
}



/*****************************************************************************/
int skipws_but_detect_delimiter(FILE *f, int delimiter) {
/*****************************************************************************/
    int c = 0, s = 0;

    while (EOF != (c=getc(f))) {
        if (c==delimiter)
            return 1;
        switch (s) {
        case '#':  continue;

        case 0:    if (isspace(c)) { s = ' '; continue; }
                   if ('#'==c)     { s = '#'; continue; }
                   ungetc(c, f);              return 0;

        case ' ':  if (isspace(c))       continue;
                   if ('#'==c) {s = '#'; continue;}
                   ungetc(c, f);         return 0;

        }
    }
    return 2;
}




/*****************************************************************************/
int skip_to_delimiter(FILE *f, int delimiter) {
/*****************************************************************************/
    int c = 0;

    while (EOF != (c=getc(f))) {
        if (c==delimiter)
            return 1;
    }
    return 2;
}




/* get next token, converted to a double, from stream f */
/*****************************************************************************/
double get_next_value(FILE *f) {
/*****************************************************************************/
    double v;

    skipws(f);
    if (feof(f))
        return HUGE_VAL;

    /* if the next characters cannot be interpreted as a double, format is wrong */
    if (1!= fscanf(f, "%lg", &v))
        return HUGE_VAL;

    return v;
}




/* get next token, converted to a double, from stream f
set flag to 0 if ok,
            1 delimiter detected (end-of-record)
            2 for end-of-file
            3 for wrong format.                           */
/*****************************************************************************/
double get_next_value_but_detect_delimiter(FILE *f, int delimiter, int *flag) {
/*****************************************************************************/
    double v;
    int i;

    i = skipws_but_detect_delimiter(f, delimiter);

    *flag = i;
    if (i)
        return HUGE_VAL;

    /* if the next characters cannot be interpreted as a double, format is wrong */
    *flag = 3;
    if (1!= fscanf(f, "%lg", &v))
        return HUGE_VAL;

    *flag = 0;
    return v;
}









/*****************************************************************************/
ESRIGRID *parse_grid_opt(char *arg) {
/*****************************************************************************/
    int n;
    ESRIGRID *e = calloc(1, sizeof(ESRIGRID));
    if (0==e)
        return 0;

    n = sscanf(arg, "G/%lf/%lf/%ld/%ld/%lf/%lf", &e->yllcenter, &e->xllcenter,&e->nrows,&e->ncols,&e->cellsize,&e->nodata_value);
    e->type = grid;  /* TODO: implement support for "image" type here! */

    if (6!=n) {
        free(e);
        return 0;
    }
    return e;
}

#ifdef ESRIGRID_TABBING
#define ESRIGRID_HELPTEXT \
    ESRIGRID_TABBING \
    "[G|I]/LOWER_LEFT_CORNER_Y/LOWER_LEFT_CORNER_X/ROWS/COLUMNS/CELLSIZE/NODATA_VALUE\n" \
    ESRIGRID_TABBING \
    "\n" \
    "A leading G indicates grid  style georeference (reference point is center of cell).\n" \
    ESRIGRID_TABBING \
    "A leading I indicates image style georeference (reference point is lower left corner of cell).\n" \
    ESRIGRID_TABBING \
    "Currently only G is supported.\n" \
    "\n" \
    ESRIGRID_TABBING \
    "Example:  The grid descriptor G/6600000.5/550000.5/1000/2000/1/-9999 describes\n" \
    ESRIGRID_TABBING \
    "- A grid which is georeferenced using the center of the lower left cell\n" \
    ESRIGRID_TABBING \
    "  as reference point.\n" \
    ESRIGRID_TABBING \
    "- The northing of the reference point is 6600000.5 m.\n" \
    ESRIGRID_TABBING \
    "- The easting of the reference point is 550000.5 m.\n" \
    ESRIGRID_TABBING \
    "- The cell size (i.e. the grid increment) is 1 m.\n" \
    ESRIGRID_TABBING \
    "- The grid size is 1000 rows by 2000 columns.\n" \
    ESRIGRID_TABBING \
    "  Hence, the (northing, easting) coordinates of the \n" \
    ESRIGRID_TABBING \
    "  upper rightmost grid point is (6600999.5 m, 551999.5 m).\n" \
    ESRIGRID_TABBING \
    "- Cells with undefined values are assigned the value -9999.\n" 
#endif

ESRIGRID *esri_grid_free(ESRIGRID *g) {
    free (g);
    return 0;
}


#if 0
int isesri(FILE *f) {
	int magic;
    magic = fgetc(f);
    ungetc(magic, f);
    if ((int) 'n' != magic)
        return 0;
    return 1;
}
#endif

int isesri(char *filename, FILE *p) {
	int firstchar = 0;
	if (p) {
		firstchar = fgetc (p);
		ungetc (firstchar, p);
    }
    else {
        FILE *f;
        f = fopen (filename, "rt");
        if (0==f)
            return 0;
		firstchar = fgetc (f);
        fclose (f);
    }
    if (((int)'n')==firstchar)
        return 1;
    return 0;
}


/****************************************************************************
    R E A D _ E S R I _ A S C I I _ G R I D _ H E A D E R
    Thomas Knudsen, Sundbyøster, 2007-06-08
        2011-11-10: added check for "magic char" = 'n'
****************************************************************************/
ESRIGRID *read_esri_ascii_grid_header(FILE *f) {
    int n = 0, corner = 0, magic;
    double buf;
    fpos_t pos;
    ESRIGRID *e;

    skipws(f); /* skipping whitespace & comment lines - this is controversial! */

    magic = fgetc(f);
    ungetc(magic, f);
    if ((int) 'n' != magic)
        return 0;

    if (0==(e = malloc(sizeof(ESRIGRID))))
        return 0;

    e->type      = grid;
    e->status    = 0;
    e->data      = 0;
    e->data_size = 0;


    n += fscanf(f, "ncols %lf%*[^\n]", &buf); e->ncols = buf;
    /* printf("%d - %ld\n", n, e->ncols); */
    n += fscanf(f, "\nnrows %lf%*[^\n]", &buf); e->nrows = buf;
    /* printf("%d - %ld\n", n, e->nrows); */
    fgetpos(f, &pos);
    n += fscanf(f, "\nxllcenter %lf%*[^\n]", &e->xllcenter);
    /* printf("%d - %lf\n", n, e->xllcenter); */

    switch(n) {
	case 2:
	    /* image style grid registration? - try re-reading */
        fsetpos (f, &pos);
        n += fscanf (f, "\nxllcorner %lf%*[^\n]", &e->xllcenter);
        /* printf("%d - %lf\n", n, e->xllcenter); */
        corner = 1;
        if (n==3) e->type = image;
    case 3:
        n += fscanf (f, corner? "\nyllcorner %lf%*[^\n]":  "\nyllcenter %lf%*[^\n]", &e->yllcenter);
        /* printf("%d - %lf\n", n, e->yllcenter); */
        n += fscanf(f, "\ncellsize %lf%*[^\n]", &e->cellsize);
        /* printf("%d - %lf\n", n, e->cellsize); */
        n += fscanf(f, "\nNODATA_value %lf%*[^\n]", &e->nodata_value); /* TODO: nodata_value really is optional - take better care of this */
        /* printf("%d - %lf\n", n, e->nodata_value); */
        if (6!=n)
            break;
        if ('\n'!=fgetc(f))
            break;
        if (corner) {
            e->xllcenter += e->cellsize/2;
            e->yllcenter += e->cellsize/2;
        }
        return e;
 	}
    free(e);
    return 0;

#if 0
This is a sample ESRI ascii grid header:
ncols 751
nrows 690
xllcenter 720900.000
yllcenter 6173997.600
cellsize 1.6000
NODATA_value -9999
#endif
}




void write_esrigrid_header(FILE *f, struct ESRIGRID *e) {
    fprintf(f, "ncols %ld\n",        e->ncols);
    fprintf(f, "nrows %ld\n",        e->nrows);
    if (e->type==image) {
        fprintf(f, "xllcorner %f\n",    e->xllcenter - e->cellsize/2);
        fprintf(f, "yllcorner %f\n",    e->yllcenter - e->cellsize/2);
    }
    else {
        fprintf(f, "xllcenter %f\n",    e->xllcenter);
        fprintf(f, "yllcenter %f\n",    e->yllcenter);
    }
    fprintf(f, "cellsize %f\n",     e->cellsize);
    fprintf(f, "NODATA_value %f\n", e->nodata_value);
}




ESRIGRID *read_esri_ascii_grid(FILE *f) {
    ESRIGRID *e;
    int i, n;

    /* read header */
    e = read_esri_ascii_grid_header (f);
    if (0==e)
        return 0;

    /* get memory for grid data */
    n = e->ncols * e->nrows;
    e->data = malloc(n*sizeof(double));
    if (0==e->data) {
        free (e);
        return 0;
    }
    e->data_size = n;

    /* read grid data */
    for (i = 0;  i < n;  i++) {
        e->data[i] = get_next_value (f);
        if (HUGE_VAL==e->data[i]) {
            e->status = feof(f)? 2: 3;
            return e;
        }
    }
    return e;
}









/*****************************************************************************
NAME:              bilin
BRIEF:             bilinear interpolation in a 2d grid
DATE:              1997-05-05 (tk)
                   2011-11-14 (tk) added support for nodata
*****************************************************************************/
float oldbilin(double *g, int nx, int ny, double x, double y, double nodata){
#define IN(i,j) ( (j)*nx + (i) )
  double p, q,   a, b, c, d;
  int    i, j;

  /*y = (ny-1) - y;*/
  i = x;
  j = y;
  printf("[i,j] = [%2.2d,%2.2d]\n", i,j);
  if ( x <  0 ) return HUGE_VAL;
  if ( x >= nx) return HUGE_VAL;
  if ( y <  0 ) return HUGE_VAL;
  if ( y >= ny) return HUGE_VAL;

  a = g[IN(i   ,j  )];
  b = g[IN(i+1 ,j  )];
  c = g[IN(i   ,j+1)];
  d = g[IN(i+1 ,j+1)];

  for (i = 0;  i < 4;  i++) {
    if (a==nodata) a = b;
    if (b==nodata) b = c;
    if (c==nodata) c = d;
    if (d==nodata) d = a;
  }

  if (a==nodata)
      return nodata;

  p = (x - i);
  q = (y - j);


  return  (1-p) * (1-q) * a
        +    p  * (1-q) * b
        + (1-p) *    q  * c
        +    p  *    q  * d;
# undef IN
}









/*****************************************************************************
NAME:              bilin
BRIEF:             bilinear interpolation in a 2d grid
DATE:              1997-05-05 (tk)
                   2011-11-14 (tk) added support for nodata
*****************************************************************************/
float bilin(double *g, int nr, int nc, double r, double c, double nodata){
#define IN(row,col) ( (row)*nc + (col) )
  double dr, dc,   A, B, C, D,  AC, BD;
  int    i, j, n;

  /* could allow extrapolation by setting to 0, nr, etc. (think!) */
  if ( r <  0 ) return HUGE_VAL;
  if ( r >= nr) return HUGE_VAL;
  if ( c <  0 ) return HUGE_VAL;
  if ( c >= nc) return HUGE_VAL;


  /* i,j becomes upper left corner of cell */
  i = r;
  j = c;

  A = g[IN(i   ,j  )];        C = g[IN(i   ,j+1)];

  B = g[IN(i+1 ,j  )];        D = g[IN(i+1 ,j+1)];


  /* fill in nodata cyclically from anticlockwise neighbour */
  for (n = 0;  n < 4;  n++) {
    if (A==nodata) A = B;
    if (B==nodata) B = D;
    if (D==nodata) D = C;
    if (C==nodata) C = A;
  }


  if (A==nodata)
      return nodata;

  dr =  (r - (double)i);
  dc =  (c - (double)j);

  AC = dc * C + (1-dc) * A;
  BD = dc * D + (1-dc) * B;

  return dr * BD + (1-dr) * AC;
# undef IN
}



double interpolate_esri_ascii_grid(ESRIGRID *e, double northing, double easting) {

    /* scale northing and easting to fit with bilin's concept */
    /* northing = (northing - (e->yllcenter + e->cellsize*(e->nrows-1))) / e->cellsize; */
    northing = e->nrows-1 - (northing - e->yllcenter) / e->cellsize;
    easting  = (easting - e->xllcenter) / e->cellsize;

    /* and let bilin do the hard work */
    return bilin(e->data, e->ncols, e->nrows, northing, easting, e->nodata_value);
}




#ifdef TESTesrigrid

const char esrifilecontents[] = {
"ncols 10\n"
"nrows 2\n"
"xllcenter 720900.000\n"
"yllcenter 6173997.600\n"
"cellsize 1.6000\n"
"NODATA_value -9999\n"
"    # Testing esrigrid  \r\n\r\r\t    # toot\n123\n456# 789\n101112 4 5 6 7 8 9 10\n 2.0 2.1 2.2 2.3 2.4 2.5 2.6 2.7 2.8 2.9"
}

int main(void) {
    FILE *f;
    double v;


    f = fopen ("esrigrid.test", "wt");
    fprintf (f, );
    fclose (f);

    f = fopen ("esrigrid.test", "rt");
    while (HUGE_VAL != (v = get_next_value(f)))
        printf ("%f\n", v);
    return 0;
}

#endif
