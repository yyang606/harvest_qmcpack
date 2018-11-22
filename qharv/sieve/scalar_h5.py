import os
import h5py
import numpy as np

def twist_average_h5(fh5, **suffix_kwargs):
  """ twist average data in an HDF5 archive

  each twist should be a group in at root

  example:
    twist000
      myr
      gr_mean
      gr_error
    twist001
      myr
      gr_mean
      gr_error

  Args:
    fh5 (str): h5 file location
  Return:
    (dict, np.array, np.array): (meta data, mean, error)
  """
  fp = h5py.File(fh5)
  # determine ymean, yerror from first twist
  twist0 = fp.keys()[0]
  ymean, yerror = get_ymean_yerror(fp, twist0, **suffix_kwargs)
  # treat all other entries as metadata
  meta = {}
  for name in fp[twist0].keys():
    if name not in [ymean, yerror]:
      meta[name] = fp[os.path.join(twist0, name)].value
  # extract all ymean and yerror
  yml = []
  yel = []
  for twist in fp.keys():
    for name in fp[twist].keys():
      mpath = os.path.join(twist, ymean)
      epath = os.path.join(twist, yerror)
      yml.append(fp[mpath].value)
      yel.append(fp[epath].value)
  fp.close()
  # twist average
  ym = np.mean(yml, axis=0)
  yea = np.array(yel)
  ye = np.sqrt(np.sum(yea**2, axis=0))/len(yml)
  return meta, ym, ye

def get_ymean_yerror(fp, twist0, msuffix='_mean', esuffix='_error'):
  ymean = None
  yerror = None
  for name in fp[twist0].keys():
    if name.endswith(msuffix):
      ymean = name
    if name.endswith(esuffix):
      yerror = name
  if ymean is None:
    raise RuntimeError('no entry with suffix %s' % msuffix)
  if yerror is None:
    raise RuntimeError('no entry with suffix %s' % esuffix)
  ynamem = '_'.join(ymean.split('_')[:-1])
  ynamee = '_'.join(yerror.split('_')[:-1])
  if ynamem != ynamee:
    raise RuntimeError('yname mismatch')
  return ymean, yerror