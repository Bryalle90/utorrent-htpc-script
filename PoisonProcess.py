import os
import sys
import binascii
import ConfigParser
import libs.client.utorrent as TorClient

class PoisonProcess(object):
	def __init__(self):
		pass
	
	def main(self, torrent_hash):
		output_dir = config.get("General", "outputDirectory")
		append_label = config.getboolean("General", "appendLabel")
		append_torName = config.getboolean("General", "appendTorrentName")
		overwriteFiles = config.getboolean("General", "overwrite")
		deleteOnFinish = config.getboolean("General", "delete")
		
		extractor = config.get("Extract", "extractor")
		extractor_path = config.get("Extract", "path")
		queryPassword = config.getboolean("Extract", "askOnPW")
		
		useRenamer = config.getboolean("Renamer", "useTheRenamer")
		if useRenamer:
			renamer_path = config.get("Renamer", "renamerPath")
		
		webui_port = config.get("Client", "port")
		webui_URL = 'http://localhost:' + str(webui_port) + '/gui/'
		webui_user = config.get("Client", "username")
		webui_pass = config.get("Client", "password")
		
		email_notify = config.getboolean("Notifications", "email")
		email_server = config.getboolean("Notifications", "SMTPServer")
		email_port = config.getboolean("Notifications", "SMTPPort")
		email_user = config.getboolean("Notifications", "username")
		email_pass = config.getboolean("Notifications", "password")
		email_to = config.getboolean("Notifications", "emailTo")
		
		#connect to utorrent and get info for torrent using torrent hash
		uTorrent = TorClient.TorrentClient()
		if not uTorrent.connect(webui_URL, webui_user, webui_pass):
			print 'could not connect to utorrent - exiting'
			sys.exit(-1)
		torrent = uTorrent.find_torrent(torrent_hash)
		torrent_info = uTorrent.get_info(torrent)
		
		#
		if torrent_info:
			if torrent_info['state'] == 'Seeding' or torrent_info['state'] == '[F] Seeding' or torrent_info['state'] == 'Queued seed':
				destination = os.path.normpath(os.path.join(output_dir, torrent_info['label'] if append_label else '', torrent_info['name'] if append_torName else ''))
			
				self.make_directories(destination)
			
				keep_files, compressed_files = self.filter_files(torrent_info['files'], torrent_info['label'])
				
				# Loop through keep_files and copy the files
				for f in keep_files:
					file_name = os.path.split(f)[1]
					if self.process_file(f, destination, file_action):
						print("Successfully copied: %s", file_name)
					else:
						print("Failed to copy: %s", file_name)

				# Loop through extract_files and extract all files
				for f in compressed_files:
					file_name = os.path.split(f)[1]
					if self.extract_file(f, destination):
						print("Successfully extracted: %s", file_name)
					else:
						print("Failed to extract: %s", file_name)

			
		
		
		
		
		
		
def is_mainRar(file):	#checks if file is the main rar file in a rar set or just a single rar
	with open(file, "rb") as file:
		byte = file.read(12)

	spanned = binascii.hexlify(byte[10])
	main = binascii.hexlify(byte[11])

	if spanned == "01" and main == "01":	# main rar archive in a set of archives
		return True
	elif spanned == "00" and main == "00":	# single rar
		return True

	return False
		
	def make_directories(self, destination):
		if not os.path.exists(destination):
			try:
				os.makedirs(destination)
			except OSError as e:
				if e.errno != errno.EEXIST:
					raise
				pass


if __name__ == "__main__":
	this_dir = os.getcwd()
	config = ConfigParser.ConfigParser()
	configFilename = os.path.normpath(os.path.join(os.path.dirname(sys.argv[0]), "config.cfg"))
	config.read(configFilename)
	
	
	def filter_files(files, label):
		ignore_words = (config.get("Extensions", "ignore")).split('|')
		archive_ext = tuple((config.get("Extensions", "compressed")).split('|'))
		keep_ext = ()
		keep_files = []
		compressed_files = []
		
		#############change to config type layout, this is too complicated####################
		# Get what extensions to keep from label rule
		if os.path.exists(os.path.join(this_dir, 'labels', label) + '.py'):
			try:
				label = 'labels.' + label
				label = __import__(label, fromlist=[])
				file_prefs = label.get_filePrefs()
				# Add files to keep based on label rule
				if file_prefs['video']:
					keep_ext.extend(config.get("Extensions", "video").split('|'))
				if file_prefs['audio']:
					keep_ext.extend(config.get("Extensions", "audio").split('|'))
				if file_prefs['image']:
					keep_ext.extend(config.get("Extensions", "image").split('|'))
				if file_prefs['subs']:
					keep_ext.extend(config.get("Extensions", "subtitle").split('|'))
				if file_prefs['readme']:
					keep_ext.extend(config.get("Extensions", "readme").split('|'))
				keep_ext = tuple(keep_ext)
			except:
				print 'failed importing label preferences'
		else:
			print 'label file does not exist'

			
		# Sort files into lists depending on file extension
		for f in files:
			if not any(word in f for word in ignore_words):
				if f.endswith(keep_ext):
					keep_files.append(f)

				elif f.endswith(archive_ext):
					if f.endswith('.rar') and is_mainRar(f):	# This will ignore rar sets where all (rar) files end with .rar
						compressed_files.append(f)

		return keep_files, compressed_files
	
	webui_port = config.get("Client", "port")
	webui_URL = 'http://localhost:' + str(webui_port) + '/gui/'
	webui_user = config.get("Client", "username")
	webui_pass = config.get("Client", "password")
	#connect to utorrent and get info for torrent using torrent hash
	uTorrent = TorClient.TorrentClient()
	if not uTorrent.connect(webui_URL, webui_user, webui_pass):
		print 'could not connect to utorrent - exiting'
		sys.exit(-1)
	torrent = uTorrent.find_torrent('F33C84AC2D179EBC5B082710891EFDFF2CF579D7')
	torrent_info = uTorrent.get_info(torrent)
	keep_files, compressed_files = filter_files(torrent_info['files'], torrent_info['label'])
	print keep_files
	
	
	exit(0)
	
	
	
	
	
	torrent_hash = sys.argv[1]  # Hash of the torrent, %I

	if len(torrent_hash) == 32:
		torrent_hash = b16encode(b32decode(torrent_hash))

	if len(torrent_hash) == 40:
		rp = PoisonProcess()
		rp.main(torrent_hash)
	else:
		print 'Script only compatible with uTorrent 3.1+'