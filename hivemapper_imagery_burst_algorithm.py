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
import glob
import bursts
import base64

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import (QCoreApplication,QVariant)
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterString,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterFolderDestination,
                       QgsVectorLayer, 
                       QgsProject, 
                       QgsFeature, 
                       QgsField, 
                       QgsGeometry, 
                       QgsPointXY,
                       QgsAction)
# Path to the config file
config_path = os.path.join(os.path.expanduser("~"), ".hivemapper_imagery_config.json")

# Load config values
def load_config():
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

# Save config values
def save_config(config):
    with open(config_path, 'w') as f:
        json.dump(config, f)

def get_personal_token(user_name, api_key):
    string_to_encode = f"{user_name}:{api_key}"
    encoded_bytes = base64.b64encode(string_to_encode.encode("utf-8"))
    encoded_string = encoded_bytes.decode("utf-8")
    return encoded_string


class HivemapperImageryBurstAlgorithm(QgsProcessingAlgorithm):
    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    API_KEY = 'API_KEY'
    USERNAME = 'USERNAME'
    OUTPUT = 'OUTPUT'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        config = load_config()  # Load saved config

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        # Add API key input
        self.addParameter(
            QgsProcessingParameterString(
                self.API_KEY,
                self.tr('API Key'),
                defaultValue=config.get("api_key", "")
            )
        )

        # Add username input
        self.addParameter(
            QgsProcessingParameterString(
                self.USERNAME,
                self.tr('Username'),
                defaultValue=config.get("username", "")
            )
        )
        self.addParameter(
                QgsProcessingParameterString(
                    self.OUTPUT,
                    self.tr('Result Message'),
                    defaultValue="Process complete"  # Optional default message
                )
            )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Get the input values
        api_key = self.parameterAsString(parameters, self.API_KEY, context)
        username = self.parameterAsString(parameters, self.USERNAME, context)
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        config = load_config()  # Load saved config

        # Save values to config dictionary
        config['api_key'] = api_key
        config['username'] = username
        save_config(config)

        # Get the authorization token
        authToken = get_personal_token(username, api_key)

        # Compute the number of steps to display within the progress bar and
        if not layer:
            raise ValueError("Input layer is not valid")

        layer.startEditing()
        layer_provider = layer.dataProvider()

        # Add the 'imagery_metadata' field if it doesn't exist and commit immediately
        if layer_provider.fields().indexFromName("burst_metadata") == -1:
            layer_provider.addAttributes([QgsField("burst_metadata", QVariant.String)])
            layer.updateFields()  # Refresh the layer fields to include the new field
            layer.commitChanges()  # Commit changes after adding the field
            layer.startEditing()  # Reopen editing session

        # Verify field addition
        layer.updateFields()
        # Only process selected features
        selected_features = layer.selectedFeatures()
        if not selected_features:
            raise ValueError("No features selected")
        total = 100.0 / len(selected_features) if selected_features else 0

        success = 0
        # for each feature, query frames and download files
        for current, feature in enumerate(selected_features):

            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            # Update the progress bar
            feedback.setProgress(int(current * total))

            # Get the geometry of the feature and convert it to GeoJSON
            geom = feature.geometry()
            geom_geojson = json.loads(geom.asJson())  # Convert geometry to JSON-compatible format
            if geom.isEmpty():
                print("Skipping empty geometry")
                continue
            with tempfile.NamedTemporaryFile(mode='w', suffix='.geojson', delete=False) as temp_geojson_file:
                # Write the GeoJSON data to the temporary file
                json.dump(geom_geojson, temp_geojson_file)
                temp_geojson_file.flush()  # Ensure all data is written to the file
                temp_geojson_file_path = temp_geojson_file.name
                print(f"Temporary GeoJSON file created at: {temp_geojson_file_path}")
            result = bursts.create_bursts(geojson_file_path=temp_geojson_file_path, authorization = 'Basic '+authToken)
            # add attribute to feature 'burst_metadata'
            if isinstance(result, dict) and result.get('success'):
                success += 1
                # Convert the result data to JSON string and update feature
                json_string = json.dumps(result.get('bursts', []))
                feature.setAttribute('burst_metadata', json_string)
                layer.updateFeature(feature)
            else:
                print("Failed to create burst for feature")
        layer.commitChanges()
        feedback.pushInfo(f"Successfully created {success} burst(s)" if success > 0 else "Error processing features to create bursts")

        return {self.OUTPUT: f"Successfully created {success} burst(s)" if success > 0 else "Error processing features to create bursts"}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Create Bursts'

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
        return HivemapperImageryBurstAlgorithm()