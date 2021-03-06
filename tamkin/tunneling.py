# -*- coding: utf-8 -*-
# TAMkin is a post-processing toolkit for normal mode analysis, thermochemistry
# and reaction kinetics.
# Copyright (C) 2008-2012 Toon Verstraelen <Toon.Verstraelen@UGent.be>, An Ghysels
# <An.Ghysels@UGent.be> and Matthias Vandichel <Matthias.Vandichel@UGent.be>
# Center for Molecular Modeling (CMM), Ghent University, Ghent, Belgium; all
# rights reserved unless otherwise stated.
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
# parts of this program are required to cite the following article:
#
# "TAMkin: A Versatile Package for Vibrational Analysis and Chemical Kinetics",
# An Ghysels, Toon Verstraelen, Karen Hemelsoet, Michel Waroquier and Veronique
# Van Speybroeck, Journal of Chemical Information and Modeling, 2010, 50,
# 1736-1750W
# http://dx.doi.org/10.1021/ci100099g
#
# TAMkin is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
#--
"""Tunneling models to approximate QM behavior in reaction coordinate.

   Instances of the classes :class:`Eckart` or :class:`Wigner` act as functions
   that take one argument, the temperature, and return a correction factor
   for the rate coefficient. Such an object can be given as an optional
   argument to the constructor of a :class:`tamkin.chemmod.KineticModel`
   object to take tunneling corrections into account for the computation of
   rate constants.
"""


from molmod import boltzmann, planck, kjmol

import numpy


__all__ = ["TunnelingCorrection", "Eckart", "Wigner", "Miller"]


class TunnelingCorrection(object):
    """Abstract base class for the implementation of a Tunneling correction

       This class merely defines the interface and holds some docstrings.
    """
    def __call__(self, temps):
        """Compute a the tunneling correction as function of the temperature

           Argument:
            | ``temps`` -- a numpy array of temperatures or a single temperature

           Derived classes must override this method with a function that
           computes the correction factors for the rate constant at the given
           temperatures.
        """
        raise NotImplementedError


class Eckart(TunnelingCorrection):
    """Implements the Eckart tunneling correction factor

       This correction is proposed in C. Eckart, Phys. Rev. 35, 1303 (1930),
       http://link.aps.org/doi/10.1103/PhysRev.35.1303.
    """

    def __init__(self, pfs_react, pf_trans, pfs_prod):
        """
           Arguments:
            | ``pfs_react`` -- a list with partition functions of the reactants
            | ``pf_trans`` -- the partition function of the transition state
            | ``pfs_prod`` -- a list with partition functions of the products

           Attributes derived from these arguments:
            | ``self.Ef`` -- forward energy barrier
            | ``self.Er`` -- reverse energy barrier
            | ``self.nu`` -- the imaginary frequency (as a real number)

           Note that this correction is only defined for transition states
           with only one imaginary frequency.
        """
        if len(pf_trans.vibrational.negative_freqs) != 1:
            raise ValueError("The partition function of the transition state must have exactly one negative frequency, found %i" % len(pf_prod.negative_freqs))
        if len(pfs_react) == 0:
            raise ValueError("At least one reactant is required.")
        if len(pfs_react) == 0:
            raise ValueError("At least one product is required.")
        self.Ef = pf_trans.electronic.energy - sum(pf.electronic.energy for pf in pfs_react)
        if self.Ef < 0:
            raise ValueError("The forward barrier is negative. Can not apply Eckart tunneling.")
        self.Er = pf_trans.electronic.energy - sum(pf.electronic.energy for pf in pfs_prod)
        if self.Er < 0:
            raise ValueError("The reverse barrier is negative. Can not apply Eckart tunneling.")
        self.nu = pf_trans.vibrational.negative_freqs[0]

    @classmethod
    def _from_parameters(cls, Ef, Er, nu):
        """An alternative constructor used for testing purposes.

           Arguments:
            | ``Ef`` -- The forward barrier
            | ``Er`` -- The reverse barrier
            | ``nu`` -- The imaginary frequency (as a real number)

           The constructor should not be used in normal situations.
        """
        if Ef < 0:
            raise ValueError("The forward barrier is negative. Can not apply Eckart tunneling.")
        if Er < 0:
            raise ValueError("The reverse barrier is negative. Can not apply Eckart tunneling.")
        result = cls.__new__(cls)
        result.Ef = Ef
        result.Er = Er
        result.nu = nu
        return result

    def _compute_one_temp(self, temp):
        """Computes the correction for one temperature

           Arguments:
            | ``temp`` -- the temperature (scalar)
        """
        from scipy.integrate import quad

        h = 2*numpy.pi # the Planck constant in atomic units
        l = (self.Ef**(-0.5) + self.Er**(-0.5))**(-1)*numpy.sqrt(2) / self.nu

        def alpha(E):
            return numpy.sqrt(2*l**2*E/h**2)

        def beta(E):
            return numpy.sqrt(2*l**2*(E -(self.Ef-self.Er))/h**2)

        def delta(E):
            return numpy.sqrt(4*self.Ef*self.Er/(h*self.nu)**2-0.25)

        def P(E):
            return (
                numpy.cosh(2*numpy.pi*(alpha(E) + beta(E))) -
                numpy.cosh(2*numpy.pi*(alpha(E) - beta(E)))
            ) / (
                numpy.cosh(2*numpy.pi*(alpha(E) + beta(E))) +
                numpy.cosh(2*numpy.pi*(delta(E)))
            )

        def integrandum(E):
            return P(E)*numpy.exp(-(E-self.Ef)/(boltzmann*temp))

        # integration interval
        emin = max([0, self.Ef-self.Er])
        emax = 500*kjmol # The maximum reasonable barrier height.

        # this is just a sanity check to see whether the integrandum is
        # negligible at the borders of the integration interval
        energies = numpy.arange(emin, emax, 1*kjmol)
        integranda = numpy.array([integrandum(energy) for energy in energies])
        if max(integranda) * 1e-5 < max([integranda[0], integranda[-1]]):
            print "Integrandum is not negligible at borders.", integranda[0] / max(integranda), integranda[-1] / max(integranda)

        # actual integration
        integral, error = quad(integrandum, emin, emax)
        factor = 1.0/(boltzmann*temp)
        return integral*factor

    def __call__(self, temps):
        """See :meth:`TunnelingCorrection.__call__`."""
        if hasattr(temps, "__len__"):
            result = numpy.zeros(len(temps))
            for i, temp in enumerate(temps):
                result[i] = self._compute_one_temp(temp)
            return result
        else:
            return self._compute_one_temp(temps)


class Wigner(TunnelingCorrection):
    """Implements the Wigner tunneling correction factor

       This correction is proposed in E. Wigner, Z. Physik. Chern. B 19, 203
       (1932).
    """
    def __init__(self, pf_trans):
        """
           Arguments:
            | ``pf_trans`` -- the partition function of the transition state

           Attribute derived from these argument:
            | ``self.nu`` -- the imaginary frequency (as a real number)

           Note that this correction is only defined for transition states
           with only one imaginary frequency.
        """
        if len(pf_trans.vibrational.negative_freqs) != 1:
            raise ValueError("The partition function of the transition state must have exactly one negative frequency, found %i" % len(pf_prod.negative_freqs))
        self.nu = pf_trans.vibrational.negative_freqs[0]

    @classmethod
    def _from_parameters(cls, nu):
        """An alternative constructor used for testing purposes.

           Arguments:
            | ``nu`` -- The imaginary frequency (as a real number)

           This method should not be used in normal situations.
        """
        result = cls.__new__(cls)
        result.nu = nu
        return result

    def __call__(self, temps):
        """See :meth:`TunnelingCorrection.__call__`."""
        return 1+(planck*self.nu/(boltzmann*temps))**2/24


class Miller(TunnelingCorrection):
    """Implements the Miller tunneling correction factor

       This correction is proposed in Miller, W. H. J. Chem. Phys. 1973, 61,
       1823, http://dx.doi.org/10.1063/1.1682181.
    """
    def __init__(self, pf_trans):
        """
           Arguments:
            | ``pf_trans`` -- the partition function of the transition state

           Attribute derived from these argument:
            | ``self.nu`` -- the imaginary frequency (as a real number)

           Note that this correction is only defined for transition states
           with only one imaginary frequency.
        """
        if len(pf_trans.vibrational.negative_freqs) != 1:
            raise ValueError("The partition function of the transition state must have exactly one negative frequency, found %i" % len(pf_prod.negative_freqs))
        self.nu = pf_trans.vibrational.negative_freqs[0]

    @classmethod
    def _from_parameters(cls, nu):
        """An alternative constructor used for testing purposes.

           Arguments:
            | ``nu`` -- The imaginary frequency (as a real number)

           This method should not be used in normal situations.
        """
        result = cls.__new__(cls)
        result.nu = nu
        return result

    def __call__(self, temps):
        """See :meth:`TunnelingCorrection.__call__`."""
        x = 0.5*planck*self.nu/(boltzmann*temps)
        return x/numpy.sin(x)
