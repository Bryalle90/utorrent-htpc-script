import os
import sys
import binascii
import ConfigParser
import libs.client.utorrent as TorClient
from libs.unrar2 import RarFile

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
			print 'could not connect to utorrent - exiting'
			sys.exit(-1)
		torrent = uTorrent.find_torrent(torrent_hash)
		torrent_info = uTorrent.get_info(torrent)
		
		torrent_state = torrent_info['state'].split(' ')
		torrent_state = torrent_state[1] if torrent_state[0] == '[F]' or \
											torrent_state[0] == 'Queued' or \
											torrent_state[0] == 'Super' and not \
											torrent_state[1] == '' else \
											torrent_state[0]
		torrent_state = torrent_state.lower()
		
		#
		if torrent_info:
			if torrent_state == 'seeding' or torrent_state == 'seed':

				# get what files to keep and what to extract
				keep_files, compressed_files, keep_structure = filter_files(torrent_info['files'], torrent_info['label'])

				if keep_structure:
					destination = os.path.normpath(os.path.join(output_dir,
																torrent_info['label'] if append_label else '',
																torrent_info['name'])
					copy_tree(os.path.normpath(torrent_info['folder']), destination)
				else:
					# create destination if it doesn't exist
					destination = os.path.normpath(os.path.join(output_dir,
																torrent_info['label'] if append_label else '',
																torrent_info['name'] if append_torName else ''))
					self.make_directories(destination)
					# Loop through keep_files and copy the files
					for f in keep_files:
						file_name = os.path.split(f)[1]
						if self.copy_file(f, destination):
							print("Successfully copied: %s", file_name)
						else:
							print("Failed to copy: %s", file_name)

				# Loop through compressed_files and extract all files
				for f in compressed_files:
					file_name = os.path.split(f)[1]
					if self.extract_file(f, destination):
						print("Successfully extracted: %s", file_name)
					else:
						print("Failed to extract: %s", file_name)

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

		return keep_files, compressed_files, kfs
		
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

	def copy_file(self, source_file, destination):	# copies a file to a destination folder
		file_name = os.path.split(source_file)[1]
		destination_file = os.path.join(destination, file_name)
		if not os.path.isfile(destination_file):
			try:
				print "Copying file: %s to: %s", file_name, destination
				shutil.copy2(source_file, destination_file)

				return True

			except Exception, e:
				print "Failed to process %s: %s %s", file_name, e, traceback.format_exc()
			return False

	def copy_tree(self, src, dest):	# copy full file structure and files
		try:
			shutil.copytree(sourced, destination)
		except OSError as e:
			print('Directory not copied. Error: %s' % e)
						
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
			return True

		except Exception, e:
			print "Failed to extract %s: %s %s", os.path.split(source_file)[1], e, traceback.format_exc()
		return False

if __name__ == "__main__":
	this_dir = os.getcwd()
	config = ConfigParser.ConfigParser()
	configFilename = os.path.normpath(os.path.join(this_dir, "config.cfg"))
	config.read(configFilename)
	
	exit(0)

	torrent_hash = sys.argv[1]  # Hash of the torrent, %I

	if len(torrent_hash) == 32:
		torrent_hash = b16encode(b32decode(torrent_hash))

	if len(torrent_hash) == 40:
		pp = PoisonProcess()
		pp.main(torrent_hash)
	else:
		print 'Script only compatible with uTorrent 3.0+'