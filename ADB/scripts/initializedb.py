from clld.cliutil import Data, bibtex2source
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib import bibtex

import ADB
from ADB import models


def main(args):
    data = Data()
    ds = args.cldf

    data.add(
        common.Dataset,
        ADB.__name__,
        id=ADB.__name__,
        domain='localhost',

        publisher_name = "",
        publisher_place = "",
        publisher_url = "",
        license = "http://creativecommons.org/licenses/by/4.0/",
        jsondata = {
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'},

    )


    contrib = data.add(
        common.Contribution,
        None,
        id='cldf',
        name=ds.properties.get('dc:title'), #args.cldf.properties.get('dc:title'),
        description=ds.properties.get('dc:bibliographicCitation'), #args.cldf.properties.get('dc:bibliographicCitation'),
    )

    for lang in ds['LanguageTable'].iterdicts():
            #in args.cldf.iter_rows('LanguageTable', 'id', 'glottocode', 'name', 'latitude', 'longitude'):
        data.add(
            models.Variety,
            lang['language_id'],
            id=lang['language_id'],
            name=lang['Name'],
            iso639p3code=lang.get('ISO639P3code'),
            latitude=lang['Latitude'],
            longitude=lang['Longitude'],
            glottocode=lang['Glottocode'],
            family_name=lang['Family_name'],
            family_level_id=lang['Family_level_ID'],
        )
    
    for row in ds['frames.csv'].iterdicts():
        data.add(
            models.Frame,
            row['frame_id'],
            id=row['frame_id'],
            frame=row['frame']
        )

    try:
        frame_concepticon_rows = ds['frames_concepticon.csv'].iterdicts()
    except KeyError:
        frame_concepticon_rows = []

    for i, row in enumerate(frame_concepticon_rows, start=1):
        frame = data['Frame'][row['frame_id']]
        concepticon_id = row.get('concepticon_id')
        data.add(
            models.FrameConcepticon,
            row.get('concepticon_id'),
            frame=frame,
            concepticon_id=int(concepticon_id) if concepticon_id not in [None, ''] else None,
            concepticon=row.get('concepticon'),
        )
    
    for row in ds['groups.csv'].iterdicts():
        variety = data['Variety'][row['language_id']]
        frame = data['Frame'][row['frame_id']]
        data.add(
            models.Group,
            row['group_id'],
            id=row['group_id'],
            variety=variety,
            frame=frame,
            term=row['term'],
        )
    
    for row in ds['lexemes.csv'].iterdicts():
        group = data['Group'][row['group_id']]
        data.add(
            models.Lexeme,
            row['lexeme_id'],
            id=row['lexeme_id'],
            group=group,
            lexeme=row['lexeme'],
            russian=row.get('russian'),
        )
    
    for row in ds['meanings.csv'].iterdicts():
        order = row.get('order')
        data.add(
            models.Meaning,
            row['meaning_id'],
            id=row['meaning_id'],
            order=int(order) if order not in [None, ''] else None,
            name=row['meaning'],
        )
    
    # lexeme-to-meanings relation
    for row in ds['lexeme_meaning.csv'].iterdicts():
        lexeme_id = row.get('lexeme_id')
        meaning_id = row.get('meaning_id')
        if not lexeme_id or not meaning_id:
            continue
        lexeme = data['Lexeme'][lexeme_id]
        meaning = data['Meaning'][meaning_id]
        lexeme.meanings.append(meaning)
    
    if ds.bibpath:
        for rec in bibtex.Database.from_file(ds.bibpath, lowercase=True):
            data.add(common.Source, rec.id, _obj=bibtex2source(rec))
    
    DBSession.flush()


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
