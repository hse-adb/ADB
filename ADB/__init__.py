from pyramid.config import Configurator
from clld.interfaces import IMapMarker
from clld.web.icon import MapMarker

# we must make sure custom models are known at database initialization!
from ADB import models
from ADB import interfaces


def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.include('clld.web.app')
    config.include('ADB.datatables')

    config.register_resource('frame', models.Frame, interfaces.IFrame, with_index=True)
    config.register_resource('group', models.Group, interfaces.IGroup, with_index=True)

    config.registry.registerUtility(MapMarker(), IMapMarker)

    return config.make_wsgi_app()
