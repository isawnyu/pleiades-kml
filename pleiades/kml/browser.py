from pleiades.capgrids import Grid
from zgeo.kml.browser import Document, Folder, Placemark


class GridPlacemark(Placemark):
    
    @property
    def id(self):
        return self.context.id
        
    @property
    def alternate_link(self):
        return self.context.id


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
        x = list(self.context.getLocations())
        if len(x) > 0:
            yield Placemark(x[0], self.request)
        for item in self.context.getFeatures():
            yield Placemark(item, self.request)


class PlaceDocument(Document):

    @property
    def features(self):
        return iter([PlaceFolder(self.context, self.request)])
