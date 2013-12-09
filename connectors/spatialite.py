# -*- coding: utf-8 -*-
"""
SpatiaLite Manager
Copyright 2010 by Giuseppe Sucameli (Faunalia) and Alessandro Furieri

based on PostGIS Manager
Copyright 2008 Martin Dobias

Licensed under the terms of GNU GPL v2 (or any layer)
http://www.gnu.org/copyleft/gpl.html
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import qgis.core

from pyspatialite import dbapi2 as sqlite
from .. import DbConnection as DbConn

class TableAttribute(DbConn.TableAttribute):
	def __init__(self, row):
		self.num, self.name, self.data_type, self.notnull, self.default, self.primary_key = row
		self.hasdefault = self.default != None


class TableIndex(DbConn.TableIndex):
	def __init__(self, row):
		self.num, self.name, self.unique, self.columns = row


class TableTrigger(DbConn.TableTrigger):
	def __init__(self, row):
		self.name, self.function = row
		self.enabled = True


class DbError(DbConn.DbError):
	def __init__(self, error, query=None):
		print type(error), dir(error), error, error.args[0]
		msg = unicode( error.args[0], 'utf-8' )
		if query != None:
			query = unicode( query, 'utf-8' )
		DbConn.DbError.__init__(self, msg, query)
		

class TableField(DbConn.TableField):
	def __init__(self, name, data_type, is_null=None, default=None):
		self.name, self.data_type, self.is_null, self.default = name, data_type, is_null, default


class Connection(DbConn.Connection):

	@classmethod
	def getTypeName(self):
		return 'spatialite'

	@classmethod
	def getTypeNameString(self):
		return 'SpatiaLite'

	@classmethod
	def getProviderName(self):
		return 'spatialite'

	@classmethod
	def getSettingsKey(self):
		return 'SpatiaLite'

	@classmethod
	def icon(self):
		return QIcon(":/icons/spatialite_icon.png")

	@classmethod
	def connect(self, selected, parent=None):
		settings = QSettings()
		settings.beginGroup( u"/%s/connections/%s" % (self.getSettingsKey(), selected) )

		if not settings.contains( "sqlitepath" ): # non-existent entry?
			raise DbError( 'there is no defined database connection "%s".' % selected )

		database = unicode(settings.value("sqlitepath"))

		uri = qgis.core.QgsDataSourceURI()
		uri.setDatabase(database)
		return Connection(uri)


	def __init__(self, uri):
		DbConn.Connection.__init__(self, uri)
	
		self.dbname = uri.database()		
		try:
			self.con = sqlite.connect( self.con_info() )
		except sqlite.OperationalError, e:
			raise DbError(e)
		
		self.has_spatial = self.check_spatial()

		# a counter to ensure that the cursor will be unique
		self.last_cursor_id = 0

	def con_info(self):
		return '%s' % self.dbname
		
	def get_info(self):
		c = self.con.cursor()
		self._exec_sql(c, "SELECT sqlite_version()")
		return c.fetchone()[0]
	
	def check_spatial(self):
		""" check if is a valid spatialite db """
		try:
			c = self.con.cursor()
			self._exec_sql(c, "SELECT CheckSpatialMetaData()")
			self.has_geometry_columns = c.fetchone()[0] == 1
		except Exception, e:
			self.has_geometry_columns = False

		self.has_geometry_columns_access = self.has_geometry_columns
		return self.has_geometry_columns
	
	def get_spatial_info(self):
		""" returns tuple about spatialite support:
			- lib version
			- geos version
			- proj version
		"""
		c = self.con.cursor()
		self._exec_sql(c, "SELECT spatialite_version(), NULL, NULL, geos_version(), proj4_version(), NULL")
		return c.fetchone()
					
	def list_geotables(self):
		"""
			get list of tables, whether table has geometry column(s) etc.
			
			geometry_columns:
			- f_table_name
			- f_geometry_column
			- coord_dimension
			- srid
			- type
		"""
		c = self.con.cursor()

		sys_tables = ['sqlite_stat1']
		# get the R*Tree tables
		sql = "SELECT f_table_name, f_geometry_column FROM geometry_columns WHERE spatial_index_enabled = 1"
		self._exec_sql(c, sql)		
		for idx_item in c.fetchall():
			sys_tables.append( 'idx_%s_%s' % idx_item )
			sys_tables.append( 'idx_%s_%s_node' % idx_item )
			sys_tables.append( 'idx_%s_%s_parent' % idx_item )
			sys_tables.append( 'idx_%s_%s_rowid' % idx_item )

		items = []
		# get geometry info from geometry_columns if exists
		if self.has_geometry_columns:
			sql = """SELECT m.name, m.type, g.f_geometry_column, g.type, g.coord_dimension, g.srid 
							FROM sqlite_master AS m LEFT JOIN geometry_columns AS g ON lower(m.name) = lower(g.f_table_name)
							WHERE m.type in ('table', 'view') 
							ORDER BY m.name, g.f_geometry_column"""
		else:
			sql = "SELECT name, type, NULL, NULL, NULL, NULL FROM sqlite_master WHERE type IN ('table', 'view')"

		self._exec_sql(c, sql)

		for geo_item in c.fetchall():
			item = list(geo_item)
			item.append( item[0] in sys_tables )
			items.append( item )
			
		return items
	
	
	def get_table_rows(self, table, schema=None):
		c = self.con.cursor()
		self._exec_sql(c, "SELECT COUNT(*) FROM %s" % self._quote(table) )
		return c.fetchone()[0]
		
		
	def get_table_fields(self, table, schema=None):
		""" return list of columns in table """
		c = self.con.cursor()
		sql = "PRAGMA table_info(%s)" % (self._quote(table))
		self._exec_sql(c, sql)

		attrs = []
		for row in c.fetchall():
			attrs.append( TableAttribute(row) )

		return attrs
		
		
	def get_table_indexes(self, table, schema=None):
		""" get info about table's indexes """
		c = self.con.cursor()
		sql = "PRAGMA index_list(%s)" % (self._quote(table))
		self._exec_sql(c, sql)

		indexes = []
		for num, name, unique in c.fetchall():
			c2 = self.con.cursor()
			sql = "PRAGMA index_info(%s)" % (self._quote(name))
			self._exec_sql(c2, sql)

			row = [num, name, unique]
			cols = []
			for seq, cid, cname in c2.fetchall():
				cols.append(cid)

			row.append(cols)
			indexes.append( TableIndex(row) )

		return indexes
	
	
	def get_table_triggers(self, table, schema=None):
		c = self.con.cursor()
		sql = "SELECT name, sql FROM sqlite_master WHERE tbl_name = %s AND type = 'trigger'" % (self._quote_str(table))
		self._exec_sql(c, sql)
		
		triggers = []
		for row in c.fetchall():
			triggers.append( TableTrigger(row) )

		return triggers

	# TODO get_table_constraints		
	
	def get_table_estimated_extent(self, geom, table, schema=None):
		""" find out estimated extent (from the statistics) """
		c = self.con.cursor()
		sql = """ SELECT Min(MbrMinX(%(geom)s)), Min(MbrMinY(%(geom)s)), Max(MbrMaxX(%(geom)s)), Max(MbrMaxY(%(geom)s)) 
						FROM %(table)s """ % { 'geom' : self._quote(geom), 'table' : self._quote(table) }
		self._exec_sql(c, sql)
		
		row = c.fetchone()
		return row
	
	def get_view_definition(self, view, schema=None):
		""" returns definition of the view """
		sql = "SELECT sql FROM sqlite_master WHERE type = 'view' AND name = %s" % (self._quote_str(view))
		c = self.con.cursor()
		self._exec_sql(c, sql)
		return c.fetchone()[0]
		
	def add_geometry_column(self, table, geom_type, geom_column='the_geom', srid=-1, dim='XY'):
		sql = "SELECT AddGeometryColumn('%s', '%s', %d, '%s', %s)" % (self._quote_str(table), self._quote_str(geom_column), srid, self._quote_str(geom_type), dim)
		self._exec_sql_and_commit(sql)
		
	def delete_geometry_column(self, table, geom_column):
		""" discard a geometry column """
		sql = "SELECT DiscardGeometryColumn('%s', '%s')" % (self._quote_str(table), self._quote_str(geom_column))
		self._exec_sql_and_commit(sql)
		
	def delete_geometry_table(self, table):
		""" delete table with one or more geometries """
		sql = "DROP TABLE %s" % (self._quote(table))
		self._exec_sql_and_commit(sql)
		
	def create_table(self, table, fields, pkey=None):
		""" create ordinary table
				'fields' is array containing instances of TableField
				'pkey' contains name of column to be used as primary key
		"""
				
		if len(fields) == 0:
			return False
		
		table_name = self._quote(table)
		
		sql = "CREATE TABLE %s (%s" % (table_name, fields[0].field_def(self))
		for field in fields[1:]:
			sql += ", %s" % field.field_def(self)
		if pkey:
			sql += ", PRIMARY KEY (%s)" % self._quote(pkey)
		sql += ")"
		self._exec_sql_and_commit(sql)
		return True
	
	def delete_table(self, table):
		""" delete table from the database """
		table_name = self._quote(table)
		sql = "DROP TABLE %s" % table_name
		self._exec_sql_and_commit(sql)
		
	def empty_table(self, table):
		""" delete all rows from table """
		sql = "DELETE FROM %s" % self._quote(table)
		self._exec_sql_and_commit(sql)
		
	def rename_table(self, table, new_table):
		""" rename a table """
		sql = "ALTER TABLE %s RENAME TO %s" % (self._quote(table), self._quote(new_table))
		self._exec_sql_and_commit(sql)
		
		# update geometry_columns
		if self.has_geometry_columns:
			sql = "UPDATE geometry_columns SET f_table_name = %s WHERE f_table_name = %s" % (self._quote_str(new_table), self._quote_str(table))
			self._exec_sql_and_commit(sql)
		
	def create_view(self, name, query):
		sql = "CREATE VIEW %s AS %s" % (self._quote(name), query)
		self._exec_sql_and_commit(sql)
	
	def delete_view(self, name):
		sql = "DROP VIEW %s" % ( self.quote(name) )
		self._exec_sql_and_commit(sql)
	
	def rename_view(self, name, new_name):
		""" rename view """
		self.rename_table(name, new_name)
		
	def table_add_column(self, table, field):
		""" add a column to table (passed as TableField instance) """
		sql = "ALTER TABLE %s ADD %s" % (self.quote(table), field.field_def(self))
		self._exec_sql_and_commit(sql)
	
	def table_delete_trigger(self, trigger):
		""" delete trigger """
		sql = "DROP TRIGGER %s" % (self._quote(trigger))
		self._exec_sql_and_commit(sql)

	def create_index(self, table, name, column, unique=True):
		""" create index on one column """
		unique_str = "UNIQUE" if unique else ""
		sql = "CREATE " + unique_str + " INDEX %s ON %s (%s)" % (self._quote(index), self.quote(table), self._quote(column))
		self._exec_sql_and_commit(sql)
	
	def create_spatial_index(self, table, geom_column='the_geom'):
		table_name = self._quote(table)
		idx_name = self._quote("sidx_"+table)
		sql = "SELECT CreateSpatialIndex(%s, %s)" % (self._quote(table), self._quote(geom_column))
		self._exec_sql_and_commit(sql)

	def delete_index(self, name):
		sql = "DROP INDEX %s" % (self._quote(name))
		self._exec_sql_and_commit(sql)
		
	def delete_spatial_index(self, name, geom_column='the_geom'):
		sql = "SELECT DiscardSpatialIndex(%s, %s)" % (self._quote(name), self._quote(geom_column))
		self._exec_sql_and_commit(sql)
	
	def vacuum(self):
		""" run vacuum on the db """
		self._exec_sql_and_commit("VACUUM")
		
	def sr_info_for_srid(self, srid):
		c = self.con.cursor()
		self._exec_sql(c, "SELECT ref_sys_name FROM spatial_ref_sys WHERE srid = %s" % self._quote_str(srid))
		return c.fetchone()[0]

	def insert_table_row(self, table, values, cursor=None):
		""" insert a row with specified values to a table.
		 if a cursor is specified, it doesn't commit (expecting that there will be more inserts)
		 otherwise it commits immediately """
		sql = ""
		for value in values:
			# TODO: quote values?
			if sql: sql += ", "
			sql += value
		sql = "INSERT INTO %s VALUES (%s)" % (self._quote(table), sql)
		if cursor:
			self._exec_sql(cursor, sql)
		else:
			self._exec_sql_and_commit(sql)
		
	def _exec_sql(self, cursor, sql):
		try:
			cursor.execute(sql)
		except sqlite.Error, e:
			# do the rollback to avoid a "current transaction aborted, commands ignored" errors
			self.con.rollback()
			raise DbError(e)
		
	def _exec_sql_and_commit(self, sql):
		""" tries to execute and commit some action, on error it rolls back the change """
		c = self.con.cursor()
		self._exec_sql(c, sql)
		self.con.commit()

	def _quote(self, identifier):
		""" quote identifier if needed """
		identifier = unicode(identifier) # make sure it's python unicode string
		return u'"%s"' % identifier.replace('"', '""')
	
	def _quote_str(self, txt):
		""" make the string safe - replace ' with '' """
		txt = unicode(txt) # make sure it's python unicode string
		return u"'%s'" % txt.replace("'", "''")

