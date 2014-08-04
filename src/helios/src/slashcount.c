/* minimal example of using slash-h */
/* Thomas Knudsen, 2014 */

#include "../include/slash.h"

int main (int argc, char **argv) {
    LAS *h;
    long n = 0;

    h = las_open (argv[1], "rb");
    while  (las_read (h))
        n++;
    las_close (h);
    printf ("%s: %ld records\n", argv[1], n);

    return 0;
}
