from Products.Five import zcml
from Products.Five import fiveconfigure

from Testing import ZopeTestCase as ztc

from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup

ztc.installProduct('ATVocabularyManager')
ztc.installProduct('PleiadesEntity')
ztc.installProduct('zgeo.plone.geographer')
ztc.installProduct('zgeo.plone.kml')

@onsetup
def setup_pleiades_kml():
    """Set up the additional products required for the Pleiades site policy.
    
    The @onsetup decorator causes the execution of this body to be deferred
    until the setup of the Plone site testing layer.
    """

    # Load the ZCML configuration for the optilux.policy package.
    
    fiveconfigure.debug_mode = True
    import pleiades.kml
    zcml.load_config('configure.zcml', pleiades.kml)
    fiveconfigure.debug_mode = False
    
    # We need to tell the testing framework that these products
    # should be available. This can't happen until after we have loaded
    # the ZCML.

    ztc.installPackage('pleiades.workspace')
    ztc.installPackage('pleiades.kml')
    
# The order here is important: We first call the (deferred) function which
# installs the products we need for the Pleiades package. Then, we let 
# PloneTestCase set up this product on installation.

setup_pleiades_kml()
ptc.setupPloneSite(
    products=[
    'ATVocabularyManager', 
    'PleiadesEntity',
    'pleiades.workspace',
    'zgeo.plone.geographer', 
    'zgeo.plone.geographer'
    ])

class PleiadesKMLTestCase(ptc.PloneTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """

class PleiadesKMLFunctionalTestCase(ptc.FunctionalTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """

    def afterSetUp(test):
        test.setRoles(('Manager',))
        pt = test.portal.portal_types
        for type in [
            'Topic', 
            'PlaceContainer', 
            'FeatureContainer',
            'LocationContainer',
            'NameContainer',
            'Workspace Folder',
            'Workspace',
            'Workspace Collection',
            'Place',
            'Feature',
            'Location',
            'Name'
            ]:
            lpf = pt[type]
            lpf.global_allow = True

        _ = test.portal.invokeFactory(
            'PlaceContainer', id='places', title='Places', 
            description='All Places'
            )
        _ = test.portal.invokeFactory(
            'FeatureContainer', id='features', title='Features'
            )
        _ = test.portal.invokeFactory(
            'LocationContainer', id='locations', title='Locations'
            )
        _ = test.portal.invokeFactory(
            'NameContainer', id='names', title='Names'
            )
        _ = test.portal.invokeFactory(
            'Workspace Folder', id='workspaces', title='Workspaces'
            )

        test.names = test.portal['names']
        test.locations = test.portal['locations']
        test.features = test.portal['features']
        test.places = test.portal['places']
        test.workspaces = test.portal['workspaces']

        nid = test.names.invokeFactory('Name', nameTransliterated='Foo')
        name = test.names[nid]
        name.reindexObject()

        lid = test.locations.invokeFactory(
            'Location', geometry='Point:[0.0, 0.0]')
        location = test.locations[lid]
        location.reindexObject()

        fid = test.features.invokeFactory('Feature', description='A Feature')
        feature = test.features[fid]
        feature.addReference(name, 'hasName')
        feature.addReference(location, 'hasLocation')
        feature.reindexObject()

        pid = test.places.invokeFactory('Place', id='a', description='A Place')
        place = test.places[pid]
        place.addReference(feature, 'hasFeature')
        place.reindexObject()

        cid = test.portal.invokeFactory('Topic', id='places-topic')
        test.topic = test.portal[cid] 
        c = test.topic.addCriterion('Type', 'ATPortalTypeCriterion')
        c.setValue('Place')

        cid = test.portal.invokeFactory('Topic', id='features-topic')
        test.topic = test.portal[cid] 
        c = test.topic.addCriterion('Type', 'ATPortalTypeCriterion')
        c.setValue('Feature')

