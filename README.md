# README #

version: 0.1
date: June 15, 2014

## Program Requirements ##

### Required ###

* Python 2.7+
* uTorrent 3.0+

### Optional ###

* theRenamer

## How do I get set up? ##

* In uTorrent go to settings , advanced , run program , run program when torrent changes state
* input(with quotes):
                "Path\to\pythonw.exe" "Path\to\script.py" %I %K %P %S
* edit included config.cfg file
* it is recommended to at least keep seeding for a few mins to allow time for 
  script to finish extracting and moving files before removing the torrent
  from uTorrent, if enabled

## TODO ##

* Finish copying folder structure - Done
* Finish extracting file to destination - Done
* Delete unwanted items in destination folder - Done
* Edit the remove torrent script ( should be easy ) - Done
* Implement theRenamer or couchpotato/sickbeard postprocess scripts - Done
* Implement notifications