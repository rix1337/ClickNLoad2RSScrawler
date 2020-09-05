# -*- coding: utf-8 -*-
# ClickNLoad2RSScrawler
# Projekt von https://github.com/rix1337
#
# Enthält Code von https://github.com/drwilly/clicknload2text
# Lizenz: https://github.com/drwilly/clicknload2text/blob/master/LICENSE

"""RSScrawler.

Usage:
  cnl2rsscrawler.py [--url=<URL>]

Options:
  --url=<URL>    Your RSScrawler's base URL
"""

import base64
import cgi
import fnmatch
import http.server
import subprocess
from io import StringIO

import requests
from docopt import docopt


class URLMap:
    def __init__(self, pattern, get_fn=None, post_fn=None):
        self.pattern = pattern
        self.get_fn = get_fn
        self.post_fn = post_fn


class output:
    def __init__(self, fn, file=None):
        self.fn = fn
        self.file = file

    def __call__(self, *args, **kwargs):
        output = self.fn(*args, **kwargs)
        if self.file is None:
            print(output)
        else:
            print(output, file=self.file)
        return output


class CNLHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server):
        self.URL_MAPPING = [
            URLMap("/", get_fn=self.alive),
            URLMap("/jdcheck.js", get_fn=self.jdcheck),
            URLMap("/crossdomain.xml", get_fn=self.crossdomain),
            URLMap("/flash/add", post_fn=self.add),
            URLMap("/flash/addcrypted2", post_fn=self.addcrypted2),
        ]
        super().__init__(request, client_address, server)

    def do_GET(self):
        response_fn = None
        for mapping in (m for m in self.URL_MAPPING if m.get_fn is not None):
            if fnmatch.fnmatch(self.path, mapping.pattern):
                response_fn = mapping.get_fn
                break
        self.respond(response_fn)

    def do_POST(self):
        parameters = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']}
        )
        response_fn = None
        for mapping in (m for m in self.URL_MAPPING if m.post_fn is not None):
            if fnmatch.fnmatch(self.path, mapping.pattern):
                response_fn = lambda: mapping.post_fn(parameters)
                break
        self.respond(response_fn)

    def respond(self, response_fn):
        if response_fn is None:
            self.send_error(404, "Not Found")
            return
        try:
            self.send_response(200, "OK")
            self.end_headers()
            self.wfile.write(response_fn().encode())
        except Exception as e:
            self.send_error(500, str(e))
            return

    @staticmethod
    def alive():
        return "JDownloader"

    @staticmethod
    def jdcheck():
        return "jdownloader=true; var version='17461';"

    @staticmethod
    def crossdomain():
        return """
			<?xml version="1.0" ?>
			<!DOCTYPE cross-domain-policy SYSTEM "http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">
			<cross-domain-policy>
				<allow-access-from domain="*" secure="false" />
			</cross-domain-policy>
		"""

    @staticmethod
    @output
    def add(parameters):
        passwords = parameters.getfirst("passwords")
        name = parameters.getfirst("package", "ClickAndLoad Package")
        urls = [u for u in parameters.getfirst("urls").split("\r\n") if len(u) > 0]

        return format_package(name, urls, passwords)

    @staticmethod
    @output
    def addcrypted2(parameters):
        passwords = parameters.getfirst("passwords")
        name = parameters.getfirst("package", "ClickAndLoad Package")
        crypted = parameters.getfirst("crypted")
        jk = parameters.getfirst("jk")

        key = jk_eval(jk)

        uncrypted = aes_decrypt(crypted, key)
        urls = [result for result in uncrypted.replace('\x00', '').split("\r\n") if len(result) > 0]

        return format_package(name, urls, passwords)


def encode_base64(value):
    return base64.b64encode(value.encode("utf-8")).decode().replace("/", "-")


def format_package(name, urls, passwords=None):
    buf = StringIO()

    # Load RSScrawler base URL
    arguments = docopt(__doc__, version='RSScrawler')
    rsscrawler_url = "http://" + arguments['--url'].replace("http://", "")

    # Create and send RSScrawler Payload
    print("[RSScrawler Sponsors Helper Click'n'Load erfolgreich] - " + name)
    links = str(urls).replace(" ", "")
    crawler = rsscrawler_url + '/sponsors_helper/to_download/'
    payload = encode_base64(links + '|' + name + '|' + str(passwords))
    requests.get(crawler + payload)

    return buf.getvalue()


def call(cmd, input=None):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    if input is not None:
        p.stdin.write(input.encode())
    p.stdin.close()
    with p.stdout:
        return p.stdout.read().decode()


def aes_encrypt(data, key):
    """
    data	- base64 encoded input
    key	- hex encoded password
    """
    enc_cmd = ["openssl", "enc", "-e", "-AES-128-CBC", "-nosalt", "-base64", "-A", "-K", key, "-iv", key]
    return call(enc_cmd, data).strip()


def aes_decrypt(data, key):
    """
    data	- base64 encoded input
    key	- hex encoded password
    """
    dec_cmd = ["openssl", "enc", "-d", "-AES-128-CBC", "-nosalt", "-base64", "-A", "-K", key, "-iv", key, "-nopad"]
    return call(dec_cmd, data).strip()


def jk_eval(f_def):
    """
    f_def	- JavaScript code that defines a function f -> String
    """
    f_call = """
		if(typeof console !== 'undefined') {
			console.log(f());
		} else {
			print(f());
		}
	"""
    js_cmd = ["node"]
    return call(js_cmd, ';'.join((f_def, f_call))).strip()


def main():
    httpd = http.server.HTTPServer(("localhost", 9666), CNLHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
