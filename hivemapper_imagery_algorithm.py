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
import imagery
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

def generate_image_list_html(image_metadata):
    """
    Generates HTML for displaying images with titles in a scrollable list.
    
    :param image_metadata: List of dictionaries containing 'image_path' and 'title' keys.
                           Example: [{'image_path': '/path/to/image1.jpg', 'title': 'Image Title 1'}, ...]
    :return: HTML string
    """
    html_content = '''
    <div class="image-list">
    '''

    # Generate each image item in the list
    for item in image_metadata:
        html_content += f'''
        <div class="image-item">
            <p>{item['timestamp']}</p>
            <a href="file:///{item['image_path']}" target="_blank">
                <img src="file:///{item['image_path']}" alt="{item['image_path']}">
            </a>
        </div>
        '''

    # Close the image list container div and add CSS styling
    html_content += '''
    </div>

    <style>
        .image-list {
        max-width: 480px;
        max-height: 480px;
        overflow-y: auto;
    }

        .image-item img {
            width: 100%;
            margin-bottom: 10px;
        }

        .image-item p {
            font-weight: bold;
            margin: 0 0 5px;
            color: white;
        }
    </style>
    '''
    
    return html_content

def extract_unique_sequences(paths):
    unique_paths = set()
    for path in paths:
        # Check if the file ends with .jpg
        if path.endswith('.jpg'):
            # Get the path before 'keyframes'
            path_before_keyframes = os.path.dirname(os.path.dirname(path))
            unique_paths.add(path_before_keyframes)
    return unique_paths

def filter_imagery_paths(image_paths):
    result = []
    # Filter out paths that end with ".jpg"
    jpg_paths = [path for path in image_paths if path.endswith(".jpg")]
     # Get the parent directory of "keyframes"
    dir = extract_unique_sequences(jpg_paths)
    # for each dir, get all the metadata files and output the image_path and timestamp
    for d in dir:
        metadata_files = glob.glob(os.path.join(d, "metadata", "*.json"))
        for metadata_file in metadata_files:
            with open(metadata_file, 'r') as json_file:
                metadata = json.load(json_file)
                position = metadata.get("position", {})
                lat = position.get("lat")
                lon = position.get("lon")
                # Skip if lat/lon is missing
                if lat is None or lon is None:
                    continue
                # Get the imagery path
                image_idx = metadata['idx'] 
                image_path = os.path.join(d, "keyframes", f"{image_idx}.jpg")
                result.append({
                    "image_path": image_path,
                    "timestamp": metadata.get("timestamp"),
                    "sequence": metadata.get("sequence"),
                    "lat": lat,
                    "lon": lon,
                })
    return result
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

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT,
                self.tr('Output Directory'),
                defaultValue=config.get("output", "output")
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
 

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Get the input values
        api_key = self.parameterAsString(parameters, self.API_KEY, context)
        username = self.parameterAsString(parameters, self.USERNAME, context)
        layer = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        output = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        # Save values to config file
        config = {
            "api_key": api_key,
            "username": username,
            "output": output
        }
        save_config(config)

        # Get the authorization token
        authToken = get_personal_token(username, api_key)

        # Compute the number of steps to display within the progress bar and
        if not layer:
            raise ValueError("Input layer is not valid")

        # Ensure layer is editable
        layer.startEditing()
        layer_provider = layer.dataProvider()

        # Add the 'imagery_metadata' field if it doesn't exist and commit immediately
        if layer_provider.fields().indexFromName("imagery_metadata") == -1:
            layer_provider.addAttributes([QgsField("imagery_metadata", QVariant.String)])
            layer.updateFields()  # Refresh the layer fields to include the new field
            layer.commitChanges()  # Commit changes after adding the field
            layer.startEditing()  # Reopen editing session

        # Verify field addition
        layer.updateFields()
        imagery_metadata_index = layer.fields().indexFromName("imagery_metadata")
        if imagery_metadata_index == -1:
            raise ValueError("Field 'imagery_metadata' was not added successfully")

        imagery_metadata_index = layer.fields().indexFromName("imagery_metadata")
        if imagery_metadata_index == -1:
            raise ValueError("Field 'imagery_metadata' was not added successfully")

        # Only process selected features
        selected_features = layer.selectedFeatures()
        if not selected_features:
            raise ValueError("No features selected")
        total = 100.0 / len(selected_features) if selected_features else 0

        # for each feature, query frames and download files
        for current, feature in enumerate(selected_features):
            # to store imagery metadata in a list
            metadata_list = []

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
            frames = imagery.query(file_path=temp_geojson_file_path, output_dir=output, authorization = authToken, latest=True, start_day=None, end_day=None, use_cache=False)
            # get result frames and get filtered imagery paths
            results = filter_imagery_paths(frames)
            for result in results:
                metadata_list.append(result)

            # Sort the metadata list by timestamp in descending order       
            sorted_metadata = sorted(metadata_list, key=lambda x: x['timestamp'], reverse=True)
            html = generate_image_list_html(sorted_metadata)
            feature.setAttribute(imagery_metadata_index, html)
            layer.updateFeature(feature)

        layer.setMapTipTemplate("[% imagery_metadata %]")
        layer.commitChanges()

        return {self.OUTPUT: output}

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