import setuptools

with open("README.md") as f:
	long_description = f.read()

setuptools.setup(
	name = "makomailer",
	packages = setuptools.find_packages(),
	version = "0.0.3",
	license = "gpl-3.0",
	description = "Versatile CLI-based tool to send mails rendered from Mako templates, supporting SMTP and IMAP",
	long_description = long_description,
	long_description_content_type = "text/markdown",
	author = "Johannes Bauer",
	author_email = "joe@johannes-bauer.com",
	url = "https://github.com/johndoe31415/makomailer",
	download_url = "https://github.com/johndoe31415/makomailer/archive/v0.0.3.tar.gz",
	keywords = [ "mako", "template", "email" ],
	install_requires = [
		"mako",
	],
	entry_points = {
		"console_scripts": [
			"makomailer = makomailer.__main__:main",
		]
	},
	include_package_data = False,
	classifiers = [
		"Development Status :: 4 - Beta",
		"Intended Audience :: Developers",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
		"Programming Language :: Python :: 3",
		"Programming Language :: Python :: 3 :: Only",
		"Programming Language :: Python :: 3.5",
		"Programming Language :: Python :: 3.6",
		"Programming Language :: Python :: 3.7",
		"Programming Language :: Python :: 3.8",
		"Programming Language :: Python :: 3.9",
		"Programming Language :: Python :: 3.10",
	],
)
