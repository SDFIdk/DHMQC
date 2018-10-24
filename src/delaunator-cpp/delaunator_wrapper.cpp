# Copyright (c) 2018, Danish Agency for Data Supply and Efficiency <sdfe@sdfe.dk>
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

#include "delaunator.hpp"
#include <stdlib.h> // for malloc/free

#ifdef _WIN32
    #define SHARED_EXPORT __declspec(dllexport)
#else
    #define SHARED_EXPORT
#endif

extern "C" {
    SHARED_EXPORT void triangulate(unsigned long long num_vertices, double *vertices, int *ptr_num_faces, int **ptr_faces)
    {
        std::vector<double> coords;
        
        //TODO can the vector be constructed directly from the pointer?
        for (unsigned long long i = 0; i < num_vertices; i++)
        {
            coords.push_back(vertices[2*i + 0]);
            coords.push_back(vertices[2*i + 1]);
        }
        
        // Actually perform triangulation
        delaunator::Delaunator triangulation(coords);
        
        int num_faces = triangulation.triangles.size() / 3;
        int *faces = (int *)malloc(num_faces * 3 * sizeof(int));
        
        for (int i = 0; i < num_faces; i++)
        {
            faces[3*i + 0] = triangulation.triangles[3*i + 0];
            faces[3*i + 1] = triangulation.triangles[3*i + 1];
            faces[3*i + 2] = triangulation.triangles[3*i + 2];
        }
        
        *ptr_faces = faces;
        *ptr_num_faces = num_faces;
    }
    
    SHARED_EXPORT void free_face_data(int **ptr_faces)
    {
        free(*ptr_faces);
        *ptr_faces = NULL;
    }
}