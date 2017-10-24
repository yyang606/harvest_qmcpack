# Author: Yubo "Paul" Yang
# Email: yubo.paul.yang@gmail.com
# Routines to roughly process scalar Dataframes. Mostly built around pandas's API.
import numpy as np
import pandas as pd
from qharv.reel.scalar_dat import error

def list2df(df_of_list,cols):
  """ convert a dataframe of lists to a dataframe of series,
   assuming df_of_list has 1 column
   Args:
    df_of_list (pd.DataFrame): dataframe of lists
    cols (list): a list of names, must be the same length as each list in df_of_list
   Returns:
    pd.DataFrame: a dataframe of pd.Series
   """
  data = {}
  for idx in df_of_list.index:
    mylist = df_of_list.loc[idx]
    assert len(mylist) == len(cols)
    # construct entry from list
    icol = 0
    entry= {}
    for col in cols:
      entry[col] = mylist[icol]
      icol += 1
    # end for
    data[idx] = entry
  # end for idx
  df = pd.DataFrame(data).T
  return df
# end def list2df

def mean_error_scalar_df(df,nequil,labels=['path','fout']):
  """ get mean and average from a dataframe of raw scalar data (per-block) 
   take dataframe having columns ['LocalEnergy','Variance',...] to a 
   dataframe having columns ['LocalEnergy_mean','LocalEnergy_error',...]
   Args:
    df (pd.DataFrame): raw scalar dataframe, presumable generated using
     qharv.scalar_dat.parse with extra labels columns added to identify
     the different runs.
    nequil (int): number of equilibration blocks to throw out for each run.
    labels (list,optional): extra labels added to identifiy runs, by default
     labels=['path','fout'], namely the runs are identified by their scalar.dat
     filename.
   Returns:
    pd.DataFrame: mean_error dataframe 
  """

  # sort values by simulation block index, important for equilibration cut
  df.sort_values('index',inplace=True)

  # create dataframe of mean
  mdf = df.groupby(labels).apply(lambda x:np.mean(x[nequil:]))

  # create dataframe of error
  # each entry is a list because error cannot be applied to matrix yet
  elist_df = df.groupby(labels).apply(
     lambda x:np.apply_along_axis(error,0
      ,x[nequil:].drop(labels,axis=1))
  )

  # convert dataframe of list to dataframe of series
  cols = df.drop(labels,axis=1).columns
  edf =list2df(elist_df,cols)

  df1 = mdf.reset_index().drop('index',axis=1)
  df2 = edf.reset_index().drop('index',axis=1)

  jdf = df1.join(df2,lsuffix='_mean',rsuffix='_error')
  return jdf
# end def