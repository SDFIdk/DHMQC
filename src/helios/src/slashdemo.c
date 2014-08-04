#include "../include/slash.h"



int main (int argc, char **argv) {
    LAS *h;
    size_t r = 0, read = 10, skip = 0;

    assert (argc > 1);

    /* open las file for reading */
    h = las_open (argv[1], "rb");
    assert (h!=0);

    if (argc > 2)
        skip = atoll (argv[2]);
    if (argc > 3)
        read = atoll (argv[3]);


    /* show general information */
    las_header_display (h, stdout);
    las_vlr_interpret_all (h, stdout);
    if (0==read)
        return 0;

    /* skip first records */
    las_seek (h, skip, SEEK_SET);

    /* loop over remaining records - extract data */
    while  (las_read (h))  {
        double x, y, z, t, v;
        int    c;
        size_t i, n;
        if (r >= read)
            break;
        r++;

        x = las_x (h);
        y = las_y (h);
        z = las_z (h);
        t = las_gps_time (h);
        v = las_intensity (h);
        c = las_class (h);
        las_waveform_read (h);
        printf ("\n# %ld  %d  %d  ", (long) h->waveform_metadata.offset_to_data, (int) h->waveform_metadata.packet_size, h->waveform_metadata.descriptor_index);

        las_record_display (h, stdout);
        las_waveform_metadata_display (h->waveform_metadata, stdout);

        /* read (and print) the waveform corresponding to the last record read */
        n = las_waveform_read (h);

        for (i = 0;  i < n; i++) {
            LAS_WAVEFORM_SAMPLE s = las_waveform_sample (h, i);
            assert (s.valid);
            printf ("%4.4d %4.4d %4g %9.1f  %9.3f %9.3f %9.3f\n", (int)r, (int)i, s.intensity, s.time, s.x, s.y, s.z);
        }

        /* (...do what needs to be done...) */
    }



    las_close (h);
    return 0;
}
