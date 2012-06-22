"""Test the fulltext implementation"""
import transaction
import urllib

from nose.tools import ok_
from pyramid import testing
from unittest import TestCase

from bookie.models import DBSession
from bookie.models.fulltext import WhooshFulltext
from bookie.models.fulltext import get_fulltext_handler
from bookie.tests import empty_db

API_KEY = None


class TestFulltext(TestCase):
    """Test that our fulltext classes function"""

    def setUp(self):
        """Setup Tests"""
        from pyramid.paster import get_app
        from bookie.tests import BOOKIE_TEST_INI
        app = get_app(BOOKIE_TEST_INI, 'main')
        from webtest import TestApp
        self.testapp = TestApp(app)
        testing.setUp()
        global API_KEY
        if API_KEY is None:
            res = DBSession.execute(
                "SELECT api_key FROM users WHERE username = 'admin'").\
                fetchone()
            API_KEY = res['api_key']

    def tearDown(self):
        """Tear down each test"""
        testing.tearDown()
        empty_db()

    def _get_good_request(self, new_tags=None):
        """Return the basics for a good add bookmark request"""
        session = DBSession()
        prms = {
                'url': u'http://google.com',
                'description': u'This is my google desc SEE',
                'extended': u'And some extended notes about it in full form',
                'tags': u'python search',
                'api_key': API_KEY,
        }

        if new_tags:
            prms['tags'] = new_tags

        req_params = urllib.urlencode(prms)
        res = self.testapp.post('/api/v1/admin/bmark',
                                params=req_params)

        session.flush()
        transaction.commit()
        return res

    def test_get_handler(self):
        """Verify we get the right type of full text store object"""
        handler = get_fulltext_handler("")

        ok_(isinstance(handler, WhooshFulltext),
                "Should get a whoosh fulltext by default")

    def test_sqlite_save(self):
        """Verify that if we store a bookmark we get the fulltext storage"""
        # first let's add a bookmark we can search on
        self._get_good_request()

        search_res = self.testapp.get('/api/v1/admin/bmarks/search/google')
        ok_(search_res.status == '200 OK',
                "Status is 200: " + search_res.status)
        ok_('my google desc' in search_res.body,
            "We should find our description on the page: " + search_res.body)

        search_res = self.testapp.get('/api/v1/admin/bmarks/search/python')
        ok_(search_res.status == '200 OK',
                "Status is 200: " + search_res.status)

        ok_('my google desc' in search_res.body,
            "Tag search should find our description on the page: " + \
                search_res.body)

        search_res = self.testapp.get(
            '/api/v1/admin/bmarks/search/extended%20notes')
        ok_(search_res.status == '200 OK',
                "Status is 200: " + search_res.status)
        ok_('extended notes' in search_res.body,
            "Extended search should find our description on the page: " + \
                search_res.body)

    def test_sqlite_update(self):
        """Verify that if we update a bookmark, fulltext is updated

        We need to make sure that updates to the record get cascaded into the
        fulltext table indexes

        """
        self._get_good_request()

        # now we need to do another request with updated tag string
        self._get_good_request(new_tags="google books icons")

        search_res = self.testapp.get('/admin/results?search=icon')
        ok_(search_res.status == '200 OK',
                "Status is 200: " + search_res.status)

        ok_('icon' in search_res.body,
            "We should find the new tag icon on the page: " + search_res.body)

    def test_ajax_search(self):
        """Verify that we can get a json MorJSON response when ajax search"""
        # first let's add a bookmark we can search on
        self._get_good_request()

        search_res = self.testapp.get(
                        '/admin/results/google',
                        headers={
                            'X-Requested-With': 'XMLHttpRequest',
                            'Accept': 'application/json'
                        }
        )

        ok_(search_res.status == '200 OK',
                "Status is 200: " + search_res.status)

        ok_('my google desc' in search_res.body,
            "We should find our description on the page: " + search_res.body)

        # also check for our specific json bits
        ok_('success' in search_res.body,
                "We should see a success bit in the json: " + search_res.body)

        ok_('payload' in search_res.body,
                "We should see a payload bit in the json: " + search_res.body)

        ok_('message' in search_res.body,
                "We should see a message bit in the json: " + search_res.body)
