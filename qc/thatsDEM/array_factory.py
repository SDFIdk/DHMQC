# Copyright (c) 2015, Danish Geodata Agency <gst@gst.dk>
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
#
###################
# Factory functions for creating arrays of the right type which can safely be passed on to c-functions
# np.float64 <-> double
# np.float32 <-> float
# np.int32   <->  int  (on some platforms)
# np.bool     <-> char
#####################
import numpy as np

# These functions should not copy data when input is ok....


def point_factory(xy):
    xy = np.asarray(xy)
    if xy.ndim < 2:  # TODO: also if shape[1]!=2
        n = xy.shape[0]
        if n % 2 != 0:
            raise TypeError("Input must have size n*2")
        xy = xy.reshape((int(n / 2), 2))
    return np.require(xy, dtype=np.float64, requirements=[
                      'A', 'O', 'C'])  # aligned, own_data, c-contiguous


def z_factory(z):
    return np.require(z, dtype=np.float64, requirements=['A', 'O', 'C'])


def int_array_factory(I):
    if I is None:
        return None
    I = np.asarray(I)
    if I.ndim > 1:
        I = np.flatten(I)
    return np.require(I, dtype=np.int32, requirements=['A', 'O', 'C'])
