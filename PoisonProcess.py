import os
import sys
import binascii
import ConfigParser
import shutil
import errno
import libs.client.utorrent as TorClient
from libs.unrar2 import RarFile

class PoisonProcess(object):
	def __init__(self):
		pass
	
	def main(self, torrent_hash, torrent_kind, torrent_state, torrent_prev):
		output_dir = config.get("General", "outputDirectory")
		append_label = config.getboolean("General", "appendLabel")
		append_torName = config.getboolean("General", "appendTorrentName")
		deleteOnFinish = config.getboolean("General", "remove")
		
		useRenamer = config.getboolean("Renamer", "useTheRenamer")
		if useRenamer:
			renamer_path = config.get("Renamer", "renamerPath")
		
		email_notify = config.getboolean("Notifications", "email")
		email_server = config.get("Notifications", "SMTPServer")
		email_port = config.get("Notifications", "SMTPPort")
		email_user = config.get("Notifications", "username")
		email_pass = config.get("Notifications", "password")
		email_to = config.get("Notifications", "emailTo")

		webui_port = config.get("Client", "port")
		webui_URL = 'http://localhost:' + str(webui_port) + '/gui/'
		webui_user = config.get("Client", "username")
		webui_pass = config.get("Client", "password")
		
		#connect to utorrent and get info for torrent using torrent hash
		uTorrent = TorClient.TorrentClient()
		if not uTorrent.connect(webui_URL, webui_user, webui_pass):
			print 'could not connect to utorrent - exiting' + '\n'
			sys.exit(-1)
		torrent = uTorrent.find_torrent(torrent_hash)
		torrent_info = uTorrent.get_info(torrent)

		if torrent_info:
			if torrent_prev == 'downloading' and torrent_state == 'seeding':

				# get what files to keep and what to extract
				keep_files, compressed_files, keep_structure, keep_ext = self.filter_files(torrent_info['files'], torrent_info['label'])

				if keep_structure and torrent_kind == 'multi':
					destination = os.path.normpath(os.path.join(output_dir,
																torrent_info['label'] if append_label else '',
																torrent_info['name']))
					print 'Copying files from: ' + torrent_info['folder']
					print 'to: ' + destination
					print '--'
					self.copy_tree(os.path.normpath(torrent_info['folder']), destination, keep_ext)
					print '--\n'
				else:
					# create destination if it doesn't exist
					destination = os.path.normpath(os.path.join(output_dir,
																torrent_info['label'] if append_label else '',
																torrent_info['name'] if append_torName else ''))
					self.make_directories(destination)
					print 'Copying files from: ' + torrent_info['folder']
					print 'to: ' + destination

					# Loop through keep_files and copy the files
					print '--'
					for f in keep_files:
						self.copy_file(f, destination)
					print '--\n'

				# Loop through compressed_files and extract all files
				print 'Extracting files to: ' + destination
				print '--'
				for f in compressed_files:
					self.extract_file(f, destination)
				print '--\n'

				print 'Cleaning up unwanted files in: ' + destination
				print '--'
				self.clean_dest(destination, keep_ext)
				print '--\n'
			# if torrent goes from seeding -> finished, remove torrent from list
			elif torrent_prev == 'seeding' and torrent_state == 'finished' and deleteOnFinish:
				print 'Removing torrent: ' + torrent_info['name']
				uTorrent.delete_torrent(torrent)

	def filter_files(self, files, label):	# returns a list of files to keep in destination and a list of files to extract and whether or not to keep the folder structure
		ignore_words = (config.get("Extensions", "ignore")).split('|')
		archive_ext = tuple((config.get("Extensions", "compressed")).split('|'))
		keep_ext = []
		keep_files = []
		compressed_files = []
		kfs = False
		
		label_config = ConfigParser.ConfigParser()
		
		if os.path.exists(os.path.join(this_dir, 'labels', label) + '.cfg'):
			label_file = os.path.normpath(os.path.join(this_dir, 'labels', label) + '.cfg')
			label_config.read(label_file)

			if label_config.getboolean("Type", "video"):
				keep_ext.extend(config.get("Extensions", "video").split('|'))
			if label_config.getboolean("Type", "audio"):
				keep_ext.extend(config.get("Extensions", "audio").split('|'))
			if label_config.getboolean("Type", "image"):
				keep_ext.extend(config.get("Extensions", "image").split('|'))
			if label_config.getboolean("Type", "subtitle"):
				keep_ext.extend(config.get("Extensions", "subtitle").split('|'))
			if label_config.getboolean("Type", "readme"):
				keep_ext.extend(config.get("Extensions", "readme").split('|'))
			keep_ext = tuple(keep_ext)
			kfs = label_config.getboolean("Type", "keepFolderStructure")

			print 'Successfully read label config file' + '\n'
			print 'Keeping files with extension: '
			for e in keep_ext:
				print '\t\t\t\t' + e
			print ''
		else:
			print 'label file, ' + label + '.cfg does not exist' + '\n'
			
		# Sort files into lists depending on file extension
		for f in files:
			if not any(word in f for word in ignore_words):
				if f.endswith(keep_ext):
					keep_files.append(f)

				elif f.endswith(archive_ext):
					if f.endswith('.rar') and self.is_mainRar(f):	# This will ignore rar sets where all (rar) files end with .rar
						compressed_files.append(f)

		return keep_files, compressed_files, kfs, keep_ext
		
	def is_mainRar(self, file):	# returns true if file is the main rar file in a rar set or just a single rar
		with open(file, "rb") as file:
			byte = file.read(12)

		spanned = binascii.hexlify(byte[10])
		main = binascii.hexlify(byte[11])

		if spanned == "01" and main == "01":	# main rar archive in a set of archives
			return True
		elif spanned == "00" and main == "00":	# single rar
			return True

		return False
			
	def make_directories(self, directory):	# creates a directory if it doesn't already exist
		if not os.path.exists(directory):
			try:
				os.makedirs(directory)
			except OSError as e:
				if e.errno != errno.EEXIST:
					raise
				pass

	def copy_file(self, source_file, destination):	# copies a file to a destination folder, returns success
		file_name = os.path.split(source_file)[1]
		destination_file = os.path.join(destination, file_name)
		if not os.path.isfile(destination_file):
			try:
				shutil.copy2(source_file, destination_file)
				print 'Successfully copied ' + file_name + ' to destination'
			except Exception, e:
				print 'Failed to copy ' + file_name + '\n'
		else:
			print file_name + ' already exists in destination - skipping'

	def copy_tree(self, source, dest, keep_ext):	# copies a folder structure to destination and only files with the specified extensions
		for dirName, subdirList, fileList in os.walk(source):
			for fname in fileList:
				if fname.endswith(keep_ext):
					full_file = os.path.normpath(os.path.join(dirName, fname))
					relPath = os.path.relpath(full_file, source)
					newPath = os.path.normpath(os.path.join(dest, os.path.split(relPath)[0]))
					self.make_directories(newPath)
					self.copy_file(full_file, newPath)
						
	def extract_file(self, source_file, destination):	# extracts files from source rar to destination directory
		try:
			rar_handle = RarFile(source_file)
			for rar_file in rar_handle.infolist():
				sub_path = os.path.join(destination, rar_file.filename)
				if rar_file.isdir and not os.path.exists(sub_path):
					os.makedirs(sub_path)
				else:
					rar_handle.extract(condition=[rar_file.index], path=destination, withSubpath=True, overwrite=False)
			del rar_handle
			print "Successfully extracted " + os.path.split(source_file)[1] + " to destination"
		except Exception, e:
			print "Failed to extract " + os.path.split(source_file)[1] + ": " + e + " " + traceback.format_exc()

	def clean_dest(self, dest, keep_ext): # cleans the destination of all files that done end with extensions in keep_ext
		for dirName, subdirList, fileList in os.walk(dest):
			for fname in fileList:
				if not fname.endswith(keep_ext):
					print 'deleting: ' + fname
					os.remove(os.path.normpath(os.path.join(dirName, fname)))
		for dirName, subdirList, fileList in os.walk(dest, topdown=False):
			if len(fileList) == 0 and len(subdirList) == 0:
				os.rmdir(dirName)


if __name__ == "__main__":
	torrent_hash = sys.argv[1]  # Hash of the torrent, %I
	torrent_kind = sys.argv[2]  # Kind of the torrent, %K
	torrent_prev = sys.argv[3]  # Kind of the torrent, %P
	torrent_state = sys.argv[4]  # Kind of the torrent, %S

	if int(torrent_state) == 4 or\
		 int(torrent_state) == 5 or\
		 int(torrent_state) == 7 or\
		 int(torrent_state) == 8 or\
		 int(torrent_state) == 10:
		torrent_state = 'seeding'
	elif int(torrent_state) == 6 or int(torrent_state) == 9:
		torrent_state = 'downloading'
	elif int(torrent_state) == 11:
		torrent_state = 'finished'
	if int(torrent_prev) == 4 or\
		 int(torrent_prev) == 5 or\
		 int(torrent_prev) == 7 or\
		 int(torrent_prev) == 8 or\
		 int(torrent_prev) == 10:
		torrent_prev = 'seeding'
	elif int(torrent_prev) == 6 or int(torrent_prev) == 9:
		torrent_prev = 'downloading'
	elif int(torrent_prev) == 11:
		torrent_prev = 'finished'

	print 'torrent hash:\t\t' + torrent_hash
	print 'previous state:\t\t' + torrent_prev
	print 'state:\t\t' + torrent_state
	print 'kind:\t\t' + torrent_kind + '\n'

	this_dir = os.getcwd()
	config = ConfigParser.ConfigParser()
	configFilename = os.path.normpath(os.path.join(this_dir, "config.cfg"))
	try:
		config.read(configFilename)
		print 'Successfully read config' + '\n'
	except:
		print 'Could not read config - exiting' + '\n'
		exit(-1)

	if len(torrent_hash) == 32:
		torrent_hash = b16encode(b32decode(torrent_hash))

	if len(torrent_hash) == 40:
		pp = PoisonProcess()
		pp.main(torrent_hash, torrent_kind, torrent_state, torrent_prev)
	else:
		print 'Script only compatible with uTorrent 3.0+'