
import logging
import os
#from sys import stdin, stdout

from Products.CMFCore.utils import getToolByName
#from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from pleiades.kml.browser import AggregationPlacemark
from pleiades.kml.browser import PleiadesBrainPlacemark, PleiadesSearchDocument

log = logging.getLogger('pleiades.kml')


class PleiadesDumpPlacemark(PleiadesBrainPlacemark):

    @property
    def alternate_link(self):
        return "http://pleiades.stoa.org/places/%s" % self.context.getId


class AggregationDumpPlacemark(AggregationPlacemark):

    @property
    def alternate_link(self):
        query = '&'.join(
            "getId:list=%s" % ob.context.getId for ob in self.objects)
        return "http://pleiades.stoa.org/search?location_precision=rough&%s" % query


class AllPlacesDocument(PleiadesSearchDocument):
    template = ViewPageTemplateFile("kml_topic_document.pt")
    filename = "all.kml"

    def __init__(self, context):
        self.context = context

    @property
    def features(self):
        catalog = getToolByName(self.context, 'portal_catalog')
        query = {
            'location_precision': ['precise'],
            'portal_type': ['Place'],
            'review_state': ['published']
            }
        for brain in catalog(query):
            yield PleiadesDumpPlacemark(brain, self.request)
        geoms = {}
        objects = {}
        query = {
            'location_precision': ['rough'],
            'portal_type': ['Place'],
            'review_state': ['published']
            }
        for brain in catalog(query):
            item = PleiadesDumpPlacemark(brain, self.request)
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


if __name__ == '__main__':
    site = app['plone']

    #context = makerequest(site)
    #import pdb; pdb.set_trace()
    #context.REQUEST.form.update(
    #    {'portal_type': ['Place'], 'review_state': ['published']})
    view = AllPlacesDocument(site)
    import pdb; pdb.set_trace() #, context.REQUEST)
    sys.stdout.write(view())
    
