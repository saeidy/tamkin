# TAMkin is a post-processing toolkit for thermochemistry and kinetics analysis.
# Copyright (C) 2008 Toon Verstraelen <Toon.Verstraelen@UGent.be>,
# Matthias Vandichel <Matthias.Vandichel@UGent.be> and
# An Ghysels <An.Ghysels@UGent.be>
#
# This file is part of TAMkin.
#
# TAMkin is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
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


from molmod.constants import boltzmann
from molmod.units import kjmol

import numpy


__all__ = ["Eckart", "Wigner"]


class TunnelingCorrection(object):
    def __call__(self, temps):
        # temps is an array with temperatures in Kelvin.
        # Derived classes must override this method with a function that
        # computes the correction factors for the rate constant at the given
        # temperatures.
        raise NotImplementedError


class Eckart(TunnelingCorrection):
    """Implements the Eckart tunneling correction factor
    """

    def __init__(self, pfs_react, pf_trans, pfs_prod):
        """Initialize the Eckart correction

           Arguments:
             pfs_react  --  a list with partition functions of the reactants
             pf_trans  --  the partition function of the transition state
             pfs_prod  --  a list with partition functions of the products
        """
        # Just compute the quantities of interest and do not keep the partition
        # function objects as attributes:
        #  self.Ef: forward energy barrier
        #  self.Er: reverse energy barrier
        #  self.nu: the imaginary frequency (as a real number)
        if len(pf_trans.vibrational.negative_freqs) != 1:
            raise ValueError("The partition function of the transition state must have exactly one negative frequency, found %i" % len(pf_prod.negative_freqs))
        if len(pfs_react) == 0:
            raise ValueError("At least one reactant is required.")
        if len(pfs_react) == 0:
            raise ValueError("At least one product is required.")
        self.Ef = sum(energy for pf.energy in pfs_react) - pf_trans.energy
        self.Er = sum(energy for pf.energy in pfs_prod) - pf_trans.energy
        self.nu = pf_trans.vibrational.negative_freqs

    @classmethod
    def _from_parameters(cls, Ef, Er, nu):
        """An alternative constructor used for testing purposes.

           It should not be used in normal situations.
        """
        result = cls.__new__(cls)
        result.Ef = Ef
        result.Er = Er
        result.nu = nu
        return result

    def _compute_one_temp(self, temp):
        """Computes the correction for one temperature"""
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
        """Compute the correction for an array of temperatures"""
        result = numpy.zeros(len(temps))
        for i, temp in enumerate(temps):
            result[i] = self._compute_one_temp(temp)
        return result


class Wigner(TunnelingCorrection):
    """Implements the Wigner tunneling correction factor
    """
    def __init__(self, pf_trans):
        """Initialize the Wigner correction

           Arguments:
             pf_trans  --  the partition function of the transition state
        """
        # Just compute the quantities of interest and do not keep the partition
        # function objects as attributes:
        #  self.nu: the imaginary frequency (as a real number)
        if len(pf_trans.vibrational.negative_freqs) != 1:
            raise ValueError("The partition function of the transition state must have exactly one negative frequency, found %i" % len(pf_prod.negative_freqs))
        self.nu = pf_trans.vibrational.negative_freqs

    @classmethod
    def _from_parameters(cls, nu):
        """An alternative constructor used for testing purposes.

           It should not be used in normal situations.
        """
        result = cls.__new__(cls)
        result.nu = nu
        return result

    def __call__(self, temps):
        """Compute the correction for an array of temperatures"""
        h = 2*numpy.pi # the Planck constant in atomic units
        return 1+(h*self.nu/(boltzmann*temps))**2/24


