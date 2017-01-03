
Quickstart

$ setiup install

> from athspectralscan import * as athss
> athss.discover_hw()
wlan1

> scanner = athss.AthSS(interface='wlan1')
> scanner.supported_frequencies()
[2313, 2121, ...]
> scanner.set_frequency(2412)
> scanner.set_mode("HT40")
> scanner.bg


Features

* low level wrapper - use set cmd instead of fiddle with files
* mutliple decoder: simple or LUT 
* device discover
* restore former config



Needs root -> debugFS (or mount debugFS)?
