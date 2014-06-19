import smtplib
import time

class email():
	def __init__(self):
		pass

	def send_email(self, to, username, password, smtp_server, smtp_port, email_info):

		receivers = []

		receivers.extend(to.split('|'))
		subject = 'Poison\'s autoHTPC Script Notification'
		title = email_info['title']
		label = email_info['label']
		date = time.strftime("%m/%d/%Y")
		ctime = time.strftime("%I:%M:%S%p")
		action = email_info['action']

		try:
			smtpserver = smtplib.SMTP(smtp_server,smtp_port)
			smtpserver.ehlo()
			smtpserver.starttls()
			smtpserver.ehlo
			smtpserver.login(username, password)
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
					<tr><th align="left">Torrent:</th></tr>
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

		smtpserver.sendmail(username, receivers, msg)
		print 'email sent!'
		smtpserver.close()
		return True