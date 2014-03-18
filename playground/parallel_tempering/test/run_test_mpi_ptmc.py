import os
import tempfile
import numpy as np
import unittest
import logging

def read_Visits(fname):
    """HACKED"""
    data = np.genfromtxt(fname, delimiter='\t')
    return data[:,0], data[:,1]

class ParallelTemperingTest(unittest.TestCase):
    
    def test_heat_capacity(self):
        self.ndim=3
        self.nprocs=4
        self.dir = os.getcwd()
        self.cmd='mpiexec -n {0} python {1}/test_mpi_ptmc.py'.format(self.nprocs,self.dir)
        # create a temporary directory using the context manager
        tmpdir=tempfile.mkdtemp()
        print('created temporary directory', tmpdir)
        os.chdir(tmpdir)
        os.system(self.cmd)
        resdir = tmpdir+'/ptmc_results'
        os.chdir(resdir)
        temperatures = np.genfromtxt('temperatures', delimiter='\t')
        for i in xrange(self.nprocs):
            d = resdir+'/{}'.format(i)
            pre = 'Visits.his.'
            files = os.listdir(d)
            ftlist = []
            for s in files:
                if pre in s:
                    ftlist.append(s)
            timel = []
            for s in ftlist:
                t = float(s[len(pre):])
                timel.append(t)
            max_t = np.amax(timel)
            
            ener, hist = read_Visits(d+'/'+pre+'{}'.format(max_t))
            
            T = temperatures[i]
            
            average = np.average(ener,weights=hist)
                        
            average2 = np.average(np.square(ener),weights=hist)
                        
            cv =  (average2 - average**2)/(T**2) + float(self.ndim)/2
                        
            self.assertLess(cv-self.ndim,0.001,'failed for replica of rank {}'.format(i))
            
if __name__ == "__main__":
    logging.basicConfig(filename='ParallelTempering.log',level=logging.DEBUG)  
    unittest.main()
        
                
            
              
                
                
                