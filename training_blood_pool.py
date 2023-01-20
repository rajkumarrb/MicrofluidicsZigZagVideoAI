#!/usr/bin/python3

import framegenerator
import cv2
import tensorflow as tf
import matplotlib.pyplot as plt
import matplotlib.animation as animation

#devices = tf.config.list_physical_devices('GPU')
#tf.config.experimental.set_memory_growth(devices[0],True)

paths_to_healthy = [ "/data/RBC-ZigZag/ALL/60xPhotron_20mBar_C001H001S0008.avi",
                     "/data/RBC-ZigZag/ALL/60xPhotron_20mBar_C001H001S0009.avi",
                     "/data/RBC-ZigZag/ALL/60xPhotron_20mBar_C001H001S0010.avi" ]

paths_to_ill = [ "/data/RBC-ZigZag/ALL/60xPhotron_20mBar_2___FA3_7percent_C001H001S0001.avi",
                "/data/RBC-ZigZag/ALL/60xPhotron_20mBar_2___FA3_7percent_C001H001S0002.avi",
                "/data/RBC-ZigZag/ALL/60xPhotron_20mBar_2___FA3_7percent_C001H001S0003.avi",
                "/data/RBC-ZigZag/ALL/60xPhotron_20mBar_2___FA3_7percent_C001H001S0004.avi"
]

background_subtraction_method = "rect"

crop = [[100,0],[500,120]]
clip_len = 50
fret = False
do_background_subtraction = "rect"

avi_healthy = framegenerator.AVIpool(
  paths_to_healthy,
  "Healthy",
  crop_rect = crop,
  clip_length = clip_len,
  subtract_background = background_subtraction_method)

avi_ill  = framegenerator.AVIpool(
  paths_to_ill,
  "Ill",
  crop_rect = crop,
  clip_length = clip_len,
  subtract_background = background_subtraction_method)

avi_files = [avi_healthy,avi_ill]

healthy_first_clip = avi_healthy.get_frames_of_clip(0)
#print(healthy_first_clip)
#print(healthy_first_clip.shape)

train_clips_list = range(0,400,4)
val_clips_list = range(400,500)
test_clips_list = range(400,600)

# Create the training set
output_signature = (tf.TensorSpec(shape = (None, None, None, 3), dtype = tf.float32),
                    tf.TensorSpec(shape = (), dtype = tf.int16))

fg_train = framegenerator.FrameGenerator(avi_files, train_clips_list, training=True)
train_ds = tf.data.Dataset.from_generator(fg_train,
                                          output_signature = output_signature)

for frames, labels in train_ds.take(10):
  print(labels)

fg_val = framegenerator.FrameGenerator(avi_files, val_clips_list, training=True)
val_ds = tf.data.Dataset.from_generator(fg_val,
                                          output_signature = output_signature)

# Print the shapes of the data
train_frames, train_labels = next(iter(train_ds))
print(f'Shape of training set of frames: {train_frames.shape}')
print(f'Shape of training labels: {train_labels.shape}')

val_frames, val_labels = next(iter(val_ds))
print(f'Shape of validation set of frames: {val_frames.shape}')
print(f'Shape of validation labels: {val_labels.shape}')

AUTOTUNE = tf.data.AUTOTUNE

train_ds = train_ds.cache().shuffle(1000).prefetch(buffer_size = AUTOTUNE)
val_ds = val_ds.cache().shuffle(1000).prefetch(buffer_size = AUTOTUNE)

train_ds = train_ds.batch(2)
val_ds = val_ds.batch(2)

train_frames, train_labels = next(iter(train_ds))
print(f'Shape of training set of frames: {train_frames.shape}')
print(f'Shape of training labels: {train_labels.shape}')

val_frames, val_labels = next(iter(val_ds))
print(f'Shape of validation set of frames: {val_frames.shape}')
print(f'Shape of validation labels: {val_labels.shape}')





########
## Random Keras Model

net = tf.keras.applications.EfficientNetB0(include_top = False)
net.trainable = False

model = tf.keras.Sequential([
    tf.keras.layers.Rescaling(scale=255),
    tf.keras.layers.TimeDistributed(net),
    tf.keras.layers.Dense(10),
    tf.keras.layers.GlobalAveragePooling3D()
])

model.compile(optimizer = 'adam',
              loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits = True),
              metrics=['accuracy'])

model.fit(train_ds, 
          epochs = 10,
          validation_data = val_ds,
          callbacks = tf.keras.callbacks.EarlyStopping(patience = 2, monitor = 'val_loss'))

model.summary()

# model.save('models/blood')

converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open('model.tflite', 'wb') as f:
  f.write(tflite_model)