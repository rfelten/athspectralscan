
## What is this? 

This is a Python 3 library for the [ath9k spectral scan](https://wireless.wiki.kernel.org/en/users/drivers/ath9k/spectral_scan)
feature. It provides a convenient wrapper for the ```spectral_scan_*``` debugfs files and a decoder for the spectral
scan frame format. Also it configures the Wi-Fi interface for you.

This tool was written by Robert Felten for his master thesis _"Design and prototypical implementation of a Radio
Measurement Map"_.

## Example Session
 
tba


## Dependencies

 * iw, ifconfig, sudo
 * $USER in the sudoers file
 * ```/sys/kernel/debug/ieee80211``` needs to be read+writeable for the current user
  

## Installation

tba

## Overview

<architecture image here>

The general flow is:
```
spectral_scan_* <- AthSpectralScanner
spectral_scan0 -> DataHub -> (file, queue) -> AthSpectralScanDecoder -> queue
```
The ```AthSpectralScanner``` is used to configure the interface/spectral scan appropriately.
Then the spectral data is read-out by the ```DataHub``` class. The spectral data can be stored to a file 
or passed into a queue for "real-time" decoding. The ```AthSpectralScanDecoder``` parses the binary spectral 
data and transform it into something meaning full, e.g. time, frequency, power (dBm).


## More Detailed Documentation (API)

The folder ```examples/``` contains several example how to use the API.

AthSpectralScanner:
 
 * AthSpectralScanner(wifi_interface) -
 * set_mode_chanscan() -
 * set_mode_background() -
 * set_mode_manual() -
 * set_mode_disable() -
 * trigger() -
 * set_spectral_count(int 0-255) -
 * set_spectral_fft_period(int 0-15) -
 * set_spectral_period(int 0-255) -
 * set_spectral_short_repeat(int 0-1) - 
 * set_channel(int channel number) -
 * set_frequency(int frequency [MHz]) -
 * start() - Issue a trigger (for BG/manual) or start a sub-process for chanscan
 * stop() - Tear down spectral scanning and remove sub-process (chanscan)
 * str get_mode()
 * json get_config()

AthSpectralScanDecoder:
 * AthSpectralScanDecoder(input_queue_timeout)
 * set_output_queue(Queue q) - The user have to provide a output queue, otherwise the decoding make no sense
 * set_number_of_processes(int i) - Number of processes used for decoding.
 _Warning_: If use more than one process the decoded samples are maybe out-of-order at the output queue
 * disable_pwr_decoding() - Disable the CPU intense decoding of pwr. Still decoded: tsf, freq, noise, rssi
 * enqueue(sample) - Input. Place raw samples here
 * start() - start to read the input queue, decode and store to the output queue
 * stop() - Tear down the decoding process(es)
 * bool is_finished() - Test if decoder was disabled or input queue was empty longer than a time out

DataHub:
 * DataHub(scanner=None, dump_file_in=None, dump_file_out=None, decoder=None)
        # Config ok: {S_xx, _Ixx} (1 input) Output is always xx (don't care)
        # Config invalid: {SIxx} (2 inputs), {__xx} (0 inputs)
 * start() - create a thread to read from input file and push data to dump_file and/or decoder
 * stop() - destroy reader thread, write metadata (.json) and close open files


Dataformat of dump files:
 * (length, data ): ```[4 Byte unsgigned int][raw spetral data]``` Packed via:
  ```python
self.dump_file_out_handle.write(struct.pack("<I", len(data)))
self.dump_file_out_handle.write(data) 
 ```
 Unpack via:
 ```python
<read 'data' from dump file>
while len(data) > 4:
    (length, ) = struct.unpack_from('<I', data[0:4])
    if length > len(data[4:]):
        break  # need more data
    data = data[4:]
    sample = data[0:length]
    data = data[length:]
    <process 'sample', eg. queue it>
```
See ```DataHub``` for more details.
This kind of storage keep the structure how the data was read from the kernel and allow
to distinguish (groups of) samples without decode them.
  
## Pitfalls

 * Need run as root in order to access debugfs files. Alternativly to the user needs to allow non-root
 users to acess the debugfs via ```$ sudo chmod a+rx /sys/kernel/debug```
 * A lot more ..

## Open Issues / To Do

See ```internal_notes```.