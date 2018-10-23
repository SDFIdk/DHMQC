#include "delaunator.hpp"
#include <stdlib.h> // for malloc/free

#ifdef _WIN32
    #define SHARED_EXPORT __declspec(dllexport)
#else
    #define SHARED_EXPORT
#endif

extern "C" {
    SHARED_EXPORT void triangulate(unsigned long long num_vertices, double *vertices, unsigned long long *ptr_num_faces, unsigned long long **ptr_faces)
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
        
        unsigned long long num_faces = triangulation.triangles.size() / 3;
        unsigned long long *faces = (unsigned long long *)malloc(num_faces * 3 * sizeof(unsigned long long));
        
        for (unsigned long long i = 0; i < num_faces; i++)
        {
            faces[3*i + 0] = triangulation.triangles[3*i + 0];
            faces[3*i + 1] = triangulation.triangles[3*i + 1];
            faces[3*i + 2] = triangulation.triangles[3*i + 2];
        }
        
        *ptr_faces = faces;
        *ptr_num_faces = num_faces;
    }
    
    SHARED_EXPORT void free_face_data(unsigned long long **ptr_faces)
    {
        free(*ptr_faces);
        *ptr_faces = NULL;
    }
}