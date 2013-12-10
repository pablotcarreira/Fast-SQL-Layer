"""
/***************************************************************************
 Fast SQL Layer
                                 A QGIS plugin
 Just type the query to add the layer, for experienced users
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
 This script initializes the plugin, making it known to QGIS.
"""

def classFactory(iface):
    # load PostgisLayer class from file PostgisLayer
    from postgislayer import PostgisLayer
    return PostgisLayer(iface)
