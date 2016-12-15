#
# PAOpy
#
# Utility to construct and operate on Hamiltonians from the Projections of DFT wfc on Atomic Orbital basis (PAO)
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
from scipy import fftpack as FFT
from numpy import fft as NFFT
import numpy as np
import cmath
import sys, time
from mpi4py import MPI
import pyfftw
import multiprocessing

sys.path.append('./')

from zero_pad import *

comm=MPI.COMM_WORLD
size = comm.Get_size()

nthread = size

def do_double_grid(nfft1,nfft2,nfft3,HRaux):
    # Fourier interpolation on extended grid (zero padding)
    if HRaux.shape[0] != 3 and HRaux.shape[1] == HRaux.shape[0]:
        nawf,nawf,nk1,nk2,nk3,nspin = HRaux.shape
        nk1p = nfft1
        nk2p = nfft2
        nk3p = nfft3
        nfft1 = nfft1-nk1
        nfft2 = nfft2-nk2
        nfft3 = nfft3-nk3
        nktotp= nk1p*nk2p*nk3p

        # Extended R to k (with zero padding)
        Hksp  = np.zeros((nk1p,nk2p,nk3p,nawf,nawf,nspin),dtype=complex)
        aux = np.zeros((nk1,nk2,nk3),dtype=complex)

        scipy = False
        for ispin in xrange(nspin):
            if not scipy:
                for i in xrange(nawf):
                    for j in xrange(nawf):
                        aux = HRaux[i,j,:,:,:,ispin]
                        fft = pyfftw.FFTW(zero_pad(aux,nk1,nk2,nk3,nfft1,nfft2,nfft3),Hksp[:,:,:,i,j,ispin], axes=(0,1,2), direction='FFTW_FORWARD',\
                                flags=('FFTW_MEASURE', ), threads=nthread, planning_timelimit=None )
                        Hksp[:,:,:,i,j,ispin] = fft()
            else:
                for i in xrange(nawf):
                    for j in xrange(nawf):
                        aux = HRaux[i,j,:,:,:,ispin]
                        Hksp[:,:,:,i,j,ispin] = FFT.fftn(zero_pad(aux,nk1,nk2,nk3,nfft1,nfft2,nfft3))

    else:
        sys.exit('wrong dimensions in input array')

    nk1 = nk1p
    nk2 = nk2p
    nk3 = nk3p
    aux = None
    return(Hksp,nk1,nk2,nk3)

