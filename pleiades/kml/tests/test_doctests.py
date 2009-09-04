import unittest
from zope.testing import doctestunit
from zope.component import testing
from Testing import ZopeTestCase as ztc
from Products.Five import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import PloneSite
import pleiades.kml
from pleiades.kml.tests.base import PleiadesKMLFunctionalTestCase

ptc.setupPloneSite()

class TestCase(ptc.PloneTestCase):
    class layer(PloneSite):
        @classmethod
        def setUp(cls):
            fiveconfigure.debug_mode = True
            zcml.load_config('configure.zcml', pleiades.kml)
            fiveconfigure.debug_mode = False

        @classmethod
        def tearDown(cls):
            pass


def test_suite():
    return unittest.TestSuite([

        # Unit tests
        #doctestunit.DocFileSuite(
        #    'README.txt', package='zgeo.plone.kml',
        #    setUp=testing.setUp, tearDown=testing.tearDown),

        #doctestunit.DocTestSuite(
        #    module='zgeo.plone.kml.mymodule',
        #    setUp=testing.setUp, tearDown=testing.tearDown),


        # Integration tests that use PloneTestCase
        #ztc.ZopeDocFileSuite(
        #    'README.txt', package='zgeo.plone.kml',
        #    test_class=PloneKMLFunctionalTestCase),

        ztc.FunctionalDocFileSuite(
            'places.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase
            ),

        ztc.FunctionalDocFileSuite(
            'place.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase
            ),

        ztc.FunctionalDocFileSuite(
            'place-gridsquare.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase
            ),
            
        ztc.FunctionalDocFileSuite(
            'place-location.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase
            ),

        #ztc.FunctionalDocFileSuite(
        #    'large-folder-kml.txt', package='zgeo.plone.kml.tests',
         #   test_class=PloneKMLFunctionalTestCase
        #    ),

        ])

if __name__ == '__main__':
    unittest.main(defaultTest='test_suite')
