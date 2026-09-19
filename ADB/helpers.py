from pathlib import Path
from urllib.parse import quote, urlparse

import ADB


EMPTY_VALUE = "&mdash;"


def id_sort_key(value):
    try:
        return 0, int(value)
    except (TypeError, ValueError):
        return 1, str(value)


def format_meanings(meanings):
    meanings = list(meanings or [])
    if not meanings:
        return EMPTY_VALUE

    ordered = sorted(meanings, key=lambda item: id_sort_key(item.id))
    left = [meaning.name for meaning in ordered if meaning.order == 1]
    right = [meaning.name for meaning in ordered if meaning.order == 2]
    return "&lt;{}, {}&gt;".format(
        " ".join(left) or EMPTY_VALUE,
        " ".join(right) or EMPTY_VALUE,
    )


def collect_group_meanings(group):
    meanings = {}
    for lexeme in group.lexemes:
        for meaning in lexeme.meanings:
            meanings[meaning.pk] = meaning
    return meanings


def group_sort_key(meanings):
    meanings = list(meanings or [])
    if not meanings:
        return 1, ()
    return 0, min(id_sort_key(meaning.id) for meaning in meanings)


def format_group_meanings(group_meanings):
    group_meanings = list(group_meanings or [])
    if not group_meanings:
        return EMPTY_VALUE

    return "<br>".join(
        format_meanings(meanings.values())
        for meanings in sorted(
            group_meanings,
            key=lambda item: group_sort_key(item.values()),
        )
    )


def language_description(language):
    iso_code = getattr(language, 'iso639p3code', None)
    iso_code = (iso_code or '').strip().lower()
    if not iso_code:
        return ''

    path = Path(ADB.__file__).parent.joinpath(
        'data',
        'descriptions',
        '{}.txt'.format(iso_code),
    )
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8').strip()


def language_external_links(language):
    jsondata = getattr(language, 'jsondata', None) or {}
    links = jsondata.get('glottolog_links') or []
    visible_links = []
    for link in links:
        item = _external_link_item(link)
        if item is not None:
            visible_links.append(item)
    return visible_links


def _external_link_item(link):
    item = {
        'label': (link.get('label') or '').strip(),
        'url': (link.get('url') or '').strip(),
        'icon_url': (link.get('icon_url') or '').strip(),
        'icon_alt': (link.get('icon_alt') or '').strip(),
    }
    if not item['label'] or not item['url'] or _is_language_identifier_link(item):
        return None
    return item


def _is_language_identifier_link(link):
    parsed = urlparse(link['url'])
    hostname = (parsed.hostname or '').lower()
    path = parsed.path.rstrip('/')
    label = link['label'].lower()

    if hostname == 'iso639-3.sil.org' and path.startswith('/code/'):
        return True
    if hostname in {'glottolog.org', 'www.glottolog.org'}:
        return path.startswith('/resource/languoid/id/')
    return label.startswith('glottocode:') or ' at iso 639-3' in label


def language_identifier_badges(language):
    glottocode = (getattr(language, 'glottocode', None) or '').strip()
    iso_code = (getattr(language, 'iso639p3code', None) or '').strip().lower()
    badges = []

    if glottocode:
        badges.append({
            'label': 'Glottocode:',
            'value': glottocode,
            'url': 'http://glottolog.org/resource/languoid/id/{}'.format(
                quote(glottocode)
            ),
            'identifier_class': 'glottolog',
        })

    if iso_code:
        badges.append({
            'label': 'ISO 639-3:',
            'value': iso_code,
            'url': 'https://iso639-3.sil.org/code/{}'.format(quote(iso_code)),
            'identifier_class': 'iso639-3',
        })

    return badges


def language_wals_breadcrumb(language):
    jsondata = getattr(language, 'jsondata', None) or {}
    wals_info = jsondata.get('wals_info') or {}

    return [
        {
            'label': (item.get('label') or '').strip(),
            'value': (item.get('value') or '').strip(),
            'url': (item.get('url') or '').strip(),
        }
        for item in wals_info.get('breadcrumb') or []
        if (item.get('label') or '').strip() and (item.get('value') or '').strip()
    ]


def language_wals_spoken_in(language):
    jsondata = getattr(language, 'jsondata', None) or {}
    wals_info = jsondata.get('wals_info') or {}

    return [
        {
            'label': (item.get('label') or '').strip(),
            'url': (item.get('url') or '').strip(),
        }
        for item in wals_info.get('spoken_in') or []
        if (item.get('label') or '').strip()
    ]
