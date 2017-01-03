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

import threading
import time
import datetime
import json
import struct


class DataHub(object):

    ts_format_string = "%Y-%m-%d %H:%M:%S"

    def __init__(self, scanner=None, dump_file_in=None, dump_file_out=None, decoder=None):
        # Config ok: {S_xx, _Ixx} (1 input) Output is always xx (don't care)
        # Config invalid: {SIxx} (2 inputs), {__xx} (0 inputs)
        if (scanner is not None and dump_file_in is not None) or (scanner is None and dump_file_in is None):
            raise Exception("Invalid input configuration. Need exact 1x scanner OR 1x dump_file_in!")
        self.scanner = scanner
        self.read_recorded_data = True
        if self.scanner is not None:
            dump_file_in = self.scanner.get_data_filename()
            self.read_recorded_data = False
        try:
            self.dump_file_in_handle = open(dump_file_in, "rb")
        except FileNotFoundError:
            raise Exception("Can not read input file '%s'!" % dump_file_in)

        self.dump_file_out_handle = None
        if dump_file_out is not None:
            try:
                self.dump_file_out_handle = open(dump_file_out, "wb")
            except FileNotFoundError:
                raise Exception("Can not write output file '%s'!" % dump_file_out)
            self.filename_meta_data = dump_file_out + ".json"
        else:
            self.filename_meta_data = None

        self.reader_thread = None
        self.stop_reader_thread = threading.Event()
        self.start_time = None
        self.dump_meta_info = None
        self.decoder = decoder

    def start(self):
        if self.reader_thread is not None:
            return

        if not self.read_recorded_data:
            while True:  # flush old data in debugfs on start dumping
                data = self.dump_file_in_handle.read()
                if not data:
                    break
            self.dump_meta_info = self.scanner.get_config()
            self.dump_meta_info['start_time'] = datetime.datetime.now().strftime(DataHub.ts_format_string)

        self.stop_reader_thread.clear()
        self.reader_thread = threading.Thread(target=self._distribute_data, args=())
        self.reader_thread.start()

    def stop(self):
        if self.reader_thread is None:
            return
        self.stop_reader_thread.set()
        if not self.read_recorded_data and self.filename_meta_data is not None:
            self.dump_meta_info['end_time'] = datetime.datetime.now().strftime(DataHub.ts_format_string)
            with open(self.filename_meta_data, "w") as f:
                json.dump(self.dump_meta_info, f)
        self.reader_thread.join()
        self.reader_thread = None
        self.dump_file_in_handle.close()
        if self.dump_file_out_handle is not None:
            self.dump_file_out_handle.close()

    def _distribute_data(self):
        chunk_size = 1024*1024*1024
        while not self.stop_reader_thread.is_set():
            if self.read_recorded_data:
                # read <len><samples><len><samples> until the file ends, then exit thread
                data = bytes()
                file_pos = 0
                while True:
                    self.dump_file_in_handle.seek(file_pos)
                    data += self.dump_file_in_handle.read(chunk_size)
                    file_pos += chunk_size
                    if len(data) is 0:  # hit EOF
                        self.stop_reader_thread.set()  # EOF -> quit
                    # if output is a file, no need to unpack something
                    if self.dump_file_out_handle is not None:
                        self.dump_file_out_handle.write(data)
                    # if output is a decoder, we need to unpack it
                    if self.decoder is not None:
                        while len(data) > 4:
                            (length, ) = struct.unpack_from('<I', data[0:4])
                            if length > len(data):
                                break  # need more data
                            data = data[4:]
                            sample = data[0:length]
                            data = data[length:]
                            self.decoder.enqueue(sample)
                    if self.stop_reader_thread.is_set():
                        break
            # read live data -> already chunk'ed
            else:
                data = self.dump_file_in_handle.read()
                if not data:
                    time.sleep(.1)  # wait for need data from hardware
                    continue
                else:
                    # if output is file, pack <len><samples>
                    if self.dump_file_out_handle:
                        self.dump_file_out_handle.write(struct.pack("<I", len(data)))
                        self.dump_file_out_handle.write(data)
                    # if output is decoder, just pass
                    if self.decoder:
                        self.decoder.enqueue(data)


