import requests, json, getpass
import statistics

import hrv
import numpy as np
from ecgdetectors import Detectors

def getData():
    
    token_url = "https://auth.dlr.wobcom.tech/auth/realms/default/protocol/openid-connect/token"
    test_api_url = "https://api.dlr.wobcom.tech/quantumleap/v2/entities/urn:ngsiv2:Ecg:Patient01?limit=17"

    #Resource owner (enduser) credential
    RO_user = input('Enduser netid: ')
    RO_password = getpass.getpass('Enduser password: ')

    client_id = 'api'

    #step B, C - single call with resource owner credentials in the body  and client credentials as the basic auth header
    # will return access_token

    data = {'grant_type': 'password','username': RO_user, 'password': RO_password, 'scope': 'entity:read entity:write entity:delete entity:op entity:create subscription:read subscription:create subscription:write subscription:delete', 'client_id': 'api'}

    access_token_response = requests.post(token_url,data=data, verify=False, allow_redirects=False)

    tokens = json.loads(access_token_response.text)

    # Step C - now we can use the access_token to make as many calls as we want.
    api_call_headers = {'Authorization': 'Bearer ' + tokens['access_token'], 'fiware-service': 'dlr_ekg', 'fiware-servicepath': '/dlr_ekg'}
    print(api_call_headers)
    api_call_response = requests.get(test_api_url, headers=api_call_headers, verify=False)

    return np.array(json.loads(api_call_response.text)["attributes"][2]["values"])

def medfilt(data, k=17):
    """Apply a length-k median filter to a 1D-array data.
    Boundaries are extended by repeating endpoints.
    :param data: the data for which to apply the filter
    :param k: the length of the median filter. Default 17
    """

    assert k % 2 == 1, "Median filter length must be odd."

    k2 = (k - 1) // 2
    y = np.zeros((len(data), k), dtype=data.dtype)
    y[:, k2] = data
    for i in range(k2):
        j = k2 - i
        y[j:, i] = data[:-j]
        y[:j, i] = data[0]
        y[:-j, -(i + 1)] = data[j:]
        y[-j:, -(i + 1)] = data[-1]
    return np.median(y, axis=1)


def sliding_window(data, current_window_start=0, end_index=None, window_size=5*256, window_step=256):
    """
    Return an array from data that corresponds to a sliding window at the current window index with given window size.
    :param data: the array for which to calculate the sliding window
    :param current_window_start: the current window start index.
    :param end_index: An end index in the provided dataset. If None then equals to length of data.
    :param window_size: the size of the used window
    :param window_step: the amount of data used to move the window along its data
    :return: A tuple: 1. element is an array of the data. 2. element is the next window start index used for calculating
    the next data portion.
    """
    end = current_window_start + window_size

    if end > len(data):
        return None
    else:
        if end_index is not None:
            if end > end_index + 1:
                return None

    s_w_data = data[current_window_start:end]
    new_start = current_window_start + window_step
    return s_w_data, new_start


def calculate_window_heart_rates(ecg_data, sampling_rate=256, window_size=256 * 5, end_index=None, window_step=256):
    """
    Calculate heart rates for each window partition of a given ecg data set.
    :param ecg_data: the ecg data. Must be in Volt.
    :param sampling_rate: the sampling rate of the ecg signal in Hz.
    :param window_size: the window size for the sliding window
    :param end_index: An end index in the provided dataset. If None then equals to length of data.
    :param window_step: the amount of data used to move the window along its data
    :return: A 2d list with heart rates for each calculated sliding window.
    """
    detector = Detectors(sampling_rate)
    heart_rate_variability = hrv.HRV(sampling_rate)

    heart_rates_list = []

    sliding_window_running = True
    window_start = 0

    while sliding_window_running:
        result = sliding_window(ecg_data, window_start, end_index, window_size, window_step)
        if result is None:
            # sliding window of given size cannot fit the data array
            sliding_window_running = False
        else:
            r_peaks = detector.hamilton_detector(result[0])
            heart_rate = heart_rate_variability.HR(r_peaks)
            heart_rates_list.append(heart_rate)
            window_start = result[1]
    return heart_rates_list


def post_process_heart_rates(heart_rates_list, median_filter_length=17):
    """
    Apply some statistics and the median filter to a provided list of heart rates calculated via sliding window.
    :param heart_rates_list: the 2D array with lists of heart rates for each sliding window partition
    :param median_filter_length: the length of the median filter to apply.
    :return: the filtered heart rates. This is a 1d array.
    """
    avg_heart_rates = []
    for i in range(len(heart_rates_list)):
        avg_heart_rates.append(statistics.mean(heart_rates_list[i]))
    avg_heart_rates = np.array(avg_heart_rates)
    med_filtered_data = medfilt(avg_heart_rates, median_filter_length)

    return med_filtered_data


def process_ecg_signal(ecg_data, sampling_rate=256, window_size=5 * 256, end_index=None, window_step=256,
                       medfilter_length=17, check_function=None):
    """
    Check the heart rates for the given ecg data for a given check condition and return if the condition applies
    to the provided data.
    :param ecg_data: the ecg data. Is a 1d array.
    :param sampling_rate: the sampling rate of the ecg signal
    :param window_size: the size used for sliding window
    :param end_index: An end index in the provided dataset. If None then equals to length of data.
    :param window_step: the amount of data used to move the window along its data
    :param medfilter_length: the median filter length to apply in post process.
    :param check_function: a function to apply to each element of the heart rates list
    :return: True if condition function is True for an element of the calculated HR, False otherwise.
    """
    if check_function is None:
        check_function = bpm_check
    calculated_heart_rates = calculate_window_heart_rates(ecg_data, sampling_rate, window_size, end_index, window_step)
    calculated_heart_rates = post_process_heart_rates(calculated_heart_rates, medfilter_length)
    return check_function(calculated_heart_rates)


def bpm_check(data):
    """
    Simple function that iterates over a list of heart rates and checks if any bpm is over a given threshold.
    :param data: the heart rate list.
    :return: True if any beat is over the threshold of 120, False otherwise.
    """
    return any(bpm > 150 for bpm in data)


if __name__ == '__main__':
    print(getData())