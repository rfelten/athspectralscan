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


def collect_samples(interface, filename):
    # Setup scanner and data hub
    scanner = AthSpectralScanner(interface=interface)
    hub = DataHub(scanner=scanner, dump_file_out=filename)
    scanner.set_mode("background")
    scanner.set_channel(1)
    # Start to read from spectral_scan0
    hub.start()
    # Start to acquire dara
    scanner.start()
    logger.info("Collect spectral samples for 5 sec")
    time.sleep(5)
    # Tear down hardware
    scanner.stop()
    hub.stop()
    logger.info("Spectral samples written to %s" % filename)
    logger.info("Meta-data written to %s.json" % filename)


if __name__ == '__main__':
    if len(sys.argv) == 2 and os.geteuid() == 0 :
        collect_samples(interface=sys.argv[1], filename="dump.bin")
    elif len(sys.argv) == 3 and os.geteuid() == 0:
        collect_samples(interface=sys.argv[1], filename=sys.argv[2])
    else:
        print("Usage: $ sudo %s <wifi-interface> [dump file]" % sys.argv[0])
        exit(0)



