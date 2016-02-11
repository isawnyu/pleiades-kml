from collective.geo.geographer.interfaces import IGeoreferenced
from pleiades.kml.browser import PlaceDocument, PlaceNeighborsDocument
from pleiades.kml.browser import PleiadesPlacemark, PlaceFolder
from pleiades.kml.tests.base import PleiadesKMLTestCase
from zope.interface import implements
from zope.publisher.browser import TestRequest
import zope.dublincore


class AdaptPlaceTestCase(PleiadesKMLTestCase):

    def test_place(self):
        class MockPlace:
            implements(zope.dublincore.interfaces.ICMFDublinCore)
            def Description(self):
                return "A place"
            def Title(self):
                return "Place A"
            def getTimePeriods(self):
                return ['Archaic', 'Classical']
        request = TestRequest()
        p = PleiadesPlacemark(MockPlace(), request)
        self.assertEqual(p.description, "A place")
        self.assertEqual(p.timePeriods, 'Archaic, Classical')


class AdaptPlaceFolderTestCase(PleiadesKMLTestCase):

    def test_place_folder(self):
        class MockPlace:
            implements(zope.dublincore.interfaces.ICMFDublinCore)
            def Description(self):
                return "A place"
            def Title(self):
                return "Place A"
            def getTimePeriods(self):
                return ['Archaic', 'Classical']
            def getLocations(self):
                return [MockPlace()]
            def getFeatures(self):
                return []
        request = TestRequest()
        p = PlaceFolder(MockPlace(), request)
        self.assertEqual(len(list(p.features)), 1)


class PlaceDocumentTestCase(PleiadesKMLTestCase):

    def test_place_document(self):
        class MockPlace:
            implements(zope.dublincore.interfaces.ICMFDublinCore)
            def Description(self):
                return "A place"
            def Title(self):
                return "Place A"
            def getTimePeriods(self):
                return ['Archaic', 'Classical']
            def getLocations(self):
                return range(4)
            def absolute_url(self):
                return "http://example.com/foo/"

        request = TestRequest()
        m = MockPlace()
        p = PlaceDocument(m, request)
        self.assertEqual(len(list(p.features)), 1)
        self.assertEqual(
            p.neighbors_kml, "http://example.com/foo/neighbors-kml")


class PlaceNeighborsDocumentTestCase(PleiadesKMLTestCase):

    def test_place_neighbors_document(self):
        class MockPlace:
            implements(
                zope.dublincore.interfaces.ICMFDublinCore, IGeoreferenced)
            def Title(self):
                return "Foo"
            def Description(self):
                return "A place"
            def getTimePeriods(self):
                return ['Archaic', 'Classical']
            def getLocations(self):
                return range(4)
            def absolute_url(self):
                return "http://example.com/foo/"
            bounds = (0, 0, 0, 0)
            class MockCatalog:
                def __call__(self, **kw):
                    return []
            portal_catalog = MockCatalog()

        request = TestRequest()
        m = MockPlace()
        p = PlaceNeighborsDocument(m, request)
        self.assertEqual(p.name, "All neighbors of Foo")
        self.assertEqual(len(list(p.features)), 0)
