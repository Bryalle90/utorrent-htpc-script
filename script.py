import os
import sys
from libs.PoisonProcess import PoisonProcess

torrent_hash = sys.argv[1]  # Hash of the torrent, %I
torrent_kind = sys.argv[2]  # Kind of the torrent, %K
torrent_prev = sys.argv[3]  # Kind of the torrent, %P
torrent_state = sys.argv[4]  # Kind of the torrent, %S

if int(torrent_state) == 4 or int(torrent_state) == 5 or int(torrent_state) == 7 or int(torrent_state) == 8 or int(torrent_state) == 10:
	torrent_state = 'seeding'
elif int(torrent_state) == 6 or int(torrent_state) == 9:
	torrent_state = 'downloading'
elif int(torrent_state) == 20:
	torrent_state = 'moving'
elif int(torrent_state) == 11:
	torrent_state = 'finished'
elif int(torrent_state) == 3:
	torrent_state = 'paused'

if int(torrent_prev) == 4 or int(torrent_prev) == 5 or int(torrent_prev) == 7 or int(torrent_prev) == 8 or int(torrent_prev) == 10:
	torrent_prev = 'seeding'
elif int(torrent_prev) == 6 or int(torrent_prev) == 9:
	torrent_prev = 'downloading'
elif int(torrent_prev) == 20:
	torrent_prev = 'moving'
elif int(torrent_prev) == 11:
	torrent_prev = 'finished'
elif int(torrent_prev) == 3:
	torrent_prev = 'paused'

print 'torrent hash:    ' + torrent_hash
print 'previous state:  ' + torrent_prev
print 'state:           ' + torrent_state
print 'kind:            ' + torrent_kind + '\n'

this_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
configFilename = os.path.normpath(os.path.join(this_dir, "config.cfg"))

if len(torrent_hash) == 32:
	torrent_hash = b16encode(b32decode(torrent_hash))

if len(torrent_hash) == 40:
	pp = PoisonProcess()
	try:
		pp.process_torrent(this_dir, configFilename, torrent_hash, torrent_kind, torrent_prev, torrent_state)
	except Exception, e:
		print e
else:
	print 'Script only compatible with uTorrent 3.0+'

# raw_input("Press Enter to continue...")
exit(0)