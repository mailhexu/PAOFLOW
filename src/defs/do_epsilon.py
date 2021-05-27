# 
# PAOFLOW
#
# Utility to construct and operate on Hamiltonians from the Projections of DFT wfc on Atomic Orbital bases (PAO)
#
# Copyright (C) 2016-2018 ERMES group (http://ermes.unt.edu, mbn@unt.edu)
#
# Reference:
# M. Buongiorno Nardelli, F. T. Cerasoli, M. Costa, S Curtarolo,R. De Gennaro, M. Fornari, L. Liyanage, A. Supka and H. Wang,
# PAOFLOW: A utility to construct and operate on ab initio Hamiltonians from the Projections of electronic wavefunctions on
# Atomic Orbital bases, including characterization of topological materials, Comp. Mat. Sci. vol. 143, 462 (2018).
#
# This file is distributed under the terms of the
# GNU General Public License. See the file `License'
# in the root directory of the present distribution,
# or http://www.gnu.org/copyleft/gpl.txt .
#

import numpy as np
from mpi4py import MPI

comm = MPI.COMM_WORLD
rank = comm.Get_rank()

def do_dielectric_tensor ( data_controller, ene ):
  from .constants import LL

  arrays,attributes = data_controller.data_dicts()

  smearing = attributes['smearing']
  if smearing != None and smearing != 'gauss' and smearing != 'm-p':
    if rank == 0:
      print('%s Smearing Not Implemented.'%smearing)
    quit()

  d_tensor = arrays['d_tensor']

  for ispin in range(attributes['nspin']):
    for n in range(d_tensor.shape[0]):
      ipol = d_tensor[n][0]
      jpol = d_tensor[n][1]

      epsi, epsr, jdos = do_epsilon(data_controller, ene, ispin, ipol, jpol)

      indices = (LL[ipol], LL[jpol], ispin)

      fepsi = 'epsi_%s%s_%d.dat'%indices
      data_controller.write_file_row_col(fepsi, ene, epsi)

      fjdos = 'jdos_%s%s_%d.dat'%indices
      data_controller.write_file_row_col(fjdos, ene, jdos)

      if epsr is not None:
        fepsr = 'epsr_%s%s_%d.dat'%indices
        data_controller.write_file_row_col(fepsr, ene, epsr)
    
  if rank == 0 and attributes['metal']:
    renorm = np.sqrt((1./np.pi)*(ene[3]-ene[2])*np.sum(epsi*ene))
    print(ipol,jpol,' plasmon frequency = ',renorm,' eV')
#    print(' integration over JDOS = ', (ene[3]-ene[2])*np.sum(jdos))


def do_epsilon ( data_controller, ene, ispin, ipol, jpol ):

  # Compute the dielectric tensor

  arrays,attributes = data_controller.data_dicts()

  esize = ene.size
  if ene[0] == 0.:
    ene[0] = .00001

  #=======================
  # Im
  #=======================
  epsi_aux,jdos_aux = epsi_loop(data_controller, ene, ispin, ipol, jpol)

  epsi = np.zeros(esize, dtype=float)
  comm.Allreduce(epsi_aux, epsi, op=MPI.SUM)
  epsi_aux = None

  jdos = np.zeros(esize, dtype=float)
  comm.Allreduce(jdos_aux, jdos, op=MPI.SUM)
  jods_aux = None

  #=======================
  # Re
  #=======================
  epsr_aux = epsr_kramerskronig(data_controller, ene, epsi)

  epsr = np.zeros(esize, dtype=float)
  comm.Allreduce(epsr_aux, epsr, op=MPI.SUM)
  epsr_aux = None

  epsr += 1.0

  return(epsi, epsr, jdos)


def epsi_loop ( data_controller, ene, ispin, ipol, jpol):
  from .constants import EPS0, EVTORY
  from .smearing import intgaussian,gaussian,intmetpax,metpax

### What is this?
  orig_over_err = np.geterr()['over']
  np.seterr(over='raise')

  arrays,attributes = data_controller.data_dicts()

  esize = ene.size
  bnd = attributes['bnd']
  temp = attributes['temp']
  delta = attributes['delta']
  deltaint = attributes['deltaint']
  snktot = arrays['pksp'].shape[0]
  smearing = attributes['smearing']

  Ef = 0.
  eps=1.e-8
  kq_wght = 1./attributes['nkpnts']

  jdos = np.zeros(esize, dtype=float)
  epsi = np.zeros(esize, dtype=float)

  fn = None
  if smearing == None:
    fn = 1./(1.+np.exp(arrays['E_k'][:,:bnd,ispin]/temp, dtype=np.float128))
#    fn = 1./(1.+np.exp(arrays['E_k'][:,:bnd,ispin]/delta, dtype=np.float128))
  elif smearing == 'gauss':
    fn = intgaussian(arrays['E_k'][:,:bnd,ispin], Ef, arrays['deltakp'][:,:bnd,ispin])
  elif smearing == 'm-p':
    fn = intmetpax(arrays['E_k'][:,:bnd,ispin], Ef, arrays['deltakp'][:,:bnd,ispin])

  '''upper triangle indices'''
  uind = np.triu_indices(bnd, k=1)
  ni = len(uind[0])

  # E_kn-Ek_m for every k-point and every band combination (m,n)
  E_diff_nm = (np.reshape(arrays['E_k'][:,:bnd,ispin],(snktot,1,bnd))-np.reshape(arrays['E_k'][:,:bnd,ispin],(snktot,bnd,1)))[:,uind[0],uind[1]]

  # fn_n-fn_m for every k-point and every band combination (m,n)
  f_nm = (np.reshape(fn,(snktot,bnd,1))-np.reshape(fn,(snktot,1,bnd)))[:,uind[0],uind[1]]
  fn = None

  # <p_n|p_m> for every k-point and every band combination (m,n)
  pksp2 = arrays['pksp'][:,ipol,uind[0],uind[1],ispin]*arrays['pksp'][:,jpol,uind[1],uind[0],ispin]
  pksp2 = (abs(pksp2) if smearing is None else np.real(pksp2))

  sq2_dk2 = (1.0/(np.sqrt(np.pi)*arrays['deltakp2'][:,uind[0],uind[1],ispin]) if smearing=='gauss' else None)

  for i,e in enumerate(ene):
    if smearing is None:
      dfunc = np.exp(-((e-E_diff_nm)/delta)**2)/(delta*np.sqrt(np.pi))
    elif smearing == 'gauss':
      dfunc = np.exp(-((e-E_diff_nm)/arrays['deltakp2'][:,uind[0],uind[1],ispin])**2)*sq2_dk2
    elif smearing == 'm-p':
      dfunc = metpax(E_diff_nm, e, arrays['deltakp2'][:,uind[0],uind[1],ispin])
    epsi[i] = np.sum(dfunc*f_nm*pksp2/(e**2+delta**2))
    jdos[i] = np.sum(dfunc*f_nm)

  f_nm = dfunc = uind = pksp2 = sq2_dk2 = E_diff_nm = None

  if attributes['metal']:
    fnF = None
    if smearing is None:
      fnF = np.empty((snktot,bnd), dtype=float)
      for n in range(bnd):
        for i in range(snktot):
          try:
            fnF[i,n] = .5/(1.+np.cosh(arrays['E_k'][i,n,ispin]/deltaint))
          except:
            fnF[i,n] = 1e8
      fnF /= temp
#      fnF /= delta
    elif smearing == 'gauss':
### Why .03* here?
      fnF = gaussian(arrays['E_k'][:,:bnd,ispin], Ef, arrays['deltakp'][:,:bnd,ispin])
    elif smearing == 'm-p':
      fnF = metpax(arrays['E_k'][:,:bnd,ispin], Ef, arrays['deltakp'][:,:bnd,ispin])

    diag_ind = np.diag_indices(bnd)

    pksp2 = arrays['pksp'][:,ipol,diag_ind[0],diag_ind[1],ispin]*arrays['pksp'][:,jpol,diag_ind[0],diag_ind[1],ispin]

    fnF *= (abs(pksp2) if smearing is None else np.real(pksp2))

    sq2_dk1 = (1./(np.sqrt(np.pi)*arrays['deltakp'][:,:bnd,ispin]) if smearing=='gauss' else None)

    pksp2 = None

    for i,e in enumerate(ene):
      if smearing is None:
        E_diff_nn = (np.reshape(arrays['E_k'][:,:bnd,ispin],(snktot,1,bnd))-np.reshape(arrays['E_k'][:,:bnd,ispin],(snktot,bnd,1)))[:,diag_ind[0],diag_ind[1]]
        dfunc = np.exp(-((e-E_diff_nn)/delta)**2)/(delta*np.sqrt(np.pi))
      elif smearing == 'gauss':
        dfunc = np.exp(-(e/arrays['deltakp'][:,:bnd,ispin])**2)*sq2_dk1
      elif smearing == 'm-p':
        dfunc = metpax(0., e, arrays['deltakp'][:,:bnd,ispin])
      epsi[i] += np.sum(dfunc*fnF/e)

    fnF = sq2_dk1 = diag_ind = None

  epsi *= 4.0*np.pi*kq_wght/(EPS0 * EVTORY * attributes['omega'])
#  epsi *= (16.0 * RYTOEV * np.pi * kq_wght / (attributes['omega'])) * (RYTOEV / attributes['alat'])
  jdos *= kq_wght

  np.seterr(over=orig_over_err)
  return(epsi, jdos)

def epsr_kramerskronig ( data_controller, ene, epsi ):
  from .smearing import intmetpax
  from scipy.integrate import simps
  from .communication import load_balancing

  arrays,attributes = data_controller.data_dicts()

  esize = ene.size
  de = ene[1] - ene[0]

  epsr = np.zeros(esize, dtype=float)

  ini_ie,end_ie = load_balancing(comm.Get_size(), rank, esize)

  # Range checks for Simpson Integrals
  if end_ie == ini_ie:
    return
  if ini_ie < 3:
    ini_ie = 3
  if end_ie == esize:
    end_ie = esize-1

  f_ene = intmetpax(ene, attributes['shift'], 1.)
  for ie in range(ini_ie, end_ie):
    I1 = simps(ene[1:(ie-1)]*de*epsi[1:(ie-1)]*f_ene[1:(ie-1)]/(ene[1:(ie-1)]**2-ene[ie]**2))
    I2 = simps(ene[(ie+1):esize]*de*epsi[(ie+1):esize]*f_ene[(ie+1):esize]/(ene[(ie+1):esize]**2-ene[ie]**2))
    epsr[ie] = 2.*(I1+I2)/np.pi

  return epsr
