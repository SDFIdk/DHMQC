/**********************************************************************


sLASh - a *S*imple *LAS* reader in a single *H*eader file.


********************************************************************
Copyright (c) 1994-2013, Thomas Knudsen knudsen.thomas AT gmail DOT com
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
********************************************************************


    ------------------------------------------------------------
    sLASh - a simple LAS reader library in a single header file.
    ------------------------------------------------------------

    With two excellent LAS data handling libraries on the market,
    (libLAS and LASlib), one may rightfully wonder whether a
    reasonable reason could exist for introducing yet another LAS
    library.

    In the case of sLASh, the "reasonable reason" is to provide a
    set of simplistic, lightweight, easy-to-use, core functionality
    for reading LAS files, primarily targetting utility programs
    written in the C programming language.

    To reach this goal, sLASh has been designed with "leave it out"
    as its primary guiding principle:

    - If it is not core functionality, then leave it out.
    - If it is awkward to expose in the API, then leave it out.
    - If it is complex, then leave it out.

    and in general: if in doubt - then leave it out!

    This means that sLASh may be characterized as a simplistic
    LAS *reading* library, whereas the major LAS libraries may
    better be described as more complete LAS *handling* libraries.

    Specifically, sLASh leaves out all support for

    - writing data
    - the compressed LAZ format
    - data indexing
    - variable length records
    - waveform data

    To reach the goal of targetting programs written in C, the sLASh
    API has been modelled after the C standard input/output (stdio)
    file access API.

    This means that programs may be written according to ingrained
    C idioms: The stdio primitives fopen/fseek/fread/fclose have
    their direct sLASh counterparts in las_open/las_seek/las_read/
    las_close.

    Likewise, the role of the stdio "FILE" object is played by the
    sLASh "LAS" object.

    The sLASh library is lightweight and very compact. It comprises
    approximately 300 lines of code for the API, supplemented by
    an additional 100 lines of code, primarily supporting the use of
    sLASh on big endian (i.e. non-Intel) processor architectures.

    To further simplify the use of sLASh, it has been implemented
    entirely in a single header file. Hence, using sLASh in a program
    is as simple as writing "#include <slash.h>".

    The primary sLASh use case is in supporting the development of
    small programs "filling in gaps" where the major LAS packages
    lack functionality for project specific needs.

    In these cases, sLASh provides a simple way of interfacing, by
    reading the LAS format which the major LAS packages write and
    handle so well.

    sLASh is distributed under the highly permissive OpenBSD/ISC
    licence, making it suitable for use in a wide range of commercial
    and non-commercial, open-source and closed-source projects.


H I S T O R Y

2013-05-22 - Thomas Knudsen, knudsen.thomas (AT) gmail (DOT) com
    SiLAS - based on former work on point observation data readers,
    from the uf/busstop/boogie projects, intermittently designed,
    written and occasionally maintained during the time frame
    1991-2013, and Copyright (c) 1991-2013 by Thomas Knudsen

2013-07-04 - Thomas Knudsen, thokn (AT) gst (DOT) dk
    Renamed, simplified, recast as header library. Added GST (C) and
    ISC/OpenBSD licence text.


R E F E R E N C E S

LAS 1.1 spec http://asprs.org/a/society/committees/standards/asprs_las_format_v11.pdf
LAS 1.2 spec http://asprs.org/a/society/committees/standards/asprs_las_format_v12.pdf
LAS 1.3 spec http://www.asprs.org/a/society/committees/standards/asprs_las_spec_v13.pdf
LAS 1.4 spec http://www.asprs.org/a/society/committees/standards/LAS_1_4_r11.pdf
LAS 1.4 paper PERS 2012-02 ftp://lidar.dnr.state.mn.us/documentation/LAS%20spec%201.4.pdf


gcc -DTESTslash -W -Wall -pedantic -Wno-long-long -O2 -x c -o slash ../boogie/src/slash.h

***********************************************************************/


#include <stdio.h>
#include <stdlib.h>    /*  for malloc/calloc/realloc/free  */
#include <stddef.h>    /*  for offsetof macro             */
#include <string.h>    /*  for memcpy                     */
#include <math.h>      /*  for log10()                    */
#include <errno.h>
#include <time.h>      /*  for struct tm */
#include <assert.h>


/*********************************************************************/
/**   inlined functions - currently only supported for gcc          **/
/*********************************************************************/
#ifdef __GNUC__
#define INLINE inline
#endif
#ifdef INLINE
#define inline INLINE
#else
#define inline
#endif




/*********************************************************************/
/**  P R O T O T Y P E S   A N D   G E N E R A L   O V E R V I E W  **/
/*********************************************************************/

/* -- Data types -------------------------------------------------- */
struct lasheader;
typedef struct lasheader LAS;
struct las_nrgb;
typedef struct las_nrgb    LAS_NRGB;
struct las_wf_desc;
typedef struct las_wf_desc LAS_WAVEFORM_DESCRIPTOR;
struct lasrecord;
struct lasvlr;
typedef struct lasrecord LAS_RECORD;
typedef struct lasvlr    LAS_VLR;


/* -- Main API ---------------------------------------------------- */
LAS          *las_open (const char *filename, const char *mode) ;
void          las_close (LAS *h) ;
inline int    las_seek (LAS *h, size_t pos, int whence) ;
inline size_t las_read (LAS *h) ;


/* -- Record access API ------------------------------------------- */
inline double       las_x (const LAS *h) ;
inline double       las_y (const LAS *h) ;
inline double       las_z (const LAS *h) ;
inline double       las_intensity (const LAS *h) ;
inline unsigned int las_classification (const LAS *h) ;

inline double       las_scan_angle_rank (const LAS *h) ;
inline int          las_point_source_id (const LAS *h) ;
inline double       las_gps_time (const LAS *h) ;

inline unsigned int las_return_number (const LAS *h) ;
inline unsigned int las_number_of_returns (const LAS *h) ;
inline unsigned int las_classification_flags (const LAS *h) ;
inline int          las_scanner_channel (const LAS *h) ;
inline unsigned int las_scan_direction (const LAS *h) ;
inline unsigned int las_edge_of_flight_line (const LAS *h) ;

inline unsigned long long las_record_number (const LAS *h) ;
inline LAS_WAVEFORM_DESCRIPTOR las_waveform_descriptor (const LAS *h) ;
inline LAS_NRGB las_colour (const LAS *h) ;


/* -- Variable length records API --------------------------------- */
LAS_VLR *las_vlr_read (LAS *h, int type) ;
void las_vlr_free (LAS_VLR *self) ;


/* -- Printing and formatting API --------------------------------- */
struct tm yd2dmy(int y, int d) ;
void las_record_display (FILE *f, const LAS *h) ;
void las_header_display (FILE *f, const LAS *h) ;
void las_vlr_display (LAS_VLR *self, FILE *stream) ;
void las_vlr_display_all (LAS *h, FILE *stream) ;


/* -- Low level portability functions ----------------------------- */
inline void memcpy_swapping (void *dest, const void *src, size_t offset, size_t n) ;
inline long long get_signed_16 (const void *buf, size_t offset) ;
inline long long get_signed_32 (const void *buf, size_t offset) ;
inline long long get_signed_64 (const void *buf, size_t offset) ;
inline unsigned long long get_unsigned_16 (const void *buf, size_t offset) ;
inline unsigned long long get_unsigned_32 (const void *buf, size_t offset) ;
inline unsigned long long get_unsigned_64 (const void *buf, size_t offset) ;
inline float get_float (const void *buf, size_t offset) ;
inline double get_double (const void *buf, size_t offset) ;





/*********************************************************************/
/**                    P O R T A B I L I T Y                        **/
/**********************************************************************

    This section handles 3 portability issues:

    1. Whether to compile as inline or plain functions.

    2. Reading the little endian data specified for LAS
       on big endian metal.

    3. Platform variations in the definitions of the short,
       int and long data types.

    The latter is solved by returning all integer data types
    extended to an 8 byte long long (or unsigned long long).

    Hence, we assume two things about the compiler:

    1. Support for long long and unsigned long long data types

    2. These data types are 8 bytes wide.

    Since it is next to impossible to support the LAS format
    on platforms without a 64 bit integer type, these assumptions
    are not unreasonable - and certainly less far flung than
    the alternative.

    The following 8 functions replace a simpler memcpy based
    decoding in order to support platforms with other byte
    orderings or integer type widths than the Intel framework
    of the LAS specifications.



*********************************************************************/




/********************************************************************/
/**   large file support om Windows 32.                            **/
/*********************************************************************

    Cf. http://thompsonng.blogspot.dk/2011/09/vs2010-fseeko.html
    need to compile with -D_FILE_OFFSET_BITS=64
    cf. http://stackoverflow.com/questions/4003405/32-bit-windows-and-the-2gb-file-size-limit-c-with-fseek-and-ftell
    see also http://stackoverflow.com/questions/1035657/seeking-and-reading-large-files-in-a-linux-c-application

**********************************************************************/
#ifdef _WIN32
#define I64FMT "%I64d"
#ifdef __MINGW32__
#  define fseeko fseeko64
#  define ftello ftello64
#else
#  define fseeko _fseeki64
#  define ftello _ftelli64
#endif

#else /* not _WIN32*/
#define I64FMT "%lld"
#endif




/*********************************************************************/
/**   Endianness indicator                                          **/
/*********************************************************************/
const unsigned int  first_byte_is_nonzero_if_little_endian = 1;
const unsigned char *is_little_endian =
                         (const unsigned char *) &first_byte_is_nonzero_if_little_endian;
#define IS_LITTLE_ENDIAN (*is_little_endian)
/*********************************************************************/



/*********************************************************************/
inline void memcpy_swapping (void *dest, const void *src, size_t offset, size_t n) {
/*********************************************************************/
    char *ddest=dest;
    const char *ssrc = (const char *) src + offset;
    if (IS_LITTLE_ENDIAN) {
        memcpy (dest, (const char *) src + offset, n);
        return;
    }
    ddest += n;
    while (n--)
        *(--ddest) = *(ssrc++);
    return;
}




/*********************************************************************/
inline long long get_signed_16 (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = (unsigned char *) buf+offset;
    long long result = 0;
    int sign = b[1] & 128;

    if (sign)
        result = -1;
    if (IS_LITTLE_ENDIAN)
        memcpy (&result, b, 2);
    else
        memcpy_swapping (((char *)(&result))+6, b, 0, 2);
    return result;
}


/*********************************************************************/
inline long long get_signed_32 (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = ((unsigned char *) (buf))+offset;
    long long result =  0;
    int       sign   = b[3] & 128;
    if (sign)
        result = -1;
    if (IS_LITTLE_ENDIAN)
        memcpy (&result, b, 4);
    else
        memcpy_swapping (((char *)(&result))+4, b, 0, 4);
    return result;
}


/*********************************************************************/
inline long long get_signed_64 (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = (unsigned char *) buf+offset;
    unsigned long long result;
    memcpy_swapping (((char *)(&result)), b, 0, 8);
    return result;
}



/*********************************************************************/
inline unsigned long long get_unsigned_16 (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = (unsigned char *) buf+offset;
    unsigned long long result = 0;
    if (IS_LITTLE_ENDIAN)
        memcpy (&result, b, 2);
    else
        memcpy_swapping (((char *)(&result))+6, b, 0, 2);
    return result;
}


/*********************************************************************/
inline unsigned long long get_unsigned_32 (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = (unsigned char *) buf+offset;
    unsigned long long result = 0;
    if (IS_LITTLE_ENDIAN)
        memcpy (&result, b, 4);
    else
        memcpy_swapping (((char *)(&result))+4, b, 0, 4);
    return result;
}


/*********************************************************************/
inline unsigned long long get_unsigned_64 (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = (unsigned char *) buf+offset;
    unsigned long long result = 0;
    memcpy_swapping (((char *)(&result)), b, 0, 8);
    return result;
}



/*********************************************************************/
inline float get_float (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = (unsigned char *) buf+offset;
    float result = 0;
    memcpy_swapping (((char *)(&result)), b, 0, 4);
    return result;
}



/*********************************************************************/
inline double get_double (const void *buf, size_t offset) {
/*********************************************************************/
    unsigned char *b = (unsigned char *) buf+offset;
    double result = 0;
    memcpy_swapping (((char *)(&result)), b, 0, 8);
    return result;
}


/* end of PORTABILITY section */









/*********************************************************************/
/**                        D A T A   T Y P E S                      **/
/*********************************************************************/



/* LAS file header straightforwardly implemented from the LAS 1.0, 1.2, 1.3 & 1.4 specifications */
struct lasheader {
    char                     signature[8];                      /* LASF */
    unsigned short           file_source_id;
    unsigned short           global_encoding;

    unsigned long            project_id_1;
    unsigned short           project_id_2;
    unsigned short           project_id_3;
    unsigned char            project_id_4[8];

    unsigned char            version_major;
    unsigned char            version_minor;

    char                     system_id[32];
    char                     generated_by[32];

    unsigned short           file_creation_day_of_year;
    unsigned short           file_creation_year;

    unsigned short           header_size;
    unsigned long            offset_to_point_data;
    unsigned long            number_of_variable_length_records;

    unsigned char            point_data_format;
    unsigned short           point_data_record_length;
    unsigned long long       number_of_point_records;
    unsigned long long       number_of_points_by_return[15];

    double                   x_scale;
    double                   y_scale;
    double                   z_scale;
    double                   x_offset;
    double                   y_offset;
    double                   z_offset;

    double                   x_max;
    double                   x_min;
    double                   y_max;
    double                   y_min;
    double                   z_max;
    double                   z_min;

    unsigned long long       offset_to_waveform_data_packet_record;
    unsigned long long       start_of_extended_vlrs;
    unsigned long long       number_of_extended_vlrs;

    /* additional fields for internal use by sLASh */
    size_t  next_record;
    FILE   *f;
    char mode[256];
    size_t class_histogram[256];

    /* number of decimals recommended (computed from scale factors by las_open)*/
    int nx, ny, nz;
    unsigned char raw[8192];
    unsigned char record[1024];
};


/* Colour information - types 2, 3, 5, 7 (rgb), and 8, 10 (nrgb) */
struct las_nrgb {double n, r, g, b;};


/* Waveform information - types 4, 5, 9, 10*/
struct las_wf_desc {
    unsigned char      descriptor_index;
    float              return_point_location;
    float              x_t, y_t, z_t;
    unsigned long long offset_to_data;
    unsigned long long packet_size;
};





struct lasrecord {
    /* The common (unpacked) subset for all record types */
    double x, y, z;
    double intensity;

    /* Flags and narrow data fields from bytes 14-15 */
    unsigned int return_number, number_of_returns;
    unsigned int scanner_channel, scan_direction, edge_of_flight_line;
    /* Classification flags (overlap: types 6-10 only) */
    unsigned int synthetic, key_point, withheld, overlap;

    unsigned int classification;

    double scan_angle;
    unsigned char user_data;
    unsigned int  point_source_id;

    /* Record types 0 and 2 omits the GPS time */
    double gps_time;

    /* Colour information - types 2, 3, 5, 7 (rgb), and 8, 10 (nrgb) */
    LAS_NRGB colour;

    /* Waveform information - types 4, 5, 9, 10*/
    LAS_WAVEFORM_DESCRIPTOR waveform;
};



struct lasvlr {
    unsigned long long reserved;
    char user_id[16];
    unsigned long long record_id;
    unsigned long long payload_size;
    char description[32];
    /* ------------------- */
    fpos_t pos;
    int type; /* vlr: 0, evlr: 1, (waveform: 2???)*/
    unsigned char *payload;
};


/* end of section "data types" */

































/*********************************************************************/
/**                        M A I N    A P I                         **/
/*********************************************************************/






/*********************************************************************/
LAS *las_open (const char *filename, const char *mode) {
/*********************************************************************/
    LAS *p;
    FILE *f;
    unsigned char *raw = 0;
    int i, number_of_bins_in_return_histogram = 5, offset;

    p = (LAS *) calloc (1, sizeof(LAS));
    if (0==p)
        return 0;

    strncpy (p->mode, mode, sizeof(p->mode));

    /* TODO: support text files with mode = "rt%..." */
    /* TODO: support stdin with filename==0 || filename[0]=='\0' */
    f = fopen (filename, mode);
    if (0==f)
        return free (p), (LAS *) 0;
    p->f = f;

    raw = p->raw;

    /* the "safe subset" (i.e. version invariant part) of a */
    /* LAS header consists of the first 100 bytes            */
    fread (raw, 100, 1, p->f);

    /* check obvious indicators of non-validity of the file */
    p->header_size = get_unsigned_16 (raw, 94);
    if ((p->header_size > 1023) || (0!=strncmp("LASF", (char *) raw, 4)))
        return fclose (p->f), free (p), (LAS *) 0;

    strncpy (p->signature, (const char *) raw, 4);
    p->signature[4] = '\0';

    /* TODO: support any size offset */
    p->offset_to_point_data = get_unsigned_32 (raw,  96);
    if ((p->offset_to_point_data > 8191))
        return fclose (p->f), free (p), (LAS *) 0;

    /* now we know the full header size + offset to point data, and can read what remains */
    fread (raw + 100, p->header_size - 100, 1, p->f);

    p->file_source_id  = get_unsigned_16 (raw, 4);
    p->global_encoding = get_unsigned_16 (raw, 6);

    p->project_id_1  = get_unsigned_16 (raw,  8);
    p->project_id_2  = get_unsigned_16 (raw, 12);
    p->project_id_3  = get_unsigned_16 (raw, 14);
    memcpy (p->project_id_4, raw + 16, 8);

    p->version_major  = get_unsigned_16 (raw, 24);
    p->version_minor  = get_unsigned_16 (raw, 25);

    /* for some obscure reason, version 1.3 (and ONLY 1.3) adds two extra return bins here. */
    if ((p->version_major==1) && (p->version_minor == 3))
        number_of_bins_in_return_histogram = 7;

    memcpy (p->system_id,    raw + 26, 32);
    memcpy (p->generated_by, raw + 58, 32);

    p->file_creation_day_of_year  = get_unsigned_16 (raw, 90);
    p->file_creation_year         = get_unsigned_16 (raw, 92);

    p->number_of_variable_length_records  = get_unsigned_32 (raw, 100);

    p->point_data_format         =  raw[104];
    assert (p->point_data_format < 15);
    p->point_data_record_length  =  get_unsigned_16 (raw, 105);

    p->number_of_point_records   =  get_unsigned_32 (raw, 107);

    for (i = 0; i < number_of_bins_in_return_histogram; i++)
        p->number_of_points_by_return[i] = get_unsigned_32 (raw, 111+i*4);

    offset = 111 + 4 * number_of_bins_in_return_histogram;

    p->x_scale = get_double (raw, offset +  0*8);
    p->y_scale = get_double (raw, offset +  1*8);
    p->z_scale = get_double (raw, offset +  2*8);

    p->x_offset = get_double (raw, offset +  3*8);
    p->y_offset = get_double (raw, offset +  4*8);
    p->z_offset = get_double (raw, offset +  5*8);

    p->x_max = get_double (raw, offset +  6*8);
    p->x_min = get_double (raw, offset +  7*8);
    p->y_max = get_double (raw, offset +  8*8);
    p->y_min = get_double (raw, offset +  9*8);
    p->z_max = get_double (raw, offset + 10*8);
    p->z_min = get_double (raw, offset + 11*8);

    /* Version 1.3 introduces waveforms */
    if ((p->version_major>=1) && (p->version_minor >= 3))
        p->offset_to_waveform_data_packet_record = get_unsigned_64 (raw, offset + 12*8);

    /* Version 1.4 introduces support for very large files (untested) and 15 returns */
    if ((p->version_major>=1) && (p->version_minor >= 4)) {
        number_of_bins_in_return_histogram = 15;

        p->start_of_extended_vlrs   = get_unsigned_64 (raw, offset + 13*8);
        p->number_of_extended_vlrs  = get_unsigned_32 (raw, offset + 14*8);
        p->number_of_point_records  = get_unsigned_64 (raw, offset + 14*8 + 4);

        offset += 15*8+4;
        for (i = 0; i < number_of_bins_in_return_histogram; i++)
            p->number_of_points_by_return[i] = get_unsigned_64 (raw,  offset +  i*8);
    }


    /* Determine a reasonable number of decimals for x,y,z */
    p->nx = -log10 (p->x_scale) + 0.5;
    p->ny = -log10 (p->y_scale) + 0.5;
    p->nz = -log10 (p->z_scale) + 0.5;
    p->nx = (p->nx < 0)? 0: (p->nx > 10)? 10: p->nx;
    p->ny = (p->ny < 0)? 0: (p->ny > 10)? 10: p->ny;
    p->nz = (p->nz < 0)? 0: (p->nz > 10)? 10: p->nz;


    /* NB: should not be necessary, since we already read this amount */
    fseek (f, p->offset_to_point_data, SEEK_SET);
    p->next_record = 0;

    return p;
}




/*********************************************************************/
inline int las_seek (LAS *h, size_t pos, int whence) {
/*********************************************************************/
    int i = 0;

    if (0==h)
        return -1;
    if (SEEK_END==whence)
        pos = h->number_of_point_records - pos;
    if (pos > h->number_of_point_records)
        return (errno = EFBIG), -1;
    switch (whence) {
    case SEEK_SET:
    case SEEK_END:
        i = fseek (h->f, h->offset_to_point_data + pos * h->point_data_record_length, SEEK_SET);
        if (0==i)
            return h->next_record = pos, 0;
    case SEEK_CUR:
        i = fseek (h->f, pos * h->point_data_record_length, SEEK_CUR);
        if (0==i)
            return h->next_record += pos, 0;
    default:
        errno = EINVAL;
        return -1;
    }

    return -1;
}




/*********************************************************************/
inline size_t las_read (LAS *h) {
/*********************************************************************/
    if (0==h)
        return 0;
    if (h->next_record >= h->number_of_point_records)
        return 0;
    h->next_record++;
    return fread (h->record, h->point_data_record_length, 1, h->f);
}




/*********************************************************************/
void las_close (LAS *h) {
/*********************************************************************/
    /* TODO: free x,y if needed */
    if (0==h)
        return;
    if (h->f && (stdin != h->f) && (stdout != h->f))
        fclose (h->f);
    free (h);
}

/* end of main API section */




/*********************************************************************/
/**              R E C O R D   A C C E S S   A P I                  **/
/*********************************************************************/

/*                              0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 */
const int gps_time_offset[] = { 0,20, 0,20,20,20,22,22,22,22,22, 0, 0, 0, 0, 0};
const int colour_offset[]   = { 0, 0,20,28, 0,28, 0,30,30, 0,30, 0, 0, 0, 0, 0};
const int nir_offset[]      = { 0, 0, 0, 0, 0, 0, 0, 0,36, 0,36, 0, 0, 0, 0, 0};
const int waveform_offset[] = { 0, 0, 0, 0,28,34, 0, 0, 0,30,38, 0, 0, 0, 0, 0};



/*********************************************************************/
inline double las_x (const LAS *h) {
/*********************************************************************/
    return h->x_scale * get_signed_32(h->record, 0) + h->x_offset;
}


/*********************************************************************/
inline double las_y (const LAS *h) {
/*********************************************************************/
    return h->y_scale * get_signed_32(h->record, 4) + h->y_offset;
}


/*********************************************************************/
inline double las_z (const LAS *h) {
/*********************************************************************/
    return h->z_scale * get_signed_32(h->record, 8) + h->z_offset;
}


/*********************************************************************/
inline double  las_intensity (const LAS *h) {
/*********************************************************************/
    return get_unsigned_16(h->record, 12) / 65535.0;
}


/*********************************************************************/
inline unsigned int las_classification (const LAS *h) {
/*********************************************************************/
    if (h->point_data_format < 6)
        return (unsigned char) h->record[15] & 31;
    return (unsigned char) h->record[16];
}


/*********************************************************************/
inline double las_scan_angle_rank (const LAS *h) {
/*********************************************************************/
    if (h->point_data_format < 6)
        return (double) ((signed char) h->record[16]);
    return get_signed_16(h->record, 18) * 0.006;
}


/*********************************************************************/
inline int las_point_source_id (const LAS *h) {
/*********************************************************************/
    if (h->point_data_format < 6)
        return get_unsigned_16(h->record, 18);
    return get_unsigned_16(h->record, 20);
}


/*********************************************************************/
inline double las_gps_time (const LAS *h) {
/*********************************************************************/
    int i = gps_time_offset[h->point_data_format];
    if (0==i)
        return 0;
    return get_double (h->record, i);
}


/*********************************************************************/
inline unsigned int las_return_number (const LAS *h) {
/*********************************************************************/
    /* 1-5:  bits 0, 1, 2 */
    if (h->point_data_format < 6)
       return h->record[14] & 7;
    /* 6-10:  bits 0, 1, 2, 3 */
    return h->record[14] & 15;
}


/*********************************************************************/
inline unsigned int las_number_of_returns (const LAS *h) {
/*********************************************************************/
    /* 1-5:  bits 3, 4, 5 */
    if (h->point_data_format < 6)
    return ((unsigned char) h->record[14] & 56) / 8;
    /* 6-10:  bits 4, 5, 6, 7 */
    return h->record[14] / 16;
}


/*********************************************************************/
inline unsigned int las_classification_flags (const LAS *h) {
/*********************************************************************/
    /* 1-5:  upper 3 bits of the classification byte (15) */
    if (h->point_data_format < 6)
        return ((unsigned char) h->record[15] & 224) / 32;
    /* 6-10:  lower 4 bits of the second flag byte (15) */
    return h->record[15] & 15;
}   /* TODO: should be individual functions (cf. lasrecord) !!!!! */


/*********************************************************************/
inline int las_scanner_channel (const LAS *h) {
/*********************************************************************/
    /* 1-5:  undefined */
    if (h->point_data_format < 6)
        return -1;
    /* 6-10:  byte 15 bits 4, 5 */
    return (unsigned char)(h->record[15] & 48) / 16;
}


/*********************************************************************/
inline unsigned int las_scan_direction (const LAS *h) {
/*********************************************************************/
    /* 1-5:  byte 14, bit 6 */
    if (h->point_data_format < 6)
        return ((unsigned char) h->record[14] & 64) ? 1: 0;
    /* 6-10:  byte 15, bit 6 */
    return ((unsigned char) h->record[15] & 64) ? 1: 0;
}


/*********************************************************************/
inline unsigned int las_edge_of_flight_line (const LAS *h) {
/*********************************************************************/
    /* 1-5:  byte 14, bit 7 */
    if (h->point_data_format < 6)
        return ((unsigned char) h->record[14] & 128) ? 1: 0;
    /* 6-10:  byte 15, bit 7 */
    return ((unsigned char) h->record[15] & 128) ? 1: 0;
}

/*********************************************************************/
inline unsigned long long las_record_number (const LAS *h) {
/*********************************************************************/
    return h->next_record - 1;
}

/*********************************************************************/
inline LAS_WAVEFORM_DESCRIPTOR las_waveform_descriptor (const LAS *h) {
/*********************************************************************/
    LAS_WAVEFORM_DESCRIPTOR w = {0,0,0,0,0,0,0};
    unsigned int offset = waveform_offset[h->point_data_format];
    unsigned char *desc;

    if (0==offset)
        return w;

    desc = ((unsigned char *) &(h->record)) + offset;
    w.descriptor_index      = desc[0];
    w.offset_to_data        = get_unsigned_64 (desc, 1);
    w.packet_size           = get_unsigned_32 (desc, 9);
    w.return_point_location = get_float (desc, 13);
    w.x_t                   = get_float (desc, 17);
    w.y_t                   = get_float (desc, 21);
    w.z_t                   = get_float (desc, 25);
    return w;
}

/*********************************************************************/
inline LAS_NRGB las_colour (const LAS *h) {
/*********************************************************************/
    LAS_NRGB c = {0,0,0,0};
    unsigned int offset = colour_offset[h->point_data_format];
    unsigned char *col;

    if (0==offset)
        return c;

    /* RGB (record types 2, 3, 5, 7, 8, 10) */
    col = ((unsigned char *) &(h->record)) + offset;
    c.r = get_unsigned_16 (col, 0) / 65535.0;
    c.g = get_unsigned_16 (col, 2) / 65535.0;
    c.b = get_unsigned_16 (col, 4) / 65535.0;


    /* Check for NIR */
    offset = nir_offset[h->point_data_format];
    if (0==offset)
        return c;

    /* NIR (record types 8, 10) */
    col = ((unsigned char *) &(h->record)) + offset;
    c.n = get_unsigned_16 (col, 12) / 65535.0;
    
    /* TODO: should we put scaled intensity here if no NIR? */
    return c;
}


/* end of record access API section */


















/*********************************************************************/
/**     V L R   S U B S Y S T E M    ( E X P E R I M E N T A L )    **/
/*********************************************************************/




/*********************************************************************/
LAS_VLR *las_vlr_read (LAS *h, int type) {
/*********************************************************************/
    LAS_VLR *self;
    unsigned char buffer[100];
    if (h==0)
        return 0;
    if (0!=type)
        return 0;
    self = calloc (1, sizeof(LAS_VLR));
    if (0==self)
        return 0;

    fgetpos (h->f, &(self->pos));
    assert (0!=self->pos);
    self->type = type;
    self->payload = 0;

    fread (buffer, 54, 1, h->f);
    memcpy (self->user_id,     buffer+2,  16);
    memcpy (self->description, buffer+22, 32);
    self->reserved     =  get_unsigned_16 (buffer,  0);
    self->record_id    =  get_unsigned_16 (buffer, 18);
    self->payload_size =  get_unsigned_16 (buffer, 20);
    
    /* read contents of official vlrs only */
    if (0==strncmp ("LASF", self->user_id, 4)) {
        self->payload = malloc (self->payload_size);
        if (0==self->payload)
            return self;
        fread (self->payload, self->payload_size, 1, h->f);
    }
    
    return self;
}

/*********************************************************************/
void las_vlr_free (LAS_VLR *self) {
/*********************************************************************/
    if (0==self)
        return;
    if (0 != self->payload)
        free (self->payload);
    free (self);
}

/* end of experimental vlr API section */










/*********************************************************************/
/**      P R I N T I N G   A N D   F O R M A T T I N G   A P I      **/
/*********************************************************************/


/*********************************************************************/
struct tm yd2dmy(int y, int d) {
/*********************************************************************/
/* utility function for las_header_display: convert day-of-year to mm+dd */
/* mktime() from the standard library performs the opposite operation */
    int i, day = 0;
    struct tm dmy;
    int l[12] = {31,28,31,  30,31,30,  31,31,30, 31,30,31};
    l[1] += ((0==y%4) && ((y%100)||(0==y%400)))? 1:0;
    for (i = 0; i < 12; i++) {
        day += l[i];
        if (day>=d)
            break;
    }
    day -= l[i];
    dmy.tm_year = y-1900;
    dmy.tm_mon  = i;
    dmy.tm_mday = d - day;
    return dmy;
}







/*********************************************************************/
void las_record_display (FILE *f, const LAS *h) {
/*********************************************************************/
    double x = las_x (h);
    double y = las_y (h);
    double z = las_z (h);
    double t = las_gps_time (h);
    int    i = las_intensity (h);
    unsigned long    n = las_record_number (h);

    fprintf (f, "%10lu %15.*f %15.*f %15.*f %8d %15.6f\n",
                n, h->nx, x, h->ny, y, h->nz, z, i, t);
    return;
}




/*********************************************************************/
void las_header_display (FILE *f, const LAS *h) {
/*********************************************************************/
    /* we turn the last 8 bytes of the UUID into 2 shorts and a long to make it printable as an UUID */
    /* TODO: do the right thing on big-endian platforms */
    short suuid1 = *(short *)(((char *) h) + offsetof(LAS, project_id_4));
    short suuid2 = *(short *)(((char *) h) + offsetof(LAS, project_id_4) + 2);
    long  luuid  = *(long  *)(((char *) h) + offsetof(LAS, project_id_4) + 4);
    struct tm dmy;
    int d, m, y;

    dmy = yd2dmy (h->file_creation_year, h->file_creation_day_of_year);
    d = dmy.tm_mday;
    m = dmy.tm_mon + 1;
    y = dmy.tm_year + 1900;

    fprintf (f, "LAS header entries\n");

    fprintf (f, "%40s  %.4s\n", "file signature:",  h->signature);
    fprintf (f, "%40s  %u\n", "file source ID:",    h->file_source_id);
    fprintf (f, "%40s  %u\n", "global_encoding:",   h->global_encoding);

    fprintf (f, "%40s  %.8x-%.4x-%.4x-%.4x-%.4x%.8x\n", "project id:",
                   (unsigned int) h->project_id_1,  h->project_id_2,  h->project_id_3,  suuid1, suuid2, (unsigned int) luuid);

    fprintf (f, "%40s  %d.%d\n",  "version:",  h->version_major, h->version_minor);

    fprintf (f, "%40s  %.32s\n",  "system identifier:",        h->system_id);
    fprintf (f, "%40s  %.32s\n",  "generating software:",      h->generated_by);

    fprintf (f, "%40s  %4.4d-%2.2d-%2.2d\n",  "file creation date:", y, m, d);
    fprintf (f, "%40s  %u\n",     "header size:",                   h->header_size);
    fprintf (f, "%40s  %u\n",    "offset to point data:",           (unsigned int) h->offset_to_point_data);
    fprintf (f, "%40s  %u\n",    "number of var. length records:",  (unsigned int) h->number_of_variable_length_records);
    fprintf (f, "%40s  %d\n",     "point data format:",             h->point_data_format);
    fprintf (f, "%40s  %u\n",     "point data record length:",      h->point_data_record_length);
    fprintf (f, "%40s  %u\n",    "number of point records:",        (unsigned int) h->number_of_point_records);
    /* fprintf (f, "%-40s  %f\n", "number of points by return:" 2087467 10 0 0 0 */

    fprintf (f, "%40s  %15g %15g %15g\n",     "scale factor x y z:", h->x_scale, h->y_scale, h->z_scale);
    fprintf (f, "%40s  %15f %15f %15f\n",     "offset x y z:",       h->x_offset, h->y_offset, h->z_offset);

    fprintf (f, "%40s  %15f %15f %15f\n", "min x y z:",  h->x_min, h->y_min, h->z_min);
    fprintf (f, "%40s  %15f %15f %15f\n", "max x y z:",  h->x_max, h->y_max, h->z_max);
}


/*********************************************************************/
void las_vlr_display (LAS_VLR *self, FILE *stream) {
/*********************************************************************/
    fprintf (stream, "%-16s(%5.5d,%5.5d): %6d bytes. %32s\n",
        self->user_id,
        (int) self->record_id,
        (int) self->reserved,
        (int) self->payload_size,
        self->description
    );
}

/*********************************************************************/
void las_vlr_display_all (LAS *h, FILE *stream) {
/*********************************************************************/
    fpos_t pos;
    LAS_VLR *vlr;
    unsigned int i;
    if (0==h)
        return;

    fgetpos (h->f, &pos);
    fseek (h->f, h->header_size, SEEK_SET);
    for (i = 0; i < h->number_of_variable_length_records; i++) {
        vlr = las_vlr_read (h, 0);
        /* skip payload if it wasn't read by las_read_vlr, to arrive at next vlr */
        if (0==vlr->payload)
            fseek (h->f, vlr->payload_size, SEEK_CUR);
        las_vlr_display (vlr, stream);
        las_vlr_free (vlr);
    }

    /* clean up */
    fsetpos (h->f, &pos);
}















/*********************************************************************/
/**                    U N I T   T E S T I N G                      **/
/*********************************************************************/


#ifdef TESTslash
/*********************************************************************/
int main (int argc, char **argv) {
/*********************************************************************/
    LAS *h;
    struct tm dmy;
    int i = 0, target = 1;
    short s, starget;
    long long ll, lltarget;
    double d, dtarget;

    h = las_open (argc < 2? "test.las": argv[1], "rb");
    if (0==h) {
        fprintf (stderr, "Cannot open 'test.las'\n");
        return 1;
    }

    las_header_display (stderr, h);

    while  (las_read (h)) {
        if (i==target) {
            las_record_display (stdout, h);
            target *= 10;
        }
        h->class_histogram[las_classification (h)]++;
        i++;
    }

    printf ("records read = %d\n", i);

    /* print class histogram */
    for (i=0; i<256; i++)
        if (h->class_histogram[i])
            printf ("h[%3.3d] = %d\n", i, (int) h->class_histogram[i]);

    las_vlr_display_all (h, stdout);

    /* test little endian data readers */
    target = -1234;
    memcpy_swapping (&i, &target, 0, 4);
    printf ("get_signed_32: %d\n", (int) get_signed_32(&i, 0));
    starget = -1234;
    memcpy_swapping (&s, &starget, 0, 2);
    printf ("get_signed_16: %d\n", (int) get_signed_16(&s, 0));
    starget = 3456;
    memcpy_swapping (&s, &starget, 0, 2);
    printf ("get_signed_16: %d\n", (int) get_signed_16(&s, 0));
    lltarget = -1010101010101010LL;
    memcpy_swapping (&ll, &lltarget, 0, 8);
    printf ("get_signed_64: " I64FMT "\n", get_signed_64(&ll, 0)); /*%I64d*/

    dtarget = 1234.5678;
    memcpy_swapping (&d, &dtarget, 0, 8);
    printf ("new get_double: %f\n", get_double(&d, 0));

    /* test date kludge */
    dmy = yd2dmy (2000, 59); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 2000-02-28 */
    dmy = yd2dmy (2000, 61); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 2000-03-01 */
    dmy = yd2dmy (1900, 59); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 1900-02-28 */
    dmy = yd2dmy (1900, 61); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 1900-03-02 */
    dmy = yd2dmy (2012, 59); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 2012-02-28 */
    dmy = yd2dmy (2012, 61); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 2012-03-01 */
    dmy = yd2dmy (2013, 59); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 2013-02-28 */
    dmy = yd2dmy (2013, 61); printf ("%4.4d-%2.2d-%2.2d\n", dmy.tm_year+1900, dmy.tm_mon+1, dmy.tm_mday); /* 2013-03-02 */


    las_close (h);
    return 0;
}
#endif

