import os
import sys
import time
import errno
import shutil
import binascii
import subprocess
import ConfigParser
import libs.client.utorrent as torrent_client

from libs.unrar2 import RarFile
from libs.notifications import email
from libs.notifications import pbullet


class PoisonProcess(object):

    def __init__(self, this_dir, config_filename):
        self.this_dir = this_dir
        self.config = ConfigParser.ConfigParser()
        try:
            self.config.read(config_filename)
            print 'Successfully opened config' + '\n'
        except Exception, e:
            print 'could not open config: ' + str(e)
            exit(-1)
        self.output_dir = self.config.get("General", "outputDirectory")
        self.append_label = self.config.getboolean("General", "appendLabel")
        self.deleteOnFinish = self.config.getboolean("General", "remove")

        self.notifyOnAdd = self.config.getboolean("General", "notify")
        self.notifyOnRem = self.config.getboolean("General", "notifyRemove")

        self.filebot_path = self.config.get("FileBot", "installDirectory")
        self.filebot_path = os.path.join(self.filebot_path, 'filebot.exe')

        self.email_info = {
            'enable': self.config.getboolean("Email", "enable"),
            'server': self.config.get("Email", "SMTPServer"),
            'port': self.config.get("Email", "SMTPPort"),
            'user': self.config.get("Email", "username"),
            'pass': self.config.get("Email", "password"),
            'to': self.config.get("Email", "emailTo")
        }
        self.pb_info = {
            'enable': self.config.getboolean("PushBullet", "enable"),
            'token': self.config.get("PushBullet", "token")
        }

        self.webui_port = self.config.get("Client", "port")
        self.webui = {
            'URL': 'http://localhost:' + str(self.webui_port) + '/gui/',
            'username': self.config.get("Client", "username"),
            'password': self.config.get("Client", "password")
        }

        self.uTorrent = torrent_client.TorrentClient()

        self.keep_files = []
        self.compressed_files = []

    # returns a list of files to keep in destination and a list of files
    # to extract and whether or not to keep the folder structure
    def filter_files(self, files, label):
        ignore_words = (self.config.get("Extensions", "ignore")).split('|')
        archive_ext = tuple((self.config.get("Extensions", "compressed")).split('|'))
        keep_ext = []
        filebot_info = []
        kfs = False
        label_config = ConfigParser.ConfigParser()

        if label != '' or os.path.exists(os.path.join(self.this_dir, 'labels', label) + '.cfg'):
            label_file = os.path.normpath(os.path.join(self.this_dir, 'labels', label) + '.cfg')
            label_config.read(label_file)

            if label_config.getboolean("Type", "video"):
                keep_ext.extend(self.config.get("Extensions", "video").split('|'))
            if label_config.getboolean("Type", "audio"):
                keep_ext.extend(self.config.get("Extensions", "audio").split('|'))
            if label_config.getboolean("Type", "image"):
                keep_ext.extend(self.config.get("Extensions", "image").split('|'))
            if label_config.getboolean("Type", "subtitle"):
                keep_ext.extend(self.config.get("Extensions", "subtitle").split('|'))
            if label_config.getboolean("Type", "readme"):
                keep_ext.extend(self.config.get("Extensions", "readme").split('|'))

            kfs = label_config.getboolean("Folders", "keepFolderStructure")

            filebot_info = {
                'enable': label_config.get("Filebot", "enable"),
                'db': label_config.get("Filebot", "database"),
                'path': label_config.get("Filebot", "path"),
                'format': label_config.get("Filebot", "format"),
            }

            print 'Successfully read ' + label + ' config file' + '\n'
        else:
            keep_ext.extend([
                self.config.get("Extensions", "video").split("|"),
                self.config.get("Extensions", "audio").split("|"),
                self.config.get("Extensions", "image").split("|"),
                self.config.get("Extensions", "subtitle").split("|"),
                self.config.get("Extensions", "readme").split("|")
            ])
            kfs = True
            filebot_info = {
                'enable': False,
                'db': None,
                'path': None,
                'format': None,
            }

        keep_ext = tuple(keep_ext)
        print 'Keeping files with extension: '
        for ext in keep_ext:
            print '\t\t\t\t' + ext
        print ''
        # Sort files into lists depending on file extension
        for f in files:
            if not any(word in f for word in ignore_words):
                if f.endswith(keep_ext):
                    self.keep_files.append(f)

                elif f.endswith(archive_ext):
                    # This will ignore rar sets where all (rar) files end with .rar
                    if f.endswith('.rar') and self.is_mainrar(f):
                        self.compressed_files.append(f)

        return kfs, keep_ext, ignore_words, filebot_info

    # returns true if file is the main rar file in a rar set or just a single rar
    def is_mainrar(self, f):
        with open(f, "rb") as this_file:
            byte = this_file.read(12)

        spanned = binascii.hexlify(byte[10])
        main = binascii.hexlify(byte[11])

        if spanned == "01" and main == "01":    # main rar archive in a set of archives
            return True
        elif spanned == "00" and main == "00":  # single rar
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
                print 'Failed to copy ' + file_name + ': ' + str(e) + '\n'
        else:
            print file_name + ' already exists in destination - skipping'

    # copies a folder structure to destination and only files with the specified extensions
    def copy_tree(self, source, dest, keep_ext):
        for dirName, subdirList, fileList in os.walk(source):
            for fname in fileList:
                if fname.endswith(keep_ext):
                    full_file = os.path.normpath(os.path.join(dirName, fname))
                    relative_path = os.path.relpath(full_file, source)
                    new_path = os.path.normpath(os.path.join(dest, os.path.split(relative_path)[0]))
                    self.make_directories(new_path)
                    self.copy_file(full_file, new_path)

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

    # cleans the destination of all files that don't end with extensions in keep_ext
    def clean_path(self, path, keep_ext, ignore_words):
        for dirName, subdirList, fileList in os.walk(path):
            for fname in fileList:
                if not fname.endswith(keep_ext) or any(word in fname for word in ignore_words):
                    print 'deleting: ' + fname
                    try:
                        os.remove(os.path.normpath(os.path.join(dirName, fname)))
                    except Exception, e:
                        print 'could not delete ' + fname + ': ' + str(e)
        for dirName, subdirList, fileList in os.walk(path, topdown=False):
            if len(fileList) == 0 and len(subdirList) == 0:
                os.rmdir(dirName)

    # renames files from source path and moves them to dest path using filebot
    def rename_move(self, source, dest, db, file_format):
        try:
            fb_args = [
                self.filebot_path,
                '-rename', source,
                '--output', dest,
                '--db', db,
                '--format', file_format,
                '-non-strict'
            ]
            subprocess.call(fb_args)
        except Exception, e:
            print 'could not rename file:', str(e)
        shutil.rmtree(source, ignore_errors=True)

    # notifies user via email or pushbullet
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

    def process_torrent(self, torrent_hash, torrent_kind, torrent_prev, torrent_state):

        #connect to utorrent and get info for torrent using torrent hash
        if not self.uTorrent.connect(self.webui['URL'], self.webui['username'], self.webui['password']):
            print 'could not connect to utorrent - exiting' + '\n'
            sys.exit(-1)

        torrent = None
        torrent_info = None
        try:
            torrent = self.uTorrent.find_torrent(torrent_hash)
            torrent_info = self.uTorrent.get_info(torrent)
            print 'retrieved torrent info'
        except Exception, e:
            print 'error getting torrent info: ' + str(e)
            exit(-1)

        if torrent_info['label'] != 'skip':

            action = None
            # if torrent goes from downloading -> seeding, copy and extract files
            if (torrent_prev == 'downloading') and (torrent_state == 'seeding' or torrent_state == 'moving'):

                # get what files to keep and what to extract
                keep_structure, keep_ext, ignore_words, filebot = self.filter_files(torrent_info['files'], torrent_info['label'])

                if self.append_label:
                    if torrent_info['label'] != '':
                        torrent_label = torrent_info['label']
                    else:
                        torrent_label = 'blank'
                else:
                    torrent_label = ''
                destination = os.path.normpath(os.path.join(self.output_dir, torrent_label, torrent_info['name']))

                print 'Copying files from:\n\t' + torrent_info['folder']
                print 'to:\n\t' + destination
                print '--'
                if keep_structure and torrent_kind == 'multi':
                    self.copy_tree(os.path.normpath(torrent_info['folder']), destination, keep_ext)
                else:
                    # create destination if it doesn't exist
                    self.make_directories(destination)
                    # Loop through keep_files and copy the files
                    for f in self.keep_files:
                        self.copy_file(f, destination)
                print '--\n'

                # Loop through compressed_files and extract all files
                print 'Extracting files to:\n\t' + destination
                print '--'
                for f in self.compressed_files:
                    self.extract_file(f, destination)
                print '--\n'

                # clean files from destination that don't end with an extension in keep_ext
                print 'Cleaning up unwanted files in:\n\t' + destination
                print '--'
                self.clean_path(destination, keep_ext, ignore_words)
                print '--\n'

                # rename files and move them
                print 'Renaming and moving files from:\n\t' + destination
                print '--'
                if filebot['enable']:
                    self.rename_move(destination, filebot['path'], filebot['db'], filebot['format'])
                print '--\n'

                action = 'added'

            # if torrent goes from seeding -> finished and has a label config file, remove torrent from list
            elif torrent_prev == 'seeding' and torrent_state == 'finished' and self.deleteOnFinish and os.path.exists(os.path.join(self.this_dir, 'labels', torrent_info['label']) + '.cfg'):
                print 'Removing torrent:\n\t' + torrent_info['name']
                self.uTorrent.delete_torrent(torrent)
                action = 'removed'

            # notify user
            if action is not None and ((action == 'added' and self.notifyOnAdd) or (action == 'removed' and self.notifyOnRem)):
                notification_info = {
                    'title': torrent_info['name'],
                    'label': torrent_info['label'],
                    'date': time.strftime("%m/%d/%Y"),
                    'time': time.strftime("%I:%M:%S%p"),
                    'action': action
                }
                print 'Notifying user'
                print '--'
                self.notify(self.email_info, self.pb_info, notification_info)
                print '--\n'
        else:
            print 'label is blank - skipping'