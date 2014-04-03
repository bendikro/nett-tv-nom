nett-tv-nom
===========

A simple python script to fetch and play video from nrk nett-tv.

The new NRK Nett-TV provides high-quality web TV without using Flash
on platforms deemed "supported" [1]. Presently (July 2012), this
does not include Firefox on GNU/Linux, which gets served a
Flash-based player instead.

This little program sends an appropriate user agent header (grabbed
from [1]) to Nett-TV and parses the reply to obtain the URL of a
video stream that can be used with any player that supports HLS.

Supported platforms: Any (Only tested on Linux)

Copyright (2012) gspr, bro
Licensed under the 3-clause BSD license.

We are not in any way affiliated with NRK. Use of NRK Nett-TV is subject to
NRK's terms of service. [2]

[1] http://nrkbeta.no/2012/04/23/test-nrks-splitter-nye-nett-tv/
[2] http://tv.nrk.no/
