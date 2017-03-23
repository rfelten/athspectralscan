#!/usr/bin/env python3
#  -*- coding: utf-8 -*-
##
## This file is part of the athspectralscan project.
##
## Copyright (C) 2016 Robert Felten - https://github.com/rfelten/
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

import os
import logging
import subprocess
from multiprocessing import Process
logger = logging.getLogger(__name__)


class AthSpectralScanner(object):

    def __init__(self, interface):
        # Set interface, phy, driver and debugfs directory
        self.interface = interface
        self.phy = None
        with open('/sys/class/net/%s/phy80211/name' % interface) as f:
            self.phy = f.read().strip()
        self.driver = None
        self.debugfs_dir = None
        for dirname, subd, files in os.walk('/sys/kernel/debug/ieee80211'):
            if 'spectral_scan_ctl' in files:
                phy = dirname.split(os.path.sep)[-2]
                if phy == self.phy:
                    self.driver = dirname.split(os.path.sep)[-1]
                    self.debugfs_dir = dirname
                    break
        if self.debugfs_dir is None:
            raise Exception("Unable to access 'spectral_scan_ctl' file for interface '%s'. "
                    "Maybe you need to adjust the access rights of /sys/kernel/debug/ieee80211 ?" % interface)  # Fixme: sudo chmod -R 777 /sys/kernel/debug
        logger.debug("interface '%s' is on '%s' via %s. debugfs found at %s" %
                     (self.interface, self.phy, self.driver, self.debugfs_dir))

        # hardware capabilities: channels to tune to
        self.channels = []
        self._get_supported_channels()
        logger.debug("interface '%s' supports the channels: %s" % (self.interface, self.channels))
        self.current_freq = -1
        self.current_chan = -1

        # chanscan mode triggers on changed channels. Use Process to run "iw scan" to tune to all channels
        self.chanscan_process = None

        self.channel_mode = "HT20"  # Fixme: use enum here?

        # Store current state of the config files
        self.cfg_files = {}
        self.cfg_filenames = (
            "spectral_count", "spectral_fft_period", "spectral_period",
            "spectral_scan_ctl", "spectral_short_repeat"
        )
        self._store_former_config()
        self.mode = self.cfg_files['spectral_scan_ctl']['former_value']
        self.need_tear_down = True # fixme
        self.running = False

    def __del__(self):
        #self.stop()  # FIXME
        pass

    # suger for set_mode(mode)
    def set_mode_chanscan(self):
        self.set_mode("chanscan")

    def set_mode_background(self):
        self.set_mode("background")

    def set_mode_manual(self):
        self.set_mode("manual")

    def set_mode_disable(self):
        self.set_mode("disable")

    def set_mode(self, mode, skip_interface_config=False):
        if mode not in ["chanscan", "background", "manual", "disable"]:
            raise Exception("Unknown mode requested: '%s'" % mode)

        if mode is "chanscan" and self.mode is not "chanscan":
            self.mode = mode
            if not skip_interface_config:
                logger.debug("enter 'chanscan' mode: set dev type to 'managed'")
                os.system("sudo ifconfig %s down" % self.interface)
                os.system("sudo iw dev %s set type managed" % self.interface)
                os.system("sudo ifconfig %s up" % self.interface)  # FIXME: does the interface need to be up?
            self._set_spectral_cfg('spectral_scan_ctl', "chanscan")
            #self._start_scan_process() -> start()
            self.need_tear_down = True
            return
        self._stop_scan_process()  # all other modes: kill external "iw scan" (if any)
        if mode is "background" and self.mode is not "background":
            self.mode = mode
            if not skip_interface_config:
                logger.debug("enter 'background' mode: set dev type to 'monitor'")
                os.system("sudo ifconfig %s down" % self.interface)
                os.system("sudo iw dev %s set monitor fcsfail" % self.interface)  # fcsfail = also report frames with corrupt FCS
                os.system("sudo ifconfig %s up" % self.interface)  # need to be up
            self._set_spectral_cfg('spectral_scan_ctl', "background")
            #self._set_spectral_cfg('spectral_scan_ctl', "trigger") -> start()
            self.need_tear_down = True
            return
        if mode is "manual" and self.mode is not "manual":
            self.mode = mode
            if not skip_interface_config:
                logger.debug("enter 'manual' mode: set dev type to 'monitor'")
                os.system("sudo ifconfig %s down" % self.interface)
                os.system("sudo iw dev %s set monitor fcsfail" % self.interface)  # fcsfail = also report frames with corrupt FCS
                os.system("sudo ifconfig %s up" % self.interface)  # need to be up
            self._set_spectral_cfg('spectral_scan_ctl', "manual")
            self.need_tear_down = True
            return
        if mode is "disable" and self.mode is not "disable":
            self.mode = mode
            if not skip_interface_config:
                os.system("sudo ifconfig %s down" % self.interface)
                os.system("sudo iw dev %s set type managed" % self.interface)
            self._set_spectral_cfg('spectral_scan_ctl', "disable")
            # need to trigger() here? ? -> not needed. ath9k_cmn_spectral_scan_config() calls
            # ath9k_hw_ops(ah)->spectral_scan_config() which unset the AR_PHY_SPECTRAL_SCAN_ENABLE flag if needed
            self.need_tear_down = True
            return

    def trigger(self):
        self._set_spectral_cfg('spectral_scan_ctl', "trigger")

    def retrigger(self):
        if self.mode == "background":
            self._set_spectral_cfg('spectral_scan_ctl', "trigger")

    def get_mode(self):
        return self.mode

    def get_debugfs_directory(self):
        return self.debugfs_dir

    def get_data_filename(self):
        return self.debugfs_dir + os.path.sep + "spectral_scan0"

    def get_config(self):
        cfg = {}
        for fn in self.cfg_filenames:
            path = self.debugfs_dir + os.path.sep + fn
            with open(path, 'r') as f:
                cfg[fn] = f.read().strip()
        cfg['driver'] = self.driver
        cfg['frequency'] = self.current_freq
        return cfg

    def set_channel(self, channel):
        self._tune(channel=channel)

    # sugar: get_channel()?

    def set_frequency(self, frequency):
        self._tune(frequency=frequency)

    # sugar: get_frequency()?

    def get_supported_freqchan(self):
        return self.channels

    # Source of min/max values for parameters: ath9k/spectral-common.c
    def set_spectral_count(self, count):
        if count > 255 or count < 0:
            logger.error("invalid value for 'spectral_count' of %d. valid: 0-255" % count)
            return
        self._set_spectral_cfg('spectral_count', count)

    def get_spectral_count(self):
        return int(self._get_spectral_cfg('spectral_count'))

    def set_spectral_fft_period(self, period):
        if period > 15 or period < 0:
            logger.error("invalid value for 'spectral_fft_period' of %d. valid: 0-15" % period)
            return
        self._set_spectral_cfg('spectral_fft_period', period)

    def get_spectral_fft_period(self):
        return int(self._get_spectral_cfg('spectral_fft_period'))

    def set_spectral_period(self, period):
        if period > 255 or period < 0:
            logger.error("invalid value for 'spectral_period' of %d. valid: 0-255" % period)
            return
        self._set_spectral_cfg('spectral_period', period)

    def get_spectral_period(self):
        return int(self._get_spectral_cfg('spectral_period'))

    def set_spectral_short_repeat(self, repeat):
        if repeat > 1 or repeat < 0:
            logger.error("invalid value for 'spectral_short_repeat' of %d. valid: 0-1" % repeat)
            return
        self._set_spectral_cfg('spectral_short_repeat', repeat)

    def get_spectral_short_repeat(self):
        return int(self._get_spectral_cfg('spectral_short_repeat'))

    def _set_spectral_cfg(self, filenname, value):
        logger.debug("set '%s' to '%s'" % (filenname, value))
        with open(self.cfg_files[filenname]['path'], 'w') as f:
            f.write("%s" % value)

    def _get_spectral_cfg(self, filenname):
        with open(self.cfg_files[filenname]['path']) as f:
            return f.read()

    def start(self):
        self.running = True
        if self.mode is "chanscan":
            self._start_scan_process()
        else:
            self._set_spectral_cfg('spectral_scan_ctl', "trigger")

    def stop(self):
        self.running = False
        self.set_mode("disable")
        if self.need_tear_down:
            self._restore_former_config()
            self._stop_scan_process()
            self.need_tear_down = False

    def _tune(self, channel=None, frequency=None):
        if self.mode is "chanscan":  # FIXME allow "manual chanscan": chanscan w/o iw scan
            logger.warn("Manual set of channel/frequency gets probably overwritten in chanscan mode.")
            return
        for i in range(0, len(self.channels)):
            (freq, chan) = self.channels[i]
            if chan == channel or freq == frequency:
                self.current_freq = freq
                self.current_chan = chan
                logger.debug("set freq to %d in mode %s" % (freq, self.channel_mode))
                os.system("sudo iw dev %s set freq %d %s" % (self.interface, freq, self.channel_mode))
                if self.running:
                    self._set_spectral_cfg('spectral_scan_ctl', "trigger")  # need to trigger again after switch channel
                return
        logger.warning("can not tune to unsupported channel %d / frequency %d. Supported channels: %s"
                       % chan, freq, self.channels)


    # FIXME: add interface config, use with open
    def _store_former_config(self):
        for fn in self.cfg_filenames:
            path = self.debugfs_dir + os.path.sep + fn
            f = open(path, 'r')
            val = f.read().strip()
            f.close()
            self.cfg_files[fn] = {'path': path, 'former_value': val}
            logger.debug("read config for '%s': '%s'" % (path, val))

    def _restore_former_config(self):
        #for fn, stored_cfg in self.cfg_files.iteritems(): python2 # FIXME remove
        for fn, stored_cfg in self.cfg_files.items():
            val = stored_cfg['former_value']
            path = stored_cfg['path']
            f = open(path, 'w')
            f.write(val)
            f.close()
            logger.debug("restore '%s' to: '%s'" % (path, val))

    def _get_supported_channels(self):
        # parses the supported channels as (channel, freq) from 'iw phy'
        iw_phy_output = subprocess.check_output(["iw", "phy"]).decode('UTF-8')
        found_device = False
        for line in iw_phy_output.split('\n'):
            line = line.strip()
            if "Wiphy" in line:
                if self.phy in line:
                    found_device = True
                else:
                    found_device = False
                continue
            if found_device:
                if "*" in line and "MHz" in line and "[" in line and "]" in line:
                    try:
                        freq = int(line.split("MHz")[0].split("*")[1].strip())
                        chan = int(line.split("[")[1].split("]")[0].strip())
                        self.channels.append((freq, chan))
                    except Exception as e:
                        raise Exception("Cant parse freq/channel from line '%s': '%s'" % (line, e))

    def _start_scan_process(self):
        if self.chanscan_process is None:
            logger.debug("start process chanscan")
            self.chanscan_process = Process(target=self._scan, args=())
            self.chanscan_process.start()

    def _stop_scan_process(self):
        if self.chanscan_process is not None:
            logger.debug("stop process chanscan")
            self.chanscan_process.terminate()
            self.chanscan_process.join()
            self.chanscan_process = None

    def _scan(self):
        while True:
            cmd = 'iw dev %s scan' % self.interface
            os.system('%s >/dev/null 2>/dev/null' % cmd)  # call blocks
