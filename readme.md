
## What is this? 

This is a Python 3 library for the [Atheros Spectral Scan](https://wireless.wiki.kernel.org/en/users/drivers/ath9k/spectral_scan)
feature. It provides a convenient wrapper for the ```spectral_scan_*``` debugfs files and a decoder for the spectral
scan frame format. Also it configures the interface for you depending on the mode of spectral scan.

This tool was written by Robert Felten as part of his master thesis _"Design and prototypical implementation of a Radio
Measurement Map"_.

## Example Session
 
```python
$ sudo python3
>>> import athspectralscan as athss
>>> scanner = athss.AthSpectralScanner(interface="wlan0")
... tba
```

## Installation

```bash
$ git clone ...
$ cd athspectralscan
$ sudo pip install .
```

## More Detailed Documentation

TBA

## Pitfalls

 * Need to be root in order to access debugfs files
 * A lot more ..

## Open Issues / To Do

see ```internal_notes```.