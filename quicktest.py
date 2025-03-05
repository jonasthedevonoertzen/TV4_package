import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(user_email):
    # set up the SMTP server
    smtp_server = smtplib.SMTP(host='smtp.web.de', port=587)
    smtp_server.starttls()

    # Login to your email account
    smtp_server.login("talevortex@web.de", "14JbH6zAZWiMr0")

    # create a message
    msg = MIMEMultipart()

    # setup the parameters of the message
    msg['From'] = "talevortex@web.de"
    msg['To'] = user_email
    msg['Subject'] = "This is a test email from Python"

    # add in the message body
    msg.attach(MIMEText("This is a test email sent from a Python script", 'plain'))

    # send the message via the server
    smtp_server.send_message(msg)

    smtp_server.quit()

send_email('thede.v.oertzen@web.de')