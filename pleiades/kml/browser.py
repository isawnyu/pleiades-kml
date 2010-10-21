from Products.CMFCore.utils import getToolByName

from pleiades.capgrids import Grid

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.PleiadesEntity.content.interfaces import ILocation
from Products.PleiadesEntity.geo import NotLocatedError

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
        # For locations that use getDescription
        return getattr(
            self.context, 'getDescription', self.context.Description)()

    @property
    def timePeriods(self):
        return ', '.join([x.capitalize() for x in self.context.getTimePeriods()]) or 'None'

    @property
    def edit_link(self):
        if ILocation.providedBy(self.context):
            return '%s/@@edit-geometry' % self.context.absolute_url()
        return None
        

class PleiadesBrainPlacemark(BrainPlacemark):
    
    @property
    def timePeriods(self):
        tp = getattr(self.context, 'getTimePeriods')
        if tp is None:
            return 'None'
        else:
            if callable(tp):
                values = tp()
            else:
                values = tp
        return ', '.join([x.capitalize() for v in values])

    @property
    def alternate_link(self):
        return self.context.getURL() #
            

class PlaceFolder(Folder):
    
    @property
    def description(self):
        s = self.context.Description()
        modernLocation = self.context.getModernLocation()
        if modernLocation:
            s += ', modern location: %s'  % modernLocation
        return s
    
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

class PlaceNeighborsDocument(TopicDocument):
    template = ViewPageTemplateFile('kml_topic_document.pt')

    @property
    def name(self):
        return "Neighborhood of %s" % self.dc.Title()

    @property
    def features(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        try:
            g = IGeoreferenced(self.context)
        except NotLocatedError:
            raise StopIteration
        for brain in catalog(
            geolocation={'query': (g.bounds, 20000.0), 'range': 'distance' }, 
            portal_type={'query': ['Place']}):
            if brain.getId == self.context.getId():
                # skip self
                continue
            yield PleiadesBrainPlacemark(brain, self.request)

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
