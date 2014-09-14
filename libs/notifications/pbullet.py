import sys
from pushbullet.pushbullet import PushBullet

class Pushbullet():
	def __init__(self):
		pass

	def push(self, token, notification_info):
		try:
			pb = PushBullet(token)
			pbDevices = pb.devices
		except Exception, e:
			print e
			return False

		title = 'Poison autoHTPC Notification'
		body = 'title: ' + notification_info['title'] + '\n' +\
				'label: ' + notification_info['label'] + '\n' +\
				'date: ' + notification_info['date'] + '\n' +\
				'time: ' + notification_info['time'] + '\n' +\
				'action: ' + notification_info['action']

		try:
			pbDevices[0].push_note(title, body)
		except Exception, e:
			print e
			return False
		return True