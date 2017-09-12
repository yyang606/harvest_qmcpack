# Author: Yubo "Paul" Yang
# Email: yubo.paul.yang@gmail.com
# Routines to visualize volumetric data
import numpy as np

def isosurf(ax,vol,level_frac=0.25):
    """ draw iso surface of volumetric data on matplotlib axis at given level

    Example usage:
      from mpl_toolkits.mplot3d import Axes3D # enable 3D projection
      vol = np.random.randn(10,10,10)
      fig = plt.figure()
      ax  = fig.add_subplot(1,1,1,projection='3d')
      isosurf(ax,vol)
      plt.show()
    
    Args:
      ax (plt.Axes3D): ax = fig.add_subplot(1,1,1,projection="3d")
      vol (np.array): 3D volumetric data having shape (nx,ny,nz) 
      level_frac (float): 0.0->1.0, isosurface value as a fraction between min and max
    Returns:
      Poly3DCollection: mesh
    Effect:
      draw on ax """
    from skimage import measure
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    nx,ny,nz = vol.shape
    lmin,lmax = vol.min(),vol.max()

    level = lmin + level_frac*(lmax-lmin)
    if level<lmin or level>lmax:
        raise RuntimeError('level must be >%f and < %f'%(lmin,lmax))
    # end if

    # make marching cubes
    verts, faces, normals, values = measure.marching_cubes_lewiner(
        vol, level)

    # plot surface
    mesh = Poly3DCollection(verts[faces])
    mesh.set_edgecolor('k')
    ax.add_collection3d(mesh)
    ax.set_xlim(0,nx)
    ax.set_ylim(0,ny)
    ax.set_zlim(0,nz)
    ax.set_xlabel('x')
    ax.set_ylabel('y')
    ax.set_zlabel('z')
    return mesh
# end def isosurf

def spline_volumetric(val3d):
  """ spline 3D volumetric data onto a unit cube

  Args:
    val3d (np.array): 3D volumetric data of shape (nx,ny,nz)
  Returns:
    RegularGridInterpolator: 3D function defined on the unit cube
  """
  from scipy.interpolate import RegularGridInterpolator
  nx,ny,nz = val3d.shape
  myx = np.linspace(0,1,nx)
  myy = np.linspace(0,1,ny)
  myz = np.linspace(0,1,nz)
  fval3d = RegularGridInterpolator((myx,myy,myz),val3d)
  return fval3d
# end def

def axes_func_on_grid3d(axes,func,grid_shape):
  """ put a function define in axes units on a 3D grid
  Args:
    axes (np.array): dtype=float, shape=(3,3); 3D lattice vectors in row major (i.e. a1 = axes[0])
    func (RegularGridInterpolator): 3D function defined on the unit cube
    grid_shape (np.array): dtype=int, shape=(3,); shape of real space grid
  Returns:
    grid (np.array): dtype=float, shape=grid_shape; volumetric data
  """
  from itertools import product # iterate through grid points fast

  # make a cubic grid that contains the simulation cell
  grid = np.zeros(grid_shape)
  farthest_vec = axes.sum(axis=0)
  dxdydz = farthest_vec/grid_shape

  # fill cubic grid
  inv_axes = np.linalg.inv(axes)
  nx,ny,nz = grid_shape
  for i,j,k in product(range(nx),range(ny),range(nz)):
    rvec = np.array([i,j,k])*dxdydz
    uvec = np.dot(rvec,inv_axes)

    # skip points without data
    sel = (uvec>1.) | (uvec<0.)
    if len(uvec[sel])>0:
      continue
    # end if

    grid[i,j,k] = func(uvec)
  # end for i,j,k
  return grid
# end def axes_func_on_grid3d

