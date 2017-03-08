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

from athspectralscan import AthSpectralScanner, DataHub,  AthSpectralScanDecoder
import multiprocessing as mp
import queue
import logging
import time
import sys
import os

# Setup logger
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def decode_samples(dump_file, output_file):
    # Setup a queue to store the result
    work_queue = mp.Queue()
    decoder = AthSpectralScanDecoder()
    decoder.set_number_of_processes(1)  # so we do not need to sort the results by TSF
    decoder.set_output_queue(work_queue)
    # decoder.disable_pwr_decoding(True)   # enable to extract "metadata": time (TSF), frequency, etc  (much faster!)
    decoder.start()

    hub = DataHub(dump_file_in=dump_file, decoder=decoder)
    hub.start()

    logger.info("Start to decode samples from '%s' ..." % dump_file)
    with open(output_file, "wt") as f:
        while True:
            try:
                (ts, (tsf, freq, noise, rssi, pwr)) = work_queue.get(block=False)
                # pwr is a OrderedDict. flat it
                power = ",".join(["%.2f" % p for (freq, p) in pwr.items()])
                s = "%s,%s,%s,%s,%s,%s\n" % (ts, tsf, freq, noise, rssi, power)
                f.write(s)
            except queue.Empty:
                if decoder.is_finished():  # only break if decoder is finished AND queue is empty
                    break
                else:
                    time.sleep(0.1)  # wait for new data
                    continue
    hub.stop()
    decoder.stop()
    logger.info("Decoded samples for '%s' written to '%s'" % (dump_file, output_file))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        decode_samples(dump_file=sys.argv[1], output_file="dump.csv")
    elif len(sys.argv) == 3:
        decode_samples(dump_file=sys.argv[1], output_file=sys.argv[2])
    else:
        print("Usage: $ %s <dump file> [output.csv]" % sys.argv[0])
        exit(0)