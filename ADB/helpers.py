from pathlib import Path

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
