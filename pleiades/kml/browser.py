from Products.CMFCore.utils import getToolByName

from pleiades.capgrids import Grid

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PleiadesEntity.content.interfaces import ILocation
from pleiades.geographer.geo import NotLocatedError

from zgeo.kml.browser import Document, Folder, Placemark
from zgeo.plone.kml.browser import Document, TopicDocument, BrainPlacemark
from zgeo.geographer.interfaces import IGeoreferenced

from zope.component import adapts
from zope.publisher.interfaces import browser
from zope.contentprovider.interfaces import IContentProvider
from zope.interface import implements, Interface
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.dublincore.interfaces import ICMFDublinCore
from zgeo.kml.interfaces import IFeature, IPlacemark, IContainer


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


class PlaceNeighborhoodDocument(PlaceDocument):
    implements(IContainer)
    template = ViewPageTemplateFile('kml_neighborhood_document.pt')
    
    @property
    def neighbors_kml(self):
        return "%s/neighbors-kml" % self.context.absolute_url().rstrip('/')


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
            geolocation={'query': (g.bounds, 10), 'range': 'nearest' }, 
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
            geolocation={'query': (g.bounds, 10), 'range': 'nearest' }, 
            portal_type={'query': ['Place']},
            location_precision={'query': ['precise']}
            )

class PlaceRoughNeighborsDocument(PlaceNeighborsDocument):
    disposition_tmpl = "%s-r-neighbors.kml"

    @property
    def name(self):
        return "Roughly located neighbors of %s" % self.dc.Title()

    def criteria(self, g):
        return dict(
            geolocation={'query': (g.bounds, 10), 'range': 'nearest' }, 
            portal_type={'query': ['Place']},
            location_precision={'query': ['rough']}
            )


class PleiadesDocument(Document):
    template = ViewPageTemplateFile('kml_document.pt')


class PleiadesTopicDocument(TopicDocument):
    template = ViewPageTemplateFile('kml_topic_document.pt')

    @property
    def features(self):
        for brain in self.context.queryCatalog():
            yield PleiadesBrainPlacemark(brain, self.request)

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
