#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
	A set of tests for myGengo. They all require internet connections.
	In fact, this entire library and API requires an internet connection.
	Don't complain.

	Also keep in mind that all the test cases test against the Sandbox API,
	since... well, it makes more sense to do that. If you, for some odd reason,
	want/need to test against the regular API, modify the SANDBOX flag at the top
	of this file.

	-- Ryan McGrath (ryan @ venodesigns dat net)
"""

import unittest
import random

from pprint import pprint
from mygengo import MyGengo, MyGengoError, MyGengoAuthError

# test_keys is a file I use to store my keys separately. It's stuck in the
# .gitignore as well, so feel free to use it for your own purposes, but there's
# no warranty with this. Keys are needed to run the tests below, though, so if want to
# run the tests, copy over the example keys file and throw your information in.
#
# e.g, cp test_keys_example.py test_keys.py
from test_keys import public_key, private_key

# We test in the myGengo sandbox for all these tests. Flip this if you need/want to.
SANDBOX = True

class TestMyGengoCore(unittest.TestCase):
	"""
		Handles testing the core parts of myGengo (i.e, authentication signing, etc).
	"""
	def test_MethodDoesNotExist(self):
		myGengo = MyGengo(public_key = public_key, private_key = private_key, sandbox = SANDBOX)
		# With how we do functions, AttributeError is a bit tricky to catch...
		self.assertRaises(AttributeError, getattr, myGengo, 'bert')
	
	def test_MyGengoAuthNoCredentials(self):
		myGengo = MyGengo(public_key = '', private_key = '', sandbox = SANDBOX)
		self.assertRaises(MyGengoError, myGengo.getAccountStats)
	
	def test_MyGengoAuthBadCredentials(self):
		myGengo = MyGengo(public_key = 'bert', private_key = 'beeeerrrttttt', sandbox = SANDBOX)
		self.assertRaises(MyGengoAuthError, myGengo.getAccountStats)


class TestAccountMethods(unittest.TestCase):
	"""
		Tests the methods that deal with retrieving basic information about
		the account you're authenticating as. Checks for one property on each
		method; if your keys work with these methods, well...
	"""
	def test_getAccountStats(self):
		myGengo = MyGengo(public_key = public_key, private_key = private_key, sandbox = SANDBOX)
		stats = myGengo.getAccountStats()
		self.assertEqual(stats['opstat'], 'ok')
	
	def test_getAccountBalance(self):
		myGengo = MyGengo(public_key = public_key, private_key = private_key, sandbox = SANDBOX)
		balance = myGengo.getAccountBalance()
		self.assertEqual(balance['opstat'], 'ok')


class TestLanguageServiceMethods(unittest.TestCase):
	"""
		Tests the methods that deal with getting information about language-translation
		service support from myGengo.
	"""
	def test_getServiceLanguagePairs(self):
		myGengo = MyGengo(public_key = public_key, private_key = private_key, sandbox = SANDBOX)
		resp = myGengo.getServiceLanguagePairs()
		self.assertEqual(resp['opstat'], 'ok')
	
	def test_getServiceLanguages(self):
		myGengo = MyGengo(public_key = public_key, private_key = private_key, sandbox = SANDBOX)
		resp = myGengo.getServiceLanguages()
		self.assertEqual(resp['opstat'], 'ok')


class TestTranslationJobFlow(unittest.TestCase):
	"""
		Tests the flow of creating a job, updating it, getting the details, and then 
		deleting the job. This is the thick of it!
		
		Flow is as follows:
		
			1: Create a mock job and get an estimate for it (setUp)
			2: Create three jobs - 1 single, 2 batched
			3: Update the first job with some arbitrary information or something
			4: Post a comment on the first job
			6: Perform a hell of a lot of GETs to the myGengo API to check stuff
			7: Delete the job if all went well (teardown phase)
	"""
	def setUp(self):
		"""
			Creates the initial batch of jobs for the other test functions here to operate on.
		"""
		# First we'll create three jobs - one regular, and two at the same time...
		self.myGengo = MyGengo(public_key = public_key, private_key = private_key, sandbox = SANDBOX)		
		self.created_job_ids = []
		
		single_job = {
			'type': 'text',
			'slug': 'Single :: English to Japanese',
			'body_src': 'Test%ding myGe%dngo A%dPI li%dbrary calls.' % (int(random.randrange(1,226,1)), int(random.randrange(1,226,1)), int(random.randrange(1,226,1)), int(random.randrange(1,226,1))),
			'lc_src': 'en',
			'lc_tgt': 'ja',
			'tier': 'standard',
			'auto_approve': 0,
		}
		
		multiple_jobs = {
			'job_1': {
				'type': 'text',
				'slug': 'Multiple :: English to Japanese',
				'body_src': 'H%dow i%ds th%de weather?' % (int(random.randrange(1,226,1)), int(random.randrange(1,226,1)), int(random.randrange(1,226,1))),
				'lc_src': 'en',
				'lc_tgt': 'ja',
				'tier': 'standard',
			},
			'job_2': {
				'type': 'text',
				'slug': 'Multiple :: Japanese To English',
				'body_src': '天%d気%dはど%dうですか' % (int(random.randrange(1,226,1)), int(random.randrange(1,226,1)), int(random.randrange(1,226,1))),
				'lc_src': 'ja',
				'lc_tgt': 'en',
				'tier': 'ultra',
			},
		}
		
		# Now that we've got the job, let's go ahead and see how much it'll cost.
		cost_assessment = self.myGengo.determineTranslationCost(jobs = {'jobs': multiple_jobs})
		self.assertEqual(cost_assessment['opstat'], 'ok')
		
		# If that method worked, sweet. Move on and create three jobs, store their IDs. Make sure we got an ID
		# back, since these methods are otherwise largely useless without that returned data. These tests walk a fine
		# line between testing myGengo and the myGengo API functionality as a whole - watch yourself if you add to this. :)
		job = self.myGengo.postTranslationJob(job = single_job)
		self.assertEqual(job['opstat'], 'ok')
		self.assertIsNotNone(job['response']['job']['job_id'])
		self.created_job_ids.append(job['response']['job']['job_id'])
		
		jobs = self.myGengo.postTranslationJobs(jobs = {'jobs': multiple_jobs})
		self.assertEqual(job['opstat'], 'ok')
		
		# This is a fairly ugly way to check for and retrieve job IDs; in an ideal system you know the keys, and... well,
		# truthfully we do here too. I suppose this is moreso here as an example of how to get IDs in a situation where you
		# don't know the keys. May or may not be useful to some.
		for job_obj in jobs['response']['jobs']:
			for job in job_obj:
				self.assertIsNotNone(job_obj[job]['job_id'])
				self.created_job_ids.append(job_obj[job]['job_id'])
	
	@unittest.skip("We don't test myGengo.getTranslationJobPreviewImage() because it's potentially resource heavy on the myGengo API.")
	def test_getTranslationJobPreviewImage(self):
		"""
			This test could be a bit more granular, but I'm undecided at the moment - testing the response stream
			of this method is more of a Unit Test for myGengo than myGengo. Someone can extend if they see fit, but I 
			currently see no reason to mess with this further.
		"""
		img = self.myGengo.getTranslationJobPreviewImage(id = self.created_job_ids[0])
		self.assertIsNotNone(img)
	
	def test_postJobDataMethods(self):
		"""
			Tests all the myGengo methods that deal with updating jobs, posting comments, etc. test_getJobDataMethods() checks things,
			but they need to exist first - think of this as the alcoholic mother to _getJobDataMethods().
		"""
		# The 'update' method can't really be tested, as it requires the translator having actually done something before
		# it's of any use. Thing is, in automated testing, we don't really have a method to flip the switch on the myGengo end. If we
		# WERE to test this method, it'd look a little something like this:
		#	
		#	updated_job = self.myGengo.updateTranslationJob(id = self.created_job_ids[0], action = {
		#		'action': 'purchase',
		#	})
		#	self.assertEqual(updated_job['opstat'], 'ok')
		
		posted_comment = self.myGengo.postTranslationJobComment(id = self.created_job_ids[0], comment = {
			'body': 'I love lamp oh mai gawd',
		})
		self.assertEqual(posted_comment['opstat'], 'ok')
	
	def test_getJobDataMethods(self):
		"""
			Test a ton of methods that GET data from the myGengo API, based on the jobs we've created and such.
			
			These are separate from the other GET request methods because this might be a huge nuisance to their API,
			and I figure it's worth separating out the pain-point test cases so they could be disabled easily in a 
			distribution or something.
		"""
		# Pull down data about one specific job...
		job = self.myGengo.getTranslationJob(id = self.created_job_ids[0])
		self.assertEqual(job['opstat'], 'ok')
		
		# Pull down the 10 most recently submitted jobs.
		jobs = self.myGengo.getTranslationJobs()
		self.assertEqual(jobs['opstat'], 'ok')
		
		# Test getting the batch that a job is in...
		job_batch = self.myGengo.getTranslationJobBatch(id = self.created_job_ids[1])
		self.assertEqual(job_batch['opstat'], 'ok')
		
		# Pull down the comment(s) we created earlier in this test suite.
		job_comments = self.myGengo.getTranslationJobComments(id = self.created_job_ids[0])
		self.assertEqual(job_comments['opstat'], 'ok')
		
		# Pull down feedback. This should work fine, but there'll be no feedback or anything, so... meh.
		feedback = self.myGengo.getTranslationJobFeedback(id = self.created_job_ids[0])
		self.assertEqual(feedback['opstat'], 'ok')
		
		# Lastly, pull down any revisions that definitely didn't occur due to this being a simulated test.
		revisions = self.myGengo.getTranslationJobRevisions(id = self.created_job_ids[0])
		self.assertEqual(revisions['opstat'], 'ok')
		
		# So it's worth noting here that we can't really test getTranslationJobRevision(), because no real revisions
		# exist at this point, and a revision ID is required to pull that method off successfully. Bai now.
	
	def tearDown(self):
		"""
			Delete every job we've created for this somewhat ridiculously thorough testing scenario.
		"""
		for id in self.created_job_ids:
			deleted_job = self.myGengo.deleteTranslationJob(id = id)
			self.assertEqual(deleted_job['opstat'], 'ok')


if __name__ == '__main__':
	unittest.main()
