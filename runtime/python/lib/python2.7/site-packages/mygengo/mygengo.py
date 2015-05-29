#!/usr/bin/python

"""
	Official Python library for interfacing with the myGengo API.
	It's released under a BSD-style license and totally, freely available. Check it out on Github
	if you find any issues!

	Questions, comments? ryan@mygengo.com
"""

__author__ = 'Ryan McGrath <ryan@mygengo.com>'
__version__ = '1.3.3'

import httplib2, mimetypes, mimetools, re, hmac

from pprint import pprint
from hashlib import sha1
from urllib import urlencode, quote
from time import time
from operator import itemgetter

# mockdb is a file with a dictionary of every API endpoint for myGengo.
from mockdb import api_urls, apihash

# There are some special setups (like, oh, a Django application) where
# simplejson exists behind the scenes anyway. Past Python 2.6, this should
# never really cause any problems to begin with.
try:
	# Python 2.6 and up
	import json
except ImportError:
	try:
		# Python 2.6 and below (2.4/2.5, 2.3 is not guranteed to work with this library to begin with)
		import simplejson as json
	except ImportError:
		try:
			# This case gets rarer by the day, but if we need to, we can pull it from Django provided it's there.
			from django.utils import simplejson as json
		except:
			# Seriously wtf is wrong with you if you get this Exception.
			raise Exception("mygengo requires the simplejson library (or Python 2.6+) to work. http://www.undefined.org/python/")

class MyGengoError(Exception):
	"""
		Generic error class, catch-all for most MyGengo issues.
		Special cases are handled by APILimit and AuthError.

		Note: You need to explicitly import them into your code, e.g:

		from mygengo import MyGengoError, MyGengoAuthError
	"""
	def __init__(self, msg, error_code=None):
		self.msg = msg
		if error_code == 1000:
			# Auth errors tend to be the most requested for their own
			# Exception instances, so give it to the masses, yo.
			raise MyGengoAuthError(msg)
	
	def __str__(self):
		return repr(self.msg)

class MyGengoAuthError(MyGengoError):
	"""
		Raised when you try to access a protected resource and it fails due to some issue with
		your authentication.
	"""
	def __init__(self, msg):
		self.msg = msg
	
	def __str__(self):
		return repr(self.msg)

class MyGengo(object):
	def __init__(self, public_key = None, private_key = None, sandbox = False, api_version = '1.1', headers = None, debug = False, hackathon = False):
		"""MyGengo(public_key = None, private_key = None, sandbox = False, headers = None)

			Instantiates an instance of MyGengo.
			
			Parameters:
				public_key - Your 'public' key for myGengo. Retrieve this from your account information if you want to do authenticated calls.
				private_key - Your 'private' key for myGengo. Retrieve this from your account information if you want to do authenticated calls.
				sandbox - Whether to use the myGengo sandbox or not. Check with myGengo for the differences with this as it may change.
				headers - User agent header, dictionary style ala {'User-Agent': 'Bert'}
				debug - a flag (True/False) which will cause things to properly blow the hell up on exceptions. Useful for debugging. ;P
		"""
		self.api_url = api_urls['sandbox'] if sandbox is True else api_urls['base']	
		self.api_version = str(api_version)
		self.public_key = public_key
		self.private_key = private_key
		# If there's headers, set them, otherwise be an embarassing parent for their own good.
		self.headers = headers
		if self.headers is None:
			self.headers = {'User-agent': 'myGengo Python Library v%s' % __version__}
		# No matter whether we get some supplied or use the generic, tell it we want JSON. ;P
		self.headers['Accept'] = 'application/json'
		self.debug = debug
		self.client = httplib2.Http()
	
	def __getattr__(self, api_call):
		"""
			The most magically awesome block of code you'll ever see.

			Rather than list out 9 million methods for this API, we just keep a table (see above) of
			every API endpoint and their corresponding function id for this library. This pretty much gives
			unlimited flexibility in API support - there's a slight chance of a performance hit here, but if this is
			going to be your bottleneck... well, don't use Python. ;P

			For those who don't get what's going on here, Python classes have this great feature known as __getattr__().
			It's called when an attribute that was called on an object doesn't seem to exist - since it doesn't exist,
			we can take over and find the API method in our table. We then return a function that downloads and parses
			what we're looking for, based on the key/values passed in.

			I'll hate myself for saying this, but this is heavily inspired by Ruby's "method_missing".

			Note: I'm largely borrowing this technique from another API library/wrapper I've written in the past (Twython).
			If you happen to read both sources and find the same text... well, that's why. ;)
		"""
		def get(self, **kwargs):
			# Grab the (hopefully) existing method 'definition' to fire off from our api hash table.
			fn = apihash[api_call]
			
			# Do a check here for specific job sets - we need to support posting multiple jobs
			# at once, so see if there's an dictionary of jobs passed in, pop it out, let things go on as normal,
			# then pick this chain back up below...
			post_data = {}
			if 'job' in kwargs: post_data['job'] = {'job': kwargs.pop('job')}
			if 'jobs' in kwargs: post_data['jobs'] = kwargs.pop('jobs')
			if 'comment' in kwargs: post_data['comment'] = kwargs.pop('comment')
			if 'action' in kwargs: post_data['action'] = kwargs.pop('action')
			if 'job_ids' in kwargs: post_data['job_ids'] = kwargs.pop('job_ids')
			
			# This is for the one-off GET call that acts like a POST call... don't ask. ;P
			if 'ids' in kwargs:
				kwargs['ids'] = '/%s' % ','.join(map(lambda i: str(i), ids))
			
			# Set up a true base URL, abstracting away the need to care about the sandbox mode
			# or API versioning at this stage.
			base_url = self.api_url.replace('{{version}}', 'v%s' % self.api_version)
			
			# Go through and replace any mustaches that are in our API url with their appropriate key/value pairs...
			# NOTE: We pop() here because we don't want the extra data included and messing up our hash down the road.
			base = re.sub(
				'\{\{(?P<m>[a-zA-Z]+)\}\}',
				lambda m: "%s" % kwargs.pop(m.group(1), 'no_argument_specified'), # In case of debugging needs
				base_url + fn['url']
			)
			
			# Build up a proper 'authenticated' url...
			#
			# Note: for further information on what's going on here, it's best to familiarize yourself
			# with the myGengo authentication API. (http://mygengo.com/services/api/dev-docs/authentication)
			query_params = dict([k, quote(v.encode('utf-8'))] for k, v in kwargs.items())
			if self.public_key is not None:
				query_params['api_key'] = self.public_key
			query_params['ts'] = str(int(time()))
			
			# If any further APIs require their own special signing needs, fork here...
			if self.api_version == '1':
				resp, content = self.signAndRequestAPIV1(fn, base, query_params, post_data)
			else:
				resp, content = self.signAndRequestAPILatest(fn, base, query_params, post_data)
			results = json.loads(content)
			
			# See if we got any weird or odd errors back that we can cleanly raise on or something...
			if 'opstat' in results and results['opstat'] != 'ok':
				raise MyGengoError(results['err']['msg'], results['err']['code'])
			
			# If not, screw it, return the junks!
			return results
			
		if api_call in apihash:
			return get.__get__(self)
		else:
			raise AttributeError
	
	def signAndRequestAPIV1(self, fn, base, query_params, post_data = {}):
		"""
			Request signatures between API v1 and later versions of the API differ greatly in
			how they're done, so they're kept in separate methods for now.

			fn - object mapping from mockdb describing POST, etc.
			base - Base URL to ping.
			query_params - Dictionary of data eventually getting sent over to myGengo.
			post_data - Any extra special post data to get sent over.
		"""
		# Encoding jobs becomes a bit different than any other method call, so we catch them and do a little
		# JSON-dumping action. Catching them also allows us to provide some sense of portability between the various
		# job-posting methods in that they can all safely rely on passing dictionaries around. Huzzah!
		if fn['method'] == 'POST' or fn['method'] == 'PUT':
			if 'job' in post_data:
				query_params['data'] = json.dumps(post_data['job'], separators = (',', ':'))
			elif 'jobs' in post_data:
				query_params['data'] = json.dumps(post_data['jobs'], separators = (',', ':'))
			elif 'comment' in post_data:
				query_params['data'] = json.dumps(post_data['comment'], separators = (',', ':'))
			elif 'action' in post_data:
				query_params['data'] = json.dumps(post_data['action'], separators = (',', ':'))
			
			query_json = json.dumps(query_params, separators = (',', ':'), sort_keys = True).replace('/', '\\/')
			query_hmac = hmac.new(self.private_key, query_json, sha1)
			query_params['api_sig'] = query_hmac.hexdigest()
			query_data = urlencode(query_params)
			
			# Httplib2 doesn't assume this for POST requests, but in the case of the myGengo API it's a bit of a hidden necessity.
			headers = self.headers
			headers['Content-Type'] = 'application/x-www-form-urlencoded'
			
			if self.debug is True: print query_data
			return self.client.request(base, fn['method'], headers = headers, body = query_data)
		else:
			query_string = urlencode(sorted(query_params.items(), key = itemgetter(0)))
			if self.private_key is not None:
				query_hmac = hmac.new(self.private_key, query_string, sha1)
				query_params['api_sig'] = query_hmac.hexdigest()
				query_string = urlencode(query_params)
			
			if self.debug is True: print query_string
			return self.client.request(base + '?%s' % query_string, fn['method'], headers = self.headers)

	def signAndRequestAPILatest(self, fn, base, query_params, post_data = {}):
		"""
			Request signatures between API v1 and later versions of the API differ greatly in
			how they're done, so they're kept in separate methods for now.

			This method signs the request with just the timestamp and private key, which is what
			api v1.1 relies on.

			fn - object mapping from mockdb describing POST, etc.
			base - Base URL to ping.
			query_params - Dictionary of data eventually getting sent over to myGengo.
			post_data - Any extra special post data to get sent over.
		"""
		# Encoding jobs becomes a bit different than any other method call, so we catch them and do a little
		# JSON-dumping action. Catching them also allows us to provide some sense of portability between the various
		# job-posting methods in that they can all safely rely on passing dictionaries around. Huzzah!
		if fn['method'] == 'POST' or fn['method'] == 'PUT':
			if 'job' in post_data:
				query_params['data'] = json.dumps(post_data['job'], separators = (',', ':'))
			elif 'jobs' in post_data:
				query_params['data'] = json.dumps(post_data['jobs'], separators = (',', ':'))
			elif 'comment' in post_data:
				query_params['data'] = json.dumps(post_data['comment'], separators = (',', ':'))
			elif 'action' in post_data:
				query_params['data'] = json.dumps(post_data['action'], separators = (',', ':'))
			
			query_json = json.dumps(query_params, separators = (',', ':'), sort_keys = True).replace('/', '\\/')
			query_hmac = hmac.new(self.private_key, query_params['ts'], sha1)
			query_params['api_sig'] = query_hmac.hexdigest()
			query_data = urlencode(query_params)
			
			# Httplib2 doesn't assume this for POST requests, but in the case of the myGengo API it's a bit of a hidden necessity.
			headers = self.headers
			headers['Content-Type'] = 'application/x-www-form-urlencoded'
			
			if self.debug is True: print query_data
			return self.client.request(base, fn['method'], headers = headers, body = query_data)
		else:
			query_string = urlencode(sorted(query_params.items(), key = itemgetter(0)))
			if self.private_key is not None:
				query_hmac = hmac.new(self.private_key, query_params['ts'], sha1)
				query_params['api_sig'] = query_hmac.hexdigest()
				query_string = urlencode(query_params)
			
			if self.debug is True: print query_string
			return self.client.request(base + '?%s' % query_string, fn['method'], headers = self.headers)
	
	@staticmethod
	def unicode2utf8(text):
		try:
			if isinstance(text, unicode):
				text = text.encode('utf-8')
		except:
			pass
		return text
