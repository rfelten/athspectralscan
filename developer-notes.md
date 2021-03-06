Docu:
* [x] write readme: install + quickstart

Refactoring:
* [ ] add additional monitor interface in bg/manual mode -> no side effects of ifup/down
* [x] Merge AthSensor + AthPhy. Remove scan_up/down logic. simplify mode_X() ?
* [x] Remove AthReader: -> DumpWriter(w/o Queue) gets sensor (metadata!)
* [x] Add DumpReader: read from file/scan0 to file /AthSpectralScanDecoder
* [ ] Decoder: add Queues: input + output (list of Queue). input(data), register_output_queue(Queue), start(), stop()

Bugs:
* [x] drop invalid sample (if sumsq_sample == 0)
* [x] sample is not squared
* [x] chanscan: use external Process. start on mode_chanscan(), stop on change
* [x] chanscan: scan(): os.system() blocks. do not wait
* [-] bg/chanscan: remove mode -> use Enum + AthSensor.get_mode()
* [x] _find_debug_fs: backport better method from speccy ?
* [ ] meta info: read frequency from iw / driver rather than assuming that tune was sucesssuf

(new) Features:
* [x] add userspace timestamp to samples
* [ ] auto chmod 777 of /sys/kernel/debug/ieee80211 (?)
* [ ] count how many samples are invalid
* [ ] test / switch to pypy http://speed.pypy.org/
* [ ] add hint if debugfs is not readable + remove root check in dump_to_file.py
* [x] HT40 support
* [ ] add magic/version to dump files
* [ ] write documentation about dump file format
* [ ] discovery of compatible hardware
* [ ] use 'ip' to configure interface instead of old ifconfig
* [ ] DEBUG msg if fft sample was corrupt / too short
* [ ] add on short_repeat: fix TSF by adding +4us per sample
* [x] DataHub: create chunks of samples: store <len><samples><samples><data> ... to file. reader can split them up
* [x] Decoder: option to omit the (cpu intense) decoding of pwr values
* [x] add "disable" to modes
[ ] add HT20/HT40 to config dump
* [ ] determine + restore state of network interface
* [ ] warn, if ubuntu network manager is active
* [x] DumpWriter: add metadata: date+settings
* [ ] DumpWriter: add metadata: cpuinfo (?)
* [ ] SensorFactory: load config from json file
* [ ] SensorDiscovery: Device discovery: via debugfs (?)
* [ ] use / create unittests: tester need do match hw spec (e.g. "1x hardware")
* [ ] add some testcases for decoding (no hw needed)

Never part of this lib:
- AthSpectralScanDecoder write to file (instead of a queue) - "useful" output format is task of the user
- ath10k support (since it uses closed source firmware blobs
- Auto-switch channels after X sec in background scan
- SensorOrchestra: Merge samples of multiple sensors
