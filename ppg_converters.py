import warnings
import tensorflow as tf

# Suppress TensorFlow deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)


import pandas as pd
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import os
import tensorflow as tf
import cv2
import sklearn.preprocessing as skp
import module 
import preprocessing
import tflib
from scipy.signal import savgol_filter



tf.keras.backend.set_floatx('float64')
tf.autograph.set_verbosity(0)

@tf.function
def sample_P2E(P, model):
    fake_ecg = model(P, training=False)
    return fake_ecg
ecg_sampling_freq = 128
ppg_sampling_freq = 128
window_size = 4
ecg_segment_size = ecg_sampling_freq * window_size
ppg_segment_size = ppg_sampling_freq * window_size
model_dir = 'weights'
Gen_PPG2ECG = module.generator_attention()
tflib.Checkpoint(dict(Gen_PPG2ECG=Gen_PPG2ECG), model_dir).restore()



def ppg_to_respiratory(ppg_signal, time, fs=100):
    resampled_ppg_signal = signal.resample(ppg_signal, len(ppg_signal) * 10)
    resampled_time = np.linspace(time[0], time[-1], len(resampled_ppg_signal))
    b, a = signal.butter(2, [0.5 / (fs / 2), 2 / (fs / 2)], btype='bandpass')
    filtered_ppg_signal = signal.filtfilt(b, a, resampled_ppg_signal)
    peaks, _ = signal.find_peaks(filtered_ppg_signal, distance=fs * 1.5, height=0.2)
    peak_times = resampled_time[peaks]
    peak_intervals = np.diff(peak_times)
    # peak_intervals = remove_outliers(peak_intervals)
    mean_peak_interval = np.mean(peak_intervals)
    respiratory_rate = 60.0 / mean_peak_interval
    respiratory_signal = np.interp(time, peak_times[:-1], peak_intervals)
    respiratory_signal = np.interp(time, peak_times[:-1], peak_intervals)
    smoothed_respiratory_signal = savgol_filter(respiratory_signal, window_length=51, polyorder=2)
    return smoothed_respiratory_signal, respiratory_rate

def remove_outliers(data, threshold=3.5):
    median = np.median(data)
    mad = np.median(np.abs(data - median))
    modified_z_scores = 0.6745 * (data - median) / mad
    outliers = np.abs(modified_z_scores) > threshold
    return data[~outliers]

def combine_csv(csv_filename):
    ppg_data = pd.read_csv(csv_filename)

    time = ppg_data['timestamp'].values
    ppg_signal = ppg_data['ppg_value'].values

    respiratory_signal, respiratory_rate = ppg_to_respiratory(ppg_signal, time)

    num_segments = len(ppg_signal) // 512
    x_ppg_segments = np.array_split(ppg_signal, num_segments)

    x_ecg_segments = []
    num_complete_segments = len(ppg_signal) // 512
    remaining_data_points = len(ppg_signal) % 512

    for i in range(num_complete_segments):
        segment = ppg_signal[i * 512: (i + 1) * 512]
        
        n_points = len(segment)
        time_resampled = np.linspace(time[i * 512], time[(i + 1) * 512 - 1], n_points)
        segment_resampled = np.interp(time_resampled, time[i * 512: (i + 1) * 512], segment)
        segment_filtered = preprocessing.filter_ppg(segment_resampled, 128)
        segment_reshaped = segment_filtered.reshape(1, -1)
        segment_normalized = skp.minmax_scale(segment_reshaped, feature_range=(-1, 1), axis=1)
        ecg_segment = sample_P2E(segment_normalized, Gen_PPG2ECG)
        ecg_segment = ecg_segment.numpy().flatten()
        x_ecg_segments.append(ecg_segment)

    if remaining_data_points > 0:
        last_segment = ppg_signal[-remaining_data_points:]
        n_points = len(last_segment)
        time_resampled = np.linspace(time[-remaining_data_points], time[-1], n_points)
        last_segment_resampled = np.interp(time_resampled, time[-remaining_data_points:], last_segment)
        last_segment_filtered = preprocessing.filter_ppg(last_segment_resampled, 128)
        last_segment_padded = np.pad(last_segment_filtered, (0, 512 - remaining_data_points), mode='constant')
        last_segment_reshaped = last_segment_padded.reshape(1, -1)
        last_segment_normalized = skp.minmax_scale(last_segment_reshaped, feature_range=(-1, 1), axis=1)
        last_ecg_segment = sample_P2E(last_segment_normalized, Gen_PPG2ECG)
        last_ecg_segment = last_ecg_segment.numpy().flatten()
        x_ecg_segments.append(last_ecg_segment)

    x_ecg = np.concatenate(x_ecg_segments)
    x_ecg = x_ecg[:len(time)]

    min_length = min(len(time), len(ppg_signal), len(x_ecg), len(respiratory_signal))


    # Normalize signals
    ppg_normalized = skp.minmax_scale(ppg_signal[:min_length], feature_range=(0, 1))
    ecg_normalized = skp.minmax_scale(x_ecg[:min_length], feature_range=(0, 1))
    resp_normalized = skp.minmax_scale(respiratory_signal[:min_length], feature_range=(-1, 1))

    # Create DataFrame using the smallest length
    df = pd.DataFrame({'Time': time,
                       'PPG': ppg_normalized,
                       'ECG': ecg_normalized,
                       'resp': resp_normalized})


    # Save to CSV
    df.to_csv(csv_filename, index=False)


# combine_csv('ppg_datamuhammadmoizgohar_gmail_com.csv')