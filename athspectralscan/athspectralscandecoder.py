#!/usr/bin/env python3
#  -*- coding: utf-8 -*-
##
## This file is part of the athspectralscan project.
##
## Copyright (C) 2016-2017 Robert Felten - https://github.com/rfelten/
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
##

import time
import math
import struct
from collections import OrderedDict
import multiprocessing as mp
from queue import Empty
import logging
logger = logging.getLogger(__name__)


class AthSpectralScanDecoder(object):

    """ AthSpectralScanDecoder inputs a binary Atheros Spectral Scan sample and decode its values to its clear text
    representation. The result (for HT20) is a tuple (ts (tsf, freq, noise, rssi, pwr)):
    ts - kernel timestamp
    tsf - TSF value
    freq - channel center frequency
    noise - noisefloor (some hardware do not report this, look out for the default value of -95dBm)
    rssi - a RSSI value <- where does it come from ? FIXME
    pwr - a ordered dict, containing sub-carrier->dBm entries

    The decoding consumes a lot of resources (read more below), there for it implemented as multiprocessing Pool to
    make avoid GIL and make use of modern multi core CPUs.

    The major amount of processing requirements comes from the use of a log10() function, called once per sub carrier (!)
    In other words: for a HT20 sample there are 56x log10() PER EACH SAMPLE (!!!).
    Multi threading is one approach to tackle this issue. Another is to use an precomputed look-up table. In some scenarios
    the log() can be avoided complete, for instance if the user is only interested in e.g. the TSF values, not in the
    sub carrier pwr info.

    Please note, that when using the multiprocessing approach, the samples can be delivered out-of-order!
    """

    # spectral scan packet format constants
    hdrsize = 3
    type1_pktsize = 17 + 56
    type2_pktsize = 24 + 128
    type3_pktsize = 26 + 64

    def __init__(self, empty_input_queue_timeout_sec=1):
        self.input_queue = mp.Queue()
        self.input_queue_timeout = empty_input_queue_timeout_sec
        self.output_queue = None
        self.worker_pool = None
        self.number_of_processes = 1
        self.shut_down = mp.Event()
        self.shut_down.clear()
        self.work_done = mp.Event()
        self.work_done.clear()
        self.disable_pwr_decode = False

    def start(self):
        if self.output_queue is None:
            logger.warn("no output queue is set. No decoding is done!")
            return
        self.worker_pool = mp.Pool(processes=self.number_of_processes, initializer=self._decode_data_process,)

    def disable_pwr_decoding(self, flag):
        self.disable_pwr_decode = flag

    def set_number_of_processes(self, number):
        self.number_of_processes = number

    def is_finished(self):
        return self.shut_down.is_set() or self.work_done.is_set()

    def stop(self):
        self.shut_down.set()
        self.worker_pool.close()

    def set_output_queue(self, output_queue):
        #if not isinstance(output_queue, mp.Queue):
        #    raise Exception("output_queue needs to be a multiprocessing.Queue!")
        self.output_queue = output_queue

    def enqueue(self, data):
        self.input_queue.put(data)

    def _decode_data_process(self):
        while not self.shut_down.is_set():
            try:
                data = self.input_queue.get(timeout=self.input_queue_timeout)
                self.work_done.clear()
            except Empty:
                self.work_done.set()
                continue
            # process data
            for decoded_sample in AthSpectralScanDecoder._decode(data, no_pwr=self.disable_pwr_decode):
                self.output_queue.put(decoded_sample)

    @staticmethod
    def _decode(data, no_pwr=False):
        pos = 0
        (ts, data) = data
        while pos < len(data) - AthSpectralScanDecoder.hdrsize + 1:

            (stype, slen) = struct.unpack_from(">BH", data, pos)
            if not ((stype == 1 and slen == AthSpectralScanDecoder.type1_pktsize) or
                    (stype == 2 and slen == AthSpectralScanDecoder.type2_pktsize) or
                    (stype == 3 and slen == AthSpectralScanDecoder.type3_pktsize)):
                logger.warn("skip malformed packet (type=%d, slen=%d) at pos=%d" % (stype, slen, pos))
                break  # header malformed, discard data. This event is very unlikely (once in ~3h)

            # 20 MHz
            if stype == 1:
                if pos >= len(data) - AthSpectralScanDecoder.hdrsize - AthSpectralScanDecoder.type1_pktsize + 1:
                    break
                pos += AthSpectralScanDecoder.hdrsize
                (max_exp, freq, rssi, noise, max_mag, max_index, hweight, tsf) = \
                    struct.unpack_from(">BHbbHBBQ", data, pos)
                pos += 17

                if no_pwr:
                    yield (ts, (tsf, freq, noise, rssi, dict()))
                    pos += 56
                    continue

                sdata = struct.unpack_from("56B", data, pos)
                pos += 56

                # calculate power in dBm
                sumsq_sample = 0
                samples = []
                for raw_sample in sdata:
                    sample = (raw_sample << max_exp)**2
                    sumsq_sample += sample
                    samples.append(sample)

                if sumsq_sample == 0:
                    continue  # drop invalid sample (all sub-carriers are zero)
                sumsq_sample = 10 * math.log10(sumsq_sample)

                # center freq / DC index is at bin 56/2=28 -> subcarrier_0 = freq - 28 * 0.3125 = freq - 8.75
                subcarrier_0 = freq - 8.75
                pwr = OrderedDict()
                for i, sample in enumerate(samples):
                    if sample == 0:                                         # this would break log()
                        sample = sum(samples) / len(samples)                # anyone a better idea?
                    subcarrier_i = subcarrier_0 + i * 0.3125
                    sigval = noise + rssi + 10 * math.log10(sample) - sumsq_sample
                    pwr[subcarrier_i] = sigval
                # FIXME: add sigval for channel Sum(subcarriers):
                # use log(x) + log(y) =  log(x*y) -> Sum(log(i)) = log(P(i)) with P as product

                yield (ts, (tsf, freq, noise, rssi, pwr))

            # 40 MHz
            elif stype == 2:
                if pos >= len(data) - AthSpectralScanDecoder.hdrsize - AthSpectralScanDecoder.type2_pktsize + 1:
                    break
                pos += AthSpectralScanDecoder.hdrsize
                (chantype, freq, rssi_l, rssi_u, tsf, noise_l, noise_u,
                 max_mag_l, max_mag_u, max_index_l, max_index_u,
                 hweight_l, hweight_u, max_exp) = \
                    struct.unpack_from(">BHbbQbbHHbbbbb", data, pos)
                pos += 24

                if no_pwr:
                    yield (ts, (tsf, freq, (noise_l + noise_u) / 2, (rssi_l + rssi_u) / 2, dict()))
                    pos += 128
                    continue

                sdata = struct.unpack_from("128B", data, pos)
                pos += 128

                # calculate power in dBm
                samples = []
                for raw_sample in sdata:
                    sample = (raw_sample << max_exp)**2
                    samples.append(sample)

                # create lower + upper binsum:
                sumsq_sample_lower = 0
                for sl in samples[0:63]:
                    sumsq_sample_lower += sl
                if sumsq_sample_lower == 0:
                    continue  # drop invalid sample (all sub-carriers are zero)
                sumsq_sample_lower = 10 * math.log10(sumsq_sample_lower)

                sumsq_sample_upper = 0
                for su in samples[64:127]:
                    sumsq_sample_upper += su
                if sumsq_sample_upper == 0:
                    continue  # drop invalid sample (all sub-carriers are zero)
                sumsq_sample_upper = 10 * math.log10(sumsq_sample_upper)

                # adjust center freq, depending on HT40+ or -
                if chantype == 2:  # NL80211_CHAN_HT40MINUS
                    freq -= 10
                elif chantype == 3:  # NL80211_CHAN_HT40PLUS
                    freq += 10
                else:
                    raise Exception("got unknown chantype: %d" % chantype)

                # center freq / DC index is at bin 128/2=64 -> subcarrier_0 = freq - 64 * 0.3125 = freq - 20
                subcarrier_0 = freq - 20
                pwr = OrderedDict()
                for i, sample in enumerate(samples):
                    if sample == 0:                                         # this would break log()
                        sample = sum(samples) / len(samples)                # anyone a better idea?
                    if i < 64:
                        sigval = noise_l + rssi_l + 10 * math.log10(sample) - sumsq_sample_lower
                    else:
                        sigval = noise_u + rssi_u + 10 * math.log10(sample) - sumsq_sample_upper
                    subcarrier_i = subcarrier_0 + i * 0.3125
                    pwr[subcarrier_i] = sigval

                yield (ts, (tsf, freq, (noise_l+noise_u)/2, (rssi_l+rssi_u)/2, pwr))

            # ath10k
            elif stype == 3:
                raise Exception("ath10k is not supported, sorry!")
