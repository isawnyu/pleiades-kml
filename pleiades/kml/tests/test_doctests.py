from pleiades.kml.tests.base import PleiadesKMLFunctionalTestCase
from Products.PloneTestCase import PloneTestCase as ptc
from Testing import ZopeTestCase as ztc
import doctest
import unittest

optionflags = doctest.ELLIPSIS | doctest.REPORTING_FLAGS
ptc.setupPloneSite()


def test_suite():
    return unittest.TestSuite([

        ztc.FunctionalDocFileSuite(
            'places.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase,
            optionflags=optionflags
        ),

        ztc.FunctionalDocFileSuite(
            'place.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase,
            optionflags=optionflags
        ),

        ztc.FunctionalDocFileSuite(
            'place-gridsquare.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase,
            optionflags=optionflags
        ),

        ztc.FunctionalDocFileSuite(
            'place-location.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase,
            optionflags=optionflags
        ),

        ztc.FunctionalDocFileSuite(
            'topic.txt', package='pleiades.kml.tests',
            test_class=PleiadesKMLFunctionalTestCase,
            optionflags=optionflags
        ),

    ])
