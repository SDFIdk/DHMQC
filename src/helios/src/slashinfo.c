#include "../include/slash.h"
int main (int argc, char **argv) {
    assert (argc==2);
    return (las_header_display (las_open (argv[1], "rb"), stdout),1);
}
