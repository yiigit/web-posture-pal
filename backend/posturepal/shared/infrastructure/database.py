"""Portable SQLAlchemy connections and schema for MySQL and isolated SQLite tests."""
import os
import re
from collections.abc import Mapping
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import (BigInteger, Column, ForeignKey, Index, Integer, MetaData,
                        String, Table, Text, create_engine, event, text)
from sqlalchemy.engine import URL
from sqlalchemy.pool import NullPool
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

schema = MetaData()


def table(name, *columns):
    return Table(name, schema, *columns, mysql_engine='InnoDB', mysql_charset='utf8mb4', mysql_collate='utf8mb4_unicode_ci')


def string(name, length=36, primary=False, default=None):
    return Column(name, String(length), primary_key=primary, nullable=False, server_default=default)


def user_ref(name='user_id', primary=False):
    return Column(name, String(36), ForeignKey('users.id', ondelete='CASCADE'), primary_key=primary, nullable=False)


def post_ref(primary=False):
    return Column('post_id', String(36), ForeignKey('social_posts.id', ondelete='CASCADE'), primary_key=primary, nullable=False)


def number(name, default=None):
    return Column(name, BigInteger, nullable=False, server_default=default)


metadata_table = table('metadata', string('key', 64, True))
locks = table('application_locks', string('name', 64, True))
table('exercises', string('id',80,True), string('name',100), string('area',32), number('duration'),
      Column('description',Text,nullable=False), Column('steps',Text,nullable=False), string('position',32), string('symbol',32))
table('users', string('id',36,True), Column('email',String(254),unique=True,nullable=False),
      string('display_name',100), Column('bio',Text,nullable=False), string('timezone',100,default='UTC'),
      string('theme',16,default='light'), string('role',16,default='member'), number('active','1'),
      number('created_at'), string('password_hash',256))
table('user_sessions', string('digest',64,True), user_ref(), number('expires_at'))
table('auth_attempts', string('key',255,True), number('count'), number('expires_at'))
table('social_settings', user_ref(primary=True), number('accept_requests','1'),number('sharing_enabled','1'),
      string('default_audience',16,default='private'),number('allow_comments','1'))
table('friendships',user_ref('sender',True),user_ref('recipient',True),string('status',16),number('created_at'))
table('social_blocks',user_ref('blocker',True),user_ref('blocked',True))
posts=table('social_posts',string('id',36,True),user_ref(),string('kind',16),Column('text',Text,nullable=False),string('audience',16),number('created_at'))
table('social_likes',post_ref(True),user_ref(primary=True))
comments=table('social_comments',string('id',36,True),post_ref(),user_ref(),Column('text',Text,nullable=False),number('created_at'))
table('daily_activity',user_ref(primary=True),string('day',10,True),Column('habits',Text,nullable=False),number('breaks','0'))
table('daily_break_events',user_ref(primary=True),string('event_id',36,True),string('day',10))

Index('social_posts_created',posts.c.created_at)
Index('social_comments_post',comments.c.post_id)


class Record(dict):
    """Named records with positional access for scalar and legacy repository reads."""
    def __getitem__(self, key):
        return tuple(self.values())[key] if isinstance(key,(int,slice)) else super().__getitem__(key)


class Result:
    def __init__(self,result):
        self.result=result
        self.rowcount=result.rowcount

    def fetchone(self):
        row=self.result.mappings().fetchone()
        return Record(row) if row is not None else None

    def fetchall(self):
        return [Record(row) for row in self.result.mappings().fetchall()]


class Transaction:
    def __init__(self,connection):
        self.connection=connection

    def execute(self,sql,parameters=()):
        # Compile positional repository parameters to SQLAlchemy named bindings.
        # SQLAlchemy handles the driver's escaping/placeholder syntax, never string interpolation.
        if isinstance(parameters,Mapping):
            return Result(self.connection.execute(text(sql),parameters))
        index=0
        def bind(match):
            nonlocal index
            position=int(match[1])-1 if match[1] else index
            if not match[1]: index+=1
            return f':p{position}'
        statement=re.sub(r'\?(\d+)?',bind,sql)
        return Result(self.connection.execute(text(statement),{f'p{i}':value for i,value in enumerate(parameters)}))

    def lock(self):
        if self.connection.dialect.name=='sqlite':
            self.connection.exec_driver_sql('BEGIN IMMEDIATE')
        else:
            self.connection.execute(text("SELECT name FROM application_locks WHERE name='global' FOR UPDATE"))

    def insert_once(self,table_name,data):
        target=schema.tables[table_name]
        if self.connection.dialect.name=='mysql':
            statement=mysql_insert(target).values(**data).prefix_with('IGNORE')
        else:
            statement=sqlite_insert(target).values(**data).on_conflict_do_nothing()
        return self.connection.execute(statement)


class Database:
    def __init__(self,url):
        options={'pool_pre_ping':True,'pool_recycle':1800,'hide_parameters':True}
        if str(url).startswith('sqlite'):
            options['connect_args']={'check_same_thread':False,'timeout':10}
            options['poolclass']=NullPool
        self.engine=create_engine(url,**options)
        if self.engine.dialect.name=='sqlite':
            @event.listens_for(self.engine,'connect')
            def foreign_keys(dbapi_connection,record):
                dbapi_connection.execute('PRAGMA foreign_keys=ON')
        schema.create_all(self.engine)
        with self.connection() as db:
            db.insert_once('application_locks',{'name':'global'})

    @classmethod
    def from_path(cls,path):
        path=Path(path)
        path.parent.mkdir(parents=True,exist_ok=True)
        return cls(URL.create('sqlite',database=str(path)))

    @classmethod
    def configured(cls):
        if os.getenv('POSTUREPAL_DATABASE_URL'):
            return cls(os.environ['POSTUREPAL_DATABASE_URL'])
        if os.getenv('MYSQL_PASSWORD'):
            return cls(URL.create('mysql+pymysql',username=os.getenv('MYSQL_USER','posturepal'),password=os.environ['MYSQL_PASSWORD'],
                                  host=os.getenv('MYSQL_HOST','mysql'),port=int(os.getenv('MYSQL_PORT','3306')),
                                  database=os.getenv('MYSQL_DATABASE','posturepal'),query={'charset':'utf8mb4'}))
        return cls.from_path(os.getenv('POSTUREPAL_DB_PATH','data/posturepal.db'))

    @contextmanager
    def connection(self):
        with self.engine.begin() as connection:
            yield Transaction(connection)
