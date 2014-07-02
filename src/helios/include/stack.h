/*********************************************************************
stack.h - stack/memory management template library
    gcc -W -pedantic -Wall -Wextra -DTESTstack -x c -o stack stack.h

This file is part of the Helios bundle.

demo starts at line 220
*********************************************************************
Copyright (c) 1994-2014, Thomas Knudsen <knudsen.thomas@gmail.com>
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
********************************************************************/
#ifndef __STACK_H
#define __STACK_H
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>

/***********************************************************************
    O B J E C T    D E F I N I T I O N   A N D   A L L O C A T I O N
************************************************************************
    (For an intro: skip to section "Fundamental Stack Operators" below)

    The stackable(T) macro expands to a *typedef defining* a
    new type representing a "stack of objects of type 'T'"

    The stack(T) macro expands to *the definition of* a "stack of
    objects of type 'T'"

    The stack_alloc(S, n) macro is the constructor (i.e. memory
    allocator and initializer) for S, being a stack of n objects..

    We need the typedeffing since anonymous structs as function args
    are dubious: try compiling this
    
    struct {int i,j;} foo (struct {double p,r;} a) {
        struct {int i,j;} x = {a.p,a.r}; 
        struct {double p,r;} b =  {a.p,a.r};
        return x;
    }
************************************************************************/
#define __stackable(T) typedef struct {\
    int    errlev;    \
    size_t size;      \
    size_t used;      \
    T     *nil;       \
    T     *data;      \
    T      workspace; \
}

#define stackable(T)            __stackable(T)          *__stack_of_ ## T
#define stackable_unsigned(T)   __stackable(unsigned T) *__stack_of_unsigned_ ## T
#define stackable_struct(T)     __stackable(struct T)   *__stack_of_struct_ ## T
#define stackable_pointer_to(T) __stackable(T *)        *__stack_of_pointers_to_ ## T

#define stack(T)                 __stack_of_ ## T
#define stack_of_unsigned(T)     __stack_of_unsigned_ ## T
#define stack_of_struct(T)       __stack_of_struct_ ## T
#define stack_of_pointers_to(T)  __stack_of_pointers_to_ ## T

/* pre-declare some commonly used cases */
stackable(char);      stackable_unsigned(char);
stackable(short);     stackable_unsigned(short);
stackable(int);       stackable_unsigned(int);
stackable(long);      stackable_unsigned(long);
stackable(size_t);
stackable(float);
stackable(double);
stackable_pointer_to(FILE);


/***********************************************************************
                   M E M O R Y   H A N D L I N G
************************************************************************/
#ifndef stack_growth_factor
#define stack_growth_factor 2
#endif
#ifndef stack_initial_size
#define stack_initial_size 15
#endif

/* the fundamental allocator ("constructor" in OO lingo) */
#define stack_alloc(S,n)                               \
    ((S)           =  calloc(1, sizeof(*(S))),         \
     (S==0)? S : (                                     \
     (S)->data =  calloc (n, sizeof((S)->workspace)),  \
     (S)->size =  (S)->data? n: (errno=ENOMEM), 0,     \
     (S)->used     =  0,                               \
     (S)->errlev   =  ((S)->data? 0: ENOMEM),          \
     (S)->nil      =  (void *) 0,                      \
     (S)))

/* deallocator / destructor.  Note: free(0) is legal C */
#define stack_free(S) \
    do {if (S) free ((S)->data); free (S); } while (0)

/* check whether stack is unallocated or otherwise unsafe */
#define stack_invalid(S) ((!(S)) || ((S)->errlev))

/* return the number of slots currently allocated for the stack */
#define stack_size(S)  (S)->size

/* return the number of elements currently remaining on the stack */
#define depth(S) (S)->used

/* pre-allocate n slots on the stack */
#define stack_reserve(S, n)                                      \
do {                                                             \
    void  *__p;                                                  \
    if (stack_invalid(S) || ((n) && ((n) <= (S)->size))) break;  \
    __p = realloc ((S)->data,                                    \
         ((n>(S)->used)? (n): (S)->used)*sizeof((S)->workspace));\
    if (0==__p) {errno = (S)->errlev = ENOMEM; break; }          \
    (S)->data = __p;                                             \
    (S)->size = ((n>(S)->used)? (n): (S)->used);                 \
} while (0)

/* mostly a service routine for push(S,obj) */
#define stack_grow_if_full(S)                                    \
    if (stack_size(S) <= depth(S))                               \
        stack_reserve((S), stack_growth_factor*stack_size(S))


/***********************************************************************
    F U N D A M E N T A L   S T A C K   O P E R A T O R S
************************************************************************
push (stack, value)
    push value onto stack. Expand and/or allocate storage if needed.
push_fast (stack, value)
    push value onto stack. Assume sufficient memory preallocated.
pop (stack)
    return top-of-stack element, shrink stack by one.
drop (stack, n)
    drop n elements from the top of the stack, and return nothing (void)
top (stack)
    return top-of-stack, without modifying stack.
t2p (stack)
    return the next-to-top-of-stack, without modifying stack.
dup (stack)
    duplicate the top-of-stack element and push it onto stack.
exch (stack)
    swap the two topmost elements, return the new top-of-stack
element (stack, address)
    return the element at the given address of stack. The element
    operator can be used on both sides of an "=" sign. Hence:
        element (s, 42) = 37;
        element (s, 42) = element (s, 42) - 7;
        p = element (s, 42);
    will set p = 30
erase (stack, i, n))
    remove n elements from stack, starting with element(stack, i).
    If (i + n) >= depth (stack), remove as many elements as possible,
    making element(stack, i-1) the top of stack.
ppop (stack)
    as pop (stack), but return a pointer-to-element (which will be
    overwritten or moved on next push, so beware!), rather than
    the element itself - hence *ppop(stack) is equivalent to pop(stack).
    Returns stack->nil if stack empty.
ptop (stack)
    as top (stack), but return a pointer-to-element, rather than
    the element itself.
pelement (stack, address)
    as element (stack), but return a pointer-to-element, rather than
    the element itself.
***********************************************************************/
#define element(S, address) (S)->data[address]
#define push(S, value)                          \
    do {if (0==(S))                             \
            stack_alloc(S,stack_initial_size);  \
        if (stack_invalid(S))                   \
            break;                              \
        stack_grow_if_full (S);                 \
        if (stack_invalid(S))                   \
            break;                              \
        element (S, depth(S)++) =  value;       \
    }while (0)
#define push_fast(S) element (S, depth(S)++) =  value
#define pop(S)       element((S), (depth(S)? --depth(S):   0))
#define drop(S,n)   (depth(S) = depth(S) >= n?  depth(S) - n:  0)
#define erase(S,i,n)                                           \
    do {if ((i < 0) || (n < 0) ) {S->errlev = EINVAL; break;}  \
        if (n==0) break;                                       \
        if ((i + (n)) >= depth (S)) {depth (S) = i; break;}        \
        memmove(pelement(S,i), pelement(S,(i+n)),              \
                (depth(S)-(i+1))*sizeof(S->workspace));        \
        depth (S) -= n;                                        \
    } while (0)
#define top(S)       element((S), (depth(S)?   depth(S)-1: 0))
#define t2p(S)       element((S), (depth(S) > 1?   depth(S)-2: 0))
#define dup(S)       push (top(S))
#define exch(S)     (S->workspace = t2p(S), t2p(S) = top (S), top(S) = S->workspace, top(S))

/* Pointer versions */
#define pelement(S, address) ((S)->data+address)
#define ppop(S) (depth(S)? pelement((S), --depth(S)): (S)->nil)
#define ptop(S) (depth(S)? pelement((S), depth(S)-1): (S)->nil)

/***********************************************************************
                    I T E R A T O R S    E T C .
************************************************************************
    "begin" and "end" are iterator targets in the C++ STL sense:
        typedef struct {double temperature, pressure, volume} state;
        stackable (state);
        stack(state) p = 0;
        stack_alloc (p, 15);
        for (p = begin (s);  p != end (s);  p++)
            p->temperature = 273;
***********************************************************************/
#define begin(S)    (pelement((S), 0))
#define end(S)      (pelement((S), depth(S)))
#define stack_sort(S, comparator) qsort (begin (S), depth (S), \
           sizeof ((S)->workspace), comparator)
#endif  /* __STACK_H */



/***********************************************************************
                         U N I T   T E S T S
***********************************************************************/
#ifdef TESTstack
#include <assert.h>

#ifdef yes_really_test_misworking_example_from_introduction
struct {int i,j;} foo (struct {double p,r;} a) {
    struct {int i,j;} x = {a.p,a.r}; 
    struct {double p,r;} b =  {a.p,a.r};
    if (b.p == a.p)
        puts("yup");
    return x;
}
int testfoo (void) {
    struct {double p,r;} a = {37,42};
    struct {int i,j;} as = foo (a);
    printf ("%d %d\n", as.i, as.j);
}
#endif

struct bbox { double n, e, s, w; };
stackable_struct (bbox);

stack_of_struct(bbox) push_bboxes(stack_of_struct(bbox) S) {
    /* push 3 bounding box structs onto stack S */
    struct bbox a = {1,2,3,4}, b = {5,6,7,8}, c = {9,0,1,2};
    push (S,a);
    push (S,b);
    push (S,c);
    return S;
}


int main (void) {
    stack_of_pointers_to (FILE) fop = 0;
    stack_of_unsigned (int) pladder = 0;
    stack_of_struct(bbox) bb;
    stack (int) si;
    FILE *f = 0;
    int i;

    stack_alloc (bb, 4);
    stack_alloc (fop, 15);
    stack_alloc (pladder, 15);
    stack_alloc (si, 15);

    push_bboxes (bb);
    assert (depth(bb)==3);        assert (top(bb).n==9);
    drop (bb,2);                  assert (top(bb).n==1);
    stack_reserve (bb, 10101);    assert (stack_size(bb)==10101);

    for (i = 0; i < 15000; i++) {
        push (bb, top(bb));
        top(bb).e++;
    }
    assert (depth (bb)==15001);

    push (pladder, 0);
    push (pladder, 1);
    push (pladder, 2);
    push (pladder, 3);
    assert (element(pladder,1)==1);
    erase (pladder,0,1);
    assert (element(pladder,1)==2);
    i = pop (pladder);
    assert (top(pladder)==2);
    
    push (fop, f);
    assert (top(fop)==f);
    top(fop)++;
    assert (top(fop)==f+1);
    stack_free (fop);
    stack_free (pladder);
    stack_free (si);
    return 0;
}
#endif
