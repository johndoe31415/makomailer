import datetime

class Handler():
	def __init__(self, template_vars):
		self._template_vars = template_vars

	def _iso_date_parse(self, iso_date):
		ts = datetime.datetime.strptime(iso_date, "%Y-%m-%d")
		return ts

	def _nth(self, number):
		if (number % 10) == 1:
			return f"{number}st"
		elif (number % 10) == 2:
			return f"{number}nd"
		elif (number % 10) == 3:
			return f"{number}rd"
		else:
			return f"{number}th"

	def execute_once(self):
		self._template_vars["g"]["birthday"] = self._iso_date_parse(self._template_vars["g"]["birthday"])
		self._template_vars["g"]["age"] = self._template_vars["g"]["year"] - self._template_vars["g"]["birthday"].year

	def execute_each(self):
		self._template_vars["nth"] = self._nth
		self._template_vars["present_cnt"] = len(self._template_vars["i"]["presents"])

def handle_once(template_vars):
	Handler(template_vars).execute_once()
	return template_vars

def handle_each(template_vars):
	Handler(template_vars).execute_each()
	return template_vars

