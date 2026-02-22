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

#-----------------------------------------------------------------------------
# specialized common mapper classes
#-----------------------------------------------------------------------------

@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, common.Language):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
    family_name = Column(String)
    family_level_id = Column(String)

class Frame(Base):
    __tablename__ = 'frame'
    id = Column(String, primary_key=True)
    name = Column(String)   # the frame description

class Group(Base):
    __tablename__ = 'group'
    id = Column(String, primary_key=True)
    # Foreign keys to Variety and Frame:
    variety_pk = Column(Integer, ForeignKey('variety.pk'))   # note: uses the custom model's pk
    frame_pk = Column(Integer, ForeignKey('frame.pk'))
    term = Column(String)
    # Relationships for easy navigation
    variety = relationship('Variety')
    frame = relationship('Frame')

class Lexeme(Base):
    __tablename__ = 'lexeme'
    id = Column(String, primary_key=True)
    group_pk = Column(Integer, ForeignKey('group.pk'))
    lexeme = Column(String)
    group = relationship('Group')

class Meaning(Base):
    __tablename__ = 'meaning'
    id = Column(String, primary_key=True)
    name = Column(String)   # the meaning description

# Many‑to‑many association table
lexeme_meaning = Table(
    'lexeme_meaning',
    Base.metadata,
    Column('lexeme_pk', Integer, ForeignKey('lexeme.pk')),
    Column('meaning_pk', Integer, ForeignKey('meaning.pk'))
)
