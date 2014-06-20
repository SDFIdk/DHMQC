/* minimal example of using slash-h */
/* Thomas Knudsen, 2013 */

#include "slash.h"

int main (int argc, char **argv) {
    LAS *h;
    double x, y, z;

    h = las_open (argv[1], "rb");
    while  (las_read (h))  {
        x = las_x (h);
        y = las_y (h);
        z = las_z (h);
        printf ("%f %f %f\n", x, y, z);
    }

    las_close (h);
    return 0;
}
