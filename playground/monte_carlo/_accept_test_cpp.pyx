cimport cython
import sys
from libcpp cimport bool as cbool
from _pele_mc cimport cppAcceptTest,_Cdef_AcceptTest

#===============================================================================
# Metropolis acceptance criterion
#===============================================================================

cdef extern from "pele/accept_test.h" namespace "pele":
    cdef cppclass cppMetropolisTest "pele::MetropolisTest":
        cppMetropolisTest() except +

cdef class _Cdef_Metropolis(_Cdef_AcceptTest):
    """This class is the python interface for the c++ pele::MetropolisTest acceptance test class implementation
    """
    def __cinit__(self):
        self.thisptr = <cppAcceptTest*>new cppMetropolisTest()
        
        
class MetropolisTest(_Cdef_Metropolis):
    """This class is the python interface for the c++ Metropolis implementation.
    """