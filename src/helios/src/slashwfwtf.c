#include "../include/slash.h"



int main (int argc, char **argv) {
    LAS *h;
    size_t r = 0, skip = 0, i, n, read = 10;
    long long *histo;
    int u16test;

    u16test = get_unsigned_16 ("..AB",2);
    printf ("u16test: %d  %d\n", u16test, 256*66+65);

    assert (argc > 1);

    /* open las file for reading */
    h = las_open (argv[1], "rb");
    assert (h!=0);

    if (argc > 2)
        skip = atoll (argv[2]);
    if (argc > 3)
        read = atoll (argv[3]);

    histo = calloc (65536, sizeof(long long));
    assert (0!=histo);


    /* show general information */
    las_header_display (h, stderr);
    las_vlr_interpret_all (h, stderr);

    /* skip first records */
    las_seek (h, skip, SEEK_SET);

    /* loop over remaining records - extract data */
    while  (las_read (h))  {
        if ((read != 0) && (r >= read))
            break;
        r++;

        las_waveform_read (h);
        printf ("%p\n", (void *) h->waveform_metadata.offset_to_data);

        n = las_waveform_read (h);
        for (i = 0;  i < n; i++) {
            LAS_WAVEFORM_SAMPLE s = las_waveform_sample (h, i);
            long long intensity;
            assert (s.valid);
            intensity = s.intensity;
            assert (intensity >= 0);
            assert (intensity < 65536);
            histo[intensity]++;
        }
    }

    for (i = 0;  i < 65536; i++)
        if (0!=histo[i])
            printf ("histo %5d    %10ld\n", (int) i, (long) histo[i]);
    las_close (h);
    return 0;
}
