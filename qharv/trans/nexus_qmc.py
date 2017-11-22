# Author: Yubo "Paul" Yang
# Email: yubo.paul.yang@gmail.com
# Routines transplant QMC calculations setup by qmcpack/nexus.
#  reliant on qharv.reel.mole, which uses bash's `find` command
#  the `find` dependence not ideal, because this script will not
#  work on windows or mac... oh well
import os
import subprocess as sp
from qharv.reel import mole

def find_run_folders(results_dir):
  """ find all nexus-generated run folders given the results folder """
  rr_map = {} # construct a list of result-run directory map
  ref_dir = os.path.dirname(results_dir)
  res_dirl= sp.check_output(['ls',results_dir]).split('\n')[:-1]
  for res_dir in res_dirl:
    rlist = mole.files_with_regex('*'+res_dir,ref_dir,ftype='d')
    run_dirl= [] 
    for run_dir in rlist:
      if os.path.dirname(run_dir) != results_dir:
        run_dirl.append(run_dir)
      # end if
    # end for
    if len(run_dirl) != 1:
      raise RuntimeError('Expected exactly 1 run for each result. Found runs:\n%s for result %s.' % ('\n'.join(run_dirl),res_dir) )
    # end if
    rr_map[os.path.join(results_dir,res_dir)] = run_dirl[0]
  # end for
  return rr_map
# end def

def backup(ref_loc,tar_loc,execute=False,skip_exist=False,overwrite_target=False,verbose=True):
  """ essentially `rsync` from bash, but with a bunch of checks """
  path = os.path.dirname(tar_loc)
  if execute: # create folder if not already exist
    if (not os.path.isdir(path)) :
      sp.check_call(['mkdir','-p',path])
    # end if
  else:
    if verbose: print('would have created %s'%path)
  # end if
  if execute:
    write = True
    if (os.path.isdir(tar_loc) or os.path.isfile(tar_loc)):
      # target location will be overwritten, make sure this is 
      #  what the user wants
      if overwrite_target:
        write = True
      elif skip_exist:
        write = False
      else:
        raise RuntimeError('target "%s" exists, please either skip_exist or overwrite_target'%tar_loc)
      # end if
    # end if
    if write:
      out = sp.check_output(['rsync','-avz',ref_loc.strip('/')+'/',tar_loc.strip('/')])
      if verbose:
        with open('qharv_transplant.log','a') as f:
          f.write(out)
  else:
    if verbose: print('would have copied %s to %s'%(ref_loc,tar_loc))
  # end if
  return True # no error from above
# end def

def backup_calculations(ref_dir,tar_dir,subdirs,execute=False,verbose=True,**bk_kws):
  """ copy all nexus calculations listed in subdirs from ref_dir to tar_dir
  motivation: backup nexus-generated calculations and rerun with a tweak
  problem: nexus keeps a run folder and a result folder in parallel. A full backup
   must take both folders into account and keep them consistent.

  Args:
    ref_dir (str): reference directory containing calculations to backup tar_dir (str): target directory to backup (e.g. attic/)
    subdirs (list): a list of folders names generated by nexus, e.g.
     ['opt','dmc']
    bk_kws (dict): keyword arguments to pass to backup(ref_loc,tar_loc)
  Returns:
    list: a list of source-target maps backed up, this list can be used 
     to clean the backed up directory
  """

  # find the "results" folder
  rdirl = mole.files_with_regex('*results',ref_dir,ftype='d')
  assert len(rdirl) == 1 # expect 1 results folder
  rdir  = rdirl[0]

  # find one run folder for each result folder
  rr_map = find_run_folders(rdir)
  # the result->run (rr) directory map can be printed for inspection, or replace manually

  # create a plan for the backup
  for res_dir,run_dir in rr_map.iteritems():
    # create a list of souce-target maps to copy
    st_map = {}
    for subdir in subdirs:
      sub_run_dirs = mole.files_with_regex('*/'+subdir,run_dir,ftype='d')
      sub_res_dirs = mole.files_with_regex('*/'+subdir,res_dir,ftype='d')
      for mydir in sub_run_dirs+sub_res_dirs:
        rel_path = os.path.relpath(mydir,ref_dir)
        mytar = os.path.join(tar_dir,os.path.basename(ref_dir),rel_path)
        st_map[mydir] = mytar
      # end for mydir
    # end for subdir
  # end for
  #st_map[rdir] = os.path.join(tar_dir,rdir) # do NOT backup all of results

  # the source-target map (st_map) can be checked or overrode here

  # perform backup according to the source-target map
  if execute:
    import progressbar
    pbar = progressbar.ProgressBar(max_value=len(st_map))
    ifile = 0
    for source,target in st_map.iteritems():
      pbar.update(ifile+1)
      backup(source,target,execute=execute,**bk_kws)
      ifile += 1
    # end for
  else:
    if verbose: print('generated source-target map, please check return value. set execute=True to backup')
  # end if
  if verbose: print(' do not forget to backup your nexus script!')
  return st_map
# end def backup_calculations
