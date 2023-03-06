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

import uuid
import email.utils

class HelperClass():
	@classmethod
	def mail_addr_format(cls, email_address, fullname = None):
		if fullname is None:
			return email_address
		else:
			return email.utils.formataddr((fullname, email_address))

	@classmethod
	def uuid_generate(cls):
		return str(uuid.uuid4())
