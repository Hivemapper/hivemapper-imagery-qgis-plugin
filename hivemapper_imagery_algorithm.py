# -*- coding: utf-8 -*-
__author__ = 'Hivemapper'
__date__ = '2024-10-24'
__copyright__ = '(C) 2024 by Hivemapper'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import inspect
import tempfile
import json

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFileDestination)
from imagery import query


class HivemapperImageryAlgorithm(QgsProcessingAlgorithm):
    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    OUTPUT = 'OUTPUT'
    INPUT = 'INPUT'
    API_KEY = 'API_KEY'
    USERNAME = 'USERNAME'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT,
                self.tr('Output File'),
                'CSV files (*.csv)',
            )
        )

        # Add API key input
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                self.tr('API Key'),
                defaultValue=''
            )
        )

        # Add username input
        self.addParameter(
            QgsProcessingParameterString(
                self.USERNAME,
                self.tr('Username'),
                defaultValue=''
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        source = self.parameterAsSource(parameters, self.INPUT, context)
        csv = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        api_key = self.parameterAsString(parameters, self.API_KEY, context)
        username = self.parameterAsString(parameters, self.USERNAME, context)

        authToken = "1234"#get_personal_token(api_key, username)

        fieldnames = [field.name() for field in source.fields()]

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()

        # for each feature, query frames and download files
        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            # Update the progress bar
            feedback.setProgress(int(current * total))

            # Get the geometry of the feature
            geom = feature.geometry()

            # Get the center of the geometry
            center = geom.centroid().asPoint()
            
            # Create a temporary file for the GeoJSON data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as temp_geojson_file:
                # Write the GeoJSON data to the temporary file
                json.dump(center, temp_geojson_file)
                temp_geojson_file_path = temp_geojson_file.name
                print(f"Temporary GeoJSON file created at: {temp_geojson_file_path}")

                # make the API call to query available data
                frames = query(file_path = temp_geojson_file_path, latest = True,  authorization = authToken, output_dir = csv)
                
                print('completed processing frames')
                # # download the content into folders grouped by its session id
                # download_files(frames, output_dir)


        return {self.OUTPUT: csv}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Fetch Imagery'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Hivemapper')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return ''

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return HivemapperImageryAlgorithm()