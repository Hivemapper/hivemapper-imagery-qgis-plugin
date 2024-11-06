# -*- coding: utf-8 -*-
"""
/***************************************************************************
 HivemapperImagery
                                 A QGIS plugin
 This plugin fetches the latest imagery from the Hivemapper network
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-10-24
        copyright            : (C) 2024 by Hivemapper
        email                : hi@hivemapper.com
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

__author__ = 'Hivemapper'
__date__ = '2024-10-24'
__copyright__ = '(C) 2024 by Hivemapper'

import os
import site
import pkg_resources
import sys


def pre_init_plugin():
    # Path to the extlib directory
    extra_libs_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "extlib"))
    if os.path.isdir(extra_libs_path):
        # Insert extlib at the beginning of sys.path to prioritize it
        sys.path.insert(0, extra_libs_path)
        # Add extlib to site directories
        site.addsitedir(extra_libs_path)
        # Ensure pkg_resources can locate packages in extlib
        pkg_resources.working_set.add_entry(extra_libs_path)

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load HivemapperImagery class from file HivemapperImagery.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    pre_init_plugin()

    import imagery

    from .hivemapper_imagery import HivemapperImageryPlugin
    return HivemapperImageryPlugin(iface)
