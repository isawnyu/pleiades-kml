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
        x = self.context.getLocations()
        dc_coverage = self.context.getLocation()
        if len(x) > 0:
            yield Placemark(self.context, self.request)
        elif dc_coverage.startswith('http://atlantides.org/capgrids'):
            s = dc_coverage.rstrip('/')
            mapid, gridsquare = s.split('/')[-2:]
            grid = Grid(mapid, gridsquare)
            yield GridPlacemark(grid, self.request)
        for item in self.context.getFeatures():
            yield Placemark(item, self.request)


class PlaceDocument(Document):

    @property
    def features(self):
        return iter([PlaceFolder(self.context, self.request)])
