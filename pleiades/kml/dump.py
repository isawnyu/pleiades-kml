
import logging
import os

from Products.CMFCore.utils import getToolByName
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from ZTUtils import make_query

from pleiades.kml.browser import AggregationPlacemark, PleiadesBrainPlacemark
from pleiades.kml.browser import SearchDCProvider, W

log = logging.getLogger('pleiades.kml')


class PleiadesDumpPlacemark(PleiadesBrainPlacemark):

    @property
    def alternate_link(self):
        return "http://pleiades.stoa.org/places/%s" % self.context.getId


class AggregationDumpPlacemark(AggregationPlacemark):

    @property
    def alternate_link(self):
        query = {
            'location_precision': ['rough'],
            'path': {'query': [ob.context.getPath() for ob in self.objects],
                     'depth': 0}
            }
        return "http://pleiades.stoa.org/search?%s" % make_query(query)


class AllPlacesDocument:

    def __init__(self, context):
        self.context = context
        self.dc = SearchDCProvider()
        self.filename = "all.kml"
        self.name = "Pleiades KML"
    
    @property
    def features(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'location_precision': ['precise'],
            'portal_type': ['Place'],
            'review_state': ['published']
            }
        for brain in catalog(query):
            yield PleiadesDumpPlacemark(brain, None)
        geoms = {}
        objects = {}
        query = {
            'location_precision': ['rough'],
            'portal_type': ['Place'],
            'review_state': ['published']
            }
        for brain in catalog(query):
            item = PleiadesDumpPlacemark(brain, None)
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
            [AggregationDumpPlacemark(
                self.context, geoms[key], val) for key, val in objects.items()],
                key=W,
                reverse=False)
        for placemark in placemarks:
            yield placemark


class DumpTemplateFile(PageTemplateFile):
    def pt_getContext(self, args=(), options={}, **kw):
        rval = PageTemplateFile.pt_getContext(self, args=args)
        options.update(rval)
        return options

pt = DumpTemplateFile("kml_topic_document.pt")
kml_macros = PageTemplateFile("kml_macros.pt")
main_macros = PageTemplateFile("kml_template.pt")
