# Copyright 2022-2022 Razgriz
# SPDX-License-Identifier: MIT

# Only display stream for debugging

import os
import time
import configparser
import pathlib
import logging
import datetime
from ast import literal_eval 
from pythonosc import udp_client
from collections import deque
import cv2

from eyetrackingutil import *

def timestamp_now():
    return datetime.datetime.now().strftime('%Y-%d-%m_%H-%M-%S')

# Setup basics, read config
start_time = timestamp_now()

path = str(pathlib.Path(__file__).parent.absolute())

config = configparser.ConfigParser()
config.read(path + '\\eyetracking_config.cfg')

log_level = int(config['eyetrack']['log_level'])
log_folder = config['eyetrack']['log_folder']

log_folder_path = f'{path}{log_folder}'
if not os.path.exists(log_folder_path):
    os.makedirs(log_folder_path)

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=log_level)

logging.info('Started Eyetracking program')

data_path = path + config['eyetrack']['data_path']

# Get video source

use_stream = literal_eval(config['eyetrack']['use_stream'])
stream_address = config['eyetrack']['stream_address']
video_file_name = config['eyetrack']['video_file_name']

if use_stream:
    cap = cv2.VideoCapture(stream_address, cv2.IMREAD_GRAYSCALE)
    logging.info('Loading stream from ' + stream_address)
else:
    cap = cv2.VideoCapture(data_path + video_file_name, cv2.IMREAD_GRAYSCALE)
    logging.info('Loading stream from ' + video_file_name)

## Image cropping bounds (start pixel, size)
x1, xw = literal_eval(config['eyetrack']['roi_x'])
y1, yw = literal_eval(config['eyetrack']['roi_y'])
crop_bounds = ((x1, xw), (y1, yw))

## Threshold used for filtering
thresh = int(config['eyetrack']['threshold'])

display_size = literal_eval(config['eyetrack']['display_size'])
show_original_source = literal_eval(config['eyetrack']['show_original_source'])

# OpenCV nicer exit
is_quitting = False

logging.info('Starting Eye Tracking')

# Just gonna send it bud
while True:
    # Capture frame-by-frame
    start = time.time()

    ret, f = cap.read()

    frame = f

    # if frame is read correctly ret is True
    if not ret:
        logging.info('Cannot receive frame (stream end?). Exiting ...')
        break

    ret,frame = cv2.threshold(frame,thresh,255, cv2.THRESH_BINARY)

    cv2.imshow('Thresholded', frame)
    cv2.imshow('Thresholded Crop', frame[x1:x1+xw, y1:y1+yw])
    cv2.imshow('Source', f)
    cv2.imshow('Source Crop', f[x1:x1+xw, y1:y1+yw])


    if cv2.waitKey(25) == ord('q'):
        is_quitting = True
        break


# If the user didn't exit early, wait for key entry
if not is_quitting:
    cv2.waitKey(0)

cv2.destroyAllWindows()
logging.info('Closed Eyetracking program')
