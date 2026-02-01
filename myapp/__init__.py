import collections

from pyramid.config import Configurator
from clld.interfaces import IMapMarker, IValueSet, IValue, IDomainElement
from clld.web.icon import MapMarker
from clldutils.svg import pie, icon, data_url

# we must make sure custom models are known at database initialization!
from myapp import models



class FeatureMapMarker(MapMarker):
    def __call__(self, ctx, req):
        return super(FeatureMapMarker, self).__call__(ctx, req)



def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.include('clld.web.app')


    config.registry.registerUtility(FeatureMapMarker(), IMapMarker)

    return config.make_wsgi_app()
