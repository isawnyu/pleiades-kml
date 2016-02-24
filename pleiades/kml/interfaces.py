from zope.interface import Interface, Attribute


class IFeature(Interface):
    """http://code.google.com/apis/kml/documentation/kml_tags_beta1.html
    """

    author = Attribute("""A mapping with name, URI, and email keys""")
    kid = Attribute("""A universally unique KML identifier""")
    name = Attribute("""A human readable text""")
    description = Attribute("""A human readable text summary""")
    alternate_link = Attribute("""URL of the resource linked by the entry""")


class IPlacemark(IFeature):
    """http://code.google.com/apis/kml/documentation/kml_tags_beta1.html
    """

    # geographic elements
    reprpt_kml = Attribute(
        """KML coordinates of a representative point of the location""")
    coords_kml = Attribute("""KML coordinate encoding of the location""")
    hasLineString = Attribute("""Boolean, True if has a line location""")
    hasPoint = Attribute("""Boolean, True if has a point location""")
    hasPolygon = Attribute("""Boolean, True if has a polygon location""")


class IContainer(IFeature):
    """http://code.google.com/apis/kml/documentation/kml_tags_beta1.html
    """

    features = Attribute("""An iterator over folder and placemark features""")
