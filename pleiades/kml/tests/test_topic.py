import unittest

from pleiades.kml.tests.base import PleiadesKMLTestCase
from pleiades.kml.browser import PleiadesBrainPlacemark
from zope.publisher.browser import TestRequest


class AdaptBrainsTestCase(PleiadesKMLTestCase):
    
    def test_brain(self):
        class Mock(object):
            Title = 'Thing'
            Description = 'A thingy'
            zgeo_geometry = {'type': 'Point', 'coordinates': [-1.0, 1.0]}
            getTimePeriods = ['roman', 'late-antique']
            def getURL(self):
                return 'http://example.com/thing'
        request = TestRequest()
        p = PleiadesBrainPlacemark(Mock(), request)
        self.assertEqual(p.name, 'Thing')
        self.assertEqual(p.description, 'A thingy')
        self.assertEqual(p.alternate_link, 'http://example.com/thing')
        self.assertEqual(p.geom.type, 'Point')
        self.assertEqual(bool(p.hasPoint), True)
        self.assertEqual(p.coords_kml, '-1.000000,1.000000,0.0')
        self.assertEqual(p.timePeriods, 'Roman, Late-antique')
        
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(AdaptBrainsTestCase))
    return suite