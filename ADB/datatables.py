from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy import and_, func, distinct
from clld.web.datatables.base import DataTable, Col
from clld.web.util.helpers import link
from clld.web.util.htmllib import HTML, literal

from ADB import models
from clld.db.meta import DBSession


class Frames(DataTable):
    @staticmethod
    def _id_sort_key(value):
        try:
            return 0, int(value)
        except (TypeError, ValueError):
            return 1, str(value)

    def _fmt_values(self, meaning_objs):
        if not meaning_objs:
            return "&lt;&gt;"
        ordered = sorted(meaning_objs, key=lambda item: self._id_sort_key(item.id))
        left = [m.name for m in ordered if m.order == 1]
        right = [m.name for m in ordered if m.order == 2]
        return "&lt;{}, {}&gt;".format(" ".join(left), " ".join(right))

    @property
    def languages(self):
        if not hasattr(self, '_languages'):
            self._languages = DBSession.query(models.Variety).order_by(models.Variety.name).all()
        return self._languages

    def _frame_values(self, frame):
        if not hasattr(self, '_frame_values_cache'):
            self._frame_values_cache = {}
        if frame.pk in self._frame_values_cache:
            return self._frame_values_cache[frame.pk]

        by_language = {}
        for group in frame.groups:
            lang_map = by_language.setdefault(group.variety_pk, {})
            for lex in group.lexemes:
                for meaning in lex.meanings:
                    lang_map[meaning.pk] = meaning

        formatted = {lang_pk: self._fmt_values(meanings.values()) for lang_pk, meanings in by_language.items()}
        self._frame_values_cache[frame.pk] = formatted
        return formatted

    def _n_languages(self, frame):
        return len(self._frame_values(frame))

    class NLanguagesCol(Col):
        def order(self):
            return func.count(distinct(models.Group.variety_pk))

    class FrameLanguageCol(Col):
        __kw__ = {'bSortable': False}

        def __init__(self, dt, language):
            self.language = language
            super().__init__(
                dt,
                'lang_{}'.format(language.id),
                sTitle=language.name,
                model_col=None,
                input_size='mini',
            )

        def format(self, item):
            value = self.dt._frame_values(item).get(self.language.pk, "&lt;&gt;")
            return HTML.a(
                literal(value),
                href=self.dt.req.route_url('frame', id=item.id, _query={'language': self.language.id}),
            )

    def base_query(self, query):
        return query.outerjoin(models.Group, models.Group.frame_pk == models.Frame.pk)\
            .group_by(models.Frame.pk)\
            .options(
                subqueryload(models.Frame.groups)
                .subqueryload(models.Group.lexemes)
                .subqueryload(models.Lexeme.meanings)
            )

    def get_options(self):
        return {'aaSorting': [[2, 'desc']]}

    def col_defs(self):
        cols = [
            Col(
                self,
                'frame_id',
                sTitle='Id',
                model_col=models.Frame.id,
                input_size='mini',
                format=lambda item: item.id,
            ),
            Col(
                self,
                'frame',
                sTitle='Frame',
                model_col=models.Frame.frame,
                format=lambda item: link(self.req, item, label=item.frame),
            ),
            self.NLanguagesCol(
                self,
                'n_languages',
                sTitle='N languages',
                bSearchable=False,
                bVisible=False,
                model_col=None,
                format=lambda item: self._n_languages(item),
            ),
        ]
        cols.extend(self.FrameLanguageCol(self, language) for language in self.languages)
        return cols


class Languagegroups(DataTable):
    __constraints__ = [models.Variety]

    @staticmethod
    def _id_sort_key(value):
        try:
            return 0, int(value)
        except (TypeError, ValueError):
            return 1, str(value)

    def _fmt_values(self, meaning_objs):
        if not meaning_objs:
            return "&lt;&gt;"
        ordered = sorted(meaning_objs, key=lambda item: self._id_sort_key(item.id))
        left = [m.name for m in ordered if m.order == 1]
        right = [m.name for m in ordered if m.order == 2]
        return "&lt;{}, {}&gt;".format(" ".join(left), " ".join(right))

    def _group_values(self, group):
        by_pk = {}
        for lex in group.lexemes:
            for meaning in lex.meanings:
                by_pk[meaning.pk] = meaning
        return self._fmt_values(by_pk.values())

    class AClassCol(Col):
        def search(self, qs):
            normalized = (qs or '').replace('<', ' ').replace('>', ' ').replace(',', ' ')
            tokens = [t.strip() for t in normalized.split() if t.strip()]
            if not tokens:
                return None
            return and_(*[
                models.Group.lexemes.any(
                    models.Lexeme.meanings.any(models.Meaning.name.ilike('%{}%'.format(token)))
                ) for token in tokens
            ])

    def base_query(self, query):
        query = query.join(models.Frame).options(
            joinedload(models.Group.frame),
            joinedload(models.Group.lexemes).joinedload(models.Lexeme.meanings),
        )
        if self.variety:
            query = query.filter(models.Group.variety_pk == self.variety.pk)
        return query

    def col_defs(self):
        return [
            Col(
                self,
                'frame_id',
                sTitle='Id',
                input_size='mini',
                model_col=models.Frame.id,
                format=lambda item: item.frame.id,
            ),
            Col(
                self,
                'frame',
                sTitle='Frame',
                model_col=models.Frame.frame,
                format=lambda item: link(self.req, item.frame, label=item.frame.frame),
            ),
            Col(
                self,
                'agroup',
                sTitle='A-group',
                model_col=models.Group.term,
                format=lambda item: link(self.req, item, label=item.term),
            ),
            self.AClassCol(
                self,
                'aclass',
                sTitle='A-class',
                sortable=False,
                model_col=None,
                format=lambda item: self._group_values(item),
            ),
        ]


def includeme(config):
    config.register_datatable('frames', Frames)
    config.register_datatable('groups', Languagegroups)
