# Copyright 2022-2022 Razgriz
# SPDX-License-Identifier: MIT

import os
import time
import configparser
import pathlib
import logging
import datetime
import cv2
from ast import literal_eval 
from pythonosc import udp_client

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
    filename=f'{path}{log_folder}eyetracking-{start_time}.log', 
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


## Set Up Simple Blob detector
params = cv2.SimpleBlobDetector_Params()
params.filterByArea         = literal_eval(config['eyetrack']['filter_by_area'])
params.minArea              = int(config['eyetrack']['min_area'])
params.filterByInertia      = literal_eval(config['eyetrack']['filter_by_inertia'])
params.minInertiaRatio      = float(config['eyetrack']['min_inertia_ratio'])
params.filterByCircularity  = literal_eval(config['eyetrack']['filter_by_circularity'])
params.filterByConvexity    = literal_eval(config['eyetrack']['filter_by_convexity'])

detector = cv2.SimpleBlobDetector_create(params)
logging.info('Initialized detector with params:')
logging.info('params.filterByArea         = ' + config['eyetrack']['filter_by_area'])
logging.info('params.minArea              = ' + config['eyetrack']['min_area'])
logging.info('params.filterByInertia      = ' + config['eyetrack']['filter_by_inertia'])
logging.info('params.minInertiaRatio      = ' + config['eyetrack']['min_inertia_ratio'])
logging.info('params.filterByCircularity  = ' + config['eyetrack']['filter_by_circularity'])
logging.info('params.filterByConvexity    = ' + config['eyetrack']['filter_by_convexity'])

## Image cropping bounds (start pixel, size)
x1, xw = literal_eval(config['eyetrack']['roi_x'])
y1, yw = literal_eval(config['eyetrack']['roi_y'])
crop_bounds = ((x1, xw), (y1, yw))

## Threshold used for filtering
thresh = int(config['eyetrack']['threshold'])

# Hardcoded calibration frames
up =     cv2.imread(data_path + 'up.png',       cv2.IMREAD_GRAYSCALE)
down =   cv2.imread(data_path + 'down.png',     cv2.IMREAD_GRAYSCALE)
left =   cv2.imread(data_path + 'left.png',     cv2.IMREAD_GRAYSCALE)
right =  cv2.imread(data_path + 'right.png',    cv2.IMREAD_GRAYSCALE)
center = cv2.imread(data_path + 'center.png',   cv2.IMREAD_GRAYSCALE)

cal_frames = [    
    center, 
    up, 
    down, 
    left, 
    right
]

# Ground-truth values for those frames
cal_values = np.array([ 
    [ 0, 0],
    [ 0, 1],
    [ 0,-1],
    [-1, 0],
    [ 1, 0]
])

lut_x, lut_y, cal_points, keypoints = generate_calibration(cal_frames, cal_values, detector, thresh, crop_bounds)

logging.info('Calibrated with points:')
for index, point in enumerate(cal_points):
    logging.info(f'ROI Pixel Position: x {point[0]}, y {point[1]}, Value: x {cal_values[index][0]}, y {cal_values[index][1]}')

gaze = np.array([0.0,0.0])
gaze_smooth = gaze
exp_smooth(gaze, gaze_smooth, 0)
gaze_fade_length = int(literal_eval(config['eyetrack']['gaze_fade_length']))
gaze_fade = np.array([np.full((gaze_fade_length,3), int(0))])

dt = 1/60
smoothing_tau = float(literal_eval(config['eyetrack']['filter_by_area']))

blink_accum = 0.0
is_blinking = False
was_blinking = False

display_size = literal_eval(config['eyetrack']['display_size'])
show_original_source = literal_eval(config['eyetrack']['show_original_source'])

# OSC Setup
osc_ip = config['osc']['osc_ip']
osc_port = int(config['osc']['osc_port'])
vrc_osc_client = udp_client.SimpleUDPClient(osc_ip, osc_port) # VRC reciever
logging.info('Initialized OSC server at ' + f'{osc_ip}:{osc_port}')

gaze_output = literal_eval(config['osc']['gaze_output'])
blink_output = literal_eval(config['osc']['blink_output'])

osc_address_gaze_x = config['osc']['osc_address_gaze_x']
osc_address_gaze_y = config['osc']['osc_address_gaze_y']
osc_address_blink  = config['osc']['osc_address_blink']

if gaze_output:
    logging.info('Outputting Gaze')
    vrc_osc_client.send_message(osc_address_gaze_x, float(gaze_smooth[0]))
    vrc_osc_client.send_message(osc_address_gaze_y, float(gaze_smooth[1]))

if blink_output:
    vrc_osc_client.send_message(osc_address_blink, False)
    logging.info('Outputting Blink')

# OpenCV nicer exit
is_quitting = False

logging.info('Starting Eye Tracking')

# Just gonna send it bud
while True:
    # Capture frame-by-frame
    start = time.time()

    ret, f = cap.read()

    # if frame is read correctly ret is True
    if not ret:
        logging.info('Cannot receive frame (stream end?). Exiting ...')
        break
    
    val, frame, keypoints = process_frame(f, detector, thresh, crop_bounds)

    
    g = calculate_gaze(val, lut_x, lut_y)
    gaze_smooth = (exp_smooth_dt(g[0], gaze_smooth[0], dt, 2/60), exp_smooth_dt(g[1], gaze_smooth[1], dt, 2/60))
    gaze = gaze_smooth
    logging.debug(f'Raw Gaze: ({round(g[0],3)},{round(g[1],3)})   Filtered Gaze: {round(gaze[0],3)},{round(gaze[1],3)}')

    if gaze_output:
        vrc_osc_client.send_message(osc_address_gaze_x, float(gaze_smooth[0]))
        vrc_osc_client.send_message(osc_address_gaze_y, float(gaze_smooth[1]))

    # Displaying image
    frame_proc = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    # Draw Cal, draw keypoints, and resize
    frame_proc = draw_calibration(frame_proc, cal_points)
    frame_proc = draw_keypoints(frame_proc,keypoints)
    frame_proc = cv2.resize(frame_proc, display_size, interpolation = cv2.INTER_AREA)

    
    frame_gaze = np.zeros_like(frame)
    frame_gaze = cv2.cvtColor(frame_gaze, cv2.COLOR_GRAY2BGR)
    # Faded trail
    np.append(gaze_fade, np.array([int((1 - (gaze[0] + 1.0) * 0.5) * xw), int((1 - (gaze[1] + 1.0) * 0.5) * yw), 255]))
    for index, point in enumerate(gaze_fade):
        if index < len(gaze_fade) - 1:
            gaze_fade[index][2] = clamp(gaze_fade[index][2] - int(255.0/float(gaze_fade_length)), 0, 255)
            pt0 = (gaze_fade[index][0], gaze_fade[index][1])
            pt1 = (gaze_fade[index+1][0], gaze_fade[index+1][1])
            cv2.line(frame_gaze, tupint(pt0), tupint(pt1), (int(gaze_fade[index][2]), 0, 0), thickness=2)
            # print(index, gaze_fade[index], gaze_fade[index+1])
    if len(gaze_fade) > gaze_fade_length:
        gaze_fade = gaze_fade[:gaze_fade_length]
    frame_gaze = cv2.resize(frame_gaze, display_size, interpolation = cv2.INTER_AREA)

    # Gaze Pos (x/y)
    frame_gaze = draw_circle(frame_gaze, int((1 - (gaze[0] + 1.0) * 0.5) * xw), int((1 - (gaze[1] + 1.0) * 0.5) * yw),10)
    # Gaze position (-1, 1)
    frame_gaze = cv2.putText(frame_gaze, str(round(gaze[0], 1))+'  '+str(round(gaze[1], 1)), (100,275), cv2.FONT_HERSHEY_SIMPLEX, .8, 255)
    # Pupil pixel position
    frame_gaze = cv2.putText(frame_gaze, str(int(val[0]))+'  '+str(int(val[1])), (100,175), cv2.FONT_HERSHEY_SIMPLEX, .8, 255)

    # Blinking stuff, very rough and maybe not working
    blackp = (getBlackProportion(frame))
    blink_accum = saturate(blink_accum + 0.2) if (blackp < 0.005) else saturate(blink_accum - 0.2)
    is_blinking = blink_accum > 0.3

    if blink_output:
        if is_blinking and not was_blinking: 
            vrc_osc_client.send_message(osc_address_blink, True)
            logging.debug('Blink/Eye Not Detected')
        if not is_blinking and was_blinking: 
            vrc_osc_client.send_message(osc_address_blink, False)
            logging.debug('Unblink/Eye Detected')
    was_blinking = is_blinking;

    end = time.time()

    dt = (end - start)
    
    # Display frames
    if show_original_source:
        cv2.imshow('Source', f)

    cv2.imshow('Processed', frame_proc)
    cv2.imshow('Gaze', frame_gaze)
    if cv2.waitKey(25) == ord('q'):
        is_quitting = True
        break
    logging.debug(f'Processing time: {round(dt * 1000, 2)}ms  Frame time:{round((time.time() - start)*1000,2)}ms')


# If the user didn't exit early, wait for key entry
if not is_quitting:
    cv2.waitKey(0)

cv2.destroyAllWindows()
logging.info('Closed Eyetracking program')
