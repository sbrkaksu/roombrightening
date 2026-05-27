import numpy as np

def sliding_window(min_idx, max_idx, middle_idx, window_half_size):
    num = max_idx - min_idx + 1
    window_size = 2 * window_half_size
    assert window_size <= num
    high_idx = np.minimum(middle_idx + window_half_size, max_idx + 1)
    low_idx = high_idx - window_size
    low_idx = np.maximum(low_idx, min_idx)
    high_idx = low_idx + window_size
    return print(low_idx, high_idx)

sliding_window(0, 21, 15, 4)

