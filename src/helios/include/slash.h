/**********************************************************************


sLASh - a *S*imple *LAS* reader in a single *H*eader file.


********************************************************************
Copyright (c) 1994-2014, Thomas Knudsen knudsen.thomas AT gmail DOT com
Copyright (c) 2013-2014, Danish Geodata Agency, <gst@gst.dk>

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

2013-11-04 Moved to Helios


R E F E R E N C E S

LAS specs:
    http://www.asprs.org/Committee-General/LASer-LAS-File-Format-Exchange-Activities.html
LAS 1.4 paper
    PERS 2012-02 ftp://lidar.dnr.state.mn.us/documentation/LAS%20spec%201.4.pdf

gcc -DTESTslash -W -Wall -pedantic -Wno-long-long -O2 -x c -o slash slash.h

***********************************************************************/

#ifndef __SLASH_H
#define __SLASH_H

/* TODO: write long warning about how this may affect your general health and abilities.
 * (short form: be sure to define this before ANY system headers are included, i.e. preferably on the compiler command line) */
#ifndef _FILE_OFFSET_BITS
#define _FILE_OFFSET_BITS 64
#endif

#include <stdio.h>
#include <stdlib.h>    /*  for malloc/calloc/realloc/free  */
#include <stddef.h>    /*  for offsetof macro             */
#include <string.h>    /*  for memcpy                     */
#include <math.h>      /*  for log10()                    */
#include <float.h>
#include <errno.h>
#include <time.h>      /*  for struct tm */
#include <assert.h>


/*********************************************************************/
/**   inlined functions - currently only supported for gcc          **/
/*********************************************************************/
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




/*********************************************************************/
/**  P R O T O T Y P E S   A N D   G E N E R A L   O V E R V I E W  **/
/*********************************************************************/

/* -- Data types -------------------------------------------------- */
struct lasheader;
typedef struct lasheader LAS;
struct las_nrgb;
typedef struct las_nrgb    LAS_NRGB;
struct las_wf_meta;
typedef struct las_wf_meta LAS_WAVEFORM_METADATA;
struct las_wf_desc;
typedef struct las_wf_desc LAS_WAVEFORM_DESCRIPTOR;
typedef struct las_wf_sample LAS_WAVEFORM_SAMPLE;
struct las_filter;
typedef struct las_filter LAS_FILTER;

struct lasrecord;
struct lasvlr;
typedef struct lasrecord LAS_RECORD;
typedef struct lasvlr    LAS_VLR;


/* -- Main API ---------------------------------------------------- */
LAS          *las_open (const char *filename, const char *mode) ;
void          las_close (LAS *h) ;
inline int    las_seek (LAS *h, long long  pos, int whence) ;
inline size_t las_read (LAS *h) ;
inline size_t las_waveform_read (LAS *h);

/* -- Record access API ------------------------------------------- */
inline double       las_x (const LAS *h);
inline double       las_y (const LAS *h);
inline double       las_z (const LAS *h);
inline double       las_gps_time (const LAS *h);
inline double       las_intensity (const LAS *h);

inline unsigned int las_class (const LAS *h);
inline unsigned int las_class_flags (const LAS *h);
inline unsigned int las_flag_synthetic (const LAS *h);
inline unsigned int las_flag_key_point (const LAS *h);
inline unsigned int las_flag_withheld (const LAS *h);
inline unsigned int las_flag_overlap (const LAS *h);

inline unsigned int las_return_number (const LAS *h);
inline unsigned int las_number_of_returns (const LAS *h);
inline int          las_is_last_return (const LAS *h);
inline unsigned long long las_record_number (const LAS *h);

inline double       las_scan_angle_rank (const LAS *h);
inline int          las_point_source_id (const LAS *h);
inline int          las_scanner_channel (const LAS *h);
inline unsigned int las_scan_direction (const LAS *h);
inline unsigned int las_edge_of_flight_line (const LAS *h);

inline LAS_WAVEFORM_METADATA las_waveform_metadata (const LAS *h);
inline LAS_NRGB las_colour (const LAS *h);

/* filter on point properties API/internals */
int las_filter (LAS *h);


/* -- Variable length records API --------------------------------- */
LAS_VLR *las_vlr_read (LAS *h, int type);
void las_vlr_free (LAS_VLR *v);
int las_vlr_interpret_all (LAS *h, FILE *stream);

int las_vlr_is_waveform_descriptor (LAS_VLR *v);
LAS_WAVEFORM_DESCRIPTOR las_waveform_descriptor (LAS_VLR *v);
inline LAS_WAVEFORM_SAMPLE las_waveform_sample (const LAS *h, size_t index);


/* -- Printing and formatting API --------------------------------- */
struct tm yd2dmy(int y, int d);
void las_record_display (const LAS *h, FILE *stream);
void las_header_display (const LAS *h, FILE *stream);
void las_vlr_display (LAS_VLR *v, FILE *stream);
void las_vlr_display_all (LAS *h, FILE *stream);
void las_waveform_descriptor_display (LAS_WAVEFORM_DESCRIPTOR h, FILE *stream);


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
/* In Redmond they do their utmost in order to stay incompatible with everyone else */
#  define fseeko _fseeki64
#  define ftello _ftelli64
#define isnan(x) _isnan(x)
#define isinf(x) (!_finite(x))
#define fpu_error(x) (isinf(x) || isnan(x))
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
/**   Static assertions: sizeof(long long)==8, etc.                 **/
/*********************************************************************/
/* cf eg http://www.pixelbeat.org/programming/gcc/static_assert.html http://stackoverflow.com/questions/807244/c-compiler-asserts-how-to-implement */
enum {assert_long_long_is_8_bytes = 1/(sizeof(long long)==8)};
enum {assert_unsigned_long_long_is_8_bytes = 1/(sizeof(unsigned long long)==8)};
/* enum {assert_size_t_is_8_bytes = 1/(sizeof(size_t)==8)};*/
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





/* Colour information - types 2, 3, 5, 7 (rgb), and 8, 10 (nrgb) */
struct las_nrgb {double n, r, g, b;};


/* Waveform metadata - types 4, 5, 9, 10*/
struct las_wf_meta {
    unsigned char      descriptor_index;
    float              return_point_location;
    float              x_t, y_t, z_t;
    unsigned long long offset_to_data;
    unsigned long long packet_size;
};


/* variable length record - header and payload */
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


/* waveform descriptors are decoded from corresponding  VLRs */
struct las_wf_desc {
    unsigned int bits_per_sample;
    unsigned int compression_type;
    unsigned int  index;
    unsigned long number_of_samples;
    unsigned long sample_interval;
    int valid;
    double gain;
    double offset;
};


/* coordinates and intensity for a given instant along the waveform profile */
struct las_wf_sample {
    double x;
    double y;
    double z;
    double intensity;
    double time;
    size_t index;
    int valid;
};


/* filter for selection/deselection of point classes etc. */
struct las_filter {
    double n, w, s, e;    int do_bb;  /* bounding box */
    double z, Z;          int do_vbb; /* vertical bounding box */
    double t, T;          int do_tbb; /* temporal bounding box */
    char *classification; int do_cls;
    char *return_number;  int do_ret;
    int   return_last;    int do_ret_last;
    int   errlev;
};


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
    unsigned long long  next_record;
    unsigned long long  next_vlr;
    FILE   *f;
    FILE   *wdp;
    char mode[256];
    unsigned long long      class_histogram[256];
    LAS_WAVEFORM_DESCRIPTOR waveform_descriptor[256];
    LAS_WAVEFORM_METADATA   waveform_metadata;
    unsigned char          *waveform_data;
    size_t                  waveform_data_allocated_size;

    LAS_FILTER *filter;

    /* number of decimals recommended (computed from scale factors by las_open)*/
    int nx, ny, nz;
    unsigned char raw_header[8192];
    unsigned char record[1024];
};

#ifdef __STACK_H
stackable(LAS);
#endif





/* The LAS format as of v. 1.4 supports 11 record types, numbered 0..10        */
/* The field offsets and field types included vary by record type.             */
/* The constant arrays below indicate the field offsets for extended           */
/* field types indexed by record type id.                                      */
/* Zeroes indicate that the corresponding field type is not supported for the  */
/* record type considered                                                      */
/*                              record type id                                 */
/*                              0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 */
const int gps_time_offset[] = { 0,20, 0,20,20,20,22,22,22,22,22, 0, 0, 0, 0, 0};
const int colour_offset[]   = { 0, 0,20,28, 0,28, 0,30,30, 0,30, 0, 0, 0, 0, 0};
const int nir_offset[]      = { 0, 0, 0, 0, 0, 0, 0, 0,36, 0,36, 0, 0, 0, 0, 0};
const int waveform_offset[] = { 0, 0, 0, 0,28,34, 0, 0, 0,30,38, 0, 0, 0, 0, 0};





struct lasrecord {
    /* The common (unpacked) subset for all record types */
    double x, y, z;
    double intensity;

    /* Flags and narrow data fields from bytes 14-15 */
    unsigned int return_number, number_of_returns;
    unsigned int scanner_channel, scan_direction, edge_of_flight_line;
    /* Classification flags (overlap: types 6-10 only) */
    unsigned int synthetic, key_point, withheld, overlap;

    unsigned int classification; /* "class" is reserved under C++, hence "classification" */

    double scan_angle;
    unsigned char user_data;
    unsigned int  point_source_id;

    /* Record types 0 and 2 omits the GPS time */
    double gps_time;

    /* Colour information - types 2, 3, 5, 7 (rgb), and 8, 10 (nrgb) */
    LAS_NRGB colour;

    /* Waveform information - types 4, 5, 9, 10*/
    LAS_WAVEFORM_METADATA waveform_metadata;
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
    if (0==f) {
        errno = EBADF;
        free (p);
        return (LAS *) 0;
    }
    p->f = f;

    /* File object for the waveform data packet */
    p->wdp = 0;


    raw = p->raw_header;

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

    /*
     *   Prior to R11 of the LAS1.3 spec, the return histogram size was
     *   unintentionally defined as having 7 bins, rather than the 5 as
     *   intended.
     *   Here we take care of this by noting that files written in
     *   conformance with the malformed spec has a header size of
     *   243 bytes, rather than the intended 235.
     */
    if ((p->version_major==1) && (p->version_minor == 3) && (p->header_size == 243))
        number_of_bins_in_return_histogram = 7;

    memcpy (p->system_id,    raw + 26, 32);
    memcpy (p->generated_by, raw + 58, 32);

    p->file_creation_day_of_year  = get_unsigned_16 (raw, 90);
    p->file_creation_year         = get_unsigned_16 (raw, 92);

    p->number_of_variable_length_records  = get_unsigned_32 (raw, 100);

    p->point_data_format         =  raw[104];
    assert (p->point_data_format < 11);
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
    if ((p->version_major>=1) && (p->version_minor >= 3) && waveform_offset[p->point_data_format]) {
        p->offset_to_waveform_data_packet_record = get_unsigned_64 (raw, offset + 12*8);

        /* Need file type ".las". Construct filename.wdp from filename.las */
        if ((strlen(filename)>3) && ('.'==filename[strlen (filename) - 4])) {
            char *wdp_file_name = malloc (strlen (filename) + 1);
            if (0==wdp_file_name) {
                errno = ENOMEM;
                fclose(p->f);
                free (p);
                return (LAS *) 0;
            }
            strcpy (wdp_file_name, filename);
            wdp_file_name[strlen (filename) - 4] = '\0';
            strcat (wdp_file_name, ".wdp");
            p->wdp = fopen (wdp_file_name, mode); /* may not exist */
            free (wdp_file_name);
        }
    }

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

    /* record, and variable length record counters */
    p->next_record = 0;
    p->next_vlr = 0;

    return p;
}




/*********************************************************************/
inline int las_seek (LAS *h, long long pos, int whence) {
/*********************************************************************/
    long long i = 0;

    if (0==h)
        return -1;
    if (SEEK_END==whence)
        pos = h->number_of_point_records - pos;
    if (pos > (long long) h->number_of_point_records)
        return (errno = EFBIG), -1;

    switch (whence) {
    case SEEK_SET:
    case SEEK_END:
        i = fseeko (h->f, h->offset_to_point_data + pos * h->point_data_record_length, SEEK_SET);
        if (0==i)
            return h->next_record = pos, 0;
    case SEEK_CUR:
        i = fseeko (h->f, pos * h->point_data_record_length, SEEK_CUR);
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
    if ((0==h->next_record) && (-1==las_seek (h, 0, SEEK_SET)))
        return 0;
    
    /* if filter installed, loop is executed until EOF or filter match */
    for (;;) {
        int n;
        if (h->next_record >= h->number_of_point_records)
            break;
    
        n = fread (h->record, h->point_data_record_length, 1, h->f);
        if (0==n)
            break;
        h->next_record++;
    
        /* filter not installed: return first available record */
        if (0==h->filter)
            return n;
    
        /* filter installed - loop if no match, return if match */
        if (las_filter(h))
                return n;
    }
    return 0;
}


/*********************************************************************/
inline size_t las_waveform_read (LAS *h) {
/*********************************************************************/
    size_t n, d;

    /*  make sure arg is OK and we have valid waveform data     */
    /*  (trying to read waveforms where none are to be found    */
    /*  is OK, but a waveform size of zero will be reported)    */
    if (0==h)
        return 0;
    if (0==h->wdp)
        return 0;
    if (0==waveform_offset[h->point_data_format])
        return 0;

    /*
     *   Correct (but clunky) syntax: decoding waveform meta data
     *   is deferred until now, when we need it
     */
    h->waveform_metadata = las_waveform_metadata (h);

    n = h->waveform_metadata.packet_size;
    d = h->waveform_metadata.descriptor_index;

    if (n > h->waveform_data_allocated_size) {
        unsigned char *buf = malloc (n);
        if (0==buf)
            return (errno = ENOMEM), 0;
        h->waveform_data = buf;
        h->waveform_data_allocated_size = n;
    }

    fseeko (h->wdp, h->waveform_metadata.offset_to_data, SEEK_SET);
    fread (h->waveform_data, n, 1, h->wdp);
    return h->waveform_descriptor[d].number_of_samples;
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
inline double las_gps_time (const LAS *h) {
/*********************************************************************/
    int i = gps_time_offset[h->point_data_format];
    if (0==i)
        return 0;
    return get_double (h->record, i);
}


/*********************************************************************/
inline double  las_intensity (const LAS *h) {
/*********************************************************************/
    return ((double)get_unsigned_16(h->record, 12)) / 65535.0;
}


/*********************************************************************/
inline unsigned int las_class (const LAS *h) {
/*********************************************************************/
    if (h->point_data_format < 6)
        return (unsigned char) h->record[15] & 31;
    return (unsigned char) h->record[16];
}


/*********************************************************************/
inline unsigned int las_class_flags (const LAS *h) {
/*********************************************************************/
    /* 1-5:  upper 3 bits of the classification byte (15) */
    if (h->point_data_format < 6)
        return ((unsigned char) h->record[15] & 224) / 32;
    /* 6-10:  lower 4 bits of the second flag byte (15) */
    return h->record[15] & 15;
}   /* Also see individual flag functions below */

/*********************************************************************/
inline unsigned int las_flag_synthetic (const LAS *h) {
/*********************************************************************/
    return las_class_flags (h) & (unsigned int) 1;
}

/*********************************************************************/
inline unsigned int las_flag_key_point (const LAS *h) {
/*********************************************************************/
    return las_class_flags (h) & (unsigned int) 2;
}

/*********************************************************************/
inline unsigned int las_flag_withheld (const LAS *h) {
/*********************************************************************/
    return las_class_flags (h) & (unsigned int) 4;
}

/*********************************************************************/
inline unsigned int las_flag_overlap (const LAS *h) {
/*********************************************************************/
    /* 1-5:  class == 12 indicates overlap */
    if (h->point_data_format < 6)
        return las_class (h) == 12;
    /* 6-10:  bit 3 of the classification flags */
    return las_class_flags (h) & 8;
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
inline double las_scan_angle_rank (const LAS *h) {
/*********************************************************************/
    if (h->point_data_format < 6)
        return (double) ((signed char) h->record[16]);
    return get_signed_16(h->record, 18) * 0.006;
}

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
inline int las_point_source_id (const LAS *h) {
/*********************************************************************/
    if (h->point_data_format < 6)
        return get_unsigned_16(h->record, 18);
    return get_unsigned_16(h->record, 20);
}


/*********************************************************************/
inline int las_is_last_return (const LAS *h) {
/*********************************************************************/
    return las_number_of_returns (h) == las_return_number (h);
}

/*********************************************************************/
inline unsigned long long las_record_number (const LAS *h) {
/*********************************************************************/
    return h->next_record - 1;
}




/*********************************************************************/
inline LAS_WAVEFORM_METADATA las_waveform_metadata (const LAS *h) {
/*********************************************************************/
    LAS_WAVEFORM_METADATA w = {0,0,0,0,0,0,0};
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
inline LAS_WAVEFORM_SAMPLE las_waveform_sample (const LAS *h, size_t index) {
/*********************************************************************/
    LAS_WAVEFORM_SAMPLE      s = {0,0,0,0,0,0,0};
    LAS_WAVEFORM_DESCRIPTOR  d;
    double intensity;
    int i;

    /* TODO: check index within range */

    /* pointer to the waveform descriptor used for the current waveform */
    i = h->waveform_metadata.descriptor_index;
    d = h->waveform_descriptor[i];
    switch (d.bits_per_sample) {
        case  8:
            intensity = h->waveform_data[index];
            break;
        case 16:
            intensity = get_unsigned_16 (h->waveform_data, 2*index);
            break;
        case 32:
            intensity = get_unsigned_32 (h->waveform_data, 4*index);
            break;
        default:
            return s;
    }

/*    s.intensity = d.gain * intensity + d.offset;*/
    s.intensity = intensity;
    s.valid = 1;
    return s;
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
/**  F I L T E R    S U B S Y S T E M   ( E X P E R I M E N T A L ) **/
/*********************************************************************/


#if 0
/* filter for selection/deselection of point classes etc. */
struct las_filter {
    double n, w, s, e;  int do_bb;  /* bounding box */
    double z, Z;        int do_vbb; /* vertical bounding box */
    double t, T;        int do_tbb; /* temporal bounding box */
    int *classification; int do_cls;
};
#endif

int las_filter (LAS *h) {
    /* most common case: filter on class */
    if (h->filter->do_cls && (0==h->filter->classification[las_class (h)]))
        return 0;

    /* filtering on return suffers from the  "last return complication" */
    if (h->filter->do_ret && (0==h->filter->return_number[las_return_number (h)]))
        return 0;
    if (h->filter->do_ret_last && (h->filter->return_last != las_is_last_return (h)))
        return 0;

    /* if filtering on bounding box ... */
    if (h->filter->do_bb) {
        double xx = las_x (h), yy = las_y (h);
        if (yy > h->filter->n) return 0;
        if (yy < h->filter->s) return 0;
        if (xx > h->filter->e) return 0;
        if (xx < h->filter->w) return 0;
    }

    /* if filtering on height interval ... */
    if (h->filter->do_vbb) {
        double zz = las_z (h);
        if (zz < h->filter->z) return 0;
        if (zz > h->filter->Z) return 0;
    }

    /* if filtering on time interval ... */
    if (h->filter->do_tbb) {
        double tt = las_gps_time (h);
        if (tt < h->filter->t) return 0;
        if (tt > h->filter->T) return 0;
    }

    /* survived all checks above */
    return 1;
}

LAS_FILTER *las_filter_alloc (void) {
    LAS_FILTER *p = calloc (1, sizeof(LAS_FILTER));
    if (0==p) {
        errno = ENOMEM;
        return 0;
    }
    p->classification = calloc (257, sizeof(char));
    if (0==p->classification) {
        errno = ENOMEM;
        free (p);
        return 0;
    }
    p->return_number = calloc (257, sizeof(char));
    if (0==p->return_number) {
        errno = ENOMEM;
        free (p->classification);
        free (p);
        return 0;
    }
    return p;
}

void las_filter_free (LAS_FILTER *p) {
    if (0==p)
        return;
    free (p->classification);
    free (p->return_number);
    free (p);
}

/* command line option decoding ( -F B:N/W/S/E style) */
int las_filter_decode (LAS_FILTER *f, char *optarg) {
    char *arg = optarg + 1, option;
    
    if (0==f)
        return 1000;
    if (0==optarg)
        return 1001;
    if (strlen (optarg) < 1)
        return 1002;

    option = optarg[0];

    /* skip optional colon delimiter */
    if (arg[0]==':')
        arg++;
    
    switch (option) {
        double a[4];
        int    b[4];
        int i;
        
        case 'B':  /* Bounding box */
            if (4!=sscanf (arg, "%lf/%lf/%lf/%lf", a, a+1, a+2, a+3))
                return (f->errlev = EINVAL);
            f->do_bb = 1;
            f->n = a[0]; f->w = a[1]; f->s = a[2]; f->e = a[3];
            return 0;
            
        case 'C':  /* Class */
            /* "Ci": revert selection */
            if (0==strcmp(arg, "i")) {
                for (i = 0; i <256; i++)
                    f->classification[i] = !(f->classification[i]);
                f->do_cls = 1;
                return 0;
            }
            /* "C:from/to": select range of classes */
            if (2==sscanf (arg, "%d/%d", b, b+1)) {
                if ((b[0]<0)||(b[0]>255)||(b[1]<0)||(b[1]>255)||(b[0]>b[1]))
                    return (f->errlev = EINVAL);
                for (i = b[0]; i <=b[1]; i++)
                    f->classification[i] = 1;
                f->do_cls = 1;
                return 0;
            }
            /* "C:class": select single class */
            if (1==sscanf (arg, "%d", b)) {
                f->classification[b[0]] = 1;
                f->do_cls = 1;
                return 0;
            }
            /* otherwise: something's wrong */
            return (f->errlev = EINVAL);

        case 'R': /* Returns */
            /* "Ri": revert selection */
            if (0==strcmp(arg, "i")) {
                if (f->do_ret_last)
                    f->return_last = !(f->return_last);
                if (0==f->do_ret)
                    return 0;
                for (i = 0; i <256; i++)
                    f->return_number[i] = !(f->return_number[i]);
                return 0;
            }
            /* "R:from/to": select range of classes */
            if (2==sscanf (arg, "%d/%d", b, b+1)) {
                if ((b[0]<0)||(b[0]>255)||(b[1]<0)||(b[1]>255)||(b[0]>b[1]))
                    return (f->errlev = EINVAL);
                for (i = b[0]; i <=b[1]; i++)
                    f->return_number[i] = 1;
                f->do_ret = 1;
                return 0;
            }
            /* "R:return": select single return number */
            if (1==sscanf (arg, "%d", b)) {
                f->return_number[b[0]] = 1;
                f->do_ret = 1;
                return 0;
            }
            /* "Rlast": select single return number */
            if (0==strcmp (arg, "last")) {
                f->return_last = 1;
                f->do_ret_last = 1;
                return 0;
            }
            /* otherwise: something's wrong */
            return (f->errlev = EINVAL);

        case 'T':  /* Time interval */
            a[0] = -DBL_MAX; a[1] = DBL_MAX;
            if ((2==sscanf (arg, "%lf/%lf", a, a+1))||
                (1==sscanf (arg, "/%lf",    a+1))   ||
                (1==sscanf (arg, "%lf",     a) )) {
                f->t = a[0];
                f->T = a[1];
                f->do_tbb = 1;
                return 0;
            }
            return (f->errlev = EINVAL);

        case 'Z':  /* Height interval */
            a[0] = -DBL_MAX; a[1] = DBL_MAX;
            if ((2==sscanf (arg, "%lf/%lf", a, a+1))||
                (1==sscanf (arg, "/%lf",    a+1))   ||
                (1==sscanf (arg, "%lf",     a) )) {
                f->z = a[0];
                f->Z = a[1];
                f->do_vbb = 1;
                return 0;
            }
            return (f->errlev = EINVAL);

        default:
            return (f->errlev = EINVAL);
    }

    return (f->errlev = EINVAL);
}





/*********************************************************************/
/**     V L R   S U B S Y S T E M    ( E X P E R I M E N T A L )    **/
/*********************************************************************/




/*********************************************************************/
LAS_VLR *las_vlr_read (LAS *h, int type) {
/*********************************************************************/
    LAS_VLR *self;
    unsigned char buffer[100];
    int ret = 0;
    if (h==0)
        return 0;
    if (0!=type)
        return 0;
    self = calloc (1, sizeof(LAS_VLR));
    if (0==self)
        return 0;
    if (0==h->next_vlr)
        ret = fseeko (h->f, h->header_size, SEEK_SET);
    assert (0==ret);
    h->next_vlr++;

    self->pos = ftello (h->f);
    assert (0==ret);
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
        if (0==self->payload) {
            errno = ENOMEM;
            free (self);
            return 0;
        }
        fread (self->payload, self->payload_size, 1, h->f);
    }
    else
        fseeko (h->f, self->payload_size, SEEK_CUR);
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


/*********************************************************************/
int las_vlr_is_waveform_descriptor (LAS_VLR *self) {
/*********************************************************************/
    if (0==self)
        return 0;
    if (self->record_id < 100)
        return 0;
    if (self->record_id > 355)
        return 0;
    return 1;
}




/*********************************************************************/
LAS_WAVEFORM_DESCRIPTOR las_waveform_descriptor (LAS_VLR *v) {
/*********************************************************************/
    LAS_WAVEFORM_DESCRIPTOR self = {0,0,0,0,0,0,0,0};

    if (! las_vlr_is_waveform_descriptor (v))
        return self;

    self.index             = v->record_id - 99; /* 0 indicates "no waveform available"*/
    self.bits_per_sample   = v->payload[0];
    self.compression_type  = v->payload[1];
    self.number_of_samples = get_unsigned_32 (v->payload, 2);
    self.sample_interval   = get_unsigned_32 (v->payload, 6);
    self.gain              = get_double (v->payload, 10);
    self.offset            = get_double (v->payload, 18);
    self.valid             = 1;
    return self;
}


/*********************************************************************/
int las_vlr_interpret_all (LAS *h, FILE *stream) {
/*********************************************************************/
    size_t i;
    LAS_WAVEFORM_DESCRIPTOR d;
    if (0==h)
        return 1;
    if (0!=h->next_vlr)
        return 2;
    for (i = 0; i < h->number_of_variable_length_records; i++) {
        LAS_VLR *vlr = las_vlr_read (h,0);
        las_vlr_display (vlr, stream);
        if (las_vlr_is_waveform_descriptor(vlr)) {
            d = las_waveform_descriptor (vlr);
            assert (d.valid);
            h->waveform_descriptor[d.index] = d;
            las_waveform_descriptor_display (d, stream);
        }
        las_vlr_free (vlr);
    }
    return 0;
}


/* end of experimental vlr API section */










/*********************************************************************/
/**      P R I N T I N G   A N D   F O R M A T T I N G   A P I      **/
/*********************************************************************/


/*********************************************************************/
struct tm yd2dmy(int y, int d) {
/**********************************************************************
utility function for las_header_display: convert day-of-year to mm+dd.
In general, mktime() from the standard library performs the opposite
operation, but here we trick it into do what we need by utilizing the
normalization feature of the mktine(&buf) call: pass it a struct tm
claiming to be from the d'th of January. where d is the day-of-year,
cf. e.g. http://bytes.com/topic/c/answers/507460-tm_yday-time_t and
http://www.gnu.org/software/libc/manual/html_node/Broken_002ddown-Time.html
**********************************************************************/

    struct tm dmy;

    dmy.tm_year  = y - 1900;
    dmy.tm_mon   = 0;
    dmy.tm_mday  = d;
    dmy.tm_isdst =-1; /* claim that it is unknown */
    dmy.tm_hour  = 0;
    dmy.tm_min   = 0;
    dmy.tm_sec   = 0;

    if (mktime (&dmy) != -1)
        return dmy;

    /* if garbage in, give garbage out: return 9999-13-32 */
    dmy.tm_year = 9999-1900;
    dmy.tm_mon  = 12;
    dmy.tm_mday = 32;
    return dmy;
}







/*********************************************************************/
void las_record_display (const LAS *h, FILE *stream) {
/*********************************************************************/
    double x = las_x (h);
    double y = las_y (h);
    double z = las_z (h);
    double t = las_gps_time (h);
    double i = las_intensity (h);
    unsigned long    n = las_record_number (h);

    fprintf (stream, "%10lu %15.*f %15.*f %15.*f %8.6f %16.8f\n",
                n, h->nx, x, h->ny, y, h->nz, z, i, t);
    return;
}




/*********************************************************************/
void las_header_display (const LAS *h, FILE *stream) {
/*********************************************************************/
    /* we turn the last 8 bytes of the UUID into 2 shorts and a long to make it printable as an UUID */
    /* TODO: do the right thing on big-endian platforms */
    short suuid1 = *(short *)(((char *) h) + offsetof(LAS, project_id_4));
    short suuid2 = *(short *)(((char *) h) + offsetof(LAS, project_id_4) + 2);
    long  luuid  = *(long  *)(((char *) h) + offsetof(LAS, project_id_4) + 4);
    struct tm dmy;
    int d, m, y;

    assert (h!=0);
    assert (stream!=0);

    dmy = yd2dmy (h->file_creation_year, h->file_creation_day_of_year);
    d = dmy.tm_mday;
    m = dmy.tm_mon + 1;
    y = dmy.tm_year + 1900;

    fprintf (stream, "LAS header entries\n");

    fprintf (stream, "%40s  %.4s\n", "file signature:",  h->signature);
    fprintf (stream, "%40s  %u\n", "file source ID:",    h->file_source_id);
    fprintf (stream, "%40s  %u\n", "global_encoding:",   h->global_encoding);

    fprintf (stream, "%40s  %.8x-%.4x-%.4x-%.4x-%.4x%.8x\n", "project id:",
                   (unsigned int) h->project_id_1,  h->project_id_2,  h->project_id_3,  suuid1, suuid2, (unsigned int) luuid);

    fprintf (stream, "%40s  %d.%d\n",  "version:",  h->version_major, h->version_minor);

    fprintf (stream, "%40s  %.32s\n",  "system identifier:",        h->system_id);
    fprintf (stream, "%40s  %.32s\n",  "generating software:",      h->generated_by);

    fprintf (stream, "%40s  %4.4d-%2.2d-%2.2d\n",  "file creation date:", y, m, d);
    fprintf (stream, "%40s  %u\n",     "header size:",                   h->header_size);
    fprintf (stream, "%40s  %u\n",    "offset to point data:",           (unsigned int) h->offset_to_point_data);
    fprintf (stream, "%40s  %u\n",    "number of var. length records:",  (unsigned int) h->number_of_variable_length_records);
    fprintf (stream, "%40s  %d\n",     "point data format:",             h->point_data_format);
    fprintf (stream, "%40s  %u\n",     "point data record length:",      h->point_data_record_length);
    fprintf (stream, "%40s  %u\n",    "number of point records:",        (unsigned int) h->number_of_point_records);
    /* fprintf (stream, "%-40s  %f\n", "number of points by return:" 2087467 10 0 0 0 */

    fprintf (stream, "%40s  %15g %15g %15g\n",     "scale factor x y z:", h->x_scale, h->y_scale, h->z_scale);
    fprintf (stream, "%40s  %15f %15f %15f\n",     "offset x y z:",       h->x_offset, h->y_offset, h->z_offset);

    fprintf (stream, "%40s  %15f %15f %15f\n", "min x y z:",  h->x_min, h->y_min, h->z_min);
    fprintf (stream, "%40s  %15f %15f %15f\n", "max x y z:",  h->x_max, h->y_max, h->z_max);
}


/*********************************************************************/
void las_vlr_display (LAS_VLR *v, FILE *stream) {
/*********************************************************************/
    if (0==v)
        return;
    if (0==stream)
        return;
    fprintf (stream, "%-16s(%5.5d,%5.5d): %6d bytes. %32s\n",
        v->user_id,
        (int) v->record_id,
        (int) v->reserved,
        (int) v->payload_size,
        v->description
    );
}


/*********************************************************************/
void las_waveform_descriptor_display (LAS_WAVEFORM_DESCRIPTOR wd, FILE *stream) {
/*********************************************************************/
    fprintf (stream, "index: %3.3u,  bits: %2.2u,  comp: %2.2u,  samples: %4.4lu,  interval: %4.4lu, gain: %g, offset: %g\n",
        wd.index,
        wd.bits_per_sample,
        wd.compression_type,
        wd.number_of_samples,
        wd.sample_interval,
        wd.gain,
        wd.offset
    );
}


/*********************************************************************/
void las_waveform_metadata_display (LAS_WAVEFORM_METADATA wd, FILE *stream) {
/*********************************************************************/
    fprintf (stream, "index: %3.3u,  loc(t): %g,  xyz_t: %20.10g %20.10g %20.10g\n",
        wd.descriptor_index,
        wd.return_point_location,
        wd.x_t,
        wd.y_t,
        wd.z_t
    );
}





/*********************************************************************/
void las_vlr_display_all (LAS *h, FILE *stream) {
/*********************************************************************/
    long long pos;
    unsigned int i;
    if (0==h)
        return;
    if (0==stream)
        return;

    pos = ftello (h->f);
    fseeko (h->f, h->header_size, SEEK_SET);
    for (i = 0; i < h->number_of_variable_length_records; i++) {
        LAS_VLR *vlr = las_vlr_read (h, 0);
        las_vlr_display (vlr, stream);
        las_vlr_free (vlr);
    }

    /* clean up */
    fseeko (h->f, pos, SEEK_SET);
}

#endif /* __SLASH_H */













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

    las_header_display (h, stderr);

    while  (las_read (h)) {
        if (i==target) {
            las_record_display (h, stdout);
            target *= 10;
        }
        h->class_histogram[las_class (h)]++;
        i++;
    }

    printf ("records read = %d\n", i);

    /* print class histogram */
    for (i=0; i<256; i++)
        if (h->class_histogram[i])
            printf ("h[%3.3d] = " I64FMT "\n", i, (long long) h->class_histogram[i]);

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
    printf ("get_double: %f\n", get_double(&d, 0));

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

