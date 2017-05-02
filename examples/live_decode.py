#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#   This file is part of the athspectralscan project.
#
#   Copyright (C) 2017 Robert Felten - https://github.com/rfelten/
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

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


def live_sample(interface):
    # Setup a queue to store the result
    work_queue = mp.Queue()
    decoder = AthSpectralScanDecoder()
    decoder.set_number_of_processes(1)  # so we do not need to sort the results by TSF
    decoder.set_output_queue(work_queue)
    decoder.disable_pwr_decoding(True)   # enable to extract "metadata": time (TSF), frequency, etc  (much faster!)
    decoder.start()

    # Setup scanner and data hub
    scanner = AthSpectralScanner(interface=interface)
    hub = DataHub(scanner=scanner, decoder=decoder)

    #scanner.set_mode("chanscan")
    scanner.set_spectral_short_repeat(1)
    scanner.set_mode("background")
    scanner.set_channel(1)


    # Start to read from spectral_scan0
    hub.start()
    # Start to acquire dara
    scanner.start()
    logger.info("Collect data. Press CTRL-C to abort..")

    try:
        while True:
            # time.sleep(.1)
            (ts, (tsf, freq, noise, rssi, pwr)) = work_queue.get(block=True)
            print(ts, tsf, freq, noise, rssi, pwr)
    except KeyboardInterrupt:
        pass
    # Tear down hardware
    scanner.stop()
    hub.stop()

if __name__ == '__main__':
    if len(sys.argv) == 2:
        live_sample(interface=sys.argv[1])
    else:
        print("Usage: $ %s <wifi-interface> % sys.argv[0]")
        exit(0)



