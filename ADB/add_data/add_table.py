import csv
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'
TABLES_DIR = BASE_DIR / 'tables'


def data_path(filename: str) -> Path:
    return DATA_DIR / filename


def read_csv_rows(path: str | Path):
    with open(path, 'rt', encoding='utf-8') as f:
        return list(csv.reader(f))


def load_language_ids():
    language_ids = {}
    for line in read_csv_rows(data_path('languages.csv'))[1:]:
        language_ids[line[6]] = int(line[0])
    return language_ids


def load_existing_terms():
    existing_terms = set()
    for line in read_csv_rows(data_path('groups.csv'))[1:]:
        if len(line) < 4:
            continue
        language_id = int(line[1])
        term = line[3].strip()
        if term:
            existing_terms.add((language_id, term))
    return existing_terms


def get_table_language_id(table: str, language_ids: dict[str, int]) -> int:
    language_code = Path(table).stem
    if language_code not in language_ids:
        raise ValueError(f'В таблице languages.csv нет языка, у которого ISO639P3code равен {language_code}')
    return language_ids[language_code]


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
        'groups': {},
        'lexemes': [],
        'lexeme_meaning': [],
        'next_frame_id': max(frame_ids, default=0) + 1,
        'next_group_id': max(group_ids, default=0) + 1,
        'next_lexeme_id': max(lexeme_ids, default=0) + 1,
    }


def get_column_ids(header: list[str], table: str):
    meanings = [
        'перф.EP', 'перф.EMP', 'перф.ES', 'перф.Q', 'перф.P', 'перф.P2', 'перф.MP', 'перф.S',
        'имперф.P', 'имперф.P2', 'имперф.MP', 'имперф.S',
    ]
    required_columns = ['Фрейм', 'Значение', 'Форма']
    missing_columns = [column for column in required_columns if column not in header]
    if missing_columns:
        print(f'Пропускаю {table}, так как в ней нет обязательных колонок {", ".join(missing_columns)}')
        return None

    return {
        'frame': header.index('Фрейм'),
        'russian': header.index('Значение'),
        'term': header.index('А-группа') if 'А-группа' in header else None,
        'lexeme': header.index('Форма'),
        'meanings': [(meaning_id, header.index(meaning)) for meaning_id, meaning in enumerate(meanings) if meaning in header],
    }


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
    if group_key not in state['groups']:
        group_id = state['next_group_id']
        state['groups'][group_key] = (group_id, frame_id)
        state['next_group_id'] += 1
    return state['groups'][group_key][0]


def append_lexeme(state: dict, row: list[str], columns: dict, group_id: int):
    lexeme_id = state['next_lexeme_id']
    lexeme = row[columns['lexeme']].strip()
    russian = row[columns['russian']].split()[0].split(',')[0]

    state['lexemes'].append((lexeme_id, group_id, lexeme, russian))

    for meaning_id, column_id in columns['meanings']:
        if row[column_id] == '1':
            state['lexeme_meaning'].append((lexeme_id, meaning_id))

    state['next_lexeme_id'] += 1


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

    existing_terms = load_existing_terms()

    for row in data[1:]:
        frame_value = row[columns['frame']]
        if not frame_value or frame_value == '0':
            continue
        term = get_row_term(row, columns)
        if not term:
            continue
        row_key = (language_id, term)
        if row_key in existing_terms:
            continue
        concepticon_ids = list(map(int, frame_value.split(',')))
        frame = concepts[concepticon_ids[0]]
        frame_id = get_or_create_frame_id(state, frame, concepticon_ids)
        group_id = get_or_create_group_id(state, frame_id, term, language_id)
        append_lexeme(state, row, columns, group_id)
        existing_terms.add(row_key)

    write_frames(state['frames'])
    write_frames_concepticon(state['frames_concepticon'], concepts)
    append_groups(state['groups'])
    append_lexemes(state['lexemes'])
    append_lexeme_meaning(state['lexeme_meaning'])


def main():
    language_ids = load_language_ids()

    for table in sorted(TABLES_DIR.glob('*.csv')):
        try:
            language_id = get_table_language_id(str(table), language_ids)
        except ValueError as error:
            print(f'Пропускаю {table}: {error}')
            continue
        add_language(str(table), language_id)


if __name__ == '__main__':
    main()
