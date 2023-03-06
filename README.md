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

If the third command line option ("via") is omitted, the mails are simply
printed out on the command line. If a "via" option is specified, it needs to
contain details about how/where to send the emails to.

Note that makomailer, by default, also stores if an email could successfully be
delivered so that if there is an error (e.g., connection abort) the mails that
were successfully delivered already are not re-delivered on a second run.

## Licsense
GNU GPL-3.
