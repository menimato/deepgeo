import numpy as np
import os
import sys
from importlib import reload
from datetime import datetime
import tensorflow as tf

sys.path.insert(0, '../../src')
import deepgeo.networks.model_builder as mb
import deepgeo.networks.loss_functions as lossf

# # Load input Dataset

network = 'unet_lf'
fusion = 'late'
DATA_DIR = '/home/raian/doutorado/Dados/generated'

class_names = ['no_data', 'not_deforestation', 'deforestation', 'clouds']

DATASET = os.path.join(DATA_DIR, 'dataset_316x316_def_one_cl_rm_nd_timestack_SR-2014-2017')
train_tfrecord = os.path.join(DATASET, 'dataset_train.tfrecord')
test_tfrecord = os.path.join(DATASET, 'dataset_test.tfrecord')
val_dataset = os.path.join(DATASET, 'dataset_valid.npz')
# val_tfrecord = os.path.join(DATASET, 'dataset_validation.tfrecord')

model_dir = os.path.join(DATA_DIR, 'tf_logs', 'experiments', 'unet', 'def_one_class_SR', 'fusion_%s' % fusion, 
                         'test_%s_%s' % (network, datetime.now().strftime('%Y_%m_%d-%H_%M_%S')))

weights_train = lossf.compute_weights_mean_proportion(train_tfrecord, class_names , ['no_data'])
weights_eval = lossf.compute_weights_mean_proportion(test_tfrecord, class_names , ['no_data'])

# Train the Network
params = {
    'network': network,
    'epochs': 100,
    'batch_size': 15,
    # 'chip_size': 286,
    'chip_size': 316,
    'bands': 10, 
    # 'filter_reduction': 0.5,
    'learning_rate': 0.1,
    'learning_rate_decay': True,
    'decay_rate': 0.95,
    'l2_reg_rate': 0.0005,
    # 'var_scale_factor': 2.0,  # TODO: Put the initializer as parameter
    'chips_tensorboard': 2,
    # 'dropout_rate': 0.5,  # TODO: Put a bool parameter to apply or not Dropout
    'fusion': fusion,
    'loss_func': 'avg_soft_dice',
    'data_aug_ops': ['rot90', 'rot180', 'rot270', 'flip_left_right',
                     'flip_up_down', 'flip_transpose'],
    'data_aug_per_chip': 4,
    'class_weights': {'train': weights_train, 'eval': weights_eval},
    'num_classes': len(class_names),
    'class_names': class_names,
    'num_compositions': 2,
    'bands_plot': [[1, 2, 3], [6, 7, 8]],
    'notes': 'Testing bigger chip size and avg soft dice as loss. Testing dataset with all no data removed.'
}


model = mb.ModelBuilder(params)
model.train(train_tfrecord, test_tfrecord, model_dir)

dataset = np.load(val_dataset)
model.validate(dataset['chips'], dataset['labels'], model_dir, show_plots=False, exclude_classes=[])
#model.validate(val_tfrecord, params, model_dir, show_plots=False)
