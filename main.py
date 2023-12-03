#!/usr/bin/python3

import sys
import os
import requests
import base64
import re
import hashlib
import sched, time
from prometheus_client import CollectorRegistry,Gauge
from prometheus_client import start_http_server

host = '192.168.1.1'

login_path = '/cgi-bin/logIn_mhs.cgi'
login_endpoint = 'http://' + host + login_path

traffic_path = '/cgi-bin/traffic_lan_frame.cgi'
traffic_endpoint = 'http://' + host + traffic_path

password = os.environ("ROUTER_PASSWORD")

TAGS_REGEX = '.*Interface.*\r\n.*>(.*)<.*\r\n.*>(.*)<.*\r\n.*>(.*)<.*\r\n.*>(.*)<.*\r\n.*>(.*)<.*\r\n'
SENT_BYTES_REGEX = '.*<td align="left" class="table_font2">Bytes Sent</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n'
RECEIVED_BYTES_REGEX = '.*<td align="left" class="table_font2">Bytes Received</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n.*<td align="center" class="table_font">([0-9]+)</td>\r\n'
class MovistarRouterConnector:
	
	def __init__(self) -> None:
		self.session =  requests.session()
		self.tags = []
		self.bytes_sent = []
		self.bytes_received = []
		self.declare_prometheus_metrics()
	
	def refresh_session(self):
		page = requests.get(login_endpoint) # Needed to get sid, which changed every time
		sid = re.findall(".*var sid = '(.*)';.*", page.text)[0] # needed as it changes every time
		token = password + ':' + str(sid) # merge password with sid
		hash = hashlib.md5(token.encode('utf-8'))
		
		payload = {
			'syspasswd': hash.hexdigest(),
			'syspasswd_1': "",
			'submitValue': "1",
			'leaveBlur': "0"
		}

		self.session.post(login_endpoint, data=payload) # Post to get new session

		# TODO: Check cookie ok
		print("Authenticated!")
	
	def get_traffic(self):
		response = self.session.get(traffic_endpoint)

		if '/cgi-bin/logIn_mhs.cgi' in response.text:
			self.refresh_session()
			response = self.session.get(traffic_endpoint)

		tags = re.findall(TAGS_REGEX, response.text)
		self.tags = tags[0]

		sent_bytes = re.findall(SENT_BYTES_REGEX, response.text)
		self.bytes_sent = sent_bytes[0]

		received_bytes = re.findall(RECEIVED_BYTES_REGEX, response.text)
		self.bytes_received = received_bytes[0]

		print("TAGS: " + str(self.tags))
		print("Bytes sent: " + str(self.bytes_sent))
		print("Bytes received: " + str(self.bytes_received))

	def declare_prometheus_metrics(self):
		label_names = ['interface']
		self.bytes_sent_gauge = Gauge(
			'bytes_sent',
			'Get the sent bytes.',
			label_names,
		)
		self.bytes_received_gauge = Gauge(
			'bytes_received',
			'Get the received bytes',
			label_names,
		)
	
	def update_metrics(self):
		for i, tag in enumerate(self.tags):
			self.bytes_sent_gauge.labels(
				interface=tag,
			).set(self.bytes_sent[i])

			self.bytes_received_gauge.labels(
				interface=tag,
			).set(self.bytes_received[i])

def main():

	start_http_server(8005, '0.0.0.0')
	metrics = MovistarRouterConnector()

	while True:
		
		metrics.get_traffic()
		metrics.update_metrics()
		time.sleep(5)

if __name__ == '__main__':
    sys.exit(main())  # next section explains the use of sys.exit

