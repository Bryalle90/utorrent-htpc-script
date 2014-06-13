videoFiles = True
audioFiles = False
imageFiles = False
subtitleFiles = False
readmeFiles = False


################## DO NOT EDIT BELOW ##################
def get_filePrefs():
	file_prefs = {
					'video': videoFiles ,
					'audio': audioFiles ,
					'image': imageFiles ,
					'subs': subtitleFiles ,
					'readme': readmeFiles ,
	}
	return file_prefs