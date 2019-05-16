import numpy as np
import os
import sys
from importlib import reload
from datetime import datetime
import tensorflow as tf

sys.path.insert(0, '../../src')
import deepgeo.dataset.data_augment as dtaug
import deepgeo.dataset.utils as dsutils
import deepgeo.networks.model_builder as mb

# # Load input Dataset

# In[ ]:


# DATA_DIR = os.path.join(os.path.abspath(os.path.dirname('__file__')), '../', 'data_real', 'generated')
network = 'unet'
DATA_DIR = '/home/raian/doutorado/Dados/generated'
DATASET_FILE = os.path.join(DATA_DIR, 'new_dataset_286x286_timesstack-2013-2017.npz')

train_tfrecord = os.path.join(DATA_DIR, 'train.tfrecord')
test_tfrecord = os.path.join(DATA_DIR, 'test.tfrecord')
val_tfrecord = os.path.join(DATA_DIR, 'validation.tfrecord')

model_dir = os.path.join(DATA_DIR, 'tf_logs', 'experiments', network,
                         'test_%s_%s' % (network, datetime.now().strftime('%d_%m_%Y-%H_%M_%S')))
# model_dir = '/home/raian/doutorado/deepgeo/data_real/generated/tf_logs/test_debug'
#model_dir = os.path.join(DATA_DIR, 'tf_logs', 'test_unet_lf_17_12_2018-22_39_13')

# In[ ]:

dataset = np.load(DATASET_FILE)

print('Data Loaded:')
print('  -> Images: ', len(dataset['images']))
print('  -> Labels: ', len(dataset['labels']))
print('  -> Classes: ', len(dataset['classes']))

print('Images shape: ', dataset['images'][0].shape, ' - DType: ', dataset['images'][0].dtype)
print('Labels shape: ', dataset['labels'][0].shape, ' - DType: ', dataset['labels'][0].dtype)
# print('UNIQUE LABELS: ', np.unique(dataset['labels']))


# # Split dataset between train, test and validation data

# In[ ]:

train_images, test_images, valid_images, train_labels, test_labels, valid_labels = dsutils.split_dataset(dataset,
                                                                                                         perc_test=20,
                                                                                                         perc_val=20)

print('Splitted dataset:')
print('  -> Train images: ', train_images.shape)
print('  -> Test images: ', test_images.shape)
print('  -> Validation images: ', valid_images.shape)
print('  -> Train Labels: ', train_labels.shape)
print('  -> Test Labels: ', test_labels.shape)
print('  -> Validation Labels: ', valid_labels.shape)

def wrap_bytes(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))

def wrap_float(value):
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))

def wrap_int64(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))

def save_to_tfrecord(out_path, imgs, labels):
    with tf.python_io.TFRecordWriter(out_path) as writer:
        for i in range(imgs.shape[0]):
            img = imgs[i, :, :, :]
            lbl = labels[i, :, :, :]
            
            height = img.shape[0]
            width = img.shape[1]
            channels = img.shape[2]
            
            img_raw = img.tostring()
            lbl_raw = lbl.tostring()
            
            feature = {'image': wrap_bytes(img_raw),
                       'label': wrap_bytes(lbl_raw),
                       'channels': wrap_int64(channels),
                       'height': wrap_int64(height),
                       'width': wrap_int64(width)}
            
            example = tf.train.Example(features=tf.train.Features(feature=feature))
            writer.write(example.SerializeToString())

save_to_tfrecord(train_tfrecord, train_images, train_labels)
save_to_tfrecord(test_tfrecord, test_images, test_labels)
save_to_tfrecord(val_tfrecord, valid_images, valid_labels)

# # Perform Data Augmentation

#angles = [90, 180, 270]
#rotated_imgs = dtaug.rotate_images(train_images, angles)
#flipped_imgs = dtaug.flip_images(train_images)

#train_images = np.concatenate((train_images, rotated_imgs))
#train_images = np.concatenate((train_images, flipped_imgs))

#rotated_lbls = dtaug.rotate_images(train_labels, angles)
#flipped_lbls = dtaug.flip_images(train_labels)

#train_labels = np.concatenate((train_labels, rotated_lbls))
#train_labels = np.concatenate((train_labels, flipped_lbls)).astype(dtype=np.int32)

#print('Data Augmentation Applied:')
#print('  -> Train Images: ', train_images.shape)
#print('  -> Train Labels: ', train_labels.shape)
#print('  -> Test Images: ', test_images.shape)
#print('  -> Test Labels: ', test_labels.shape)


# TODO: Put this in the __get_loss() in the model builder. Or create a class Losses.
def compute_weights_mean_proportion(batch_array, classes, classes_zero=['no_data']):
    values, count = np.unique(batch_array, return_counts=True)
    count = [count[i] if classes[i] not in classes_zero else 0 for i in range(0, len(count))]
    total = sum(count)
    proportions = [i / total for i in count]
    mean_prop = sum(proportions)/ (len(proportions) - len(classes_zero))
    weights = [mean_prop / i if i != 0 else 0 for i in proportions]
    return weights


weights_train = compute_weights_mean_proportion(train_labels, dataset['classes'])
weights_eval = compute_weights_mean_proportion(test_labels, dataset['classes'])


# # Train the Network


# # Train the Network

params = {
    'epochs': 100,
    'batch_size': 40,
    'filter_reduction': 0.5,
    'learning_rate': 0.1,
    'learning_rate_decay': True,
    'decay_rate': 0.95,
    # 'decay_steps': 1286,
    'l2_reg_rate': 0.0005,
    # 'var_scale_factor': 2.0,  # TODO: Put the initializer as parameter
    'chips_tensorboard': 2,
    # 'dropout_rate': 0.5,  # TODO: Put a bool parameter to apply or not Dropout
    'fusion': 'early',
    'loss_func': 'weighted_crossentropy',
    'class_weights': {'train': weights_train, 'eval': weights_eval},
    'num_classes': len(dataset['classes']),
    'num_compositions': 2,
    'bands_plot': [[1, 2, 3], [6, 7, 8]],
    'Notes': 'Migrating to TFRecord and MirroredStrategy. All Data Augmentation!'
}


reload(mb)
model = mb.ModelBuilder(network)
model.train(train_tfrecord, test_tfrecord, params, model_dir)
