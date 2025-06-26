#	makomailer - Sending emails from templates via CLI
#	Copyright (C) 2023-2025 Johannes Bauer
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
import dataclasses
import mailcoil
import datetime

@dataclasses.dataclass
class MailFacility():
	uri: str
	username: str
	password: str

	@classmethod
	def from_dict(cls, dict_data: dict):
		return cls(uri = dict_data["uri"], username = dict_data.get("username"), password = dict_data.get("password"))

	@property
	def fid(self):
		if self.username is not None:
			return f"{self.username} @ {self.uri}"
		else:
			return f"{self.uri}"

	@property
	def dropoff(self):
		dropoff = mailcoil.MailDropoff.parse_uri(self.uri)
		if (self.username is not None) and (self.password is not None):
			dropoff.username = self.username
			dropoff.password = self.password
		return dropoff

class MailVia():
	def __init__(self, configuration_json_filename: str, force_resend: bool = False, print_skipped: bool = False):
		with open(configuration_json_filename) as f:
			self._config = json.load(f)
		self._facilities = [ MailFacility.from_dict(facility_data) for facility_data in self._config ]
		self._force_resend = force_resend
		self._print_skipped = print_skipped

	def _send_facility(self, mail: "mailcoil.Email", facility: MailFacility, context: dict):
		if (facility.fid in context) and ("sent" in context[facility.fid]) and (not self._force_resend):
			# Skip, already sent.
			if self._print_skipped:
				print(f"{mail} skipped drop at {facility.fid} (already delivered at {context[facility.fid]['sent']})")
			return False

		if facility.fid not in context:
			context[facility.fid] = { }

		try:
			print(f"{mail} dropping at {facility.fid}")
			facility.dropoff.post(mail)
			context[facility.fid]["sent"] = datetime.datetime.now(datetime.UTC).isoformat()
		except mailcoil.MailCoilException as e:
			print(f"{mail} failed drop at {facility.fid}: {str(e)}")
			context[facility.fid]["error"] = {
				"at": datetime.datetime.now(datetime.UTC).isoformat(),
				"reason": str(e),
			}
		return True

	def send(self, mail: "mailcoil.Email", context: dict):
		changed = False
		for facility in self._facilities:
			changed = self._send_facility(mail, facility, context) or changed
		return changed
