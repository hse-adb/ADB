from functools import partial

from clld.web.adapters.geojson import GeoJson
from clld.web.maps import SelectedLanguagesMap

from ADB.helpers import EMPTY_VALUE, collect_group_meanings, format_meanings


PALETTE = [
    '#1f77b4',
    '#2ca02c',
    '#d62728',
    '#9467bd',
    '#ff7f0e',
    '#17becf',
    '#8c564b',
    '#e377c2',
    '#bcbd22',
    '#4e79a7',
    '#59a14f',
    '#e15759',
]

UNIQUE_COLOR = '#8a8f98'
NO_DATA_COLOR = '#d9dde3'
UNIQUE_ID = 'unique'
NO_DATA_ID = 'no-data'


def _group_value(group):
    return format_meanings(collect_group_meanings(group).values())


def build_frame_map_data(frame_groups):
    values_by_language = {}
    languages_by_value = {}
    value_order = []

    for group in frame_groups:
        value = _group_value(group)
        values_by_language.setdefault(group.variety_pk, []).append(value)
        if value == EMPTY_VALUE:
            continue
        if value not in languages_by_value:
            languages_by_value[value] = set()
            value_order.append(value)
        languages_by_value[value].add(group.variety_pk)

    repeated_values = [
        value for value in value_order if len(languages_by_value[value]) > 1
    ]
    value_ids = {
        value: 'value-{}'.format(index)
        for index, value in enumerate(repeated_values)
    }

    legend_values = []
    for index, value in enumerate(repeated_values):
        legend_values.append({
            'id': value_ids[value],
            'label': value,
            'color': PALETTE[index % len(PALETTE)],
            'css_var': '--frame-map-{}'.format(value_ids[value]),
            'language_count': len(languages_by_value[value]),
        })
    legend_by_value = {
        item['label']: item
        for item in legend_values
    }

    sectors_by_language = {}
    has_unique = False
    has_no_data = False
    for language_pk, values in values_by_language.items():
        sectors = []
        for value in values:
            if value == EMPTY_VALUE:
                has_no_data = True
                sectors.append({
                    'id': NO_DATA_ID,
                    'label': 'no data',
                    'color': NO_DATA_COLOR,
                    'css_var': '--frame-map-no-data',
                    'kind': 'no-data',
                })
            elif value in value_ids:
                legend_value = legend_by_value[value]
                sectors.append({
                    'id': legend_value['id'],
                    'label': value,
                    'color': legend_value['color'],
                    'css_var': legend_value['css_var'],
                    'kind': 'value',
                })
            else:
                has_unique = True
                sectors.append({
                    'id': UNIQUE_ID,
                    'label': value,
                    'color': UNIQUE_COLOR,
                    'css_var': '--frame-map-unique',
                    'kind': 'unique',
                })
        sectors_by_language[language_pk] = sectors or [{
            'id': NO_DATA_ID,
            'label': 'no data',
            'color': NO_DATA_COLOR,
            'css_var': '--frame-map-no-data',
            'kind': 'no-data',
        }]
        if not sectors:
            has_no_data = True

    return {
        'legend_values': legend_values,
        'sectors_by_language': sectors_by_language,
        'has_unique': has_unique,
        'has_no_data': has_no_data,
        'unique_color': UNIQUE_COLOR,
        'no_data_color': NO_DATA_COLOR,
    }


def css_variables(map_data):
    values = [
        '{}: {}'.format(item['css_var'], item['color'])
        for item in map_data['legend_values']
    ]
    values.extend([
        '--frame-map-unique: {}'.format(map_data['unique_color']),
        '--frame-map-no-data: {}'.format(map_data['no_data_color']),
    ])
    return '; '.join(values)


class FramePieGeoJson(GeoJson):
    def __init__(self, languages, sectors_by_language):
        super().__init__(languages)
        self.sectors_by_language = sectors_by_language

    def feature_iterator(self, ctx, req):
        return self.obj

    def feature_properties(self, ctx, req, language):
        return {
            'frame_pie': {
                'slices': self.sectors_by_language.get(language.pk, [{
                    'id': NO_DATA_ID,
                    'label': 'no data',
                    'color': NO_DATA_COLOR,
                    'css_var': '--frame-map-no-data',
                    'kind': 'no-data',
                }]),
            },
        }


class FramePieMap(SelectedLanguagesMap):
    def __init__(self, ctx, req, languages, sectors_by_language, **kw):
        super().__init__(
            ctx,
            req,
            languages,
            geojson_impl=partial(
                FramePieGeoJson,
                sectors_by_language=sectors_by_language,
            ),
            **kw
        )

    def get_options(self):
        options = super().get_options()
        options.update({
            'icon_size': 30,
            'icons': 'framePie',
        })
        return options
