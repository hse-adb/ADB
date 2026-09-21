from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy import and_, func, distinct, cast, Integer
from clld.web.datatables.base import DataTable, Col
from clld.web.util.helpers import link
from clld.web.util.htmllib import HTML, literal
from clld.web.datatables.language import Languages as CLLDLanguages
from clld.web.datatables.value import Values as CLLDValues
from clld.web.datatables.source import Sources as CLLDSources
from urllib.parse import (
    urljoin,
    urlsplit,
    urlunsplit,
)
import posixpath

from ADB import models
from ADB.helpers import collect_group_meanings, format_group_meanings, format_meanings
from clld.db.meta import DBSession


class StaticDataTableMixin(DataTable):
    """
    When ?static=1 is present, turn the normal CLLD server-side
    DataTable into a client-side DataTable containing every row.
    """

    def _static_source_dir(self):
        """
        Directory corresponding to the public URL of the current page.

        /frames          -> /frames
        /frames/1        -> /frames/1
        /                -> /
        """
        path = self.req.path.rstrip("/")
        return path or "/"

    def _staticize_url(self, value):
        """
        Convert an internal application URL into a relative static-site URL.

        External URLs are preserved.

        Examples on /frames:

            https://example.org/frames/1
                -> 1/

            /languages/1
                -> ../languages/1/

        """
        if not value:
            return value

        # Fragment-only links such as #map must remain unchanged.
        if value.startswith("#"):
            return value

        application_url = self.req.application_url.rstrip("/")

        absolute = urljoin(
            application_url + "/",
            value,
        )

        parsed = urlsplit(absolute)
        app = urlsplit(application_url)

        # Don't rewrite external URLs.
        if (
            parsed.scheme != app.scheme
            or parsed.netloc != app.netloc
        ):
            return value

        source_dir = self._static_source_dir()

        target_path = parsed.path or "/"

        # A URL without a file extension is an HTML page.
        # Represent it as a directory URL in the static site.
        is_page = not posixpath.splitext(
            posixpath.basename(target_path)
        )[1]

        if is_page:
            target_dir = target_path.rstrip("/") or "/"

            if target_dir == "/":
                rel = posixpath.relpath(
                    "/",
                    start=source_dir,
                )
            else:
                rel = posixpath.relpath(
                    target_dir,
                    start=source_dir,
                )

            if rel == ".":
                rel = "."

            rel += "/" if not rel.endswith("/") else ""

            result = rel

        else:
            result = posixpath.relpath(
                target_path,
                start=source_dir,
            )

        if parsed.query:
            result += "?" + parsed.query

        if parsed.fragment:
            result += "#" + parsed.fragment

        return result

    def _staticize_html(self, value):
        """
        Rewrite href/src attributes inside a DataTable cell
        or column title.
        """
        if not value:
            return value

        text = str(value)

        if (
            "<" not in text
            or "href" not in text and "src" not in text
        ):
            return value
        
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(
            text,
            "html.parser",
        )

        for tag in soup.find_all(True):
            for attr in ("href", "src"):
                if not tag.has_attr(attr):
                    continue

                tag[attr] = self._staticize_url(
                    tag[attr]
                )

        return str(soup)

    def _staticize_options(self, value, key=None):
        """
        Recursively rewrite HTML strings in the DataTable
        JavaScript configuration.
        """
        if key == "aaData":
            return value
        
        if isinstance(value, dict):
            return {
                key: self._staticize_options(val, key=key)
                for key, val in value.items()
            }

        if isinstance(value, list):
            return [
                self._staticize_options(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return tuple(
                self._staticize_options(item)
                for item in value
            )

        if isinstance(value, str):
            return self._staticize_html(value)

        return value

    def get_default_options(self):
        options = super().get_default_options()

        if self.req.params.get("static") != "1":
            return options

        # Get ALL active records, applying the table's normal
        # base_query() so joins, eager loading and constraints
        # defined by the concrete DataTable are preserved.
        query = self.base_query(
            DBSession.query(self.db_model())
            .filter(self.db_model().active == True)
        )

        # Reproduce the ordering that the server-side DataTable would use.
        query = query.order_by(*(
            self.default_order()
            if isinstance(self.default_order(), (tuple, list))
            else (self.default_order(),)
        ))

        items = query.all()

        # DataTables' old API expects aaData to be an array
        # of rows, with one value per column.
        data = [
            [self._staticize_html(col.format(item)) for col in self.cols]
            for item in items
        ]

        # Switch from server-side to client-side processing.
        options["bServerSide"] = False
        options["bProcessing"] = False
        options["aaData"] = data
        options.pop("sAjaxSource", None)

        # This also fixes links embedded in column titles,
        # such as the language names in the Frames table.
        options = self._staticize_options(options)

        return options


class IntegerIdCol(Col):
    def order(self):
        return cast(self.model_col, Integer)


class Frames(StaticDataTableMixin, DataTable):
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
            by_language.setdefault(group.variety_pk, []).append(collect_group_meanings(group))

        formatted = {
            lang_pk: format_group_meanings(group_meanings)
            for lang_pk, group_meanings in by_language.items()
        }
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
                sTitle=str(link(dt.req, language, label=language.name)),
                model_col=None,
                input_size='mini',
            )

        def format(self, item):
            value = self.dt._frame_values(item).get(self.language.pk, "")
            if not value:
                return literal("&mdash;")
            if value == "&mdash;":
                return literal(value)
            return HTML.a(
                literal(value),
                href=self.dt.req.route_url(
                    'frame_language',
                    id=item.id,
                    language=self.language.id,
                ),
            )

    def base_query(self, query):
        return (
            query
            .outerjoin(models.Group, models.Group.frame_pk == models.Frame.pk)
            .group_by(models.Frame.pk)
            .options(
                subqueryload(models.Frame.groups)
                .subqueryload(models.Group.lexemes)
                .subqueryload(models.Lexeme.meanings)
            )
        )

    def get_options(self):
        return {'aaSorting': [[2, 'desc']]}

    def col_defs(self):
        cols = [
            IntegerIdCol(
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
                model_col=None,
                format=lambda item: self._n_languages(item),
            ),
        ]
        cols.extend(self.FrameLanguageCol(self, language) for language in self.languages)
        return cols


class Languagegroups(StaticDataTableMixin, DataTable):
    __constraints__ = [models.Variety]

    def _group_values(self, group):
        return format_meanings(collect_group_meanings(group).values())

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
            IntegerIdCol(
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
                format=lambda item: HTML.a(
                    item.frame.frame,
                    href=self.req.route_url(
                        'frame_language',
                        id=item.frame.id,
                        language=item.variety.id,
                    ),
                ),
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


class StaticLanguages(StaticDataTableMixin, CLLDLanguages):
    pass
class StaticValues(StaticDataTableMixin, CLLDValues):
    pass
class StaticSources(StaticDataTableMixin, CLLDSources):
    pass


def includeme(config):
    config.register_datatable('frames', Frames)
    config.register_datatable('groups', Languagegroups)
    config.register_datatable('languages', StaticLanguages)
    config.register_datatable('values', StaticValues)
    config.register_datatable('sources', StaticSources)
