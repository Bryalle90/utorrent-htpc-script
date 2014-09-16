import os
import sys
import time
import errno
import shutil
import binascii
import subprocess
import ConfigParser
import libs.client.utorrent as TorClient

from libs.unrar2 import RarFile
from libs.notifications import email
from libs.notifications import pbullet

class PoisonProcess(object):
	def __init__(self):
		pass

	# returns a list of files to keep in destination and a list of files to extract and whether or not to keep the folder structure
	def filter_files(self, config, main_dir, files, label):
		ignore_words = (config.get("Extensions", "ignore")).split('|')
		archive_ext = tuple((config.get("Extensions", "compressed")).split('|'))
		keep_ext = []
		keep_files = []
		compressed_files = []
		filebot_info = []
		kfs = False
		label_config = ConfigParser.ConfigParser()

		if os.path.exists(os.path.join(main_dir, 'labels', label) + '.cfg'):
			label_file = os.path.normpath(os.path.join(main_dir, 'labels', label) + '.cfg')
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

			kfs = label_config.getboolean("Folders", "keepFolderStructure")

			filebot_info = {
				'enable': label_config.get("Filebot", "enable"),
				'db': label_config.get("Filebot", "database"),
				'path': label_config.get("Filebot", "path"),
				'format': label_config.get("Filebot", "format"),
			}

			print 'Successfully read ' + label + ' config file' + '\n'
		else:
			keep_ext.extend([config.get("Extensions", "video").split("|"),
							config.get("Extensions", "audio").split("|"),
							config.get("Extensions", "image").split("|"),
							config.get("Extensions", "subtitle").split("|"),
							config.get("Extensions", "readme").split("|")])
			print 'label file, ' + label + '.cfg does not exist' + '\n'
		keep_ext = tuple(keep_ext)
		print 'Keeping files with extension: '
		for ext in keep_ext:
			print '\t\t\t\t' + ext
		print ''
		# Sort files into lists depending on file extension
		for f in files:
			if not any(word in f for word in ignore_words):
				if f.endswith(keep_ext):
					keep_files.append(f)

				elif f.endswith(archive_ext):
					if f.endswith('.rar') and self.is_mainRar(f):	# This will ignore rar sets where all (rar) files end with .rar
						compressed_files.append(f)

		return keep_files, compressed_files, kfs, keep_ext, filebot_info

	# returns true if file is the main rar file in a rar set or just a single rar
	def is_mainRar(self, file):
		with open(file, "rb") as file:
			byte = file.read(12)

		spanned = binascii.hexlify(byte[10])
		main = binascii.hexlify(byte[11])

		if spanned == "01" and main == "01":	# main rar archive in a set of archives
			return True
		elif spanned == "00" and main == "00":	# single rar
			return True

		return False

	# creates a directory if it doesn't already exist
	def make_directories(self, directory):
		if not os.path.exists(directory):
			try:
				os.makedirs(directory)
			except OSError as e:
				if e.errno != errno.EEXIST:
					raise
				pass

	# copies a file to a destination folder, returns success
	def copy_file(self, source_file, destination):
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

	# copies a folder structure to destination and only files with the specified extensions
	def copy_tree(self, source, dest, keep_ext):
		for dirName, subdirList, fileList in os.walk(source):
			for fname in fileList:
				if fname.endswith(keep_ext):
					full_file = os.path.normpath(os.path.join(dirName, fname))
					relPath = os.path.relpath(full_file, source)
					newPath = os.path.normpath(os.path.join(dest, os.path.split(relPath)[0]))
					self.make_directories(newPath)
					self.copy_file(full_file, newPath)

	# extracts files from source rar to destination directory
	def extract_file(self, source_file, destination):
		try:
			rar_handle = RarFile(source_file)
			for rar_file in rar_handle.infolist():
				sub_path = os.path.join(destination, rar_file.filename)
				if rar_file.isdir and not os.path.exists(sub_path):
					os.makedirs(sub_path)
				else:
					rar_handle.extract(condition=[rar_file.index], path=destination, withSubpath=True, overwrite=False)
			del rar_handle
			print "Successfully extracted " + os.path.split(source_file)[1]
		except Exception, e:
			print "Failed to extract " + os.path.split(source_file)[1] + ": " + str(e)

	# cleans the destination of all files that done end with extensions in keep_ext
	def clean_dest(self, dest, keep_ext, ignore_words):
		for dirName, subdirList, fileList in os.walk(dest):
			for fname in fileList:
				if not fname.endswith(keep_ext) or any(word in fname for word in ignore_words):
					print 'deleting: ' + fname
					try:
						os.remove(os.path.normpath(os.path.join(dirName, fname)))
					except Exception, e:
						print 'could not delete ' + fname + ': ' + str(e)
		for dirName, subdirList, fileList in os.walk(dest, topdown=False):
			if len(fileList) == 0 and len(subdirList) == 0:
				os.rmdir(dirName)

	def rename_move(self, install_path, source, dest, db, format):
		self.fb_path = os.path.join(install_path, 'filebot.exe')
		try:
			fb_args = [
				self.fb_path,
				'-rename', source,
				'--output', dest,
				'--db', db,
				'--format', format,
				'-non-strict'
			]
			subprocess.call(fb_args)
		except Exception, e:
			print 'could not rename file:', str(e)
		shutil.rmtree(source, ignore_errors=True)

	def notify(self, email_info, pb_info, notification_info):
		if email_info['enable']:
			em = email.Email()
			if em.send_email(email_info, notification_info):
				print 'notification emailed!'
			else:
				print 'could not email notification'

		if pb_info['enable']:
			pb = pbullet.Pushbullet()
			if pb.push(pb_info['token'], notification_info):
				print 'notification pushed via PushBullet!'
			else:
				print 'could not push notification'

	def process_torrent(self, this_dir, configFilename, torrent_hash, torrent_kind, torrent_prev, torrent_state):
		self.config = ConfigParser.ConfigParser()
		try:
			self.config.read(configFilename)
			print 'Successfully read config' + '\n'
		except Exception, e:
			print e
			exit(-1)
		self.output_dir = self.config.get("General", "outputDirectory")
		self.append_label = self.config.getboolean("General", "appendLabel")
		self.deleteOnFinish = self.config.getboolean("General", "remove")

		self.ignore_words = (self.config.get("Extensions", "ignore")).split('|')

		self.notifyOnAdd = self.config.getboolean("General", "notify")
		self.notifyOnRem = self.config.getboolean("General", "notifyRemove")

		self.email_info = {
			'enable': self.config.getboolean("Email", "enable"),
			'server': self.config.get("Email", "SMTPServer"),
			'port': self.config.get("Email", "SMTPPort"),
			'user': self.config.get("Email", "username"),
			'pass': self.config.get("Email", "password"),
			'to': self.config.get("Email", "emailTo"),
		}
		self.pb_info = {
			'enable': self.config.getboolean("PushBullet", "enable"),
			'token': self.config.get("PushBullet", "token"),
		}

		self.filebot_path = self.config.get("FileBot", "installDirectory")

		self.webui_port = self.config.get("Client", "port")
		self.webui_URL = 'http://localhost:' + str(self.webui_port) + '/gui/'
		self.webui_user = self.config.get("Client", "username")
		self.webui_pass = self.config.get("Client", "password")

		#connect to utorrent and get info for torrent using torrent hash
		uTorrent = TorClient.TorrentClient()
		if not uTorrent.connect(self.webui_URL, self.webui_user, self.webui_pass):
			print 'could not connect to utorrent - exiting' + '\n'
			sys.exit(-1)

		try:
			self.torrent = uTorrent.find_torrent(torrent_hash)
			self.torrent_info = uTorrent.get_info(self.torrent)
		except Exception, e:
			print 'error getting torrent info'
			print e
			exit(-1)

		if self.torrent_info and self.torrent_info['label'] != '':

			self.action = None
			# if torrent goes from downloading -> seeding, copy and extract files
			if (torrent_prev == 'downloading') and (torrent_state == 'seeding' or torrent_state == 'moving'):

				# get what files to keep and what to extract
				self.keep_files = []
				self.compressed_files = []
				self.keep_files, self.compressed_files, self.keep_structure, self.keep_ext, self.filebot = self.filter_files(self.config, this_dir, self.torrent_info['files'], self.torrent_info['label'])
				if self.keep_structure and torrent_kind == 'multi':
					self.destination = os.path.normpath(os.path.join(self.output_dir,
																self.torrent_info['label'] if self.append_label else '',
																self.torrent_info['name']))
					print 'Copying files from:\n\t' + self.torrent_info['folder']
					print 'to:\n\t' + self.destination
					print '--'
					self.copy_tree(os.path.normpath(self.torrent_info['folder']), self.destination, self.keep_ext)
					print '--\n'
				else:
					# create destination if it doesn't exist
					self.destination = os.path.normpath(os.path.join(self.output_dir,
																self.torrent_info['label'] if self.append_label else '',
																self.torrent_info['name']))
					self.make_directories(self.destination)
					print 'Copying files from:\n\t' + self.torrent_info['folder']
					print 'to:\n\t' + self.destination

					# Loop through keep_files and copy the files
					print '--'
					for f in self.keep_files:
						self.copy_file(f, self.destination)
					print '--\n'

				# Loop through compressed_files and extract all files
				print 'Extracting files to:\n\t' + self.destination
				print '--'
				for f in self.compressed_files:
					self.extract_file(f, self.destination)
				print '--\n'

				print 'Cleaning up unwanted files in:\n\t' + self.destination
				print '--'
				self.clean_dest(self.destination, self.keep_ext, self.ignore_words)
				print '--\n'

				print 'Renaming and moving files from:\n\t' + self.destination
				print '--'
				if self.filebot['enable']:
					self.rename_move(self.filebot_path, self.destination, self.filebot['path'], self.filebot['db'], self.filebot['format'])
				print '--\n'

				self.action = 'added'

			# if torrent goes from seeding -> finished and has a label config file, remove torrent from list
			elif torrent_prev == 'seeding' and torrent_state == 'finished' and self.deleteOnFinish and os.path.exists(os.path.join(this_dir, 'labels', self.torrent_info['label']) + '.cfg'):
				print 'Removing torrent:\n\t' + self.torrent_info['name']
				uTorrent.delete_torrent(self.torrent)
				self.action = 'removed'

			# notify user
			if self.action != None and ( (self.action == 'added' and self.notifyOnAdd) or (self.action == 'removed' and self.notifyOnRem) ):
				self.notification_info = {
						'title': self.torrent_info['name'],
						'label': self.torrent_info['label'],
						'date': time.strftime("%m/%d/%Y"),
						'time': time.strftime("%I:%M:%S%p"),
						'action': self.action,
				}
				print 'Notifying user'
				print '--'
				self.notify(self.email_info, self.pb_info, self.notification_info)
				print '--\n'
		else:
			print 'label is blank - skipping'