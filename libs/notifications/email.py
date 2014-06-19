import smtplib

class Email():
	def __init__(self):
		pass

	def send_email(self, email_info, notification_info):

		receivers = []

		receivers.extend(email_info['to'].split('|'))
		subject = 'Poison\'s autoHTPC Script Notification'
		title = notification_info['title']
		label = notification_info['label']
		date = notification_info['date']
		ctime = notification_info['time']
		action = notification_info['action']

		try:
			smtpserver = smtplib.SMTP(email_info['server'],int(email_info['port']))
			smtpserver.ehlo()
			smtpserver.starttls()
			smtpserver.ehlo
			smtpserver.login(email_info['user'], email_info['pass'])
		except Exception, e:
			print e
			return False

		header = 'Content-type: text/html\n' + 'Subject:' + subject + '\n'
		body = """
		<html xmlns="http://www.w3.org/1999/xhtml">
			<head>
				<style type="text/css">
				table.gridtable {
					font-family: verdana,arial,sans-serif;
					font-size:11px;
					color:#333333;
					border-width: 0px;
					border-color: green;
					border-collapse: collapse;
				}
				table.gridtable th {
					border-width: 0x;
					padding: 8px;
					border-style: solid;
					border-color: green;
					background-color: green;
					align: left;
				}
				table.gridtable td {
					border-width: 0px;
					padding: 8px;
					border-style: solid;
					border-color: white;
					background-color: #ffffff;
				}
				</style>
			</head>
			<body bgcolor="black">
				<table class="gridtable">
					<colgroup>
						<col/>
						<col/>
					</colgroup>
					<tr><td>Title:</td><td>%s</td></tr>
					<tr><td>Label:</td><td>%s</td></tr>
					<tr><td>Date:</td><td>%s</td></tr>
					<tr><td>Time:</td><td>%s</td></tr>
					<tr><td>Action:</td><td>%s</td></tr>
				</table>
			</body>
		</html>
		""" % (title, label, date, ctime, action)

		msg = header + body

		smtpserver.sendmail(email_info['server'], receivers, msg)

		smtpserver.close()

		return True