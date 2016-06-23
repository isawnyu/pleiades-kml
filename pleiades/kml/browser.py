from pleiades.geographer.geo import NotLocatedError
from plone.memoize.instance import memoize
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PleiadesEntity.time import periodRanges, to_ad
from shapely.geometry import asShape, mapping
from collective.geo.geographer.interfaces import IGeoreferenced
from zope.component import getMultiAdapter
from zope.dublincore.interfaces import ICMFDublinCore
from zope.formlib.namedtemplate import NamedTemplate
from zope.formlib.namedtemplate import NamedTemplateImplementation
from zope.interface import implements, Interface
from zope.publisher.browser import BrowserPage
from zope.publisher.browser import BrowserView
from zope.traversing.browser.interfaces import IAbsoluteURL
from ZTUtils import make_query
from .interfaces import IContainer
from .interfaces import IFeature
from .interfaces import IPlacemark
import logging

log = logging.getLogger('pleiades.kml')


def to_string(coords):
    if len(coords[0]) == 2:
        tuples = ('%f,%f,0.0' % tuple(c) for c in coords)
    elif len(coords[0]) == 3:
        tuples = ('%f,%f,%f' % tuple(c) for c in coords)
    else:
        raise ValueError("Invalid dimensions")
    return ' '.join(tuples)


def coords_to_kml(geom):
    gtype = geom.type
    if gtype == 'Point':
        return to_string((geom.coordinates,))
    elif gtype == 'Polygon':
        if len(geom.coordinates) == 1:
            return (to_string(geom.coordinates[0]), None)
        elif len(geom.coordinates) > 1:
            return (
                to_string(geom.coordinates[0]), to_string(geom.coordinates[1]))
    else:
        return to_string(geom.coordinates)


def absoluteURL(ob, request):
    return getMultiAdapter((ob, request), IAbsoluteURL)()


class NullGeometry(object):
    type = None
    coordinates = None


class Geometry(object):
    implements(IGeoreferenced)

    def __init__(self, type, coordinates):
        self.type = type
        self.coordinates = coordinates


class Feature(BrowserPage):

    """Not to be instantiated.
    """
    implements(IFeature)

    @property
    def id(self):
        return '%s/@@%s' % (
            absoluteURL(self.context, self.request), self.__name__)

    @property
    def name(self):
        return self.dc.Title()

    @property
    def description(self):
        return self.dc.Description()

    @property
    def author(self):
        return {
            'name': self.dc.Creator(),
            'uri': '',
            'email': ''
            }

    @property
    def alternate_link(self):
        return absoluteURL(self.context, self.request)


class Placemark(Feature):
    implements(IPlacemark)
    __name__ = 'kml-placemark'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.dc = ICMFDublinCore(self.context)
        try:
            self.geom = IGeoreferenced(self.context)
        except:
            self.geom = NullGeometry()

    @property
    def hasPoint(self):
        return int(self.geom.type == 'Point')

    @property
    def hasLineString(self):
        return int(self.geom.type == 'LineString')

    @property
    def hasPolygon(self):
        return int(self.geom.type == 'Polygon')

    @property
    def coords_kml(self):
        return coords_to_kml(self.geom)

    @property
    def reprpt_kml(self):
        g = mapping(self.geom)
        g = g.get('geometry', g)
        g = asShape(g).representative_point()
        return to_string(list(g.coords))

    def __call__(self):
        return self.template().encode('utf-8')


class Folder(Feature):
    implements(IContainer)
    __name__ = 'kml-folder'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.dc = ICMFDublinCore(self.context)

    @property
    def features(self):
        for item in self.context.values():
            yield Placemark(item, self.request)


class Document(Feature):
    implements(IContainer)
    __name__ = 'kml-document'
    template = NamedTemplate('template-kml-document')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.dc = ICMFDublinCore(self.context)

    @property
    def features(self):
        for item in self.context.values():
            yield getMultiAdapter((item, self.request), IFeature)

    def __call__(self):
        return self.template().encode('utf-8')


class BrainPlacemark(Placemark):
    implements(IPlacemark)
    __name__ = 'kml-placemark'

    def __init__(self, context, request):
        self.context = context
        self.request = request
        try:
            g = self.context.zgeo_geometry
            self.geom = Geometry(g['type'], g['coordinates'])
        except:
            self.geom = NullGeometry()

    @property
    def id(self):
        return 'urn:uuid:%s' % self.context.UID

    @property
    def name(self):
        return self.context.Title

    @property
    def description(self):
        return self.context.Description

    @property
    def author(self):
        return {
            'name': self.context.Creator,
            'uri': '',
            'email': ''
            }

    @property
    def alternate_link(self):
        return '/'.join(
            [self.request['BASE1']]
            + self.request.physicalPathToVirtualPath(self.context.getPath())
            )

    @property
    def reprpt_kml(self):
        g = {'type': self.geom.type, 'coordinates': self.geom.coordinates}
        g = asShape(g).representative_point()
        return to_string(list(g.coords))


class TopicDocument(Document):

    @property
    def features(self):
        for brain in self.context.queryCatalog():
            yield BrainPlacemark(brain, self.request)


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
    def kid(self):
        path = self.context.getPhysicalPath()[2:]
        return "/".join(path)

    @property
    def timePeriods(self):
        return ", ".join(
            x.capitalize()
            for x in self.context.getTimePeriods()) or "Unattested"

    @property
    def featureTypes(self):
        return ", ".join(x.capitalize() for x in (
            self.context.getFeatureType() or ["unknown"]))

    @property
    def appellations(self):
        return ", ".join(
            unicode(o.getNameAttested() or o.Title(), 'utf-8')
            for o in self.context.getNames()
            ) or "Unnamed"

    @property
    def tags(self):
        return ", ".join(self.context.Subject()) or "None"

    @property
    def snippet(self):
        sdata = [self.featureTypes]
        timespan = self.timeSpanAD
        if timespan:
            sdata += ["%(start)s - %(end)s" % timespan]
        return "; ".join(sdata)

    @property
    def description(self):
        return self.context.Description()

    @property
    def author(self):
        return {'name': self.context.Creator(), 'uri': self.alternate_link}

    @property
    def timeSpan(self):
        try:
            trange = self.context.temporalRange()
            if trange:
                return {'start': int(trange[0]), 'end': int(trange[1])}
            else:
                return None
        except AttributeError:
            return None

    @property
    def timeSpanAD(self):
        span = self.timeSpan
        if span:
            return dict([(k, to_ad(v)) for k, v in span.items()])
        else:
            return None


class PleiadesBrainPlacemark(BrainPlacemark):

    @property
    def kid(self):
        return self.context.getPath().replace("/plone/", "")

    @property
    def timePeriods(self):
        tp = getattr(self.context, 'getTimePeriods', [])
        if callable(tp):
            values = tp()
        else:
            values = tp
        try:
            retval = ", ".join(v.capitalize() for v in values) or None
        except TypeError as e:
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
        except TypeError as e:
            log.warn("Feature type formatting error: %s", str(e))
            retval = None
        return retval or "Unknown"

    @property
    def appellations(self):
        catalog = self.context.aq_parent
        brains = catalog(
            portal_type='Name',
            path={'query': self.context.getPath(), 'depth': 1})
        return ", ".join(
            unicode(b.getNameAttested or b.Title, 'utf-8')
            for b in brains
        )

    @property
    def tags(self):
        return ", ".join(self.context.Subject) or "None"

    @property
    def snippet(self):
        sdata = [self.featureTypes]
        timespan = self.timeSpanAD
        if timespan:
            sdata += ["%(start)s - %(end)s" % timespan]
        return "; ".join(sdata)

    @property
    def description(self):
        return self.context.Description

    @property
    def author(self):
        return {'name': self.context.Creator, 'uri': self.alternate_link}

    @property
    def altLocation(self):
        return (
            self.context.getModernLocation or
            self.context.Description.lstrip('An ancient place, cited: ')
        )

    @property
    def alternate_link(self):
        return self.context.getURL()

    @memoize
    def periodRanges(self):
        vocab = getToolByName(
            self.context.getObject(), 'portal_vocabularies'
            ).getVocabularyByName('time-periods').getTarget()
        return periodRanges(vocab)

    @property
    def timeSpan(self):
        catalog = self.context.aq_parent
        vocab = getToolByName(
            catalog, 'portal_vocabularies'
            ).getVocabularyByName('time-periods').getTarget()
        ranges = periodRanges(vocab)
        years = []
        tp = getattr(self.context, 'getTimePeriods', [])
        if callable(tp):
            values = tp()
        else:
            values = tp
        for val in values:
            if val:
                years.extend(list(ranges[val]))
        if len(years) >= 2:
            return {'start': int(min(years)), 'end': int(max(years))}
        else:
            return None

    @property
    def timeSpanAD(self):
        span = self.timeSpan
        if span:
            return dict([(k, to_ad(v)) for k, v in span.items()])
        else:
            return None


class PlaceFolder(Folder):

    @property
    def kid(self):
        # Note: presumes we don't want site object in the path
        path = self.context.getPhysicalPath()[2:]
        return "/".join(path)

    @property
    def timePeriods(self):
        return ", ".join(
            x.capitalize() for x in self.context.getTimePeriods()
            ) or "Unattested"

    @property
    def featureTypes(self):
        return ", ".join(x.capitalize() for x in (
            self.context.getFeatureType() or ["unknown"]))

    @property
    def appellations(self):
        return ", ".join(
            unicode(o.getNameAttested() or o.Title(), 'utf-8')
            for o in self.context.getNames()
            ) or "Unnamed"

    @property
    def tags(self):
        return ", ".join(self.context.Subject()) or "None"

    @property
    def snippet(self):
        sdata = [self.featureTypes]
        timespan = self.timeSpanAD
        if timespan:
            sdata += ["%(start)s - %(end)s" % timespan]
        return "; ".join(sdata)

    @property
    def description(self):
        return self.context.Description()

    @property
    def features(self):
        for item in self.context.getLocations():
            yield PleiadesPlacemark(item, self.request)
        for item in self.context.getFeatures():
            yield PleiadesPlacemark(item, self.request)

    @property
    def timeSpan(self):
        try:
            trange = self.context.temporalRange()
            if trange:
                return {'start': int(trange[0]), 'end': int(trange[1])}
            else:
                return None
        except AttributeError:
            return None

    @property
    def timeSpanAD(self):
        span = self.timeSpan
        if span:
            return dict([(k, to_ad(v)) for k, v in span.items()])
        else:
            return None


class PlaceDocument(Document):
    implements(IContainer)
    template = ViewPageTemplateFile('kml_document.pt')
    disposition_tmpl = "%s.kml"

    @property
    def name(self):
        return "Locations of %s" % self.dc.Title()

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
    def name(self):
        return "Neighborhood of %s" % self.dc.Title()

    @property
    def kml(self):
        return "%s/kml" % self.context.absolute_url().rstrip('/')

    @property
    def r_neighbors_kml(self):
        return "%s/r-neighbors-kml" % self.context.absolute_url().rstrip('/')

    @property
    def p_neighbors_kml(self):
        return "%s/p-neighbors-kml" % self.context.absolute_url().rstrip('/')

    @property
    def connections_kml(self):
        return "%s/connections-kml" % self.context.absolute_url().rstrip('/')


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
            where={
                'query': (g.bounds, 10),
                'range': 'nearest'
            },
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
            where={'query': (g.bounds, 15), 'range': 'nearest'},
            portal_type={'query': ['Place']},
            location_precision={'query': ['precise']},
        )


class AggregationPlacemark:
    """A placemark for a location that is related to roughly located objects"""

    def __init__(self, context, geom, objects):
        # Objects here are catalog brains - metadata
        self.context = context
        self.geom = geom
        self.objects = objects

    @property
    def kid(self):
        return repr(self.geom)

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
        return coords_to_kml(Geometry(self.geom['type'], self.geom['coordinates']))

    @property
    def reprpt_kml(self):
        return to_string(list(asShape(self.geom).representative_point().coords))


class PlaceRoughNeighborsDocument(PlaceNeighborsDocument):
    disposition_tmpl = "%s-r-neighbors.kml"

    @property
    def name(self):
        return "Roughly located neighbors of %s" % self.dc.Title()

    def criteria(self, g):
        return dict(
            where={'query': g.bounds, 'range': 'intersection'},
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
            if geo and 'type' in geo and 'coordinates' in geo:
                # key = (geo['type'], geo['coordinates'])
                key = repr(geo)
                if key not in geoms:
                    geoms[key] = geo
                if key in objects:
                    objects[key].append(item)
                else:
                    objects[key] = [item]
        placemarks = sorted(
            [AggregationPlacemark(
                self.context, geoms[k], v) for k, v in objects.items()],
            key=W,
            reverse=False
        )
        for placemark in placemarks:
            yield placemark


class PleiadesDocument(Document):
    template = ViewPageTemplateFile('kml_document.pt')


class PleiadesTopicDocument(TopicDocument):
    template = ViewPageTemplateFile('kml_topic_document.pt')
    filename = "collection.kml"

    @property
    def name(self):
        return "Places collected in %s" % self.dc.Title()

    @property
    def features(self, skip=None):
        skipIds = skip or self.request.form.get('skipId') or []
        precision_param = self.request.form.get('location_precision')
        if not precision_param:
            get_precise = True
            get_rough = True
        else:
            qv = self.request.form.get('query', precision_param)
            get_precise = 'precise' in qv or (
                hasattr(qv, 'get') and 'precise' in qv.get('query'))
            get_rough = 'rough' in qv or (
                hasattr(qv, 'get') and 'rough' in qv.get('query'))
        request = self.request.form.copy()
        if get_precise:
            request['location_precision'] = ['precise']
            for brain in self.context.queryCatalog(request):
                if brain.getId in skipIds:
                    continue
                yield PleiadesBrainPlacemark(brain, self.request)
        if get_rough:
            geoms = {}
            objects = {}
            request['location_precision'] = ['rough']
            for brain in self.context.queryCatalog(request):
                if brain.getId in skipIds:
                    continue
                item = PleiadesBrainPlacemark(brain, self.request)
                geo = brain.zgeo_geometry
                if geo and 'type' in geo and 'coordinates' in geo:
                    key = repr(geo)
                    if key not in geoms:
                        geoms[key] = geo
                    if key in objects:
                        objects[key].append(item)
                    else:
                        objects[key] = [item]
            placemarks = sorted(
                [AggregationPlacemark(
                    self.context,
                    geoms[k],
                    v) for k, v in objects.items()],
                key=W,
                reverse=False,
            )
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

    @property
    def name(self):
        return "Results of %s" % self.dc.Title()

    @property
    def alternate_link(self):
        portal_url = getToolByName(self.context, 'portal_url')()
        return "%s/search?%s" % (portal_url, make_query(self.request.form))


class ConnectionsDocument(PlaceDocument):
    implements(IContainer)
    template = ViewPageTemplateFile('kml_connections_document.pt')
    disposition_tmpl = "%s-connections.kml"

    @property
    def name(self):
        return "Places connected with %s" % self.dc.Title()

    @property
    def filename(self):
        return self.disposition_tmpl % self.context.getId()

    @property
    def features(self):
        for item in self.context.getBRefs('connectsWith'):
            yield PleiadesPlacemark(item, self.request)
        for item in self.context.getRefs('connectsWith'):
            yield PleiadesPlacemark(item, self.request)


class IKMLNeighborhood(Interface):

    def p_link():
        """Query string to search for precisely located neighbors"""

    def r_link():
        """Query string to search for aggregations of roughly located neighbors"""


class KMLNeighborhood(BrowserView):
    implements(IKMLNeighborhood)

    @memoize
    def geo(self):
        log.debug("Getting georeferencing")
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
        log.debug("Getting p_qs query string")
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
            href="%s/search_kml?%s&skipId:list=%s&style=peripheral"/>
        """ % (
            getToolByName(self.context, 'portal_url')(),
            make_query(query),
            self.context.getId())

    def r_link(self):
        log.debug("Getting r_qs query string")
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
            href="%s/search_kml?%s&skipId:list=%s&style=peripheral&"/>
        """ % (
            getToolByName(self.context, 'portal_url')(),
            make_query(query),
            self.context.getId())


document_template = NamedTemplateImplementation(
    ViewPageTemplateFile('kml_base_document.pt')
)
