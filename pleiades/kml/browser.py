from zgeo.kml.browser import Document, Folder, Placemark

class PlaceFolder(Folder):
    
    @property
    def features(self):
        for item in self.context.getFeatures():
            yield Placemark(item, self.request)


class PlaceDocument(Document):

    @property
    def features(self):
        return iter([PlaceFolder(self.context, self.request)])
