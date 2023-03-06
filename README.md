# makomailer
makomailer is a tool that can send emails from the command line easily using
versatile Mako templates. The sent mails can be delivered via SMTP and can also
be stored in a "Sent" folder of an IMAP server. Source data is provided in JSON
form and inclusion of Python code to augment the rendering of the script is
easily possible by specifying Python "code" hooks that are either called once
per JSON-file or once per email to be sent.

## Example
An example can be seen when simply calling:

```
$ ./makomailer.py test_data.json test_email.email
From: Jöhannes Bauer <joe@home.net>
To: Chris Foo <foo@invalid.net>
Subject: Celebräte my 43rd birthday
Date: Tue, 07 Mar 2023 00:33:42 +0100
User-Agent: https://github.com/johndoe31415/makomailer 0.0.1rc0
Content-Type: text/plain; charset="utf-8"
Content-Transfer-Encoding: quoted-printable
MIME-Version: 1.0

Hey there Mr. Chris,

it's time to celebrate my 43rd birthday. As you have discussed with me,
I'm getting a present from you. Wow! Also note that this is a very long
line and it should, in the final email, be broken up into compliant-
length lines (72 chars per line).

Also I want to celebrate umlauts on my birthday. Have some: =C3=A4=C3=B6=C3=
=BC=C3=84=C3=96=C3=9C

I'm looking forward to the Box of chocolates.

Kind regards,
Johannes Bauer
[...]
```

This is the (abbreviated) JSON file that was used as input:

```json
{
	"global": {
		"birthday":		"1980-01-01",
		"year":			2023
	},
	"hooks_once": [
		{
			"filename": "test_preprocess.py"
		}
	],
	"hooks": [
		{
			"filename": "test_preprocess.py"
		}
	],
	"individual": [
		{
			"to": {
				"email":				"foo@invalid.net",
				"firstname":			"Chris",
				"lastname":				"Foo",
				"salutation_prefix":	"Mr.",
				"salutation":			"informal"
			},
			"presents": [
				"Box of chocolates"
			]
		}
	]
}
```

All `global` data is visible from within the template as the `g` variable. Each
rendered email has its individual `i` variable. This data is then used to
render the template, such as in this case:

```mail
From: ${h.mail_addr_format("joe@home.net", "Jöhannes Bauer")}
To: ${h.mail_addr_format(i["to"]["email"], i["to"]["firstname"] + " " + i["to"]["lastname"])}
Subject: Celebräte my ${nth(g["age"])} birthday

%if i["to"]["salutation"] == "formal":
Dear\
%else:
Hey there\
%endif
%if "salutation_prefix" in i["to"]:
 ${i["to"]["salutation_prefix"]}\
%endif
%if i["to"]["salutation"] == "formal":
 ${i["to"]["lastname"]},
%else:
 ${i["to"]["firstname"]},
%endif

it's time to celebrate my ${nth(g["age"])} birthday. As you have discussed with me, I'm getting ${"a present" if (present_cnt == 1) else f"{present_cnt} presents"} from you. ${"Wow!" if (present_cnt > 0) else "Sad."} Also note that this is a very long line and it should, in the final email, be broken up into compliant-length lines (72 chars per line).
```

Note that there is also Python code called:

```python3
def execute_once(self):
	self._template_vars["g"]["birthday"] = self._iso_date_parse(self._template_vars["g"]["birthday"])
	self._template_vars["g"]["age"] = self._template_vars["g"]["year"] - self._template_vars["g"]["birthday"].year

def execute_each(self):
	self._template_vars["nth"] = self._nth
	self._template_vars["present_cnt"] = len(self._template_vars["i"]["presents"])
```

If the third command line option (`via`) is omitted, the mails are simply
printed out on the command line. If a `via` option is specified, it needs to
contain details about how/where to send the emails to.

Note that makomailer, by default, also stores if an email could successfully be
delivered so that if there is an error (e.g., connection abort) the mails that
were successfully delivered already are not re-delivered on a second run.

## Licsense
GNU GPL-3.
