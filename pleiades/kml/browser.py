import logging
from shapely.geometry import asShape

from plone.memoize.instance import memoize
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from zgeo.kml.browser import Document, Folder, Placemark, to_string
from zgeo.kml.interfaces import IFeature, IPlacemark, IContainer
from zgeo.plone.kml.browser import Document, TopicDocument, BrainPlacemark
from zgeo.geographer.interfaces import IGeoreferenced

from zope.component import adapts
from zope.publisher.interfaces import browser
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import Attribute, implements, Interface
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.dublincore.interfaces import ICMFDublinCore
from ZTUtils import make_query

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
    def timePeriods(self):
        return ", ".join(
            x.capitalize() for x in self.context.getTimePeriods()) or "Unattested"

    @property
    def featureTypes(self):
        return ", ".join(
            x.capitalize() for x in self.context.getFeatureType()) or "Unattested"

    @property
    def tags(self):
        return ", ".join(self.context.Subject()) or "None"
            
    @property
    def snippet(self):
        return "%s; %s" % (self.featureTypes, self.timePeriods)

    @property
    def description(self):
        return self.context.Description()

    @property
    def author(self):
        return {'name': self.context.Creator(), 'uri': self.alternate_link}


class PleiadesBrainPlacemark(BrainPlacemark):
    
    @property
    def timePeriods(self):
        tp = getattr(self.context, 'getTimePeriods', [])
        if callable(tp):
            values = tp()
        else:
            values = tp
        try:
            retval = ", ".join(v.capitalize() for v in values) or None
        except TypeError, e:
            log.warn("Time period formatting error: %s", str(e))
            retval = None
        return retval or "Unattested"

    @property
    def featureTypes(self):
        ft = getattr(self.context, 'getFeatureType', [])
        if callable(ft):
            values = ft()
        else:
            values = ft
        try:
            retval = ", ".join(v.capitalize() for v in values) or None
        except TypeError, e:
            log.warn("Feature type formatting error: %s", str(e))
            retval = None
        return retval or "Unattested"

    @property
    def tags(self):
        return ", ".join(self.context.Subject) or "None"

    @property
    def snippet(self):
        return "%s; %s" % (self.featureTypes, self.timePeriods)

    @property
    def description(self):
        return self.context.Description

    @property
    def author(self):
        return {'name': self.context.Creator, 'uri': self.alternate_link}

    @property
    def altLocation(self):
        return self.context.getModernLocation or self.context.Description.listrip('An ancient place, cited: ')

    @property
    def alternate_link(self):
        return self.context.getURL()


class PlaceFolder(Folder):

    @property
    def timePeriods(self):
        return ", ".join(
            x.capitalize() for x in self.context.getTimePeriods()
            ) or "Unattested"

    @property
    def featureTypes(self):
        return ", ".join(
            x.capitalize() for x in self.context.getFeatureType()
            ) or "Unattested"

    @property
    def tags(self):
        return ", ".join(self.context.Subject()) or "None"

    @property
    def snippet(self):
        return "%s; %s" % (self.featureTypes, self.timePeriods)

    @property
    def description(self):
        return self.context.Description()

    @property
    def features(self):
        for item in self.context.getLocations():
            yield PleiadesPlacemark(item, self.request)
        for item in self.context.getFeatures():
            yield PleiadesPlacemark(item, self.request)


class PlaceDocument(Document):
    implements(IContainer)
    template = ViewPageTemplateFile('kml_document.pt')
    disposition_tmpl = "%s.kml"

    @property
    def filename(self):
        return self.disposition_tmpl % self.context.getId()
    
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
    def snippet(self):
        return "%s objects" % len(self.objects)

    @property
    def description(self):
        box = asShape(self.geom).bounds
        return "%s degree by %s degree cell" % (box[2]-box[0], box[3]-box[1])

    @property
    def author(self):
        return {'name': "Pleiades Site Search", 'uri': self.alternate_link}

    @property
    def alternate_link(self):
        portal_url = getToolByName(self.context, 'portal_url')()
        query = {
            'location_precision': ['rough'],
            'path': {'query': [ob.context.getPath() for ob in self.objects],
                     'depth': 0}
            }
        return "%s/search?%s" % (portal_url, make_query(query))

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
        request = self.request.form.copy()
        request['location_precision'] = ['precise']
        for brain in self.context.queryCatalog(request):
            yield PleiadesBrainPlacemark(brain, self.request)
        geoms = {}
        objects = {}
        request['location_precision'] = ['rough']
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


class IKMLNeighborhood(Interface):
    def p_link():
        """Query string to search for precisely located neighbors"""
    def r_link():
        """Query string to search for aggregations of roughly located neighbors"""

class KMLNeighborhood(BrowserView):
    implements(IKMLNeighborhood)

    @memoize
    def geo(self):
        log.info("Getting georeferencing")
        try:
            g = IGeoreferenced(self.context)
        except NotLocatedError:
            return None
        return g

    def __call__(self):
        return "Nothing to see here"

    def _munge(self, where):
        u = {}
        try:
            u['predicate'] = where.get('range')
            if u['predicate'] == 'intersection':
                coords = where.get('query')
            else:
                coords = where.get('query')[0]
                u['tolerance'] = where.get('query')[1]/1000.0
            u['lowerLeft'] = "%f,%f" % coords[0:2]
            if len(coords) == 4:
                u['upperRight'] = "%f,%f" % coords[2:4]
        except:
            log.warning("Failed to munge %s" % where)
        return u

    def p_link(self):
        log.info("Getting p_qs query string")
        g = self.geo()
        if g is None:
            return None
        view = PlacePreciseNeighborsDocument(self.context, self.request)
        query = view.criteria(g)
        where = query.pop('where')
        query.update(self._munge(where))
        return """
        <link rel="nofollow alternate p-neighbors"
            type="application/vnd.google-earth.kml+xml"
            href="%s/search_kml?%s"/>
        """ % (getToolByName(self.context, 'portal_url')(), make_query(query))

    def r_link(self):
        log.info("Getting r_qs query string")
        g = self.geo()
        if g is None:
            return None
        view = PlaceRoughNeighborsDocument(self.context, self.request)
        query = view.criteria(g)
        where = query.pop('where')
        query.update(self._munge(where))
        return """
        <link rel="nofollow alternate r-neighbors"
            type="application/vnd.google-earth.kml+xml"
            href="%s/search_kml?%s"/>
        """ % (getToolByName(self.context, 'portal_url')(), make_query(query))

