#	makomailer - Sending emails from templates via CLI
#	Copyright (C) 2023-2024 Johannes Bauer
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
import makomailer
import importlib.util
import email.utils
import email.message
import email.header
import mimetypes
import mako.lookup
import collections
from .HelperClass import HelperClass
from .Exceptions import InvalidTemplateException, InvalidDataException
from .MailsendGateway import MailsendGateway

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
		if show_name is None:
			show_name = os.path.basename(src_filename)
		if mimetype is None:
			mimetype = mimetypes.guess_type(show_name)[0]
			if mimetype is None:
				raise InvalidTemplateException(f"File attachment of '{src_filename}' requested without MIME type; cannot infer MIME type from extension. Please specify manually.")
		(maintype, subtype) = mimetype.split("/", maxsplit = 1)
		with open(src_filename, "rb") as f:
			attachment = self._Attachment(content = f.read(), show_name = show_name, maintype = maintype, subtype = subtype)
		self._render_results["attachments"].append(attachment)
		return ""

	def _attach_data(self, content: bytes, filename: str, mimetype = None):
		if mimetype is None:
			mimetype = mimetypes.guess_type(filename)[0]
			if mimetype is None:
				raise InvalidTemplateException(f"File attachment of '{filename}' requested without MIME type; cannot infer MIME type from extension. Please specify manually.")
		(maintype, subtype) = mimetype.split("/", maxsplit = 1)
		attachment = self._Attachment(content = content, show_name = filename, maintype = maintype, subtype = subtype)
		self._render_results["attachments"].append(attachment)
		return ""

	def _fill_default_headers(self, headers):
		if "Date" not in headers:
			headers["Date"] = email.utils.format_datetime(email.utils.localtime())
		if "User-Agent" not in headers:
			headers["User-Agent"] = f"https://github.com/johndoe31415/makomailer {makomailer.VERSION}"

	def _wrap_text(self, text):
		paragraphs = text.split("\n")
		lines = [ ]
		for par in paragraphs:
			if len(par) == 0:
				lines.append("")
			else:
				lines += textwrap.wrap(par, width = 72)
		return "\n".join(lines)

	def _handle_rendered(self, rendered):
		if "\n\n" not in rendered:
			raise InvalidTemplateException("No '\\n\\n' found in rendered template. Either no headers supplied or template file erroneously encoded with DOS line endings.")
		(headers_text, body_text) = rendered.split("\n\n", maxsplit = 1)

		headers = { }
		for header_line in headers_text.split("\n"):
			if ": " not in header_line:
				raise InvalidTemplateException(f"Not a valid header line: {header_line}")
			(key, value) = header_line.split(": ", maxsplit = 1)
			if key in headers:
				print(f"Warning: Duplicate header {key} present; newer value \"{value}\" overwrites previous \"{headers[key]}\"", file = sys.stderr)
			headers[key] = value

		if not self._args.no_default_headers:
			self._fill_default_headers(headers)


		msg = email.message.EmailMessage()
		for (key, value) in headers.items():
			msg.add_header(key, value)

		content_type = msg.get_content_type()

		if content_type.startswith("text/plain") and self._args.manual_wrap:
			body_text = self._wrap_text(body_text)

		if content_type.startswith("text/plain"):
			msg.set_content(body_text, cte = "quoted-printable")
		elif content_type.startswith("text/html"):
			msg.set_content(body_text, cte = "quoted-printable", subtype = "html")
		else:
			raise ValueError(f"Unable to handle specified content type: {content_type}")
		for attachment in self._render_results["attachments"]:
			msg.add_attachment(attachment.content, maintype = attachment.maintype, subtype = attachment.subtype, filename = attachment.show_name)
		return msg

	def run(self):
		template_dir = os.path.realpath(os.path.dirname(self._args.template))
		template_name = os.path.basename(self._args.template)
		lookup = mako.lookup.TemplateLookup([ template_dir ], strict_undefined = True)
		template = lookup.get_template(template_name)
		via = MailsendGateway(self._args.via, dump_raw = self._args.verbose <= 1, force_resend = self._args.force_resend)

		with open(self._args.data_json) as f:
			series_data = json.load(f, object_pairs_hook = collections.OrderedDict)
		if not isinstance(series_data, dict):
			raise InvalidDataException("The main JSON object must be of type 'dict'.")
		if not "individual" in series_data:
			raise InvalidDataException("The main JSON object must contain a list object named 'individual'.")

		only_nos = set(self._args.only_nos)

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
			}
			if email_no == 1:
				for hook in series_data.get("hooks_once", [ ]):
					self._execute_hook(hook, template_vars, "handle_once")

			if (len(only_nos) > 0) and (email_no not in only_nos):
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
			rendered = template.render(**template_vars)
			msg = self._handle_rendered(rendered)

			# Prepare data structure to use for storing internal information
			if (self._args.via is not None) and (not self._args.no_record_successful_send):
				if "_makomailer" not in individual_content:
					individual_content["_makomailer"] = { }
				makomailer_info = individual_content["_makomailer"]
			else:
				makomailer_info = { }

			# Then send the email
			try:
				if (self._args.verbose >= 1) and (not via.dry_run):
					print(f"Sending email #{email_no} to {msg['To']}")
				via.send(msg, makomailer_info, email_no)
			finally:
				# Even if it was aborted: if the makomailer_info structure was
				# changed, rewrite the source file
				if via.changed:
					with open(self._args.data_json, "w") as f:
						json.dump(series_data, f, indent = "\t", ensure_ascii = False)
						print(file = f)
