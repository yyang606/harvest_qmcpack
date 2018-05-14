# Author: Yubo "Paul" Yang
# Email: yubo.paul.yang@gmail.com
# Routines to manipulate an xml input. 
#  Almost all functions are built around the lxml module's API.
#  The central object is lxml.etree.ElementTree, which is usually named "doc".
import os
import numpy as np
from copy import deepcopy
from lxml import etree
from io import StringIO

# ======================== level 0: basic io =========================
def read(fname):
  """ read an xml file 
  wrap around lxml.etree.parse
  Args:
    fname (str): filename to read from
  Returns:
    lxml.etree._ElementTree: doc, parsed xml document
  """
  parser = etree.XMLParser(remove_blank_text=True)
  doc    = etree.parse(fname,parser)
  return doc

def write(fname,doc):
  """ write an xml file 
  wrap around lxml.etree._ElementTree.write
  Args:
    fname (str): filename to write to
    doc (lxml.etree._ElementTree): xml file in memory
  Effects:
    write fname using contents of doc
  """
  doc.write(fname,pretty_print=True)

def parse(text):
  """ parse the text representation of an xml node
  Args:
    text (str): string representation of an xml node
  Returns:
    lxml.etree._Element: root, parsed xml node
  """
  try:  # Python2
    root = read( StringIO(text.decode()) ).getroot()
  except AttributeError:  # Python3
    root = read( StringIO(text) ).getroot()
  return root

def str_rep(node):
  """ return the string representation of an xml node
  Args:
    node (lxml.etree._Element): xml node
  Returns:
    str: string representation of node
  """
  return etree.tostring(node,pretty_print=True)

def show(node):
  print( str_rep(node) )

def ls(node,r=False,level=0,indent="  "):
  """ List directory structure
   
   Similar to the Linux `ls` command, but for an xml node

   Args:
     node (lxml.etree._Element): xml node
     r (bool): recursive
     level (int): level of indentation, used only if r=True
     indent (str): indent string, used only if r=True
   Returns:
     str: mystr, a string representation of the directory structure
  """
  mystr=''
  children = node.getchildren()
  if len(children)>0:
    for child in children:
      if type(child) is not etree._Element: continue
      mystr += indent*level + child.tag + '\n'
      if r:
        mystr += ls(child,r=r,level=level+1,indent=indent)
      # end if r
    # end for child
  else:
    return ''
  # end if
  return mystr

# ========================= level 1: node content io =========================
#  node.get & node.set are sufficient for attribute manipulation
# level 1 routines are needed for node.text and node.children manipulation
def arr2text(arr):
  """ format a numpy array into a text string """
  text = ''
  if len(arr.shape) == 1: # vector
      text = " ".join(arr.astype(str))
  elif len(arr.shape) == 2: # matrix
      mat  = [arr2text(line) for line in arr]
      text = "\n" + "\n".join(mat) + "\n"
  else:
      raise RuntimeError('arr2text can only convert vector or matrix.')
  # end if
  return text
# end def arr2text

def text2arr(text,dtype=float,flatten=False):
  """ convert a text string into a numpy array """
  tlist = text.strip(' ').strip('\n').split('\n')
  if len(tlist) == 1:
    return np.array(tlist,dtype=dtype)
  else:
    if flatten:
      mytext = '\n'.join(['\n'.join(line.split()) for line in tlist])
      myarr = text2arr(mytext)
      return myarr.flatten()
    else:
      return np.array([line.split() for line in tlist],dtype=dtype)
    # end if
  # end if
# end def text2arr

# ================= level 2: QMCPACK specialized read =================


def get_param(node,pname):
  """ retrieve the str representation of a parameter from: 
    <parameter name="pname"> str_rep </parameter>
  Args:
    node (lxml.etree._Element): xml node with <parameter>.
    pname (str): name of parameter
  Return:
    str: string representation of the parameter value
  """
  pnode = node.find('.//parameter[@name="%s"]'%pname)
  return pnode.text
# end def


def set_param(node,pname,pval,new=False):
  """ set <parameter> with name 'pname' to 'pval' 
  if new=True, then <parameter name="pname"> does not exist. create it
  Args:
    node (lxml.etree._Element): xml node with children having tag 'parameter'
    pname (str): name of parameter
    pval (str): value of parameter
    new (bool): create new <paremter> node, default is false
  Effect:
    the text of <parameter> with 'pname' will be set to 'pval'
  """
  assert type(pval) is str
  pnode = node.find('.//parameter[@name="%s"]'%pname)
  # 4 paths dependent on (pnode is None) and new
  if (pnode is None) and (not new): # unintended input
    raise RuntimeError('<parameter name="%s"> not found in %s\n\
      please set new=True' % (pname,node.tag))
  elif (pnode is not None) and new: # unintended input
    raise RuntimeError('<parameter name="%s"> found in %s\n\
      please set new=False' % (pname,node.tag))
  elif (pnode is None) and new:
    pnode = etree.Element('parameter',{'name':pname})
    pnode.text = pval
    node.append(pnode)
  else:
    pnode.text = pval
  # end if
# end def


def get_axes(doc):
  sc_node = doc.find('.//simulationcell')
  if sc_node is None:
    raise RuntimeError('<simulationcell> not found')
  lat_node = sc_node.find('.//parameter[@name="lattice"]')
  unit = lat_node.get('units')
  assert unit == 'bohr'
  axes = text2arr( lat_node.text )
  return axes
# end def 


def get_pos(doc,pset='ion0',all_pos=True,group=None):
  # find <particleset>
  pset_node = doc.find('.//particleset[@name="%s"]'%pset)
  if pset_node is None:
    raise RuntimeError('%s not found'%pset)
  
  # find <group> if necessary
  groups = pset_node.findall('.//group')
  names = [grp.get('name') for grp in groups]
  if (group is None): # no group give, better be requesting all particle positions
    if (not all_pos):
      warn_msg = '%d groups found, please specify particle group from %s'%(len(groups),str(names))
      raise RuntimeError(warn_msg)
    # end if
  else: # group given, see if it is available
    if (all_pos): raise RuntimeError('specified group will be over-written with all_pos! Please set all_pos=False.')
    if (group not in names):
      raise RuntimeError('no group with name "%s" in %s'%(group,str(names)))
    # end if
  # end if

  pos_text = ''
  if not all_pos: # get requested group positions
    grp = pset_node.find('.//group[@name="%s"]'%group)
    pos_node = grp.find('.//attrib[@name="position"]')
    pos_text = pos_node.text
  else:
    for grp in groups:
      pos_node  = grp.find('.//attrib[@name="position"]')
      pos_text += pos_node.text.strip('\n')+'\n'
    # end for
  # end if

  # get requestsed particle positions
  pos = text2arr(pos_text.strip('\n'))
  return pos
# end def


# ================= level 3: QMCPACK specialized construct =================


def build_coeff(knots, **attribs):
  """ construct an <coefficients/> 

  example:
    build_coeff([1,2]): 
      <coefficients id="new" type="Array"> 1 2 </coefficients>

  Args:
    knots (list): a list of numbers
  Return:
    lxml.etree._Element: <coefficients/>
  """

  # add required attributes
  #id (str, optional): coefficient name, default 'new'
  if not 'id' in attribs:
    attribs['id'] = 'new'
  #type (str, optional): coefficient type, default 'Array'
  if not 'type' in attribs:
    attribs['type'] = 'Array'

  # construct node
  coeff_node = etree.Element('coefficients',attribs)
  coeff_node.text = ' ' + ' '.join( map(str,knots) ) + ' '  # 1D arr2text
  return coeff_node
# end def build_coeff


def build_jk2_iso(coeffs, kc):
  """ construct isotropic e-e reciprocal space Jastrow node

  example:
    build_jk2([1,2], 0.4):

  Args:
    coefs (list): a list of numbers at the
    kc (float): k space cutoff in a.u.
  Return:
    lxml.etree._Element: <jastrow/>
  """
  coeff_node = build_coeff(coeffs, id='cG2')
  corr_node = etree.Element('correlation', {
    'type':'Two-Body'
    , 'kc':str(kc)
    , 'symmetry':'isotropic'
  })
  corr_node.append(coeff_node)

  jk_node = etree.Element('jastrow',{
    'name':'Jk'
    , 'type':'kSpace'
    , 'source':'e'
  })
  jk_node.append(corr_node)
  return jk_node


# ================= level 4: QMCPACK specialized advanced =================

def turn_off_jas_opt(wf_node):
  # turn off jastrow optimization
  all_jas = wf_node.findall('.//jastrow')
  assert len(all_jas) > 0
  for jas in all_jas:
    assert jas.tag == 'jastrow'
    for coeff in jas.findall('.//coefficients'):
      coeff.set('optimize','no')
    # end for
  # end for
# end def


def opt_wf_fname(opt_inp,iqmc):
  """ Find the file containing the optimized <wavefunction> at optimization loop iqmc 
  example of a folder containing an optimization run:
  $ls opt_dir
    opt.xml
    qmc.s000.scalar.dat
    qmc.s000.opt.xml
    qmc.s001.scalar.dat
    qmc.s001.opt.xml
  $
  opt_wf_fname('opt_dir/opt.xml',1) returns 'opt_dir/qmc.s001.opt.xml'

  Args:
    opt_inp (str): optimization run input file
    iqmc (int): optimization loop to target
  Returns:
    str: wf_fname, name of the xml file containing the optimized <wavefunction>
  """

  # read the optimization input for nqmc & prefix to find .opt files
  doc = read(opt_inp)
  nqmc   = int( doc.find('.//loop').get('max') )
  assert iqmc < nqmc

  # read project prefix to determine .opt filename
  prefix = doc.find('.//project').get('id')
  stext  = 's'+str(iqmc).zfill(3)
  fopt   = '.'.join([prefix,stext,'opt','xml'])

  # return location of file
  opt_dir  = os.path.dirname(opt_inp)
  wf_fname = os.path.join(opt_dir,fopt)

  return wf_fname
# end def opt_wf_fname


def swap_in_opt_wf(doc,wf_node):
  """ Put an optimized wavefunction into an xml input 

  Designed to help continue a wavefunction optimization. One can also use optimized wavefunction in a VMC or DMC calculation, but the <loop> section will have to be removed, and new <qmc> sections added. See xml_examples.py.

  Args:
    doc (lxml.etree._ElementTree): xml input having an old <wavefunction>
    wf  (lxml.etree._Element): xml node containing the optimized <wavefunction>
  Returns:
    lxml.etree._ElementTree: xml input with optimized wavefunction """

  # find new <wavefunction>
  wf1 = wf_node.find('.//wavefunction')
  if (wf1 is None) and (wf_node.tag == 'wavefunction'):
    wf1 = wf_node
  # end if
  assert wf1 is not None
  wf0 = doc.find('.//wavefunction')
  assert wf0 is not None

  # swap <wavefunction>
  wup = wf0.getparent()
  idx = wup.index(wf0)
  wup.remove(wf0)
  wup.insert(idx,wf1)

  return doc
# end def swap_in_opt_wf


def add_bcc_backflow(wf_node,bf_node):
  # make sure inputs are not scrambled
  assert wf_node.tag == 'wavefunction'
  assert bf_node.tag == 'backflow'

  # make a copy of wavefunction
  mywf = deepcopy(wf_node)

  # insert backflow block
  dset = mywf.find('.//determinantset')
  dset.insert(0,bf_node)

  # use code path where <backflow> optimization still works
  bb = None # find basis set builder, should be either <sposet_builder> or <determinantset>
  spo = mywf.find('.//sposet_builder') # !!!! warning: only the first builder is modified
  if spo is None:
    bb = dset
  else:
    bb = spo
  # end if
  assert bb.tag in ('sposet_builder','determinantset')
  bb.set('use_old_spline','yes')
  bb.set('precision','double')
  bb.set('truncate','no')
  return mywf
# end def add_bcc_backflow


def dset2spo(wf_node,det_map):
  """ change <wavefunction> from old style, <basis> in <determinantset>, to new style, <basis> in <sposet_builder>
  Args:
    wf_node (etree.Element): <wavefunction> node
    det_map (dict): determinant name -> particle group name e.g. {'updet':'u','downdet':'d'}
  Returns:
    None
  """
  # convert between sposet name and determinant id
  d2sname = lambda x:'spo_'+det_map[x]
  # construct <sposet_builder> using nodes from <determinantset>
  dset = wf_node.find('.//determinantset')
  bb = etree.Element('sposet_builder',dset.attrib)

  # add <basisset> to bb
  bb.append(dset.find('.//basisset'))

  # add <sposet> to bb
  dets = dset.findall('.//determinant')
  s2dname = {} # save spo_name -> det_id
  for det in dets:
    det.tag = 'sposet'
    det_id = det.get('id')
    if det_id not in det_map.keys():
      raise RuntimeError('%s not in det_map'%det_id)
    # end if
    spo_name = d2sname(det_id)
    s2dname[spo_name] = det_id
    det.set('name',spo_name)
    det.attrib.pop('id')
    bb.append(det)
  # end for det

  # replace <determinantset> with <sposet_builder>
  idx = wf_node.index(dset)
  wf_node.insert(idx,bb)
  wf_node.remove(dset)

  # rewrite <determinantset>
  dset = etree.Element('determinantset')
  slater = etree.Element('slaterdeterminant')
  for spo_name in s2dname.keys():
    det_id = s2dname[spo_name]
    group  = det_map[det_id]
    det = etree.Element('determinant',{'id':det_id,'group':group,'sposet':spo_name})
    slater.append(det)
  # end for spo_name
  dset.append(slater)

  wf_node.insert(idx+1,dset)
# end def dset2spo
