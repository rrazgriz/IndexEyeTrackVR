# Copyright 2022-2022 Razgriz
# SPDX-License-Identifier: MIT

import numpy as np
import math
import scipy
import scipy.interpolate
import cv2

## Utility Functions
# Convert a tuple to a list of ints
def tupint(tup):
    return [int(tup[0]), int(tup[1])]

# Normalize a numpy array
def normalize(nparray):
    return nparray / np.linalg.norm(nparray)

# Limit a value to a specific range
def saturate(val, low=-1, high=1):
    if val < low:
        return low
    elif val > high:
        return high
    else:
        return val

# Alias the above
def clamp(val, low=-1, high=1):
    return saturate(val, low, high)

def exp_smooth(value, value_smooth, alpha = 0.5):
    return value * alpha + value_smooth * (1.0 - alpha)

# Exponentially smooth a value using a time delta and time constant
def exp_smooth_dt(value, value_smooth, dt=1/60, tau=4/60):
    alpha = 1 - np.exp(-dt/tau)
    return exp_smooth(value, value_smooth, alpha)

# Interpolate between two values
def lerp(a, b, x):
    return a + (b-a)*x

# Find the interpolation of a value between two values
def inverse_lerp(a, b, v):
    return (v - a) / (b - a)

# Map one range to another and output the value's equivalent in the new range
def remap(i_min, i_max, o_min, o_max, v):
    return lerp(o_min, o_max, inverse_lerp(i_min, i_max, v))



## OpenCV utility/display functions
# Pass a frame and list of points to draw lines to (center first) return frame with lines drawn
def draw_calibration(img, cal_points, col = (255, 127, 0), thick=1):
    im = img
    for point in cal_points:
        cv2.line(im, tupint(cal_points[0]), tupint(point), col, thickness=thick)
    return im

# Return a frame with keypoints drawn on
def draw_keypoints(frame, keypoints, col = (255,127,0)):
    return cv2.drawKeypoints(frame, keypoints, np.array([]), col, cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    
# Return a frame with a circle drawn on
def draw_circle(frame, circlex, circley, size=30, col=(255,127,0), thick=2):
    return cv2.circle(frame, (circlex*3, circley*3), size, col, thick)

# get percentage of black in image (0-1)
def getBlackProportion(frame):
    frame_size = frame.shape[0] * frame.shape[1]

    if len(frame.shape) == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)


    r,black = cv2.threshold(frame,127,255,cv2.THRESH_TOZERO)
    
    nonzero = (cv2.countNonZero(black))

    return float((frame_size - nonzero) / (frame_size))



## Process frame to detect blobs
def process_frame(fr, blob_detector, threshold = 127, crop=()):
    if crop is not ():
        x_1, x_w = (crop[0][0], crop[0][1])
        y_1, y_w = (crop[1][0], crop[1][1])
        frame = fr[x_1:x_1+x_w, y_1:y_1+y_w]
    else:
        frame = fr

    # convert non grayscale image
    if len(frame.shape) == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    ret,frame = cv2.threshold(frame,threshold,255, cv2.THRESH_BINARY)
    keypoints = blob_detector.detect(frame)
    
    maxarea = 0
    maxareapt = [0.0, 0.0]
    
    kp = None
    
    if len(keypoints)>0:
        for kp in keypoints:
            if kp.size > maxarea:
                maxarea = kp.size
                maxareapt = kp.pt
    
    return np.array(maxareapt), frame, keypoints

# Nearest neighbor extrapolation of griddata based on NaN Mask
def extrapolate_nans(x_values, y_values, values):
    if np.ma.is_masked(values):
        nans = values.mask
    else:
        nans = np.isnan(values)
        
    notnans = np.logical_not(nans)
    values[nans] = scipy.interpolate.griddata((x_values[notnans], y_values[notnans]), values[notnans],
        (x_values[nans], y_values[nans]), method='nearest').ravel()
    return values

# Generate luts given a list of cal points and cal values
def generate_luts(cal_points, cal_values, grid_width, grid_height):
    # create evenly spaced grid
    grid_x, grid_y = np.mgrid[range(0, grid_width, 1), range(0, grid_height, 1)]

    # build grid data and extrapolate with nearest neighbor using NaN mask
    lx = scipy.interpolate.griddata(cal_points, cal_values[:,0], (grid_x, grid_y), method='linear', fill_value=np.nan)
    lx = extrapolate_nans(grid_x, grid_y, lx)

    ly = scipy.interpolate.griddata(cal_points, cal_values[:,1], (grid_x, grid_y), method='linear', fill_value=np.nan)
    ly = extrapolate_nans(grid_x, grid_y, ly)
    
    return lx, ly

# Generate calibration luts from center frame and calibration frames
def generate_calibration(frames_cal, points_cal, detector, threshold=127, crop=()):
    cal_positions  = []
    cal_keypoints   = []

    for frame in frames_cal:
        cal_point, proc, k = process_frame(frame, detector, threshold, crop)
        cal_keypoints.append(k)
        cal_positions.append(cal_point)

    lx, ly = generate_luts(cal_positions, points_cal, crop[0][1], crop[1][1])

    return lx, ly, cal_positions, cal_keypoints
    
# Calculate gaze given point and luts
def calculate_gaze(point, lx, ly):
    p_x, p_y = (int(point[0]), int(point[1]))
    g_x, g_y = (lx[int(p_x), int(p_y)], ly[int(p_x), int(p_y)])
    g_x, g_y = (saturate(g_x), saturate(g_y))
    return np.array([g_x, g_y])