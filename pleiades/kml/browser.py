import logging
from shapely.geometry import asShape

from plone.memoize.view import memoize
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from zgeo.kml.browser import Document, Folder, Placemark, to_string
from zgeo.kml.interfaces import IFeature, IPlacemark, IContainer
from zgeo.plone.kml.browser import Document, TopicDocument, BrainPlacemark
from zgeo.geographer.interfaces import IGeoreferenced

from zope.component import adapts
from zope.publisher.interfaces import browser
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import implements, Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.dublincore.interfaces import ICMFDublinCore

from Products.PleiadesEntity.content.interfaces import ILocation
from pleiades.capgrids import Grid
from pleiades.geographer.geo import NotLocatedError
from pleiades.capgrids import Grid

log = logging.getLogger('pleiades.kml')

def coords_to_kml(geom):
    gtype = geom['type']
    if gtype == 'Point':
        return to_string((geom['coordinates'],))
    elif gtype == 'Polygon':
        if len(geom['coordinates']) == 1:
            return (to_string(geom['coordinates'][0]), None)
        elif len(geom['coordinates']) > 1:
            return (
                to_string(geom['coordinates'][0]), to_string(geom['coordinates'][1]))
    else:
        return to_string(geom['coordinates'])

class W(object):
    # spatial 'within' wrapper for use as a sorting key
    def __init__(self, o):
        self.o = o
    def __lt__(self, other):
        return asShape(self.o.geom).within(asShape(other.o.geom))

class GridPlacemark(Placemark):
    
    @property
    def id(self):
        return self.context.id
    
    @property
    def alternate_link(self):
        return self.context.id


class PleiadesPlacemark(Placemark):

    @property
    def description(self):
        return self.context.Description()

    @property
    def timePeriods(self):
        return ', '.join(
            [x.capitalize() for x in self.context.getTimePeriods()]) or 'None'


class PleiadesBrainPlacemark(BrainPlacemark):
    
    @property
    def timePeriods(self):
        tp = getattr(self.context, 'getTimePeriods')
        if tp is None:
            retval = ''
        else:
            if callable(tp):
                values = tp()
            else:
                values = tp
            try:
                retval = ', '.join([v.capitalize() for v in values])
            except TypeError:
                retval = ''
        return retval

    @property
    def featureTypes(self):
        ft = getattr(self.context, 'getFeatureType')
        if ft is None:
            retval = ''
        else:
            if callable(ft):
                values = ft()
            else:
                values = ft
            try:
                retval = ', '.join([v.capitalize() for v in values])
            except TypeError:
                retval = ''
        return retval

    @property
    def altLocation(self):
        return self.context.getModernLocation or self.context.Description.listrip('An ancient place, cited: ')

    @property
    def alternate_link(self):
        return self.context.getURL()


class PlaceFolder(Folder):
    
    @property
    def description(self):
        return self.context.Description()

    @property
    def timePeriods(self):
        return ', '.join(
            [x.capitalize() for x in self.context.getTimePeriods()]) or 'None'

    @property
    def features(self):
        for item in self.context.getLocations():
            yield PleiadesPlacemark(item, self.request)
        for item in self.context.getFeatures():
            yield PleiadesPlacemark(item, self.request)


class PlaceDocument(Document):
    implements(IContainer)
    template = ViewPageTemplateFile('kml_document.pt')
    
    @property
    def features(self):
        return iter([PlaceFolder(self.context, self.request)])

    @property
    def neighbors_kml(self):
        return "%s/neighbors-kml" % self.context.absolute_url().rstrip('/')


class PlaceNeighborhoodDocument(PlaceDocument):
    implements(IContainer)
    template = ViewPageTemplateFile('kml_neighborhood_document.pt')

    @property
    def kml(self):
        return "%s/kml" % self.context.absolute_url().rstrip('/')

    @property
    def r_neighbors_kml(self):
        return "%s/r-neighbors-kml" % self.context.absolute_url().rstrip('/')

    @property
    def p_neighbors_kml(self):
        return "%s/p-neighbors-kml" % self.context.absolute_url().rstrip('/')


class PlaceNeighborsDocument(TopicDocument):
    template = ViewPageTemplateFile('kml_neighbors_document.pt')
    disposition_tmpl = "%s-neighbors.kml"

    @property
    def name(self):
        return "All neighbors of %s" % self.dc.Title()

    @property
    def filename(self):
        return self.disposition_tmpl % self.context.getId()

    def criteria(self, g):
        return dict(
            where={'query': (g.bounds, 10), 'range': 'nearest' }, 
            portal_type={'query': ['Place']}
            )

    @property
    def features(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        try:
            g = IGeoreferenced(self.context)
        except NotLocatedError:
            raise StopIteration
        for brain in catalog(**self.criteria(g)):
            if brain.getId == self.context.getId():
                # skip self
                continue
            yield PleiadesBrainPlacemark(brain, self.request)

class PlacePreciseNeighborsDocument(PlaceNeighborsDocument):
    disposition_tmpl = "%s-p-neighbors.kml"

    @property
    def name(self):
        return "Precisely located neighbors of %s" % self.dc.Title()

    def criteria(self, g):
        return dict(
           where={'query': (g.bounds, 20000.0), 'range': 'distance' }, 
            portal_type={'query': ['Place']},
            location_precision={'query': ['precise']}
            )


class AggregationPlacemark:
    """A placemark for a location that is related to roughly located objects"""
    
    def __init__(self, context, geom, objects):
        # Objects here are catalog brains - metadata
        self.context = context
        self.geom = geom
        self.objects = objects

    @property
    def id(self):
        return repr(self.geom)

    @property
    def name(self):
        return "Aggregation of roughly located objects"

    @property
    def description(self):
        box = asShape(self.geom).bounds
        return "%s degree by %s degree cell" % (box[2]-box[0], box[3]-box[1])

    @property
    def alternate_link(self):
        portal_url = getToolByName(self.context, 'portal_url')()
        query = '&'.join(
            "getId:list=%s" % ob.context.getId for ob in self.objects)
        return "%s/search?location_precision=rough&%s" % (portal_url, query)

    @property
    def hasPoint(self):
        return int(self.geom['type'] == 'Point')

    @property
    def hasLineString(self):
        return int(self.geom['type'] == 'LineString')

    @property
    def hasPolygon(self):
        return int(self.geom['type'] == 'Polygon')

    @property
    def coords_kml(self):
        return coords_to_kml(self.geom)


class PlaceRoughNeighborsDocument(PlaceNeighborsDocument):
    template = ViewPageTemplateFile('kml_rough_neighbors_document.pt')
    disposition_tmpl = "%s-r-neighbors.kml"

    @property
    def name(self):
        return "Roughly located neighbors of %s" % self.dc.Title()

    def criteria(self, g):
        return dict(
            where={'query': g.bounds, 'range': 'intersection' }, 
            portal_type={'query': ['Place']},
            location_precision={'query': ['rough']}
            )

    @property
    def features(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        try:
            g = IGeoreferenced(self.context)
        except NotLocatedError:
            raise StopIteration
        log.debug("Criteria: %s", self.criteria(g))
        geoms = {}
        objects = {}
        for brain in catalog(**self.criteria(g)):
            if brain.getId == self.context.getId():
                # skip self
                continue
            item = PleiadesBrainPlacemark(brain, self.request)
            geo = brain.zgeo_geometry
            if geo and geo.has_key('type') and geo.has_key('coordinates'):
                # key = (geo['type'], geo['coordinates'])
                key = repr(geo)
                if not key in geoms:
                    geoms[key] = geo
                if key in objects:
                    objects[key].append(item)
                else:
                    objects[key] = [item]
        placemarks = sorted(
            [AggregationPlacemark(
                self.context, geoms[key], val) for key, val in objects.items()],
                key=W,
                reverse=False)
        for placemark in placemarks:
            yield placemark


class PleiadesDocument(Document):
    template = ViewPageTemplateFile('kml_document.pt')


class PleiadesTopicDocument(TopicDocument):
    template = ViewPageTemplateFile('kml_topic_document.pt')
    filename = "collection.kml"

    @property
    def features(self):
        # Pass extra location precision param through the request
        request = getattr(self, 'REQUEST', {})
        request['location_precision'] = 'precise'
        for brain in self.context.queryCatalog(request):
            yield PleiadesBrainPlacemark(brain, self.request)
        geoms = {}
        objects = {}
        request['location_precision'] = 'rough'
        for brain in self.context.queryCatalog(request):
            item = PleiadesBrainPlacemark(brain, self.request)
            geo = brain.zgeo_geometry
            if geo and geo.has_key('type') and geo.has_key('coordinates'):
                key = repr(geo)
                if not key in geoms:
                    geoms[key] = geo
                if key in objects:
                    objects[key].append(item)
                else:
                    objects[key] = [item]
        placemarks = sorted(
            [AggregationPlacemark(
                self.context, geoms[key], val) for key, val in objects.items()],
                key=W,
                reverse=False)
        for placemark in placemarks:
            yield placemark


class SearchDCProvider:
    def Title(self):
        return "Search"
    def Description(self):
        return "Advanced search for content"
    def Creator(self):
        return ""


class PleiadesSearchDocument(PleiadesTopicDocument):
    template = ViewPageTemplateFile('kml_topic_document.pt')
    filename = "search.kml"

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.dc = SearchDCProvider()


class PleiadesStylesProvider(object):
    implements(IContentProvider)
    adapts(Interface, IDefaultBrowserLayer, PlaceDocument)
    
    template = ViewPageTemplateFile('kml_styles.pt')
    
    def __init__(self, context, request, view):
        self.context, self.request, self.view = context, request, view
    
    def update(self):
        pass
    
    def render(self):
        return self.template().encode('utf-8')
