from zgeo.kml.browser import Document, Folder, Placemark

class PlaceFolder(Folder):
    
    @property
    def features(self):
        for item in self.context.getRefs('hasFeature'):
            yield Placemark(item, self.request)


class PlaceDocument(Document):

    @property
    def features(self):
        return iter([Folder(self.context, self.request)])
