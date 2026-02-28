from sqlalchemy.orm import joinedload
from clld.web.datatables.base import DataTable, IdCol, LinkCol, Col
from clld.web.util.helpers import link

from ADB import models


class Frames(DataTable):
    def base_query(self, query):
        return query.options(joinedload(models.Frame.groups))

    def col_defs(self):
        return [
            IdCol(self, 'id'),
            LinkCol(self, 'name'),
            Col(
                self,
                'n_languages',
                sTitle='N languages',
                sortable=False,
                model_col=None,
                format=lambda item: len({group.variety_pk for group in item.groups}),
            ),
        ]


class Languagegroups(DataTable):
    __constraints__ = [models.Variety]

    @staticmethod
    def _id_sort_key(value):
        try:
            return (0, int(value))
        except (TypeError, ValueError):
            return (1, str(value))

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
            LinkCol(
                self,
                'frame',
                sTitle='Frame',
                model_col=models.Frame.name,
                get_object=lambda item: item.frame,
            ),
            Col(
                self,
                'agroup',
                sTitle='A-group',
                model_col=models.Group.term,
                format=lambda item: link(self.req, item, label=item.term),
            ),
            Col(
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
