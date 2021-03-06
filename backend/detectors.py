import threading
import time
from events import Events
import numpy as np
import math


class detector(Events):
    # the event when a new detection came in
    __events__ = ('on_publish_new_data',)
    def __init__(self, detector_name, detector_version):
        self.detector_name = detector_name
        self.detector_version = detector_version
        self._read_out_lock = threading.Lock()
        self._last_detector_data={
            "internal_timestamp_of_update": time.time(),
            "event_counter_A": 0,
            "event_counter_B": 0,
            "event_counter_AB": 0,
            "event_stack_AB": []
        }

    def _update_detector_data(self, data_dict):
        with self._read_out_lock:
            self._last_detector_data = data_dict

    def _publish_data_via_event(self):
        with self._read_out_lock:
            self.on_publish_new_data(self._last_detector_data)



class simulated_detector(detector, threading.Thread):
    def __init__(self, IMU_Reader, average_number_of_events = 5, noise_to_signal_ratio = 0.2, length_of_event_stack = 20):
        detector.__init__(self, "Simulator", 0.1)
        threading.Thread.__init__(self)
        self.average_number_of_events = average_number_of_events
        self.noise_to_signal_ratio = noise_to_signal_ratio
        self.length_of_event_stack = length_of_event_stack
        self.imu = IMU_Reader
        # start the detector
        self.start()

    def run(self):
        # create an artificial interrupt
        while True:
            time.sleep(1)
            data = self._get_simulated_detector_data()
            self._update_detector_data(data)
            self._publish_data_via_event()

    def _generate_stack_for_events(self, numPeaks):
        # some super fancy on the spot thought up peak generation
        # each event should probably have its own list
        # this could probably be done nicer!
        stack = []
        for i in range(numPeaks):
            # set peak position for the stack
            # the variance of this is probably follows gaussian statistics
            peak_pos = int(np.random.normal(int(self.length_of_event_stack / 2), 1.0, 1)[0])
            # generate peak for stack A
            # we assume that all readout noise is poisson, which might be a flawed assumption
            # as well all peaks have about the same height
            for i in range(self.length_of_event_stack):
                if i < peak_pos:
                    stack.append(np.random.poisson(int(100 * self.noise_to_signal_ratio), 1)[0])
                elif i == peak_pos:
                    stack.append(np.random.poisson(int(100), 1)[0])
                else:
                    stack.append(np.random.poisson(
                        int((100 - 100 * self.noise_to_signal_ratio) / (i - peak_pos) + 100 * self.noise_to_signal_ratio),
                        1)[0])

        return np.asarray(stack).tolist()


    def _get_simulated_detector_data(self):
        # calculate the directional reduction
        # Todo: The reduction is linear at the moment, but it should be cos^2
        # accel returns in x,y,z-directen the number of g
        accel_data = self.imu.get_IMU_and_Pressure_data()['accel']
        # calculate length of x+y (minimum is 0, maximum is 1)
        xy_length = math.sqrt(accel_data[0]**2 + accel_data[1]**2)
        count_reduction_factor = math.sqrt((1-xy_length) ** 2)

        # produce some data
        internal_timestamp_of_update = time.time()
        reduced_num_events = self.average_number_of_events * count_reduction_factor
        event_counter_A = np.random.poisson(int(reduced_num_events / self.noise_to_signal_ratio), 1)[0]
        event_counter_B = np.random.poisson(int(reduced_num_events / self.noise_to_signal_ratio), 1)[0]
        event_counter_AB = np.random.poisson(int(reduced_num_events), 1)[0]
        # produce event stack
        event_stack_AB = [self._generate_stack_for_events(event_counter_AB), self._generate_stack_for_events(event_counter_AB)]

        # return all the stuff
        data_dict = {
            "internal_timestamp_of_update": internal_timestamp_of_update,
            "event_counter_A": event_counter_A,
            "event_counter_B": event_counter_B,
            "event_counter_AB": event_counter_AB,
            "event_stack_AB": event_stack_AB
        }
        return data_dict






