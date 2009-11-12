# TAMkin is a post-processing toolkit for thermochemistry and kinetics analysis.
# Copyright (C) 2008-2009 Toon Verstraelen <Toon.Verstraelen@UGent.be>,
# Matthias Vandichel <Matthias.Vandichel@UGent.be> and
# An Ghysels <An.Ghysels@UGent.be>, Center for Molecular Modeling (CMM), Ghent
# University, Ghent, Belgium; all rights reserved unless otherwise stated.
#
# This file is part of TAMkin.
#
# TAMkin is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# In addition to the regulations of the GNU General Public License,
# publications and communications based in parts on this program or on
# parts of this program are required to cite the following five articles:
#
# "Vibrational Modes in partially optimized molecular systems.", An Ghysels,
# Dimitri Van Neck, Veronique Van Speybroeck, Toon Verstraelen and Michel
# Waroquier, Journal of Chemical Physics, Vol. 126 (22): Art. No. 224102, 2007
# DOI:10.1063/1.2737444
#
# "Cartesian formulation of the Mobile Block Hesian Approach to vibrational
# analysis in partially optimized systems", An Ghysels, Dimitri Van Neck and
# Michel Waroquier, Journal of Chemical Physics, Vol. 127 (16), Art. No. 164108,
# 2007
# DOI:10.1063/1.2789429
#
# "Calculating reaction rates with partial Hessians: validation of the MBH
# approach", An Ghysels, Veronique Van Speybroeck, Toon Verstraelen, Dimitri Van
# Neck and Michel Waroquier, Journal of Chemical Theory and Computation, Vol. 4
# (4), 614-625, 2008
# DOI:10.1021/ct7002836
#
# "Mobile Block Hessian approach with linked blocks: an efficient approach for
# the calculation of frequencies in macromolecules", An Ghysels, Veronique Van
# Speybroeck, Ewald Pauwels, Dimitri Van Neck, Bernard R. Brooks and Michel
# Waroquier, Journal of Chemical Theory and Computation, Vol. 5 (5), 1203-1215,
# 2009
# DOI:10.1021/ct800489r
#
# "Normal modes for large molecules with arbitrary link constraints in the
# mobile block Hessian approach", An Ghysels, Dimitri Van Neck, Bernard R.
# Brooks, Veronique Van Speybroeck and Michel Waroquier, Journal of Chemical
# Physics, Vol. 130 (18), Art. No. 084107, 2009
# DOI:10.1063/1.3071261
#
# TAMkin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
# --

import numpy
from molmod.units import cm
from molmod.constants import lightspeed
#from molmod.units import kjmol, second, meter, mol, K, J
#from molmod.constants import boltzmann

###import sys, numpy, pylab, types


__all__ = [
           "calculate_overlap_nma", "calculate_overlap",
           "write_overlap",
           "calculate_sensitivity",
          ]



def read_an_freqs(filename):
    print  "-"*20
    print "Reading from an-freqs-file...", filename
    f = open(filename,'r')
    freqs = []
    for line in f:
        words = line.split(";")
        freqs.append(float(words[0]))
    f.close()

    return freqs


def read_an_modes(filename):
    print  "-"*20
    print "Reading from an-modes-file...", filename
    f = open(filename,'r')
    modes = []
    counter=0
    for line in f:
        words = line.split(";")
        if words[-1]=="\n": words = words[:len(words)-1]
        words = sum([[float(word)] for word in words],[])
        modes.append(words)
    f.close()

    return numpy.array(modes)


def read_charmm_cor(filename):
    print "-"*20
    print "Reading from charmm-file...", filename
    bestand=open(filename,'r')

    # skip the lines that start with * comments
    check=0
    while check==0:
        lijn=bestand.readline()
        if not lijn[0]=='*':
            check=1
            Nb=int(lijn.split()[0])
    print "nb atoms: ",  Nb

    # store coordinates in Nbx3 matrix
    Coord=numpy.zeros((Nb,3),dtype=float)
    Symbols=['']*Nb
    Masses=[]
    for teller in range(Nb):
        Lijn=bestand.readline().split()
        Symbols[teller]=Lijn[3]
        Coord[teller,:]=numpy.array(Lijn[4:7])
        Masses.append(float(Lijn[9]))
    bestand.close()
    return Masses,Symbols,Coord



def read_charmm_modes(filename, nbfreqs = 0):
    """Read modes and frequencies from a standard CHARMM-modes-file generated by the VIBRAN module in CHARMM.
    The function returns the frequencies atomic units and the modes (in columns).
    Charmm modes are already mass weighted and normalized.
    Optional:
    The nb of frequencies/modes can be specified with nbfreqs. This is e.g. useful when the modes-file
    does not result from a full Hessian calculation (less than 3*nb_atoms modes)."""
    f = file(filename)

    # skip the lines that start with * comments
    for line in f:
        if not line.strip().startswith("*"): break

    # read nb of atoms
    words = line.split()   # the current line is not starting with a *
    N = int(words[1])   # nb of atoms

    # skip lines with masses, 6 masses on each line
    nblines = int(numpy.ceil(N/6.0))
    for i in xrange(nblines):
        f.next()

    # read nbfreqs freqs
    if nbfreqs == 0:
         nbfreqs = 3*N  # assume a full Hessian calculation
    CNVFRQ=2045.5/(2.99793*6.28319)  # conversion factor, see c36a0/source/fcm/consta.fcm in charmm code
    nblines = int(numpy.ceil(nbfreqs/6.0))
    count = 0
    freqs = []
    for line in f:
        count+=1
        words = line.split()
        for word in words:
            # do conversion
            freqsq = float(word) #squared value
            if freqsq > 0.0:  freq = numpy.sqrt( freqsq)
            else:             freq =-numpy.sqrt(-freqsq) #actually imaginary
            freqs.append(freq*CNVFRQ) # conversion factor CHARMM
        if count >= nblines: break

    # read the nbfreqs modes
    mat = []
    for line in f:
        words = line.split()
        for word in words:
            mat.append(float(word))
    mat = numpy.transpose(numpy.reshape(numpy.array(mat),(-1,3*N)))

    f.close()
    return mat,freqs


def calculate_overlap_nma(nma1, nma2, filename=None):
    """Calculate overlap of modes of NMA objects, and print to file if requested."""
    overlap = calculate_overlapmatrix(nma1.modes, nma2.modes)
    if filename is not None:
        write_overlap(nma1.freqs, nma2.freqs, overlap, filename=filename)
    return overlap

def calculate_overlap(mat1, freqs1, mat2, freqs2, filename=None):
    """Calculate overlap of matrices (with corresponding frequencies), and write to file if requested."""
    overlap = calculate_overlapmatrix(mat1, mat2)
    if filename is not None:
        write_overlap(freqs1, freqs2, overlap, filename=filename)
    return overlap

def calculate_overlapmatrix(mat1, mat2):
    """Calculate overlap of matrices."""
    # check dimensions
    if mat1.shape[0] != mat2.shape[0] :
        raise ValueError("Length of columns in mat1 and mat2 should be equal, but found "+str(mat1.shape[0])+" and "+str(mat2.shape[0]) )
    # calculate overlap
    return numpy.dot(numpy.transpose(mat1), mat2)


def write_overlap(freqs1, freqs2, overlap, filename=None):
    """Write overlap matrix to a file, default is overlap.csv. Format:
    ------------------------
           | freqs2
    ------------------------
    freqs1 | mat1^T . mat2
    ------------------------
    """
    #freqs1 = freqs1 /lightspeed*cm
    #freqs2 = freqs2 /lightspeed*cm

    # write to file
    if filename==None:
        filename="overlap.csv"   # TODO sys.currentdir

    to_append="w+"   # not append, just overwrite
    f = file(filename,to_append)

    [rows,cols] = overlap.shape

    # 1. row of freqs2
    print >> f, ";"+";".join(str(g) for g in freqs2)  #this is the same

    # 2. start each row with freq of freqs1 and continue with overlaps
    for r in range(rows):
        print >> f, str(freqs1[r])+";"+";".join(str(g) for g in overlap[r,:].tolist())
    f.close()


def get_Delta_vector_charmmcor(charmmfile1, charmmfile2):
    masses1,symb1,vec1 = read_charmm_cor(charmmfile1)
    masses2,symb2,vec2 = read_charmm_cor(charmmfile2)
    print "check consistency (symbols):", ( symb1 == symb2 )
    print "check consistency (masses): ", (masses1==masses2)
    Delta = vec1 - vec2
    Delta = numpy.reshape(numpy.ravel(vec1 - vec2),(-1,1))
    print "Delta shape:",Delta.shape

    print "Mass-weighting Delta vector"
    for i,mass in enumerate(masses1):
        Delta[3*i:3*(i+1)] *=  numpy.sqrt(mass)
    print "Normalizing Delta vector"
    Delta /= numpy.sqrt(numpy.sum(Delta**2))
    return Delta

def get_Delta_vector_nma(molecule1, molecule2):
    """Calculate conformational change vector: positions molecule 1 - positions molecule 2.
    The vector is also mass weighted and normalized."""
    if molecule1.size != molecule2.size:
        raise ValueError("Nb of atoms is not the same in the two molecules. Found "+str(molecule1)+" (1) and "+str(molecule)+" (2).")
    for i in range(molecule1.size):
        if molecule1.numbers[i] != molecule2.numbers[i]:
            raise ValueError("Atoms of molecule1 differ from those of molecule2 (different atomic numbers), but should be the same.")

    Delta = molecule1.coordinates - molecule2.coordinates
    Delta = numpy.reshape(numpy.ravel(vec1 - vec2),(-1,1))
    for i,mass in enumerate(masses1):               # mass weight
        Delta[3*i:3*(i+1)] *=  numpy.sqrt(mass)
    Delta /= numpy.sqrt(numpy.sum(Delta**2))        # normalize
    return Delta


def calculate_sensitivity(nma, index, filename = None):
    L = len(nma.modes)
    mode = nma.modes[:,index]
    # un-mass-weight the mode   - NO assume wrt to mass weighted Hessian elements
    #for at,mass in enumerate(nma.masses):
    #    mode[3*at:3*(at+1)] /= numpy.sqrt(mass)
    mat = 2*numpy.dot( numpy.reshape(mode,(L,1)), numpy.reshape(mode,(1,L)) )
    for i in range(L):
        mat[i,i] = mat[i,i] - mode[i]**2
    #points = numpy.arange(L)*4000.0 #/(cm/lightspeed)
    #if filename is not None:
    #    write_overlap(points, points, numpy.sqrt(abs(mat)), filename = filename)   # reuse this function
    vals,vecs = numpy.linalg.eigh(mat)
    #print vals
    return mat

