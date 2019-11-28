import inspect
import operator
import sys
from collections import OrderedDict
from copy import deepcopy
from functools import wraps
from types import SimpleNamespace

import kwant
import numpy as np
import scipy.constants
import scipy.sparse
import scipy.sparse.linalg as sla
from kwant.continuum.discretizer import discretize

import pfaffian as pf

assert sys.version_info >= (3, 6), "Use Python ≥3.6"

# Parameters taken from arXiv:1204.2792
# All constant parameters, mostly fundamental constants, in a SimpleNamespace.
constants = SimpleNamespace(
    m_eff=0.015 * scipy.constants.m_e,  # effective mass in kg
    hbar=scipy.constants.hbar,
    m_e=scipy.constants.m_e,
    eV=scipy.constants.eV,
    e=scipy.constants.e,
    c=1e18 / (scipy.constants.eV * 1e-3),  # to get to meV * nm^2
    mu_B=scipy.constants.physical_constants["Bohr magneton in eV/T"][0] * 1e3,
)

constants.t = (constants.hbar ** 2 / (2 * constants.m_eff)) * constants.c


def get_names(sig):
    names = [
        (name, value)
        for name, value in sig.parameters.items()
        if value.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    ]
    return OrderedDict(names)


def filter_kwargs(sig, names, kwargs):
    names_in_kwargs = [(name, value) for name, value in kwargs.items() if name in names]
    return OrderedDict(names_in_kwargs)


def skip_pars(names1, names2, num_skipped):
    skipped_pars1 = list(names1.keys())[:num_skipped]
    skipped_pars2 = list(names2.keys())[:num_skipped]
    if skipped_pars1 == skipped_pars2:
        pars1 = list(names1.values())[num_skipped:]
        pars2 = list(names2.values())[num_skipped:]
    else:
        raise Exception("First {} arguments " "have to be the same".format(num_skipped))
    return pars1, pars2


def combine(f, g, operator, num_skipped=0):
    if not callable(f) or not callable(g):
        raise Exception("One of the functions is not a function")

    sig1 = inspect.signature(f)
    sig2 = inspect.signature(g)

    names1 = get_names(sig1)
    names2 = get_names(sig2)

    pars1, pars2 = skip_pars(names1, names2, num_skipped)
    skipped_pars = list(names1.values())[:num_skipped]

    pars1_names = {p.name for p in pars1}
    pars2 = [p for p in pars2 if p.name not in pars1_names]

    parameters = pars1 + pars2
    kind = inspect.Parameter.POSITIONAL_OR_KEYWORD
    parameters = [p.replace(kind=kind) for p in parameters]
    parameters = skipped_pars + parameters

    def wrapped(*args):
        d = {p.name: arg for arg, p in zip(args, parameters)}
        fval = f(*[d[name] for name in names1.keys()])
        gval = g(*[d[name] for name in names2.keys()])
        return operator(fval, gval)

    wrapped.__signature__ = inspect.Signature(parameters=parameters)
    return wrapped


def memoize(obj):
    cache = obj.cache = {}

    @wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]

    return memoizer


def parse_params(params):
    for k, v in params.items():
        if isinstance(v, str):
            try:
                params[k] = eval(v)
            except NameError:
                pass
    return params


@memoize
def discretized_hamiltonian(a, which_lead=None, subst_sm=None):
    ham = (
        "(0.5 * hbar**2 * (k_x**2 + k_y**2 + k_z**2) / m_eff * c - mu + V) * kron(sigma_0, sigma_z) + "
        "alpha * (k_y * kron(sigma_x, sigma_z) - k_x * kron(sigma_y, sigma_z)) + "
        "0.5 * g * mu_B * (B_x * kron(sigma_x, sigma_0) + B_y * kron(sigma_y, sigma_0) + B_z * kron(sigma_z, sigma_0)) + "
        "Delta * kron(sigma_0, sigma_x)"
    )
    if subst_sm is None:
        subst_sm = {"Delta": 0}

    if which_lead is not None:
        subst_sm["V"] = f"V_{which_lead}(z, V_0, V_r, V_l, x0, sigma, r1)"
        subst_sm["mu"] = f"mu_{which_lead}(x0, sigma, mu_lead, mu_wire)"
    else:
        subst_sm["V"] = "V(x, z, V_0, V_r, V_l, x0, sigma, r1)"
        subst_sm["mu"] = "mu(x, x0, sigma, mu_lead, mu_wire)"

    subst_sc = {"g": 0, "alpha": 0, "mu": "mu_sc", "V": 0}
    subst_interface = {"c": "c * c_tunnel", "alpha": 0, "V": 0}

    templ_sm = discretize(ham, locals=subst_sm, grid_spacing=a)
    templ_sc = discretize(ham, locals=subst_sc, grid_spacing=a)
    templ_interface = discretize(ham, locals=subst_interface, grid_spacing=a)

    return templ_sm, templ_sc, templ_interface


def cylinder_sector(r_out, r_in=0, L=1, L0=0, coverage_angle=360, angle=0, a=10):
    """Returns the shape function and start coords for a wire with
    as cylindrical cross section.

    Parameters
    ----------
    r_out : int
        Outer radius in nm.
    r_in : int, optional
        Inner radius in nm.
    L : int, optional
        Length of wire from L0 in nm, -1 if infinite in x-direction.
    L0 : int, optional
        Start position in x.
    coverage_angle : int, optional
        Coverage angle in degrees.
    angle : int, optional
        Angle of tilting from top in degrees.
    a : int, optional
        Discretization constant in nm.

    Returns
    -------
    (shape_func, *(start_coords))
    """
    coverage_angle *= np.pi / 360
    angle *= np.pi / 180
    r_out_sq, r_in_sq = r_out ** 2, r_in ** 2

    def shape(site):
        try:
            x, y, z = site.pos
        except AttributeError:
            x, y, z = site
        n = (y + 1j * z) * np.exp(1j * angle)
        y, z = n.real, n.imag
        rsq = y ** 2 + z ** 2
        shape_yz = r_in_sq <= rsq < r_out_sq and z >= np.cos(coverage_angle) * np.sqrt(
            rsq
        )
        return (shape_yz and L0 <= x < L) if L > 0 else shape_yz

    r_mid = (r_out + r_in) / 2
    start_coords = np.array([L - a, r_mid * np.sin(angle), r_mid * np.cos(angle)])

    return shape, start_coords


def is_antisymmetric(H):
    return np.allclose(-H, H.T)


def cell_mats(lead, params, bias=0):
    h = lead.cell_hamiltonian(params=params)
    h -= bias * np.identity(len(h))
    t = lead.inter_cell_hopping(params=params)
    return h, t


def get_h_k(lead, params):
    h, t = cell_mats(lead, params)

    def h_k(k):
        return h + t * np.exp(1j * k) + t.T.conj() * np.exp(-1j * k)

    return h_k


def make_skew_symmetric(ham):
    """
    Makes a skew symmetric matrix by a matrix multiplication of a unitary
    matrix U. This unitary matrix is taken from the Topology MOOC 0D, but
    that is in a different basis. To get to the right basis one multiplies
    by [[np.eye(2), 0], [0, sigma_y]].

    Parameters:
    -----------
    ham : numpy.ndarray
        Hamiltonian matrix gotten from sys.cell_hamiltonian()

    Returns:
    --------
    skew_ham : numpy.ndarray
        Skew symmetrized Hamiltonian
    """
    W = ham.shape[0] // 4
    I = np.eye(2, dtype=complex)
    sigma_y = np.array([[0, 1j], [-1j, 0]], dtype=complex)
    U_1 = np.bmat([[I, I], [1j * I, -1j * I]])
    U_2 = np.bmat([[I, 0 * I], [0 * I, sigma_y]])
    U = U_1 @ U_2
    U = np.kron(np.eye(W, dtype=complex), U)
    skew_ham = U @ ham @ U.H

    assert is_antisymmetric(skew_ham)

    return skew_ham


def calculate_pfaffian(lead, params):
    """
    Calculates the Pfaffian for the infinite system by computing it at k = 0
    and k = pi.

    Parameters:
    -----------
    lead : kwant.builder.InfiniteSystem object
          The finalized system.

    """
    h_k = get_h_k(lead, params)

    skew_h0 = make_skew_symmetric(h_k(0))
    skew_h_pi = make_skew_symmetric(h_k(np.pi))

    pf_0 = np.sign(pf.pfaffian(1j * skew_h0, sign_only=True).real)
    pf_pi = np.sign(pf.pfaffian(1j * skew_h_pi, sign_only=True).real)
    pfaf = pf_0 * pf_pi

    return pfaf


def at_interface(site1, site2, shape1, shape2):
    return (shape1[0](site1) and shape2[0](site2)) or (
        shape2[0](site1) and shape1[0](site2)
    )


def change_hopping_at_interface(syst, template, shape1, shape2):
    for (site1, site2), hop in syst.hopping_value_pairs():
        if at_interface(site1, site2, shape1, shape2):
            syst[site1, site2] = template[site1, site2]
    return syst


@memoize
def make_lead(
    a,
    r1,
    r2,
    coverage_angle,
    angle,
    with_shell,
    which_lead,
    sc_inside_wire=False,
    wraparound=False,
):
    """Create an infinite cylindrical 3D wire partially covered with a
    superconducting (SC) shell.

    Parameters
    ----------
    a : int
        Discretization constant in nm.
    r1 : int
        Radius of normal part of wire in nm.
    r2 : int
        Radius of superconductor in nm.
    coverage_angle : int
        Coverage angle of superconductor in degrees.
    angle : int
        Angle of tilting of superconductor from top in degrees.
    with_shell : bool
        Adds shell to the scattering area. If False no SC shell is added and
        only a cylindrical wire will be created.
    which_lead : str
        Name of the potential function of the lead, e.g. `which_lead = 'left'` will
        require a function `V_left(z, V_0)` and
        `mu_left(mu_func(x, x0, sigma, mu_lead, mu_wire)`.
    sc_inside_wire : bool
        Put superconductivity inside the wire.
    wraparound : bool
        Apply wraparound to the lead.

    Returns
    -------
    syst : kwant.builder.InfiniteSystem
        The finilized kwant system.

    Examples
    --------
    This doesn't use default parameters because the variables need to be saved,
    to a file. So I create a dictionary that is passed to the function.

    >>> syst_params = dict(a=10, angle=0, coverage_angle=185, r1=50,
    ...                    r2=70, with_shell=True)
    >>> syst, hopping = make_lead(**syst_params)
    """

    shape_normal_lead = cylinder_sector(r_out=r1, angle=angle, L=-1, a=a)
    shape_sc_lead = cylinder_sector(
        r_out=r2, r_in=r1, coverage_angle=coverage_angle, angle=angle, L=-1, a=a
    )

    sz = np.array([[1, 0], [0, -1]])
    cons_law = np.kron(np.eye(2), -sz)
    symmetry = kwant.TranslationalSymmetry((a, 0, 0))
    lead = kwant.Builder(
        symmetry, conservation_law=cons_law if not with_shell else None
    )

    templ_sm, templ_sc, templ_interface = discretized_hamiltonian(
        a, which_lead=which_lead, subst_sm={} if sc_inside_wire else None
    )
    templ_sm = apply_peierls_to_template(templ_sm)
    lead.fill(templ_sm, *shape_normal_lead)

    if with_shell:
        lat = templ_sc.lattice
        shape_sc = cylinder_sector(
            r_out=r2, r_in=r1, coverage_angle=coverage_angle, angle=angle, L=a, a=a
        )

        xyz_offset = get_offset(*shape_sc, lat)

        templ_interface = apply_peierls_to_template(templ_interface)
        lead.fill(templ_sc, *shape_sc_lead)

        # Adding a tunnel barrier between SM and SC
        lead = change_hopping_at_interface(
            lead, templ_interface, shape_normal_lead, shape_sc_lead
        )

    if wraparound:
        lead = kwant.wraparound.wraparound(lead)
    return lead


def apply_peierls_to_template(template, xyz_offset=(0, 0, 0)):
    """Adds p.orbital argument to the hopping functions."""
    template = deepcopy(template)  # Needed because kwant.Builder is mutable
    x0, y0, z0 = xyz_offset
    lat = template.lattice
    a = np.max(lat.prim_vecs)  # lattice contant

    def phase(site1, site2, B_x, B_y, B_z, orbital, e, hbar):
        if orbital:
            x, y, z = site1.tag
            direction = site1.tag - site2.tag
            A = [B_y * (z - z0) - B_z * (y - y0), 0, B_x * (y - y0)]
            A = np.dot(A, direction) * a ** 2 * 1e-18 * e / hbar
            phase = np.exp(-1j * A)
            if lat.norbs == 2:  # No PH degrees of freedom
                return phase
            elif lat.norbs == 4:
                return np.array(
                    [phase, phase.conj(), phase, phase.conj()], dtype="complex128"
                )
        else:  # No orbital phase
            return 1

    for (site1, site2), hop in template.hopping_value_pairs():
        template[site1, site2] = combine(hop, phase, operator.mul, 2)
    return template


def get_offset(shape, start, lat):
    coords = [site.pos for site in lat.shape(shape, start)()]
    xyz_offset = np.mean(coords, axis=0)
    return xyz_offset


def translation_ev(h, t, tol=1e6):
    """Compute the eigenvalues of the translation operator of a lead.

    Adapted from kwant.physics.leads.modes.

    Parameters
    ----------
    h : numpy array, real or complex, shape (N, N) The unit cell
        Hamiltonian of the lead unit cell.
    t : numpy array, real or complex, shape (N, M)
        The hopping matrix from a lead cell to the one on which self-energy
        has to be calculated (and any other hopping in the same direction).
    tol : float
        Numbers and differences are considered zero when they are smaller
        than `tol` times the machine precision.

    Returns
    -------
    ev : numpy array
        Eigenvalues of the translation operator in the form lambda=r*exp(i*k),
        for |r|=1 they are propagating modes.
    """
    a, b = kwant.physics.leads.setup_linsys(h, t, tol, None).eigenproblem
    ev = kwant.physics.leads.unified_eigenproblem(a, b, tol=tol)[0]
    return ev


def gap_minimizer(lead, params, energy):
    """Function that minimizes a function to find the band gap.
    This objective function checks if there are progagating modes at a
    certain energy. Returns zero if there is a propagating mode.

    Parameters
    ----------
    lead : kwant.builder.InfiniteSystem object
        The finalized infinite system.
    params : dict
        A dict that is used to store Hamiltonian parameters.
    energy : float
        Energy at which this function checks for propagating modes.

    Returns
    -------
    minimized_scalar : float
        Value that is zero when there is a propagating mode.
    """
    h, t = cell_mats(lead, params, bias=energy)
    ev = translation_ev(h, t)
    norm = (ev * ev.conj()).real
    return np.min(np.abs(norm - 1))


def gap_from_modes(lead, params, tol=1e-6):
    """Finds the gapsize by peforming a binary search of the modes with a
    tolarance of tol.

    Parameters
    ----------
    lead : kwant.builder.InfiniteSystem object
        The finalized infinite system.
    params : dict
        A dict that is used to store Hamiltonian parameters.
    tol : float
        The precision of the binary search.

    Returns
    -------
    gap : float
        Size of the gap.

    Notes
    -----
    For use with `lead = funcs.make_lead()`.
    """
    Es = kwant.physics.Bands(lead, params=params)(k=0)
    lim = [0, np.abs(Es).min()]
    if gap_minimizer(lead, params, energy=0) < 1e-15:
        # No band gap
        gap = 0
    else:
        while lim[1] - lim[0] > tol:
            energy = sum(lim) / 2
            par = gap_minimizer(lead, params, energy)
            if par < 1e-10:
                lim[1] = energy
            else:
                lim[0] = energy
        gap = sum(lim) / 2
    return gap


def phase_bounds_operator(lead, params, k_x=0, mu_param="mu"):
    params = dict(params, k_x=k_x)
    params[mu_param] = 0
    h_k = lead.hamiltonian_submatrix(params=params, sparse=True)
    sigma_z = scipy.sparse.csc_matrix(np.array([[1, 0], [0, -1]]))
    _operator = scipy.sparse.kron(scipy.sparse.eye(h_k.shape[0] // 2), sigma_z) @ h_k
    return _operator


def find_phase_bounds(lead, params, k_x=0, num_bands=20, sigma=0, mu_param="mu"):
    """Find the phase boundaries.
    Solve an eigenproblem that finds values of chemical potential at which the
    gap closes at momentum k=0. We are looking for all real solutions of the
    form H*psi=0 so we solve sigma_0 * tau_z H * psi = mu * psi.

    Parameters
    -----------
    lead : kwant.builder.InfiniteSystem object
        The finalized infinite system.
    params : dict
        A dictionary that is used to store Hamiltonian parameters.
    k_x : float
        Momentum value, by default set to 0.

    Returns
    --------
    chemical_potential : numpy array
        Twenty values of chemical potential at which a bandgap closes at k=0.
    """
    chemical_potentials = phase_bounds_operator(lead, params, k_x, mu_param)

    if num_bands is None:
        mus = np.linalg.eigvals(chemical_potentials.todense())
    else:
        mus = sla.eigs(chemical_potentials, k=num_bands, sigma=sigma, which="LM")[0]

    real_solutions = abs(np.angle(mus)) < 1e-10

    mus[~real_solutions] = np.nan  # To ensure it returns the same shape vector
    return np.sort(mus.real)
