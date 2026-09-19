import csv
import json
import re
from contextlib import nullcontext
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'
TABLES_DIR = BASE_DIR / 'tables'
GLOTTOLOG_LANGUAGE_URL = 'https://glottolog.org/resource/languoid/id/{}.json'
GLOTTOLOG_LANGUAGE_PAGE_URL = 'https://glottolog.org/resource/languoid/id/{}'
WALS_BASE_URL = 'https://wals.info'
LANGUAGE_COLUMNS = [
    'language_id',
    'Name',
    'Macroarea',
    'Latitude',
    'Longitude',
    'Glottocode',
    'ISO639P3code',
    'Family_name',
    'Family_level_ID',
    'Glottolog_links',
    'WALS_info',
]


def data_path(filename: str) -> Path:
    return DATA_DIR / filename


def read_csv_rows(path: str | Path):
    with open(path, 'rt', encoding='utf-8') as f:
        return list(csv.reader(f))


def read_language_rows():
    with open(data_path('languages.csv'), 'rt', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def is_glottocode(value: str) -> bool:
    return bool(re.fullmatch(r'[a-z0-9]{8}', value or ''))


def load_language_ids():
    language_ids = {}
    duplicate_language_ids = {}
    for row in read_language_rows():
        glottocode = (row.get('Glottocode') or '').strip()
        if not glottocode:
            continue
        language_id = int(row['language_id'])
        if glottocode in language_ids:
            duplicate_language_ids.setdefault(
                glottocode,
                [language_ids[glottocode]],
            ).append(language_id)
        else:
            language_ids[glottocode] = language_id

    for glottocode in duplicate_language_ids:
        language_ids.pop(glottocode, None)
    return language_ids, duplicate_language_ids


def fetch_glottolog_languoid(glottocode: str, opener=None) -> dict:
    if not is_glottocode(glottocode):
        raise ValueError(f'{glottocode} не похож на Glottocode')

    url = GLOTTOLOG_LANGUAGE_URL.format(glottocode)
    request = Request(url, headers={'Accept': 'application/json'})
    opener = opener or urlopen
    try:
        response = opener(request, timeout=20)
        context = response if hasattr(response, '__enter__') else nullcontext(response)
        with context as f:
            return json.loads(f.read().decode('utf-8'))
    except HTTPError as error:
        raise ValueError(
            f'Glottolog вернул HTTP {error.code} для {glottocode}'
        ) from error
    except URLError as error:
        raise ValueError(
            f'Не удалось получить данные Glottolog для {glottocode}: {error.reason}'
        ) from error


def fetch_html(url: str, opener=None) -> str:
    request = Request(url, headers={'Accept': 'text/html'})
    opener = opener or urlopen
    try:
        response = opener(request, timeout=20)
        context = response if hasattr(response, '__enter__') else nullcontext(response)
        with context as f:
            return f.read().decode('utf-8')
    except HTTPError as error:
        raise ValueError(f'HTTP {error.code} для {url}') from error
    except URLError as error:
        raise ValueError(f'Не удалось получить {url}: {error.reason}') from error


def json_csv_value(value):
    if not value:
        return ''
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


class GlottologLinksParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.in_links = False
        self.div_depth = 0
        self.current = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div' and attrs.get('id') == 'acc-partner':
            self.in_links = True
            self.div_depth = 1
            return

        if not self.in_links:
            return

        if tag == 'div':
            self.div_depth += 1
        elif tag == 'a':
            self.current = {
                'label': (attrs.get('title') or '').strip(),
                'url': urljoin(self.base_url, attrs.get('href') or ''),
                'icon_url': '',
                'icon_alt': '',
                'text': [],
            }
        elif tag == 'img' and self.current is not None:
            self.current['icon_url'] = urljoin(self.base_url, attrs.get('src') or '')
            self.current['icon_alt'] = (attrs.get('alt') or '').strip()

    def handle_data(self, data):
        if self.in_links and self.current is not None:
            self.current['text'].append(data)

    def handle_endtag(self, tag):
        if not self.in_links:
            return

        if tag == 'a' and self.current is not None:
            label = self.current['label'] or ' '.join(
                part.strip() for part in self.current['text'] if part.strip()
            )
            if label and self.current['url']:
                self.links.append({
                    'label': label,
                    'url': self.current['url'],
                    'icon_url': self.current['icon_url'],
                    'icon_alt': self.current['icon_alt'],
                })
            self.current = None
        elif tag == 'div':
            self.div_depth -= 1
            if self.div_depth <= 0:
                self.in_links = False


def fetch_glottolog_links(glottocode: str, opener=None) -> list[dict]:
    if not is_glottocode(glottocode):
        raise ValueError(f'{glottocode} не похож на Glottocode')
    url = GLOTTOLOG_LANGUAGE_PAGE_URL.format(glottocode)
    parser = GlottologLinksParser(url)
    parser.feed(fetch_html(url, opener=opener))
    return parser.links


def is_wals_language_url(url: str) -> bool:
    parsed = urlparse(url)
    return (
        (parsed.hostname or '').lower() == 'wals.info'
        and parsed.path.startswith('/languoid/lect/')
    )


def wals_links(glottolog_links: list[dict]) -> list[str]:
    return [
        link['url']
        for link in glottolog_links or []
        if is_wals_language_url(link.get('url') or '')
    ]


class WalsLanguageInfoParser(HTMLParser):
    def __init__(self, source_url: str):
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.in_breadcrumb = False
        self.breadcrumb_depth = 0
        self.current_crumb = None
        self.current_crumb_link_text = None
        self.breadcrumb = []
        self.current_row = None
        self.current_cell = None
        self.current_link = None
        self.spoken_in = []

    @staticmethod
    def has_class(attrs, class_name):
        return class_name in (attrs.get('class') or '').split()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'ul' and self.has_class(attrs, 'breadcrumb'):
            self.in_breadcrumb = True
            self.breadcrumb_depth = 1
            return

        if self.in_breadcrumb:
            if tag == 'ul':
                self.breadcrumb_depth += 1
            elif tag == 'li':
                self.current_crumb = {
                    'text': [],
                    'link_url': '',
                    'link_text': '',
                }
            elif tag == 'a' and self.current_crumb is not None:
                self.current_crumb['link_url'] = urljoin(
                    self.source_url,
                    attrs.get('href') or '',
                )
                self.current_crumb_link_text = []

        if tag == 'tr':
            self.current_row = []
        elif tag == 'td' and self.current_row is not None:
            self.current_cell = {'text': [], 'links': []}
        elif tag == 'a' and self.current_cell is not None:
            self.current_link = {
                'label': [],
                'url': urljoin(self.source_url, attrs.get('href') or ''),
                'title': (attrs.get('title') or '').strip(),
            }

    def handle_data(self, data):
        if self.current_crumb is not None:
            self.current_crumb['text'].append(data)
        if self.current_crumb_link_text is not None:
            self.current_crumb_link_text.append(data)
        if self.current_cell is not None:
            self.current_cell['text'].append(data)
        if self.current_link is not None:
            self.current_link['label'].append(data)

    def handle_endtag(self, tag):
        if self.in_breadcrumb:
            if tag == 'a' and self.current_crumb_link_text is not None:
                self.current_crumb['link_text'] = normalize_spaces(
                    ' '.join(self.current_crumb_link_text)
                )
                self.current_crumb_link_text = None
            elif tag == 'li' and self.current_crumb is not None:
                crumb = self.finish_breadcrumb_item(self.current_crumb)
                if crumb is not None:
                    self.breadcrumb.append(crumb)
                self.current_crumb = None
            elif tag == 'ul':
                self.breadcrumb_depth -= 1
                if self.breadcrumb_depth <= 0:
                    self.in_breadcrumb = False

        if tag == 'a' and self.current_link is not None:
            label = normalize_spaces(' '.join(self.current_link['label']))
            self.current_cell['links'].append({
                'label': label or self.current_link['title'],
                'url': self.current_link['url'],
            })
            self.current_link = None
        elif tag == 'td' and self.current_cell is not None:
            self.current_cell['text'] = normalize_spaces(
                ' '.join(self.current_cell['text'])
            )
            self.current_row.append(self.current_cell)
            self.current_cell = None
        elif tag == 'tr' and self.current_row is not None:
            self.finish_row(self.current_row)
            self.current_row = None

    def finish_breadcrumb_item(self, crumb):
        text = normalize_spaces(' '.join(crumb['text']).replace('/', ''))
        if ':' not in text:
            return None
        label, value = text.split(':', 1)
        value = crumb['link_text'] or normalize_spaces(value)
        if not label.strip() or not value:
            return None
        return {
            'label': label.strip(),
            'value': value,
            'url': crumb['link_url'],
        }

    def finish_row(self, row):
        if len(row) < 2:
            return
        if row[0]['text'].strip().lower() != 'spoken in:':
            return

        links = [
            {
                'label': link['label'],
                'url': link['url'],
            }
            for link in row[1]['links']
            if link['label']
        ]
        if links:
            self.spoken_in = links
        elif row[1]['text']:
            self.spoken_in = [{'label': row[1]['text'], 'url': ''}]


def normalize_spaces(value: str) -> str:
    return re.sub(r'\s+', ' ', value).strip()


def parse_wals_language_info(html: str, source_url: str) -> dict:
    parser = WalsLanguageInfoParser(source_url)
    parser.feed(html)
    info = {
        'source_url': source_url,
        'breadcrumb': parser.breadcrumb,
        'spoken_in': parser.spoken_in,
    }
    return info if info['breadcrumb'] or info['spoken_in'] else {}


def fetch_wals_language_info(url: str, opener=None) -> dict:
    if not is_wals_language_url(url):
        return {}
    return parse_wals_language_info(fetch_html(url, opener=opener), url)


def wals_info_from_links(glottolog_links: list[dict], opener=None) -> dict:
    for url in wals_links(glottolog_links):
        try:
            info = fetch_wals_language_info(url, opener=opener)
        except ValueError:
            continue
        if info:
            return info
    return {}


def resolve_wals_language_info(
    data: dict,
    glottolog_links: list[dict] | None = None,
    opener=None,
) -> dict:
    info = wals_info_from_links(glottolog_links or [], opener=opener)
    if info:
        return info

    for ancestor in reversed(data.get('classification') or []):
        ancestor_id = ancestor.get('id')
        if not is_glottocode(ancestor_id):
            continue
        try:
            info = wals_info_from_links(
                fetch_glottolog_links(ancestor_id, opener=opener),
                opener=opener,
            )
        except ValueError:
            continue
        if info:
            return info

    return {}


def format_glottolog_coord(value):
    if value is None:
        return ''
    return '{:.2f}'.format(float(value))


def format_glottolog_macroarea(macroareas):
    if not macroareas:
        return ''
    if isinstance(macroareas, dict):
        values = macroareas.values()
    else:
        values = macroareas
    return '; '.join(str(value) for value in values if value)


def direct_glottolog_coordinates(data: dict):
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    if latitude is None or longitude is None:
        return None
    return latitude, longitude


def resolve_glottolog_coordinates(data: dict, opener=None):
    coordinates = direct_glottolog_coordinates(data)
    if coordinates is not None:
        return coordinates

    for ancestor in reversed(data.get('classification') or []):
        ancestor_id = ancestor.get('id')
        if not is_glottocode(ancestor_id):
            continue
        try:
            ancestor_data = fetch_glottolog_languoid(ancestor_id, opener=opener)
        except ValueError:
            continue
        coordinates = direct_glottolog_coordinates(ancestor_data)
        if coordinates is not None:
            return coordinates

    return None, None


def language_row_from_glottolog(
    data: dict,
    language_id: int,
    coordinates=None,
    glottolog_links=None,
    wals_info=None,
) -> list[str]:
    classification = data.get('classification') or []
    family = classification[0] if classification else {}
    glottocode = data.get('id') or ''
    if coordinates is None:
        coordinates = direct_glottolog_coordinates(data) or (None, None)
    latitude, longitude = coordinates
    return [
        str(language_id),
        data.get('name') or '',
        format_glottolog_macroarea(data.get('macroareas')),
        format_glottolog_coord(latitude),
        format_glottolog_coord(longitude),
        glottocode,
        data.get('iso639-3') or data.get('hid') or '',
        family.get('name') or '',
        family.get('id') or '',
        json_csv_value(glottolog_links),
        json_csv_value(wals_info),
    ]


def append_language_from_glottolog(glottocode: str, opener=None) -> bool:
    rows = read_language_rows()
    existing_glottocodes = {
        (row.get('Glottocode') or '').strip()
        for row in rows
    }
    if glottocode in existing_glottocodes:
        return False

    next_language_id = max(
        [int(row['language_id']) for row in rows if row.get('language_id')],
        default=0,
    ) + 1
    data = fetch_glottolog_languoid(glottocode, opener=opener)
    glottolog_links = fetch_glottolog_links(glottocode, opener=opener)
    coordinates = resolve_glottolog_coordinates(data, opener=opener)
    wals_info = resolve_wals_language_info(
        data,
        glottolog_links=glottolog_links,
        opener=opener,
    )
    row = language_row_from_glottolog(
        data,
        next_language_id,
        coordinates=coordinates,
        glottolog_links=glottolog_links,
        wals_info=wals_info,
    )

    with open(data_path('languages.csv'), 'a', encoding='utf-8', newline='') as f:
        csv.writer(f).writerow(row)
    return True


def ensure_languages_for_tables(tables, opener=None):
    added = []
    for table in sorted(tables):
        glottocode = Path(table).stem
        if not is_glottocode(glottocode):
            continue
        try:
            if append_language_from_glottolog(glottocode, opener=opener):
                added.append(glottocode)
        except ValueError as error:
            print(f'Не удалось добавить язык для {table}: {error}')
    return added


def load_existing_groups():
    existing_groups = {}
    for line in read_csv_rows(data_path('groups.csv'))[1:]:
        if len(line) < 4:
            continue
        group_id = int(line[0])
        language_id = int(line[1])
        frame_id = int(line[2])
        term = line[3].strip()
        if term:
            existing_groups[(language_id, term)] = (group_id, frame_id)
    return existing_groups


def load_existing_lexemes():
    existing_lexemes = {}
    for line in read_csv_rows(data_path('lexemes.csv'))[1:]:
        if len(line) < 4:
            continue
        lexeme_id = int(line[0])
        group_id = int(line[1])
        lexeme = line[2].strip()
        russian = line[3].strip()
        existing_lexemes[(group_id, lexeme, russian)] = lexeme_id
    return existing_lexemes


def load_existing_lexeme_meanings():
    existing_lexeme_meanings = set()
    for line in read_csv_rows(data_path('lexeme_meaning.csv'))[1:]:
        if len(line) < 2:
            continue
        existing_lexeme_meanings.add((int(line[0]), int(line[1])))
    return existing_lexeme_meanings


def get_table_language_id(
    table: str,
    language_ids: dict[str, int],
    duplicate_language_ids: dict[str, list[int]] | None = None,
) -> int:
    glottocode = Path(table).stem
    duplicate_language_ids = duplicate_language_ids or {}
    if glottocode in duplicate_language_ids:
        language_ids_list = ', '.join(map(str, duplicate_language_ids[glottocode]))
        raise ValueError(
            f'Glottocode {glottocode} неоднозначен: он указан для языков '
            f'с language_id {language_ids_list}'
        )
    if glottocode not in language_ids:
        raise ValueError(
            'В таблице languages.csv нет языка, у которого '
            f'Glottocode равен {glottocode}'
        )
    return language_ids[glottocode]


def load_concepts():
    with open(BASE_DIR / 'conceptset.json', 'rt', encoding='utf-8') as f:
        concepts = json.load(f)['conceptset_labels']
    return {int(v[0]): v[1] for v in concepts.values()}


def load_frames_concepticon():
    with open(data_path('frames_concepticon.csv'), 'rt', encoding='utf-8') as f:
        frames_concepticon = {}
        for line in list(csv.reader(f))[1:]:
            frame_id = int(line[0])
            concepticon_id = int(line[1])
            frames_concepticon.setdefault(concepticon_id, frame_id)
    return frames_concepticon


def load_state():
    prev_frames = read_csv_rows(data_path('frames.csv'))
    prev_groups = read_csv_rows(data_path('groups.csv'))
    prev_lexemes = read_csv_rows(data_path('lexemes.csv'))
    frame_ids = [int(frame[0]) for frame in prev_frames[1:] if frame and frame[0]]
    group_ids = [int(group[0]) for group in prev_groups[1:] if group and group[0]]
    lexeme_ids = [int(lexeme[0]) for lexeme in prev_lexemes[1:] if lexeme and lexeme[0]]
    return {
        'frames': {frame[1]: int(frame[0]) for frame in prev_frames[1:]},
        'frames_concepticon': load_frames_concepticon(),
        'existing_groups': load_existing_groups(),
        'existing_lexemes': load_existing_lexemes(),
        'existing_lexeme_meanings': load_existing_lexeme_meanings(),
        'groups': {},
        'lexemes': [],
        'lexeme_meaning': [],
        'next_frame_id': max(frame_ids, default=0) + 1,
        'next_group_id': max(group_ids, default=0) + 1,
        'next_lexeme_id': max(lexeme_ids, default=0) + 1,
    }


def get_column_ids(header: list[str], table: str):
    normalized_header = {
        normalize_column_name(column): index
        for index, column in enumerate(header)
    }
    meanings = [
        'перф.EP', 'перф.EMP', 'перф.ES', 'перф.Q', 'перф.P', 'перф.P2', 'перф.MP', 'перф.S',
        'имперф.P', 'имперф.P2', 'имперф.MP', 'имперф.S',
    ]
    required_columns = ['Фрейм', 'Значение', 'Форма']
    missing_columns = [column for column in required_columns if column not in normalized_header]
    if missing_columns:
        print(
            f'Пропускаю {table}, так как в ней нет обязательных колонок '
            f'{", ".join(missing_columns)}'
        )
        return None

    return {
        'frame': normalized_header['Фрейм'],
        'russian': normalized_header['Значение'],
        'term': normalized_header.get('А-группа'),
        'lexeme': normalized_header['Форма'],
        'meanings': [
            (meaning_id, normalized_header[meaning])
            for meaning_id, meaning in enumerate(meanings)
            if meaning in normalized_header
        ],
    }


def normalize_column_name(column: str) -> str:
    return re.sub(r'\s*\.\s*', '.', column.strip())


def get_row_term(row: list[str], columns: dict) -> str:
    if columns['term'] is not None:
        term = row[columns['term']].strip()
        if term:
            return term
    return row[columns['lexeme']].strip()


def get_or_create_frame_id(state: dict, frame: str, concepticon_ids: list[int]) -> int:
    for concepticon_id in concepticon_ids:
        frame_id = state['frames_concepticon'].get(concepticon_id)
        if frame_id is not None:
            for linked_concepticon_id in concepticon_ids:
                state['frames_concepticon'].setdefault(linked_concepticon_id, frame_id)
            return frame_id

    frame_id = state['frames'].get(frame)
    if frame_id is None:
        frame_id = state['next_frame_id']
        state['frames'][frame] = frame_id
        state['next_frame_id'] += 1
    for concepticon_id in concepticon_ids:
        state['frames_concepticon'].setdefault(concepticon_id, frame_id)
    return frame_id


def get_or_create_group_id(state: dict, frame_id: int, term: str, language_id: int) -> int:
    group_key = (language_id, term)
    if group_key in state['existing_groups']:
        return state['existing_groups'][group_key][0]
    if group_key not in state['groups']:
        group_id = state['next_group_id']
        state['groups'][group_key] = (group_id, frame_id)
        state['next_group_id'] += 1
    return state['groups'][group_key][0]


def append_lexeme(state: dict, row: list[str], columns: dict, group_id: int):
    lexeme = row[columns['lexeme']].strip()
    russian = row[columns['russian']].strip()
    lexeme_key = (group_id, lexeme, russian)
    if lexeme_key in state['existing_lexemes']:
        lexeme_id = state['existing_lexemes'][lexeme_key]
        created = False
    else:
        lexeme_id = state['next_lexeme_id']
        state['lexemes'].append((lexeme_id, group_id, lexeme, russian))
        state['existing_lexemes'][lexeme_key] = lexeme_id
        state['next_lexeme_id'] += 1
        created = True

    for meaning_id, column_id in columns['meanings']:
        lexeme_meaning_key = (lexeme_id, meaning_id)
        if row[column_id] == '1' and lexeme_meaning_key not in state['existing_lexeme_meanings']:
            state['lexeme_meaning'].append((lexeme_id, meaning_id))
            state['existing_lexeme_meanings'].add(lexeme_meaning_key)

    return created


def write_frames(frames: dict[str, int]):
    with open(data_path('frames.csv'), 'wt', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['frame_id', 'frame'])
        for frame, frame_id in frames.items():
            writer.writerow([frame_id, frame])


def write_frames_concepticon(frames_concepticon: dict[int, int], concepts: dict[int, str]):
    with open(data_path('frames_concepticon.csv'), 'wt', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['frame_id', 'concepticon_id', 'concepticon'])
        for concepticon_id, frame_id in frames_concepticon.items():
            writer.writerow([frame_id, concepticon_id, concepts[concepticon_id]])


def append_groups(groups: dict[tuple[int, str], tuple[int, int]]):
    with open(data_path('groups.csv'), 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for (language_id, term), (group_id, frame_id) in groups.items():
            if not term:
                continue
            writer.writerow([group_id, language_id, frame_id, term])


def append_lexemes(lexemes: list[tuple[int, int, str, str]]):
    with open(data_path('lexemes.csv'), 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for lexeme_id, group_id, lexeme, russian in lexemes:
            writer.writerow([lexeme_id, group_id, lexeme, russian])


def append_lexeme_meaning(lexeme_meaning: list[tuple[int, int]]):
    with open(data_path('lexeme_meaning.csv'), 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        for lexeme_id, meaning_id in lexeme_meaning:
            writer.writerow([lexeme_id, meaning_id])


def add_language(table: str, language_id: int):
    data = read_csv_rows(table)
    if not data:
        print(f'Пропускаю {table}, так как таблица пуста')
        return False

    concepts = load_concepts()
    state = load_state()
    columns = get_column_ids(data[0], table)
    if columns is None:
        return False

    for row in data[1:]:
        frame_value = row[columns['frame']]
        if not frame_value or frame_value == '0':
            continue
        term = get_row_term(row, columns)
        if not term:
            continue
        concepticon_ids = list(map(int, frame_value.split(',')))
        frame = concepts[concepticon_ids[0]]
        frame_id = get_or_create_frame_id(state, frame, concepticon_ids)
        group_id = get_or_create_group_id(state, frame_id, term, language_id)
        append_lexeme(state, row, columns, group_id)

    write_frames(state['frames'])
    write_frames_concepticon(state['frames_concepticon'], concepts)
    append_groups(state['groups'])
    append_lexemes(state['lexemes'])
    append_lexeme_meaning(state['lexeme_meaning'])


def main():
    added_languages = ensure_languages_for_tables(TABLES_DIR.glob('*.csv'))
    for glottocode in added_languages:
        print(f'Добавлен язык из Glottolog: {glottocode}')

    language_ids, duplicate_language_ids = load_language_ids()

    for table in sorted(TABLES_DIR.glob('*.csv')):
        try:
            language_id = get_table_language_id(
                str(table),
                language_ids,
                duplicate_language_ids,
            )
        except ValueError as error:
            print(f'Пропускаю {table}: {error}')
            continue
        add_language(str(table), language_id)


if __name__ == '__main__':
    main()
