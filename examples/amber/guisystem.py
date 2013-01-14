from PyQt4 import QtGui
import NewLJ
import numpy as np

from pygmin.transition_states import dimer, tstools

from amberSystem import AMBERsystem  
 
class systemOuter(AMBERsystem):
    def __init__(self):

        # todo - use this dialog box to get path of coords.prmtop and coords.inpcrd 
#        dlg = NewLJDialog()
#        dlg.exec_()
#        self.natoms = dlg.natoms()
#        if dlg.result() == QtGui.QDialog.Rejected:
#            raise BaseException("Aborted parameter dialog")

        self.natoms = 22 # todo -- 22 is hard coded 
        super(AMBERsystem, self).__init__(self.natoms)
        
    def findTS(self, coords):
        raise NotImplementedError
        pot = self.get_potential()
                
        ret = dimer.findTransitionState(coords+np.random.random(coords.shape)*0.01, pot, zeroEigenVecs=self.zeroEigenVecs, tol=1.e-6)
        m1,m2 = tstools.minima_from_ts(pot.getEnergyGradient, ret.coords, ret.eigenvec, displace=1e-2)
        print "Energies: ", m1[1],ret.energy,m2[1]
        return [ret.coords,ret.energy],m1,m2
    

class NewLJDialog(QtGui.QDialog,NewLJ.Ui_DialogLJSetup):
    def __init__(self):
        QtGui.QDialog.__init__(self)
        self.setupUi(self)
    def natoms(self):
        return int(self.lineNatoms.text())
    def nsave(self):
        return int(self.lineNsave.text())
        
if __name__ == "__main__":
    import pygmin.gui.run as gr
    gr.run_gui(systemOuter)
    
    
    
    