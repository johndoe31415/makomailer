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

import sys
from .FriendlyArgumentParser import FriendlyArgumentParser
from .MakoMailer import MakoMailer

def main():
	parser = FriendlyArgumentParser(description = "Create emails from Mako template.")
	parser.add_argument("-n", "--only-nos", metavar = "number", type = int, action = "append", default = [ ], help = "Only generate emails with this consecutive number. Can be specified multiple times.")
	parser.add_argument("-w", "--manual-wrap", action = "store_true", help = "Rewrap email manually.")
	parser.add_argument("-N", "--no-default-headers", action = "store_true", help = "By default, standard headers that are missing like 'Date' are added automatically to create a complaint email. If this command line option is given, the email is taken verbatim as-is.")
	parser.add_argument("-x", "--external-data", metavar = "json", help = "JSON-formatted data blob that will be accessible inside the template as the 'x' variable.")
	parser.add_argument("--force-resend", action = "store_true", help = "Force resending of emails even if source JSON data indicates it was already successfully sent.")
	parser.add_argument("--no-record-successful-send", action = "store_true", help = "By default, if an email is successfully sent, this is recorded in the source file so that it is not accidently re-sent. This option prevents such a record.")
	parser.add_argument("-v", "--verbose", action = "count", default = 0, help = "Increases verbosity. Can be specified multiple times to increase.")
	parser.add_argument("data_json", help = "Data that should be rewritten into multiple emails.")
	parser.add_argument("template", help = "Email template that should be used for each email.")
	parser.add_argument("via", nargs = "?", help = "JSON file that specifies how to send the email. If omitted, prints to stdout.")
	args = parser.parse_args(sys.argv[1:])

	mako_mailer = MakoMailer(args)
	mako_mailer.run()

if __name__ == "__main__":
	sys.exit(main())
