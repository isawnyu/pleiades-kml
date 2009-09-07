from Products.Five import zcml
from Products.Five import fiveconfigure

from Testing import ZopeTestCase as ztc

from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup

from pleiades.workspace.tests.base import ContentFunctionalTestCase

ztc.installProduct('ATVocabularyManager')
ztc.installProduct('Products.CompoundField')
ztc.installProduct('Products.ATBackRef')
ztc.installProduct('PleiadesEntity')

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
    ztc.installProduct('zgeo.plone.geographer')
    ztc.installProduct('zgeo.plone.kml')
    ztc.installPackage('pleiades.kml')
    
# The order here is important: We first call the (deferred) function which
# installs the products we need for the Pleiades package. Then, we let 
# PloneTestCase set up this product on installation.

setup_pleiades_kml()
ptc.setupPloneSite(
    products=[
    'ATVocabularyManager',
    'Products.CompoundField',
    'Products.ATBackRef',
    'PleiadesEntity',
    'pleiades.workspace',
    'zgeo.plone.geographer',
    'pleiades.kml'
    ])

class PleiadesKMLTestCase(ptc.PloneTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """

class PleiadesKMLFunctionalTestCase(ContentFunctionalTestCase):
    """We use this base class for all the tests in this package. If necessary,
    we can put common utility or setup code in here.
    """

    def afterSetUp(self):
        super(PleiadesKMLFunctionalTestCase, self).afterSetUp()
        pid = self.places.invokeFactory('Place', '2', title='Ninoe')
        p = self.places[pid]
        nameAttested = u'\u039d\u03b9\u03bd\u1f79\u03b7'.encode('utf-8')
        nid = p.invokeFactory('Name', 'ninoe', nameAttested=nameAttested, nameLanguage='grc', nameType='geographic', accuracy='accurate', completeness='complete')
        attestations = p[nid].Schema()['attestations']
        attestations.resize(1)
        p[nid].update(attestations=[dict(confidence='certain', timePeriod='roman')])
        lid = p.invokeFactory('Location', 'position', title='Point 1', geometry='Point:[-86.4808333333333, 34.769722222222]')

        pid = self.places.invokeFactory('Place', '3', title='Ninoe', location='http://atlantides.org/capgrids/35/E2')
        p = self.places[pid]
        lid = p.invokeFactory('Location', 'undetermined', title='Undetermined location', geometry=None)
                
        cid = self.portal.invokeFactory('Topic', id='places-topic')
        self.topic = self.portal[cid] 
        c = self.topic.addCriterion('portal_type', 'ATPortalTypeCriterion')
        c.setValue('Place')

        cid = self.portal.invokeFactory('Topic', id='features-topic')
        self.topic = self.portal[cid] 
        c = self.topic.addCriterion('portal_type', 'ATPortalTypeCriterion')
        c.setValue('Feature')
