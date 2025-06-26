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

import os
import sys
import json
import copy
import textwrap
import datetime
import base64
import traceback
import importlib.util
import makomailer
import mailcoil
import mako.lookup
import collections
from .HelperClass import HelperClass
from .MailVia import MailVia
from .Exceptions import InvalidTemplateException, InvalidDataException

class MakoMailer():
	_Attachment = collections.namedtuple("Attachment", [ "content", "show_name", "maintype", "subtype" ])

	def __init__(self, args):
		self._args = args

	def _execute_hook(self, hook, template_vars, handler_name):
		filename = hook["filename"]
		# Relative to the actual template dir
		template_dirname = os.path.dirname(self._args.template)
		if template_dirname != "":
			filename = f"{template_dirname}/{filename}"
		spec = importlib.util.spec_from_file_location("hook_module", filename)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		handler = getattr(module, handler_name)
		template_vars = handler(template_vars)

	def _error(self, msg):
		raise Exception(msg)

	def _attach_file(self, src_filename, show_name = None, mimetype = None):
		self._render_results["attachments"].append({
			"type": "file",
			"src_filename": src_filename,
			"show_name": show_name,
			"mimetype": mimetype,
		})
		return ""

	def _attach_data(self, content: bytes, filename: str, mimetype = None):
		self._render_results["attachments"].append({
			"type": "data",
			"content": content,
			"filename": filename,
			"mimetype": mimetype,
		})
		return ""

	def _attach_b64(self, content_base64: str, filename: str, mimetype = None):
		content = base64.b64decode(content_base64)
		return self._attach_data(content, filename = filename, mimetype = mimetype)

	def _fill_default_headers(self, headers):
		if "Date" not in headers:
			headers["Date"] = email.utils.format_datetime(email.utils.localtime())
		if "User-Agent" not in headers:
			headers["User-Agent"] = f""

	def _wrap_text(self, text):
		paragraphs = text.split("\n")
		lines = [ ]
		for par in paragraphs:
			if len(par) == 0:
				lines.append("")
			else:
				lines += textwrap.wrap(par, width = 72)
		return "\n".join(lines)

	def _parse_email_text(self, rendered_text: str):
		if "\n\n" not in rendered_text:
			raise InvalidTemplateException("No '\\n\\n' found in rendered template. Either no headers supplied or template file erroneously encoded with DOS line endings.")
		(headers_text, body_text) = rendered_text.split("\n\n", maxsplit = 1)

		headers = { }
		for header_line in headers_text.split("\n"):
			if ": " not in header_line:
				raise InvalidTemplateException(f"Not a valid header line: {header_line}")
			(key, value) = header_line.split(": ", maxsplit = 1)
			lkey = key.lower()
			if lkey in headers:
				print(f"Warning: Duplicate header {key} present; newer value \"{value}\" overwrites previous \"{headers[key]}\"", file = sys.stderr)
			headers[lkey] = value
		return (headers, body_text)


	def _handle_rendered(self, rendered_text: str):
		(headers, body_text) = self._parse_email_text(rendered_text)

		if "from" not in headers:
			raise InvalidTemplateException("No 'From' header field specified.")

		from_addr = mailcoil.MailAddress.parsemany(headers["from"])
		if len(from_addr) != 1:
			raise InvalidTemplateException("You need to specify exactly one 'From' address.")

		if "to" not in headers:
			raise InvalidTemplateException("No 'To' header field specified.")
		to_addr = mailcoil.MailAddress.parsemany(headers["to"])

		if len(to_addr) < 0:
			raise InvalidTemplateException("You need to specify at least one 'To' address.")

		mail = mailcoil.Email(from_address = from_addr[0], wrap_text = self._args.manual_wrap)
		mail.user_agent = f"https://github.com/johndoe31415/makomailer v{makomailer.VERSION}"
		mail.to(*to_addr)
		if ("cc" in headers):
			cc_addr = mailcoil.MailAddress.parsemany(headers["cc"])
			mail.cc(*cc_addr)
		if ("bcc" in headers):
			bcc_addr = mailcoil.MailAddress.parsemany(headers["bcc"])
			mail.cc(*bcc_addr)

		if "subject" in headers:
			mail.subject = headers["subject"]

		if "content-type" in headers:
			if headers["content-type"] == "text/plain":
				mail.text = body_text
			elif headers["content-type"] == "text/html":
				mail.html = body_text
			else:
				raise InvalidTemplateException("When setting a Content-Type, it needs to be either text/plain or text/html.")
		else:
			# Without content-type, use text/plain
			mail.text = body_text

		for attachment in self._render_results["attachments"]:
			if attachment["type"] == "file":
				mail.attach(attachment["src_filename"], mimetype = attachment["mimetype"], shown_filename = attachment["show_name"])
			elif attachment["type"] == "data":
				mail.attach_data(attachment["content"], filename = attachment["filename"], mimetype = attachment["mimetype"])
			else:
				raise NotImplementedError(attachment["type"])
		return mail

	def run(self):
		template_dir = os.path.realpath(os.path.dirname(self._args.template))
		template_name = os.path.basename(self._args.template)
		lookup = mako.lookup.TemplateLookup([ template_dir ], strict_undefined = True)
		template = lookup.get_template(template_name)
		if self._args.via is None:
			via = None
		else:
			via = MailVia(self._args.via, force_resend = self._args.force_resend)

		with open(self._args.data_json) as f:
			series_data = json.load(f, object_pairs_hook = collections.OrderedDict)
		if not isinstance(series_data, dict):
			raise InvalidDataException("The root JSON object must be of type 'dict'.")
		if not "individual" in series_data:
			raise InvalidDataException("The root JSON object must contain a list object named 'individual'.")

		only_send_mail_numbers = set(self._args.only_nos)

		if self._args.external_data is not None:
			external_data = json.loads(self._args.external_data)
		else:
			external_data = None

		global_content = copy.deepcopy(series_data.get("global"))
		for (email_no, individual_content) in enumerate(series_data["individual"], 1):
			template_vars = {
				"g":			global_content,
				"i":			copy.deepcopy(individual_content),
				"x":			external_data,
				"h":			HelperClass,
				"error":		self._error,
				"attach_file":	self._attach_file,
				"attach_data":	self._attach_data,
				"attach_b64":	self._attach_b64,
			}
			if email_no == 1:
				for hook in series_data.get("hooks_once", [ ]):
					self._execute_hook(hook, template_vars, "handle_once")

			if (len(only_send_mail_numbers) > 0) and (email_no not in only_send_mail_numbers):
				# Skip this email, not requested on command line
				continue

			if (not self._args.force_resend) and (individual_content.get("_makomailer", { }).get("sent_utc") is not None):
				# Already sent this email, skip.
				continue

			for hook in series_data.get("hooks", [ ]):
				self._execute_hook(hook, template_vars, "handle_each")

			self._render_results = {
				"attachments":	[ ],
			}
			try:
				rendered = template.render(**template_vars)
			except Exception as e:
				print(f"Rendering of email #{email_no} failed, {e.__class__.__name__}: {str(e)}", file = sys.stderr)
				if self._args.verbose >= 2:
					print(traceback.format_exc(), file = sys.stderr)
					print(file = sys.stderr)
				continue

			# Convert the rendered email into a mailcoil email
			mail = self._handle_rendered(rendered)

			if via is None:
				print(f"{'─' * 50} Mail #{email_no} {'─' * 50}")
				print(mail.serialize().content)
			else:
				if "_makomailer" not in individual_content:
					individual_content["_makomailer"] = { }
				change = True
				try:
					change = via.send(mail, context = individual_content["_makomailer"])
				finally:
					if change and (not self._args.no_record_successful_send):
						temp_filename = self._args.data_json + ".tmp.{os.urandom(8).hex()}"
						with open(temp_filename, "w") as f:
							json.dump(series_data, f, indent = "\t", ensure_ascii = False)
							print(file = f)
						os.rename(temp_filename, self._args.data_json)
