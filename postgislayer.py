"""
/***************************************************************************
 Fast SQL Layer
                                 A QGIS plugin
 Just type the query to add the layer
                              -------------------
        begin                : 2011-05-12
        copyright            : (C) 2011 by Pablo Torres Carreira
        email                : pablotcarreira@hotmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import DbConnection
import highlighter as hl
import os
import resources

# Initialize Qt resources from file resources.py

conn = DbConnection.ConnectionManager()

class PostgisLayer:
    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(QIcon(":/plugins/postgislayer/icon.png"), "Fast SQL Layer", self.iface.mainWindow())
        #Add toolbar button and menu item
        self.iface.addPluginToDatabaseMenu("&Fast SQL Layer", self.action)
        #self.iface.addToolBarIcon(self.action)
        
        
        #load the form  
        path = os.path.dirname(os.path.abspath(__file__))
        self.dock = uic.loadUi(os.path.join(path, "ui_postgislayer.ui"))
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dock)        
        
        
        #connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.show)
        QObject.connect(self.dock.buttonRun, SIGNAL('clicked()'), self.run)        
        QObject.connect(self.dock.buttonGet, SIGNAL('clicked()'), self.get)
        
        #populate the combo with connections
        actions = conn.getAvailableConnections()
        self.actionsDb = {}
        for a in actions:
        	self.actionsDb[ unicode(a.text()) ] = a
        for i in self.actionsDb:
        	self.dock.comboConnections.addItem(i)
        
        #populate the id and the_geom combos
        self.dock.uniqueCombo.addItem('id')
        self.dock.geomCombo.addItem('the_geom')
        
        #populate the replace layer_combo
        self.dock.layerCombo.addItem('add layer')
        self.dock.layerCombo.addItem('replace layer')
        
        #start the highlight engine
        self.higlight_text = hl.Highlighter(self.dock.textQuery.document(), "sql")
        
    def show(self):
        self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.dock)
    
    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginDatabaseMenu("&Fast SQL Layer", self.action)
        
        #self.iface.removeToolBarIcon(self.action)

    
    def run(self):
		QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
		
		dados = str(self.dock.comboConnections.currentText())
		self.db = self.actionsDb[dados].connect()
		uniqueFieldName = self.dock.uniqueCombo.currentText()
		geomFieldName = self.dock.geomCombo.currentText()
		uri = self.db.getURI()
		query = str(self.dock.textQuery.toPlainText())
		
		#replace layer (not working)
		if self.dock.layerCombo.currentText() == 'replace layer':
				layer = self.iface.activeLayer()
				try: layer.actionRemoveLayer()
				except: pass
		#lstrip() is needed to remove spaces in the first line.
		uri.setDataSource("", "(" + query.lstrip() + ")", geomFieldName, "", uniqueFieldName)
		vl = self.iface.addVectorLayer(uri.uri(), "QueryLayer", self.db.getProviderName())
		
		QApplication.restoreOverrideCursor()
    
    def get(self):
        layer = self.iface.activeLayer()
        if hasattr(layer, 'type') and layer.type()==0:
            dataprovider=layer.dataProvider()
            uri2=str(dataprovider.dataSourceUri())
            text = os.linesep.join([s for s in uri2.splitlines() if s])
            #still not avaliable in py 2.5
            #text='{table}'.format(text) 
            #self.higlight_text.rehighlight()
            self.dock.textQuery.setPlainText(text)
        else: QMessageBox.warning(self.dock,'Error','Please select a vector layer',1,0)
    