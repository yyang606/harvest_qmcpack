# Author: Yubo "Paul" Yang
# Email: yubo.paul.yang@gmail.com
# Routines to manipulate QE 6.8 pwscf hdf results
import h5py
import numpy as np

# ========================== level 0: read ==========================
def read_save_hdf(fh5, name='evc', xname='MillerIndices'):
  """Read a wavefunction or charge density file in pwscf.save/
  Data values are assumed to be complex.

  Args:
    fh5 (str): "wfc[#].hdf5" or "charge-density.hdf5"
    name (str, optional): column name, default "evc"
    xname (str, optional): label name, default "MillerIndices"
  Return:
    x, y: x is "MillerIndices" by default, y is "evc" by default
  Example:
    >>> gvs, rhog = read_save_hdf("charge-density.hdf5", name="rhotot_g")
  """
  fp = h5py.File(fh5, 'r')
  gvc = fp[xname][()]
  evc = fp[name][()].view(np.complex128)
  fp.close()
  return gvc, evc

def find_wfc(fxml):
  """Find wfc hdf files using xml <band_structure> as guide.

  Args:
    fxml (str): "pwscf.xml"
  Return:
    list: locations of all wfc hdf files
  Example:
    >>> flist = find_wfc("pwscf.xml")
  """
  import os
  from qharv.cross import pwscf_xml
  prefix = fxml[:fxml.rfind('.')]
  dsave = prefix + '.save'
  if not os.path.isdir(dsave):
    msg = 'wfc save "%s" not found' % dsave
    raise RuntimeError(msg)
  # determine lsda
  doc = pwscf_xml.read(fxml)
  bgrp = doc.find('.//band_structure')
  lsda = pwscf_xml.read_true_false(doc, 'lsda')
  nk = int(bgrp.find('.//nks').text)
  wfcs = []
  if lsda:
    for spin in ['up', 'dw']:
      wfcs += [os.path.join(dsave, 'wfc%s%d.hdf5' % (spin, ik+1))
        for ik in range(nk)]
  else:
    wfcs += [os.path.join(dsave, 'wfc%d.hdf5' % (ik+1)) for ik in range(nk)]
  # check wfc
  missing = False
  nfound = 0
  nexpect = len(wfcs)
  for floc in wfcs:
    if not os.path.isfile(floc):
      print('%s not found' % floc)
      missing = True
    else:
      nfound += 1
  if missing:
    msg = 'found %d/%d wfc' % (nfound, nexpect)
    raise RuntimeError(msg)
  return wfcs

def read_wfc(fxml):
  from qharv.cross import pwscf_xml
  doc = pwscf_xml.read(fxml)
  bgrp = doc.find('.//band_structure')
  lsda = pwscf_xml.read_true_false(doc, 'lsda')
  flist = find_wfc(fxml)
  rets = [read_save_hdf(floc) for floc in flist]
  if lsda:  # concatenate spin up, spin dn wfc
    nkpt = len(flist)//2
    gvl = []
    evl = []
    for ik in range(nkpt):
      iup = ik
      idn = nkpt+ik
      gvup, evup = rets[iup]
      gvdn, evdn = rets[idn]
      assert np.allclose(gvup, gvdn)
      gvl.append(gvup)
      ev = np.concatenate([evup, evdn], axis=0)
      evl.append(ev)
  else:
    gvl = [ret[0] for ret in rets]
    evl = [ret[1] for ret in rets]
  return gvl, evl

# ========================= level 1: orbital ========================

def kinetic_energy(raxes, kfracs, gvl, evl, wtl):
  nkpt = len(kfracs)
  tkin_per_kpt = np.zeros(nkpt)
  for ik, (kfrac, gvs, evc, wts) in enumerate(zip(kfracs, gvl, evl, wtl)):
    kvecs = np.dot(gvs+kfrac, raxes)
    npw = len(kvecs)
    k2 = np.einsum('ij,ij->i', kvecs, kvecs)
    p2 = (evc.conj()*evc).real
    nk = np.dot(wts, p2)  # sum occupied bands for n(k)
    if len(nk) == 2*npw:  # noncolin
      tkin_per_kpt[ik] = np.dot(k2, nk[:npw]) + np.dot(k2, nk[npw:])
    else:
      tkin_per_kpt[ik] = np.dot(k2, nk)
  return tkin_per_kpt

def calc_kinetic(fxml, gvl=None, evl=None, wtl=None, lam=0.5):
  #lam = 1./2  # Hartree atomic units T = -lam*\nabla^2
  from qharv.cross import pwscf_xml
  doc = pwscf_xml.read(fxml)
  raxes = pwscf_xml.read_reciprocal_lattice(doc)
  kfracs = pwscf_xml.read_kfractions(doc)
  if wtl is None:
    wtl = pwscf_xml.read_occupations(doc)
  if (gvl is None) or (evl is None):
    gvl, evl = read_wfc(fxml)
  tkin_per_kpt = kinetic_energy(raxes, kfracs, gvl, evl, wtl)
  tkin = lam*tkin_per_kpt.mean()
  return tkin

# ========================== level 2: FFT ===========================

class FFTMesh:
  def __init__(self, mesh, dtype=np.complex128):
    self.mesh = mesh
    self.ngrid = np.prod(mesh)
    self.psik = np.zeros(mesh, dtype=dtype)
  def invfft(self, gvectors, eigenvector):
    self.psik.fill(0)
    for g, e in zip(gvectors, eigenvector):
      self.psik[tuple(g)] = e
    psir = np.fft.ifftn(self.psik)*self.ngrid
    return psir

def rho_of_r(mesh, gvl, evl, wtl, wt_tol=1e-8):
  rhor = np.zeros(mesh)
  fft = FFTMesh(mesh)
  psir = np.zeros(mesh, dtype=np.complex128)
  nkpt = len(gvl)
  for gvs, evc, wts in zip(gvl, evl, wtl):  # kpt loop
    sel = wt >= wt_tol
    for ev, wt in zip(evc[sel], wts[sel]):  # bnd loop
      psir = fft.invfft(gvs, ev)
      r1 = (psir.conj()*psir).real
      rhor += wt*r1
  return rhor/nkpt

def calc_rhor(fxml, mesh=None, gvl=None, evl=None, wtl=None, spin_resolved=False):
  from qharv.cross import pwscf_xml
  doc = pwscf_xml.read(fxml)
  if mesh is None:
    mesh = pwscf_xml.read_fft_mesh(doc)
  if wtl is None:
    wtl = pwscf_xml.read_occupations(doc)
  if (gvl is None) or (evl is None):
    gvl, evl = read_wfc(fxml)
  if spin_resolved:
    lsda = pwscf_xml.read_true_false(doc, 'lsda')
    if lsda:
      evupl = [ev[:len(ev)//2] for ev in evl]
      wtupl = [wt[:len(wt)//2] for wt in wtl]
      rhor_up = rho_of_r(mesh, gvl, evupl, wtupl)
      evdnl = [ev[len(ev)//2:] for ev in evl]
      wtdnl = [wt[len(wt)//2:] for wt in wtl]
      rhor_dn = rho_of_r(mesh, gvl, evdnl, wtdnl)
      return rhor_up, rhor_dn
    else:
      msg = 'cannot calculate spin-resolved density for lsda=%s' % lsda
      raise RuntimeError(msg)
  rhor = rho_of_r(mesh, gvl, evl, wtl)
  return rhor
