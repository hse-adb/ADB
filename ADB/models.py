from zope.interface import implementer
from sqlalchemy import (
    Column,
    String,
    Unicode,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    Table
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property

from clld import interfaces
from clld.db.meta import Base, CustomModelMixin
from clld.db.models import common

from ADB import interfaces as adb_interfaces

#-----------------------------------------------------------------------------
# specialized common mapper classes
#-----------------------------------------------------------------------------

@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, common.Language):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
    glottocode = Column(Unicode)
    family_name = Column(String)
    family_level_id = Column(String)

@implementer(adb_interfaces.IFrame)
class Frame(Base):
    __tablename__ = 'frame'
    id = Column(String, unique=True, nullable=False)
    name = Column(String)

@implementer(adb_interfaces.IGroup)
class Group(Base):
    __tablename__ = 'group'
    id = Column(String, unique=True, nullable=False)
    variety_pk = Column(Integer, ForeignKey('variety.pk'))
    frame_pk = Column(Integer, ForeignKey('frame.pk'))
    term = Column(String)
    variety = relationship('Variety')
    frame = relationship('Frame', backref=backref('groups'))

    @hybrid_property
    def name(self):
        return self.term

class Lexeme(Base):
    __tablename__ = 'lexeme'
    id = Column(String, unique=True, nullable=False)
    group_pk = Column(Integer, ForeignKey('group.pk'))
    lexeme = Column(String)
    russian = Column(String)
    group = relationship('Group', backref=backref('lexemes'))
    meanings = relationship('Meaning', secondary='lexeme_meaning', backref=backref('lexemes'))

class Meaning(Base):
    __tablename__ = 'meaning'
    id = Column(String, unique=True, nullable=False)
    order = Column(Integer)
    name = Column(String)

lexeme_meaning = Table(
    'lexeme_meaning',
    Base.metadata,
    Column('lexeme_pk', Integer, ForeignKey('lexeme.pk')),
    Column('meaning_pk', Integer, ForeignKey('meaning.pk'))
)
