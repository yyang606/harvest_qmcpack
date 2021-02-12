# Author: Yubo "Paul" Yang
# Email: yubo.paul.yang@gmail.com
# Routines to manipulate QE pwscf results for use in QMCPACK
import numpy as np

# ========================== level 0: read ==========================

def input_keywords(scf_in):
  """Extract all keywords from a quantum espresso input file

  Args:
    scf_in (str): path to input file
  Return:
    dict: a dictionary of inputs
  """
  keywords = dict()
  with open(scf_in, 'r') as f:
    for line in f:
      if '=' in line:
        key, val = line.split('=')
        keywords[key.strip()] = val.strip('\n')
  return keywords

# ========================= level 1: modify =========================

def change_keyword(text, section, key, val, indent=' '):
  """Change input keyword

  Args:
    text (str): input text
    section (str): section name, must be an existing section
     e.g. ['control', 'system', 'electrons', 'ions', 'cell']
    key (str): keyword name, e.g. ecutwfc, input_dft, nosym, noinv
    val (dtype): keyword value
  Return:
    str: modified input text
  """
  from qharv.reel import ascii_out
  # find section to edit
  sname = '&' + section
  if sname not in text:
    sname = '&' + section.upper()
  if sname not in text:
    msg = 'section %s not found in %s' % (section, text)
    raise RuntimeError(msg)
  # determine keyword data type
  fmt = '%s = "%s"'
  if np.issubdtype(type(val), np.integer):
    fmt = '%s = %d'
  if np.issubdtype(type(val), np.floating):
    fmt = '%s = %f'
  line = indent + fmt % (key, val)
  # edit input
  if key in text:  # change existing keyword
    text1 = ascii_out.change_line(text, key, line)
  else:  # put new keyword at beginning of section
    text1 = ascii_out.change_line(text, sname, sname+'\n'+line)
  return text1

def ktext_frac(kpts):
  """Write K_POINTS card assuming fractional kpoints with uniform weight.

  Args:
    kpts (np.array): kpoints in reciprocal lattice units
  Return:
    str: ktext to be fed into pw.x input
  """
  line_fmt = '%8.6f %8.6f %8.6f 1'
  nk = len(kpts)
  header = 'K_POINTS crystal\n%d\n' % nk
  lines = [line_fmt % (kpt[0], kpt[1], kpt[2]) for kpt in kpts]
  ktext = header + '\n'.join(lines)
  return ktext

# ========================= level 2: cross ==========================

def copy_charge_density(scf_dir, nscf_dir, execute=True):
  """Copy charge density files from scf folder to nscf folder.

  Args:
    scf_dir (str): scf folder
    nscf_dir (str): nscf folder
    execute (bool, optional): perform file system operations, default True
      if execute is False, then description of operations will be printed.
  """
  if scf_dir == nscf_dir:
    return  # do nothing
  import os
  import subprocess as sp
  from qharv.reel import mole
  from qharv.field.sugar import mkdir
  # find charge density
  fcharge = mole.find('*charge-density.dat', scf_dir)
  save_dir = os.path.dirname(fcharge)
  # find xml file with gvector description
  fxml = mole.find('*data-file*.xml', save_dir)  # QE 5 & 6 compatible
  save_rel = os.path.relpath(save_dir, scf_dir)
  save_new = os.path.join(nscf_dir, save_rel)
  # find pseudopotentials
  fpsps = mole.files_with_regex('*.upf', save_dir, case=False)
  if execute:  # start to modify filesystem
    mkdir(save_new)
    sp.check_call(['cp', fcharge, save_new])
    sp.check_call(['cp', fxml, save_new])
    for fpsp in fpsps:
      sp.check_call(['cp', fpsp, save_new])
  else:  # state what will be done
    path = os.path.dirname(fcharge)
    msg = 'will copy %s and %s' % (
      os.path.basename(fcharge), os.path.basename(fxml))
    if len(fpsps) > 0:
      for fpsp in fpsps:
        msg += ' and %s ' % fpsp
    msg += '\n to %s' % save_new
    print(msg)
