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

	def filter_files(self, config, this_dir, files, label):	# returns a list of files to keep in destination and a list of files to extract and whether or not to keep the folder structure
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

			print 'Successfully read ' + label + ' config file' + '\n'
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
	
	def process(self, this_dir, configFilename, torrent_hash, torrent_kind, torrent_prev, torrent_state):
		self.config = ConfigParser.ConfigParser()
		try:
			self.config.read(configFilename)
			print configFilename
			print 'Successfully read config' + '\n'
		except Exception, e:
			print e
			exit(-1)
		self.output_dir = self.config.get("General", "outputDirectory")
		self.append_label = self.config.getboolean("General", "appendLabel")
		self.append_torName = self.config.getboolean("General", "appendTorrentName")
		self.deleteOnFinish = self.config.getboolean("General", "remove")
		
		self.useRenamer = self.config.getboolean("Renamer", "useTheRenamer")
		if self.useRenamer:
			self.renamer_path = self.config.get("Renamer", "renamerPath")
		
		self.email_notify = self.config.getboolean("Notifications", "email")
		self.email_server = self.config.get("Notifications", "SMTPServer")
		self.email_port = self.config.get("Notifications", "SMTPPort")
		self.email_user = self.config.get("Notifications", "username")
		self.email_pass = self.config.get("Notifications", "password")
		self.email_to = self.config.get("Notifications", "emailTo")

		self.webui_port = self.config.get("Client", "port")
		self.webui_URL = 'http://localhost:' + str(self.webui_port) + '/gui/'
		self.webui_user = self.config.get("Client", "username")
		self.webui_pass = self.config.get("Client", "password")
		
		#connect to utorrent and get info for torrent using torrent hash
		uTorrent = TorClient.TorrentClient()
		if not uTorrent.connect(self.webui_URL, self.webui_user, self.webui_pass):
			print 'could not connect to utorrent - exiting' + '\n'
			sys.exit(-1)

		self.torrent = uTorrent.find_torrent(torrent_hash)
		self.torrent_info = uTorrent.get_info(self.torrent)

		if self.torrent_info:

			# if torrent goes from downloading -> seeding, copy and extract files
			if torrent_prev == 'downloading' and torrent_state == 'seeding':

				# get what files to keep and what to extract
				self.keep_files, self.compressed_files, self.keep_structure, self.keep_ext = self.filter_files(self.config, this_dir, self.torrent_info['files'], self.torrent_info['label'])

				if self.keep_structure and torrent_kind == 'multi':
					self.destination = os.path.normpath(os.path.join(self.output_dir,
																self.torrent_info['label'] if self.append_label else '',
																self.torrent_info['name']))
					print 'Copying files from: ' + self.torrent_info['folder']
					print 'to: ' + self.destination
					print '--'
					self.copy_tree(os.path.normpath(torrent_info['folder']), destination, self.keep_ext)
					print '--\n'
				else:
					# create destination if it doesn't exist
					self.destination = os.path.normpath(os.path.join(self.output_dir,
																self.torrent_info['label'] if self.append_label else '',
																self.torrent_info['name'] if self.append_torName else ''))
					self.make_directories(self.destination)
					print 'Copying files from: ' + self.torrent_info['folder']
					print 'to: ' + self.destination

					# Loop through keep_files and copy the files
					print '--'
					for f in self.keep_files:
						self.copy_file(f, self.destination)
					print '--\n'

				# Loop through compressed_files and extract all files
				print 'Extracting files to: ' + self.destination
				print '--'
				for f in self.compressed_files:
					self.extract_file(f, self.destination)
				print '--\n'

				print 'Cleaning up unwanted files in: ' + self.destination
				print '--'
				self.clean_dest(self.destination, self.keep_ext)
				print '--\n'

			# if torrent goes from seeding -> finished, remove torrent from list
			elif torrent_prev == 'seeding' and torrent_state == 'finished' and self.deleteOnFinish:
				print 'Removing torrent: ' + self.torrent_info['name']
				uTorrent.delete_torrent(self.torrent)
		else:
			print 'did not get torrent info'