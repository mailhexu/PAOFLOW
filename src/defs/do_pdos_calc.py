#
# AFLOWpi_TB
#
# Utility to construct and operate on TB Hamiltonians from the projections of DFT wfc on the pseudoatomic orbital basis (PAO)
#
# Copyright (C) 2016 ERMES group (http://ermes.unt.edu)
# This file is distributed under the terms of the
# GNU General Public License. See the file `License'
# in the root directory of the present distribution,
# or http://www.gnu.org/copyleft/gpl.txt .
#
#
# References:
# Luis A. Agapito, Andrea Ferretti, Arrigo Calzolari, Stefano Curtarolo and Marco Buongiorno Nardelli,
# Effective and accurate representation of extended Bloch states on finite Hilbert spaces, Phys. Rev. B 88, 165127 (2013).
#
# Luis A. Agapito, Sohrab Ismail-Beigi, Stefano Curtarolo, Marco Fornari and Marco Buongiorno Nardelli,
# Accurate Tight-Binding Hamiltonian Matrices from Ab-Initio Calculations: Minimal Basis Sets, Phys. Rev. B 93, 035104 (2016).
#
# Luis A. Agapito, Marco Fornari, Davide Ceresoli, Andrea Ferretti, Stefano Curtarolo and Marco Buongiorno Nardelli,
# Accurate Tight-Binding Hamiltonians for 2D and Layered Materials, Phys. Rev. B 93, 125137 (2016).
#
import numpy as np
import cmath
import sys, time

from mpi4py import MPI
from mpi4py.MPI import ANY_SOURCE
from load_balancing import *

# initialize parallel execution
comm=MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

def do_pdos_calc(E_k,emin,emax,delta,v_k,nk1,nk2,nk3,nawf,ispin):
    # PDOS calculation with gaussian smearing
    emin = float(emin)
    emax = float(emax)
    emax = float(emax) 
    de = (emax-emin)/1000
    ene = np.arange(emin,emax,de,dtype=float)
    nktot = nk1*nk2*nk3
    # Load balancing
    ini_ik, end_ik = load_balancing(size,rank,nktot)

    nsize = end_ik-ini_ik
    pdos = np.zeros((nawf,ene.size),dtype=float)
    for m in range(nawf):

        v_kaux = np.zeros((nsize,nawf,nawf,ispin+1),dtype=complex)
        E_kaux = np.zeros((nsize,nawf),dtype=float)

        comm.Barrier()
        comm.Scatter(E_k,E_kaux,root=0)
        comm.Scatter(v_k,v_kaux,root=0)

        pdosaux = np.zeros((nawf,ene.size),dtype=float)
        pdossum = np.zeros((nawf,ene.size),dtype=float)
        for n in range (nsize):
            for i in range(nawf):
                pdosaux[i,:] += 1.0/np.sqrt(np.pi)*np.exp(-((ene[:]-E_kaux[n,m])/delta)**2)/delta*(np.abs(v_kaux[n,i,m,ispin])**2)

        comm.Barrier()
        comm.Reduce(pdosaux,pdossum,op=MPI.SUM)
        pdos = pdos+pdossum

    pdos = pdos/float(nktot)

    if rank == 0:
        pdos_sum = np.zeros(ene.size,dtype=float)
        for m in range(nawf):
            pdos_sum += pdos[m]
            f=open(str(m)+'_pdos_'+str(ispin)+'.dat','w')
            for ne in range(ene.size):
                f.write('%.5f  %.5f \n' %(ene[ne],pdos[m,ne]))
            f.close()
        f=open('pdos_sum'+str(ispin)+'.dat','w')
        for ne in range(ene.size):
            f.write('%.5f  %.5f \n' %(ene[ne],pdos_sum[ne]))
        f.close()



    return
