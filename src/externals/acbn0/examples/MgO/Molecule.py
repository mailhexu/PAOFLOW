"""\
 Molecule.py: Simple class for molecules.

 TODO: *Really* need to think of a more intelligent way of handling
 units!

 This program is part of the PyQuante quantum chemistry program suite.

 Copyright (c) 2004, Richard P. Muller. All Rights Reserved. 

 PyQuante version 1.2 and later is covered by the modified BSD
 license. Please see the file LICENSE that is part of this
 distribution. 
"""


'''
PyQuante Backend
================

This backend uses another "Handler" class to take care of format file
parsing, these are FormatHandlers.  Each of them is associated with a
format identifier, and each of them parses a string of the given
format with the same naming convention, read and write (They are
really like StringHandlers, but without the format argument)
'''

import os
from numpy import dot as matrixmultiply
from numpy import zeros
from numpy.linalg import eigh

class Data(object):
    '''
    Handles the information contained in various types of chemical files,
    it can be produced with a FormatHandler
    
    Attributes:
    - molecule: Molecule instance
    - orbitals: 
    - molecules: [Molecule, Molecule, ... ]
    
    '''
    def __init__(self, molecule = None, molecules = None, orbitals = None):
        self.molecule = molecule
        self.molecules = molecules
        self.orbitals = orbitals
    def build_molecule(self, *a, **kw):

        self.molecule = Molecule(*a, **kw)
    def has(self, name):
        '''
        Check if the Data has this kind of information saved.
        '''
        if hasattr(self,name):
            attr = getattr(self,name)
            return attr
        else:
            return False



class Handler(object):
    key = "xyz"
    description = "XYZ File Format"
    ext = ".xyz"
    def read(self,string):
        """
        Arguments:
        
        - string: String to parse
        
        Return:
        
        - data: Data object, with a molecule and a molecules
          attribute.
        """

        geometries = []
        igeo = 1
        lines = string.splitlines()
        while 1:  
            try: 
                line = lines.pop(0)
            except IndexError:
                break
            if not line: break
            nat = int(line.split()[0])
            title = lines.pop(0)
            atoms = []
            for i in xrange(nat):
                line = lines.pop(0)
                words = line.split()
                atno = sym2no[words[0]]
                x,y,z = map(float,words[1:])
                atoms.append((atno,(x,y,z)))
            atoms = Molecule("XYZ geometry #%d" % igeo,atoms)
            igeo += 1
            geometries.append(atoms)
        
        data = Data()
        data.molecule = geometries[0] # First geometry
        data.molecules = geometries
        return data

    def write(self,data):
        ret = ''
        if data.molecules:
            for molecule in data.molecules:
                ret += self.generate_entry(molecule)
        elif data.molecule:
            ret += self.generate_entry(data.molecule)
        else:
            raise ValueError("Nothing to generate")
        return ret
    
    def generate_entry(self,molecule):
        ret = ''
        ret+="%d\n%s\n" % (len(molecule.atoms),"XYZ File generated by PyQuante")
        for atom in molecule.atoms:
            atno,(x,y,z) = atom.atuple()
            ret+=("%4s %10.4f %10.4f %10.4f\n"
                       % (symbol[atno],x,y,z))
        return ret



class StringHandler(object):
    """
    StringHandler is an interface for an object that reads data from a
    string and write data in a string
    """
    def read(self, string, format):
       '''
        Reads data from a string written in a given format

        Parameters:
        - string:
        - format: format identifier, a little string

        Raises:
        - FormatUnsupported exception
       '''
       return NotImplementedError()
    def write(self, data, format):
        '''
        Generates a string from the Data object passed, look at read
        for parameters description
        '''
        return NotImplementedError()
    

class FileHandler(object):
    '''
    This class extends the functionality of the StringHandler and uses
    it to read and write the strings from files.
    
    The difference with the StringHandler is the guess_format method,
    used to guess the format from the filename extension.

    Attributes:
    - string_handler: The string Handler that it uses. It's required!!!
    '''
    def read(self, filename, format=None):
        '''
        Read the content of the file "filename".

        Parameters:
        - filename
        - format: if None (the default) attempts to guess the format

        Return:
        - data: a Data instance.
        '''
        if format==None:
            format = self.guess_format(filename)
        string = open(filename,"r").read()
        return self.string_handler.read(string, format)
    def write(self, filename, data, format=None):
        '''
        Write the data (Data instance) in the file specified.
        '''
        if format==None:
            format = self.guess_format(filename)
        fd = open(filename,"w")
        string = self.string_handler.write( data, format)
        fd.write(string)
        fd.close()
    def guess_format(self,filename):
        '''
        Method used to guess the file format from the extension.
        Return:
        - format: the format key if available.
        Raises:
        - FormatUnsupported
        '''
        raise NotImplementedError()

    
class FormatUnsupported(ValueError):
    '''
    Exception raised when something goes wrong with format recognizing
    '''
    pass





class HandlerList(object):
    def __init__(self,*list):
        self.list = list
    def has_key(self,key):
        for hand in self.list:
            if hand.key == key:
                return True
        return False
    def has_ext(self,ext):
        for hand in self.list:
            if hand.ext == ext:
                return True
        return False
    def by_ext(self,ext):
        for hand in self.list:
            if hand.ext == ext:
                return hand
        raise KeyError()
    def __getitem__(self,key):
        for hand in self.list:
            if hand.key == key:
                return hand
        raise KeyError(key)


format_handlers= HandlerList(Handler)
class PyQuanteStringHandler(StringHandler):
    def read(self, string, format):
        if not format_handlers.has_key(format):
            raise FormatUnsupported("Format %s not supported"%format)
        fh = format_handlers[format]()
        return fh.read(string)
    def write(self, data, format):
        if not format_handlers.has_key(format):
            raise FormatUnsupported("Format %s not supported"%format)
        fh = format_handlers[format]()
        return fh.write(data)
     
class PyQuanteFileHandler(FileHandler):
    def __init__(self):
        self.string_handler=PyQuanteStringHandler()
    def guess_format(self,filename):
        ext = os.path.splitext(filename)[-1]
        if format_handlers.has_ext(ext):
            return format_handlers.by_ext(ext).key
        else:
            raise FormatUnsupported("Can't recognize the format of this file")

class FormatHandler(object):
    '''
    Handler class used to parse a format.

    Attributes:
    - key: Key used to recognize the format
    - ext: Filename extension used to recognize the format
    - description: Format description, used for documenting
    '''
    key = None
    ext = None
    description = None
    def read(self, string):
        '''
        The functionality is the same as the StringHandler,except for
        the absence of the format argument.
        '''
        return NotImplementedError()
    def write(self, data):
       return NotImplementedError()



# Distance units                                                                                   
bohr2ang = 0.529177249  # Conversion of length from bohr to angstrom                               
ang2bohr = 1/bohr2ang

symbol = [
    "X","H","He",
    "Li","Be","B","C","N","O","F","Ne",
    "Na","Mg","Al","Si","P","S","Cl","Ar",
    "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
    "Co", "Ni", "Cu", "Zn",
    "Ga", "Ge", "As", "Se", "Br", "Kr",
    "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru",
    "Rh", "Pd", "Ag", "Cd",
    "In", "Sn", "Sb", "Te", "I", "Xe",
    "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm",  "Eu",
    "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
    "Tl","Pb","Bi","Po","At","Rn"]


sym2no = {}
for i in xrange(len(symbol)):
    sym2no[symbol[i]] = i
    sym2no[symbol[i].lower()] = i



##################################################################################################################################
from numpy import array
#from PyQuante.cints import dist2,dist
#from Element import mass,symbol
#from Constants import bohr2ang

from numpy import *
from numpy.linalg import *
matrixmultiply = dot
    
# still need to kill these two, which are used by Optimize:
#import numpy.oldnumeric.mlab as MLab
#from numpy.oldnumeric import NewAxis
import numpy as Numeric



def dist2(A,B): #needs nothing extra
    return pow(A[0]-B[0],2)+pow(A[1]-B[1],2)+pow(A[2]-B[2],2)

def dist(A,B): return sqrt(dist2(A,B))


mass = [
    0.00,
    1.0008, 4.0026,
    6.941,9.0122,
    10.811,12.011,14.007,15.999,18.998,20.179,
    22.990,24.305,
    26.982,28.086,30.974,32.066,35.453,39.948,
    39.098, 40.078,
    44.9559, 47.867, 50.9415, 51.9961, 54.938, 55.845,
    58.9332, 58.6934, 63.546,65.39,
    69.723, 72.61, 74.9216, 78.96, 79.904, 83.80,
    85.4678, 87.62,
    88.90686, 91.224, 92.90638, 95.94, 98, 101.07,
    102.90550, 106.42, 107.8682, 112.411,
    114.818, 118.710, 121.760, 127.60, 126.90447, 131.29,
    132.90545, 137.327, 138.9055, 140.11, 140.90765, 144.24,
    145.0, 150.36, 151.964,
    157.25, 158.92534, 162.5, 164.93, 167.259, 168.934, 173.04, 174.967,
    178.49, 180.9479, 183.84, 186.207, 190.23, 192.217, 195.078, 196.96655,
    200.59]


# Careful about units! I'm not doing anything about them here;
#  whatever you store you get back.

class Atom:
    def __init__(self,atno,x,y,z,atid=0,fx=0.0,fy=0.0,fz=0.0,vx=0.0,vy=0.0,vz=0.0):
        self.atno = atno
        self.r = array([x,y,z],'d')
        #added by Hatem Helal hhh23@cam.ac.uk
        #atom id defaults to zero so as not to break preexisting code...
        self.atid = atid
        self.f = array([fx,fy,fz],'d')
        self.vel = array([vx,vy,vz],'d')
        return

    def __repr__(self): return "Atom ID: %d Atomic Num: %2d (%6.3f,%6.3f,%6.3f)" % \
        (self.atid,self.atno,self.r[0],self.r[1],self.r[2])
    def __getitem__(self, i):
        return self.r[i]
    def mass(self): return mass[self.atno]
    def pos(self): return tuple(self.r)
    def symbol(self): return symbol[self.atno]
    
    def force(self): return self.f
    def velocity(self): return self.vel
    
    # Could also do the following dists with numpy:
    def dist2(self,atom): return dist2(self.pos(),atom.pos())
    def dist(self,atom): return dist(self.pos(),atom.pos())
    def atuple(self): return (self.atno,self.r)
    def translate(self,pos): self.r += pos

    # The next two I've written as functions since if I ever handle
    #  pseudopotentials I'll need to do something clever, and this
    #  gives me a degree of indirection that will allow me to do this
    def get_nel(self): return self.atno
    def get_nuke_chg(self): return self.atno

    # This is set by the MINDO initialize routine. Will raise
    #  an error otherwise
    def get_nel_mindo(self): return self.Z

    def update_coords(self,xyz): self.r = array(xyz)
    def update_from_atuple(self,(atno,xyz)): self.update_coords(xyz)
    
    def set_force(self,fxfyfz): self.f = array(fxfyfz)
    def set_velocity(self,vxvyvz): self.vel = array(vxvyvz)

    def urotate(self,U):
        "Rotate molecule by the unitary matrix U"

        #self.r = matrixmultiply(self.r,U)
        self.r = matrixmultiply(U,self.r)
        return











###################################################################################################################################


allowed_units = ['bohr','angs']

class Molecule:
    """\
    Molecule(name,atomlist,**opts) - Object to hold molecular data in PyQuante

    name       The name of the molecule
    atomlist   A list of (atno,(x,y,z)) information for the molecule

    Options:      Value   Description
    --------      -----   -----------
    units         Bohr    Units for the coordinates of the molecule
    charge        0       The molecular charge
    multiplicity  1       The spin multiplicity of the molecule
    """
    def __init__(self,name='molecule',atomlist=[],**opts):
        self.name = name
        self.atoms = []
        self.basis = []
        self.grid = None
        units = opts.get('units','bohr')
        units = units.lower()[:4]
        assert units in allowed_units
        self.units = units
        if atomlist: self.add_atuples(atomlist)
        self.charge = int(opts.get('charge',0))
        self.multiplicity = int(opts.get('multiplicity',1))
        return
    # Alternative constructors
    # @classmethod <- python2.4
    def from_file(cls, filename, format=None,name="molecule"):
        hand = FileHandler()
        data = hand.read(filename,format)

        atomlist = [ (at.atno, at.r) for at in data.molecule.atoms ]
        return cls( name, atomlist = atomlist,
                    charge = data.molecule.charge,
                    multiplicity = data.molecule.multiplicity)
    from_file = classmethod(from_file) # old decorator syntax

    def from_string(cls, string, format, name="molecule"):
#        hand = StringHandler()
#        data = hand.read(string,format)
        data=string
        atomlist = [ (at.atno, at.r) for at in data.molecule.atoms ]
        return cls( name, atomlist = atomlist,
                    charge = data.molecule.charge,
                    multiplicity = data.molecule.multiplicity)
    from_string = classmethod(from_string) # old decorator syntax
    def as_string(self,format="xyz"):
        data = Data()
        data.molecule = self
        hand = StringHandler()
        return hand.write(data, format)
    def dump(self,filename, format=None):
        data = Data()
        data.molecule = self
        hand = FileHandler()
        hand.write(filename,data,format)
    def __repr__(self):
        outl = "\n%s: %s" % (self.__class__.__name__,self.name)
        for atom in self.atoms:
            outl += "\n\t%s" % str(atom)
        return outl

    def update_from_atuples(self,geo):
        nat = len(geo)
        assert nat == len(self.atoms)
        for i in xrange(nat):
            self.atoms[i].update_from_atuple(geo[i])
        return

    def update_coords(self,coords):
        nat = len(coords)/3
        assert nat == len(self.atoms)
        for i in xrange(nat):
            self.atoms[i].update_coords(coords[3*i:3*i+3])
        return

    def translate(self,pos):
        for atom in self.atoms: atom.translate(pos)
        return

    def add_atom(self,atom): self.atoms.append(atom)
    
    def add_atuple(self,atno,xyz,atid):
        if self.units != 'bohr': xyz = toBohr(xyz[0],xyz[1],xyz[2])
        if type(atno) == type(''): atno = sym2no[atno]
        self.atoms.append(Atom(atno,xyz[0],xyz[1],xyz[2],atid))

    def add_atuples(self,atoms):
        "Add a list of (atno,(x,y,z)) tuples to the atom list"
        for id,(atno,xyz) in enumerate(atoms):
            self.add_atuple(atno,xyz,id); id+=1
        return

    def atuples(self):
        "Express molecule as a list of (atno,(x,y,z)) tuples"
        atoms = []
        for atom in self.atoms: atoms.append(atom.atuple())
        return atoms

    def atuples_angstrom(self):
        atoms = []
        for atom in self.atoms:
            atno,xyz = atom.atuple()
            atoms.append((atno,toAng(xyz[0],xyz[1],xyz[2])))
        return atoms

    # Not really used. Consider removing
#    def add_xyz_file(self,filename,which_frame=-1):
        "Input atoms from xyz file. By default choose the last frame"
#        from IO import read_xyz
#        geos = read_xyz(filename)
#        self.add_atuples(geos[which_frame])
#        return

    def set_charge(self,charge): self.charge = int(charge)
    def get_charge(self): return self.charge
    
    def set_multiplicity(self,mult): self.multiplicity = int(mult)
    def get_multiplicity(self): return self.multiplicity

    def get_nel(self,charge=None):
        if charge:
            # Deprecation warning inserted 8/2005
            print "Warning: use of get_nel(charge) has been deprecated"
            print "Please supply charge at construction of molecule or use"
            print "mol.set_charge(charge)"
            self.set_charge(charge)
        nel = -self.charge
        for atom in self.atoms: nel += atom.get_nel()
        return nel

    def get_enuke(self):
        enuke = 0.
        nat = len(self.atoms)
        for i in xrange(nat):
            ati = self.atoms[i]
            for j in xrange(i):
                atj = self.atoms[j]
                enuke += ati.get_nuke_chg()*atj.get_nuke_chg()/ati.dist(atj)
        return enuke

    def get_closedopen(self):
        multiplicity = self.multiplicity
        nel = self.get_nel()

        assert multiplicity > 0

        if (nel%2 == 0 and multiplicity%2 == 0) \
               or (nel%2 == 1 and multiplicity%2 == 1):
            print "Incompatible number of electrons and spin multiplicity"
            print "nel = ",nel
            print "multiplicity = ",multiplicity
            raise Exception("Incompatible number of electrons and spin multiplicity")

        nopen = multiplicity-1
        nclosed,ierr = divmod(nel-nopen,2)
        if ierr:
            print "Error in Molecule.get_closedopen()"
            print 'nel = ',nel
            print 'multiplicity = ',multiplicity
            print 'nopen = ',nopen
            print 'nclosed = ',nclosed
            print 'ierr = ',ierr
            raise Exception("Error in Molecule.get_closedopen()")
        return nclosed, nopen

    def get_alphabeta(self,**opts):
        nclosed,nopen = self.get_closedopen(**opts)
        return nclosed+nopen,nclosed

    def com(self):
        "Compute the center of mass of the molecule"

        rcom = zeros((3,),'d')
        mtot = 0
        for atom in self:
            m = atom.mass()
            rcom += m*atom.r
            mtot += m
        rcom /= mtot
        return rcom

    def inertial(self):
        "Transform to inertial coordinates"

        rcom = self.com()
        print "Translating to COM: ",rcom
        self.translate(-rcom)
        I = zeros((3,3),'d')
        for atom in self:
            m = atom.mass()
            x,y,z = atom.pos()
            x2,y2,z2 = x*x,y*y,z*z
            I[0,0] += m*(y2+z2)
            I[1,1] += m*(x2+z2)
            I[2,2] += m*(x2+y2)
            I[0,1] -= m*x*y
            I[1,0] = I[0,1]
            I[0,2] -= m*x*z
            I[2,0] = I[0,2]
            I[1,2] -= m*y*z
            I[2,1] = I[1,2]
        E,U = eigh(I)
        print "Moments of inertial ",E
        self.urotate(U)
        print "New coordinates: "
        print self
        return

    def urotate(self,U):
        "Rotate molecule by the unitary matrix U"
        for atom in self: atom.urotate(U)
        return

    # These two overloads let the molecule act as a list of atoms
    def __getitem__(self,i):return self.atoms[i]
    def __len__(self): return len(self.atoms)

    # These overloads let one create a subsystem from a list of atoms
    def subsystem(self,indices,**opts):
        name=self.name
        submol = Molecule(name,None,**opts)
        for i in indices: submol.add_atom(self.atoms[i])
        return submol

    def copy(self):
        import copy
        return copy.deepcopy(self)

    def xyz_file(self,fname=None):
        if not fname: fname = self.name + ".xyz"
        lines = ["%d\nWritten by PyQuante.Molecule" % len(self.atoms)]
        for atom in self:
            x,y,z = [bohr2ang*i for i in atom.pos()]
            lines.append("%s %15.10f %15.10f %15.10f" % (atom.symbol(),x,y,z))
        open(fname,'w').write("\n".join(lines))
        return

def toBohr(*args):
    if len(args) == 1: return ang2bohr*args[0]
    return [ang2bohr*arg for arg in args]

def toAng(*args):
    if len(args) == 1: return bohr2ang*args[0]
    return [bohr2ang*arg for arg in args]

def cleansym(s):
    import re
    return re.split('[^a-zA-z]',s)[0]

def ParseXYZLines(name,xyz_lines,**opts):
    atoms = []
    for line in xyz_lines.splitlines():
        words = line.split()
        if not words: continue
        sym = cleansym(words[0])
        xyz = map(float,words[1:4])
        atoms.append((sym,xyz))
    return Molecule(name,atoms,**opts)

def mol2mpqc(mol,**kwargs):
    xc = kwargs.get('xc','B3LYP')
    basis = kwargs.get('basis','6-31g**')
    lines = ['%% %s calculation with MPQC' % xc,
             'optimize: yes',
             'method: KS (xc=%s)' % xc,
             'basis: %s' % basis,
             'molecule:']
    for atom in mol:
        atno,xyz = atom.atuple()
        xyz = toAng(xyz)
        lines.append("   %4s %12.6f %12.6f %12.6f" %
                     (symbol[atno],xyz[0],xyz[1],xyz[2]))
    return "\n".join(lines)

def mol2xyz(mol,**kwargs):
    lines = ['%d\nXYZ File for %s' % (len(mol),mol.name)]
    for atom in mol:
        atno,xyz = atom.atuple()
        xyz = toAng(xyz)
        lines.append("   %4s %12.6f %12.6f %12.6f" %
                     (symbol[atno],xyz[0],xyz[1],xyz[2]))
    return "\n".join(lines)

if __name__ == '__main__':
    h2o = Molecule('h2o',
                   [('O',(0.,0.,0.)),('H',(1.,0.,0.)),('H',(0.,1.,0.))],
                   units='Angstrom')
    print h2o
    print h2o.subsystem([0,1])
    
