from __future__ import division
import abc
import numpy as np
import random
import os
from mpi4py import MPI
from playground.parallel_tempering import _MPI_Parallel_Tempering

"""
An optimal Parallel Tempering strategy should make sure that all MCMC walks take roughly the same amount of time. 
Besides this fundamental consideration, note that root (rank=0) is not an evil master but rather an enlightened dictator that leads by
example: root is responsible to assign jobs and control parameters (e.g. temperature) to the slaves but it also performs MCMC walks along 
with them. For this reason it might be optimal to give root a set of control parameters for which the simulation is leaner so that it 
can start doing its own things while the slaves finish their work.  
"""

class MPI_PT_RLhandshake(_MPI_Parallel_Tempering):
    """
    This class performs parallel tempering by a right-left handshake: alternates swaps with right and left 
    neighbours with geometrically distributed temperatures.
    """
    def __init__(self, mcrunner, Tmax, Tmin, max_ptiter=10, pfreq=1, verbose=False):
        super(MPI_PT_RLhandshake,self).__init__(mcrunner, Tmax, Tmin, max_ptiter, pfreq=pfreq, verbose=verbose)
        self.exchange_dic = {1:'right',-1:'left'}
        self.exchange_choice = random.choice(self.exchange_dic.keys()) 
        self.anyswap = False #set to true if any swap will happen
        self.permutation_pattern = np.zeros(self.nproc,dtype='int32') #this is useful to print exchange permutations
        
    def _print(self):
        base_directory = "ptmc_results"
        if (self.ptiter == 0 and self.rank == 0):
            if not os.path.exists(base_directory):
                os.makedirs(base_directory)
            fname = "{0}/temperatures".format(base_directory)
            np.savetxt(fname, self.Tarray, delimiter='\t')
        
        if (self.rank == 0 and self.anyswap == True):
            fname = "{0}/rem_permutations".format(base_directory)
            f = open(fname,'a')
            iteration = self.mcrunner.get_iterations_count()
            f.write('{0}\t'.format(iteration))
            for p in self.permutation_pattern:
                f.write('{0}\t'.format(p))
            f.write('\n')
            f.close()
                        
        if (self.ptiter % self.pfreq == 0):
            directory = "{0}/{1}".format(base_directory,self.rank)
            if not os.path.exists(directory):
                os.makedirs(directory)
            iteration = self.mcrunner.get_iterations_count()
            fname = "{0}/Visits.his.{1}".format(directory,float(iteration))
            self.mcrunner.dump_histogram(fname)
        
        if (self.ptiter == self.max_ptiter-1):
            directory = "{0}/{1}".format(base_directory,self.rank)
            fname = "{0}/parameters".format(directory)
            accepted_frac = self.mcrunner.get_accepted_fraction()
            init_stepsize = self.mcrunner.stepsize
            fin_stepsize = self.mcrunner.get_stepsize()
            ncount = self.mcrunner.get_iterations_count()
            f = open(fname,'a')
            f.write('node:\t{0}\n'.format(self.rank))
            f.write('temperature:\t{0}\n'.format(self.T))
            f.write('initial step size:\t{0}\n'.format(init_stepsize))
            f.write('adapted step size:\t{0}\n'.format(fin_stepsize))
            f.write('PT iterations:\t{0}\n'.format(self.ptiter))
            f.write('total MC iterations:\t{0}\n'.format(ncount))
            f.write('acceptance fraction:\t{0}\n'.format(accepted_frac))
            f.close()
            
    
    def _get_temps(self):
        """
        set up the temperatures by distributing them exponentially. We give root the lowest temperature.
        This should increase performance when pair lists are used (they are updated less often at low temperature
        or when steps involve minimisation, as the low temperatures are closer to the minimum)
        """
        if (self.rank == 0):
            CTE = np.exp( np.log( self.Tmax / self.Tmin ) / (self.nproc-1) )
            Tarray = [self.Tmin * CTE**i for i in range(self.nproc)]
            #Tarray = np.linspace(self.Tmin,self.Tmax,num=self.nproc)
            self.Tarray = np.array(Tarray[::-1],dtype='d')
        else:
            self.Tarray = None
    
    def _initialise(self):
        """
        perform all the tasks required prior to starting the computation
        """
        self._get_temps()
        self.config, self.energy = self.mcrunner.get_config()
        self.T = self._scatter_single_value(self.Tarray)
        if self.verbose:
            print "processor {0} temperature {1}".format(self.rank,self.T)
        self.mcrunner.set_control(self.T)
        self.initialised = True
    
    def _find_exchange_buddy(self, Earray):
        """
        This function determines the exchange pattern alternating swaps with right and left neighbours.
        An exchange pattern array is constructed, filled with self.no_exchange_int which
        signifies that no exchange should be attempted. This value is replaced with the
        rank of the processor with which to perform the swap if the swap attempt is successful.
        The exchange partner is then scattered to the other processors.
        """        
        if (self.rank == 0):
            assert(len(Earray)==len(self.Tarray))
            exchange_pattern = np.empty(len(Earray),dtype='int32')
            exchange_pattern.fill(self.no_exchange_int)
            self.anyswap = False
            for i in xrange(0,self.nproc,2):
                if self.verbose:
                    print 'exchange choice: ',self.exchange_dic[self.exchange_choice] #this is a print statement that has to be removed after initial implementation
                E1 = Earray[i]
                T1 = self.Tarray[i]
                E2 = Earray[i+self.exchange_choice]
                T2 = self.Tarray[i+self.exchange_choice]
                deltaE = E1 - E2
                deltabeta = 1./T1 - 1./T2
                w = min( 1. , np.exp( deltaE * deltabeta ) )
                rand = np.random.rand()
                #print "E1 {0} T1 {1} E2 {2} T2 {3} w {4}".format(E1,T1,E2,T2,w) 
                if w > rand:
                    #accept exchange
                    if self.verbose:
                        self.ex_outstream.write("accepting exchange %d %d %g %g %g %g %d\n" % (self.nodelist[i], self.nodelist[i+self.exchange_choice], E1, E2, T1, T2, self.ptiter))
                    assert(exchange_pattern[i] == self.no_exchange_int)                      #verify that is not using the same processor twice for swaps
                    assert(exchange_pattern[i+self.exchange_choice] == self.no_exchange_int) #verify that is not using the same processor twice for swaps
                    exchange_pattern[i] = self.nodelist[i+self.exchange_choice]
                    exchange_pattern[i+self.exchange_choice] = self.nodelist[i]
                    self.anyswap = True
            ############end of for loop###############
            #record self.permutation_pattern to print permutations in print function
            if self.anyswap:
                for i,buddy in enumerate(exchange_pattern):
                    if (buddy != self.no_exchange_int):
                        self.permutation_pattern[i] = buddy+1 #to conform to fortran notation
                    else:
                        self.permutation_pattern[i] = i+1 #to conform to fortran notation
        else:
            exchange_pattern = None
        
        self.exchange_choice *= -1 #swap direction of exchange choice
        #print "exchange_pattern",exchange_pattern
        return exchange_pattern
            
            
            
    
    
    
        
                
            
              
                
                
                