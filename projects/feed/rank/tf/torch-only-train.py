#!/usr/bin/env python 
# -*- coding: utf-8 -*-
# ==============================================================================
#          \file   torch-train.py
#        \author   chenghuige  
#          \date   2019-08-02 01:05:59.741965
#   \Description  
# ==============================================================================

  
from __future__ import absolute_import, division, print_function

import multiprocessing
import os
import sys

import tensorflow as tf

import evaluate as ev
import gezi
import lele
import loss
import melt
import pyt.model as base
import torch
import text_dataset
from pyt.dataset import get_dataset
from pyt.model import *
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader

flags = tf.app.flags
FLAGS = flags.FLAGS

logging = melt.logging

import horovod.torch as hvd
hvd.init()
# Horovod: pin GPU to local rank.
torch.cuda.set_device(hvd.local_rank())

def main(_):
  FLAGS.torch_only = True
  #FLAGS.valid_input = None
  melt.init()
  fit = melt.get_fit()

  FLAGS.eval_batch_size = 512 * FLAGS.valid_multiplier

  model_name = FLAGS.model
  model = getattr(base, model_name)() 

  loss_fn = nn.BCEWithLogitsLoss()

  td = text_dataset.Dataset()
  train_files = gezi.list_files(FLAGS.train_input)
  train_ds = get_dataset(train_files, td)
  
  ## speed up a bit with pin_memory==True
  ## num_workers 1 is very slow especially for validation, seems 4 workers is enough, large number dangerous sometimes 12 ok sometimes hang, too much resource seems

  #kwargs = {'num_workers': 12, 'pin_memory': True, 'collate_fn': lele.DictPadCollate()}
  #kwargs = {'num_workers': 6, 'pin_memory': True, 'collate_fn': lele.DictPadCollate()}
  kwargs = {'num_workers': 8, 'pin_memory': True, 'collate_fn': lele.DictPadCollate()}
  ## for 1 gpu, set > 8 might startup very slow
  #num_workers = int(8 / hvd.size())
  # num_workers = 0
  # pin_memory = False
  #kwargs = {'num_workers': num_workers, 'pin_memory': pin_memory, 'collate_fn': lele.DictPadCollate()}
  
  train_dl = DataLoader(train_ds, FLAGS.batch_size, shuffle=True, **kwargs)

  #kwargs['num_workers'] = max(1, num_workers)
  #logging.info('num train examples', len(train_ds), len(train_dl))

  if FLAGS.valid_input:
    valid_files = gezi.list_files(FLAGS.valid_input)
    valid_ds = get_dataset(valid_files, td)
    valid_dl = DataLoader(valid_ds, FLAGS.eval_batch_size, **kwargs)

    #kwargs['num_workers'] = max(1, num_workers)
    valid_dl2 = DataLoader(valid_ds, FLAGS.batch_size, **kwargs)
    #logging.info('num valid examples', len(valid_ds), len(valid_dl))

  fit(model,  
      loss_fn,
      dataset=train_dl,
      valid_dataset=valid_dl,
      valid_dataset2=valid_dl2,
      eval_fn=ev.evaluate,
      valid_write_fn=ev.valid_write,
      #write_valid=FLAGS.write_valid)   
      write_valid=False,
     )


if __name__ == '__main__':
  tf.app.run()  
