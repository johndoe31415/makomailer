#	makomailer - Sending emails from templates via CLI
#	Copyright (C) 2023-2023 Johannes Bauer
#
#	This file is part of makomailer.
#
#	makomailer is free software; you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation; this program is ONLY licensed under
#	version 3 of the License, later versions are explicitly excluded.
#
#	makomailer is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You should have received a copy of the GNU General Public License
#	along with makomailer; if not, write to the Free Software
#	Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#	Johannes Bauer <JohannesBauer@gmx.de>

import json
import datetime
import email.utils
import urllib.parse
import time
import smtplib
import imaplib
from .Exceptions import MailSendingFailedException, InvalidSendConfigurationException

class MailsendGateway():
	def __init__(self, configuration_json, force_resend = False):
		if configuration_json is None:
			self._config = None
		else:
			with open(configuration_json) as f:
				self._config = json.load(f)
		self._force_resend = force_resend
		self._changed = False

	@property
	def changed(self):
		return self._changed

	def _get_facility_id(self, facility):
		if "id" in facility:
			return facility["id"]
		else:
			if "username" in facility:
				return f"{facility['username']} @ {facility['uri']}"
			else:
				return facility["uri"]

	def _send_through_smtp_adv(self, msg, facility, hostname, port, uri, tls):
		assert(tls in [ "no", "starttls", "tls" ])
		smtp_class = smtplib.SMTP_SSL if (tls == "tls") else smtplib.SMTP

		from_addr = email.utils.parseaddr(msg["From"])[1]
		to_addrs = [ email.utils.parseaddr(addr)[1] for addr in msg["To"].split(",") ]

		with smtp_class(host = hostname, port = port) as smtp:
			if tls == "starttls":
				smtp.starttls()
			if ("username" in facility) or ("password" in facility):
				if "username" not in facility:
					raise InvalidSendConfigurationException("Cannot login to SMTP serer without username.")
				if "password" not in facility:
					raise InvalidSendConfigurationException(f"Cannot login to SMTP serer without password (username {facility['username']}).")
				smtp.login(facility["username"], facility["password"])
			smtp.sendmail(from_addr, to_addrs, msg.as_string())

	def _send_through_smtp(self, msg, facility, hostname, port, uri):
		if port is None:
			port = 25
		return self._send_through_smtp_adv(msg, facility, hostname, port, uri, tls = "no")

	def _send_through_smtp_starttls(self, msg, facility, hostname, port, uri):
		if port is None:
			port = 25
		return self._send_through_smtp_adv(msg, facility, hostname, port, uri, tls = "starttls")

	def _send_through_smtps(self, msg, facility, hostname, port, uri):
		if port is None:
			port = 465
		return self._send_through_smtp_adv(msg, facility, hostname, port, uri, tls = "tls")

	def _send_through_imap_adv(self, msg, facility, hostname, port, uri, tls):
		if "username" not in facility:
			raise InvalidSendConfigurationException("Cannot login to IMAP serer without username.")
		if "password" not in facility:
			raise InvalidSendConfigurationException(f"Cannot login to IMAP serer without password (username {facility['username']}).")
		mailbox = uri.path.lstrip("/")
		if len(mailbox) == 0:
			raise InvalidSendConfigurationException(f"Cannot login to IMAP serer without mailbox name)")
		imap_class = imaplib.IMAP4_SSL if tls else imaplib.IMAP4
		with imap_class(host = hostname, port = port) as imap:
			imap.login(facility["username"], facility["password"])
			(status, imap_rsp) = imap.select(mailbox = mailbox)
			if status != "OK":
				raise InvalidSendConfigurationException(f"No such IMAP mailbox \"{mailbox}\" on {hostname}:{port}: {str(imap_rsp)}")

			imap_date_time = imaplib.Time2Internaldate(time.time())
			(status, imap_rsp) = imap.append(mailbox = mailbox, flags = None, date_time = imap_date_time, message = msg.as_string().encode("utf-8"))
			if status != "OK":
				raise InvalidSendConfigurationException(f"Unable to append message to IMAP mailbox \"{mailbox}\" on {hostname}:{port}: {str(imap_rsp)}")

	def _send_through_imap(self, msg, facility, hostname, port, uri):
		if port is None:
			port = 143
		return self._send_through_imap_adv(msg, facility, hostname, port, uri, tls = False)

	def _send_through_imaps(self, msg, facility, hostname, port, uri):
		if port is None:
			port = 993
		return self._send_through_imap_adv(msg, facility, hostname, port, uri, tls = True)

	def _send_through(self, msg, facility, makomailer_info):
		facility_id = self._get_facility_id(facility)
		if facility_id not in makomailer_info:
			makomailer_info[facility_id] = { }

		if (not self._force_resend) and ("sent_utc" in makomailer_info[facility_id]):
			# Already sent, ignore.
			return

		uri = urllib.parse.urlparse(facility["uri"])
		if ":" in uri.netloc:
			(hostname, port) = uri.netloc.split(":", maxsplit = 1)
			port = int(port)
		else:
			(hostname, port) = (uri.netloc, None)

		scheme = uri.scheme.replace("+", "_")
		send_handler = getattr(self, f"_send_through_{scheme}", None)
		if send_handler is None:
			raise InvalidSendConfigurationException(f"No such handler to send email: {scheme}")

		try:
			send_handler(msg, facility, hostname, port, uri)

			# Sending was successful!
			makomailer_info[facility_id]["sent_utc"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
			makomailer_info[facility_id]["mail_date"] = msg["Date"]
			self._changed = True
		except Exception as e:
			raise MailSendingFailedException(f"Error trying to deliver mail via {scheme}: {str(e)}") from e

		#if external_data is not None:
		#	individual_content["_makomailer"]["external_data"] = external_data
		pass

	def send(self, msg, makomailer_info, mail_no = 0):
		self._changed = False
		if self._config is None:
			# Only print on stdout
			print(f"{'─' * 60} mail {mail_no} follows {'─' * 60}")
			print(str(msg))
		else:
			for facility in self._config:
				self._send_through(msg, facility, makomailer_info)
