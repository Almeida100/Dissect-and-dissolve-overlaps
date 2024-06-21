# -*- coding: utf-8 -*-

"""
/***************************************************************************
 DissectAndDissolveOverlaps
                                 A QGIS plugin
 Detect, zoom to, dissect and dissolve overlaps in one polygon layer.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2022-07-30
        copyright            : (C) 2022 by Antonio Sobral Almeida
        email                : 66124.almeida@gmail.com
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

__author__ = 'Antonio Sobral Almeida'
__date__ = '2024-06-19'
__copyright__ = '(C) 2022 by Antonio Sobral Almeida'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsVectorLayer
from qgis.core import QgsProcessingParameterNumber
import processing
import re 
import os
import time
from datetime import datetime
from qgis.core import QgsProject
from qgis.core import QgsProcessingUtils
from qgis.utils import iface
from PyQt5.QtWidgets import QAction
from qgis.core import QgsProcessingParameterFeatureSink
from PyQt5 import QtWidgets



class DissectAndDissolveOverlapsAlgorithm(QgsProcessingAlgorithm):

    OPTIONS = 'OPTIONS'
    option_list = ['Select and zoom to overlaps', 'Dissect overlaps','Dissect and Dissolve overlaps']

    
    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('inputpolygonlayer', 'Input Polygon Layer', types=[QgsProcessing.TypeVectorPolygon], defaultValue=None))
        self.addParameter(QgsProcessingParameterEnum(self.OPTIONS, options=self.option_list, allowMultiple=True,defaultValue=[0]))        
        self.addParameter(QgsProcessingParameterNumber('DPI', 'Dissolve polygon into: 0 - Largest adjacent polygon; 1 - Smallest adjacent polygon; 2 - Largest common boundary', type=QgsProcessingParameterNumber.Integer, minValue=0, maxValue=2, defaultValue=0))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(13, model_feedback)
        results = {}
        outputs = {}

        # Remove duplicate layers
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == "Intersected":
                QgsProject.instance().removeMapLayers([lyr.id()])
            elif lyr.name() == "Dissolved":
                QgsProject.instance().removeMapLayers([lyr.id()])

        # Find options checked by user
        user_options = self.parameterAsEnums(parameters, self.OPTIONS, context)
        selected_items = [self.option_list[i] for i in user_options]

        # check which options are required by the user
        for l in selected_items:  
            find1 = re.findall("Select",l)  
            find2 = re.findall("Dissect",l)  
            find3 = re.findall("Dissolve",l)  
            
# *************************************************   Section1: Select and show overlaps   **************************************************************
        
        # This section will be allways executed, no matter user option

        # Create a time stamp
        tme=time.localtime()
        timeString=datetime.now().strftime('%H%M%S')
        
        # Find the path of the QGisproject
        ProjectPath= QgsProject.instance().homePath() + '/'

        # Unselect all selections
        iface.mainWindow().findChild(QAction, 'mActionDeselectAll').trigger()

        # Fix geometries
        alg_params = {
            'INPUT': parameters['inputpolygonlayer'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixGeometries'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Drop field(s)1
        Fields=['Id_SI', 'Id_SI Inte']
        alg_params = {
            'COLUMN': Fields,
            'INPUT': outputs['FixGeometries']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['DropFields1'] = processing.run('native:deletecolumn', alg_params, context=context, feedback=feedback, is_child_algorithm=True)


        # Get name and object of 'inputpolygonlayer' layer
        lyr_list = iface.layerTreeView().layerTreeModel().rootGroup().layerOrder()
        lyr_dict = {lyr.id(): lyr.name() for lyr in lyr_list}
        if parameters['inputpolygonlayer'] in lyr_dict:
            layer_name = lyr_dict[parameters['inputpolygonlayer']]
            input_layer = QgsProcessingUtils.mapLayerFromString(layer_name, context)
            iface.setActiveLayer(input_layer) 

        # Add autoincremental field
        alg_params = {
            'FIELD_NAME': 'Id_SI',
            'GROUP_FIELDS': [''],
            'INPUT': outputs['DropFields1']['OUTPUT'],
            'MODULUS': 0,
            'SORT_ASCENDING': True,
            'SORT_EXPRESSION': '',
            'SORT_NULLS_FIRST': False,
            'START': 1,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AddAutoincrementalField'] = processing.run('native:addautoincrementalfield', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Polygon Self-Intersection
        alg_params = {
            'ID': 'Id_SI',
            'POLYGONS': outputs['AddAutoincrementalField']['OUTPUT'],
            'INTERSECT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['PolygonSelfintersection'] = processing.run('sagang:polygonselfintersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        res1 = outputs['PolygonSelfintersection']['INTERSECT']

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Select by attribute
        alg_params = {
            'FIELD': 'Id_SI Inter',
            'INPUT': outputs['PolygonSelfintersection']['INTERSECT'],
            'METHOD': 0,  # creating new selection
            'OPERATOR': 7,  # contains
            'VALUE': '|'
        }
        outputs['SelectByAttribute'] = processing.run('qgis:selectbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Extract selected features
        alg_params = {
            'INPUT': outputs['SelectByAttribute']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractSelectedFeatures'] = processing.run('native:saveselectedfeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Fix geometries2
        alg_params = {
            'INPUT': outputs['ExtractSelectedFeatures']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['FixGeometries2'] = processing.run('native:fixgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Select by location
        alg_params = {
            'INPUT': parameters['inputpolygonlayer'],
            'INTERSECT': outputs['FixGeometries2']['OUTPUT'],
            'METHOD': 0,  # creating new selection
            'PREDICATE': [0] # intersect
        }
        outputs['SelectByLocation'] = processing.run('native:selectbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        # Zoom to selected features
        iface.actionZoomToSelected().trigger()
        
        # Check if there are selected features
        count_selected = input_layer.selectedFeatureCount() 
        if count_selected==0:
            w = QtWidgets.QWidget()
            b = QtWidgets.QLabel(w)
            w.setGeometry(400,400,550,20)
            w.setWindowTitle("There are no overlaps in the input layer! (Auto close in 10 seconds)")
            w.show()
            time.sleep(10)
            return results

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

# *************************************************   Section2: Dissect overlaps   **************************************************************
        # if user also selected option 'Dissect overlaps' or 'Dissect and dissolve overlaps'

        if find2 or find3:
            # Polygon Self-Intersection2
            alg_params = {
                'ID': 'Id_SI',
                'POLYGONS': outputs['AddAutoincrementalField']['OUTPUT'],
                'INTERSECT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['PolygonSelfintersection2'] = processing.run('sagang:polygonselfintersection', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            res1 = outputs['PolygonSelfintersection2']['INTERSECT']

            feedback.setCurrentStep(8)
            if feedback.isCanceled():
                return {}

            # Remove null geometries
            alg_params = {
                'INPUT': outputs['PolygonSelfintersection2']['INTERSECT'],
                'REMOVE_EMPTY': True,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['RemoveNullGeometries'] = processing.run('native:removenullgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(9)
            if feedback.isCanceled():
                return {}

            # Field calculator
            alg_params = {
                'FIELD_LENGTH': 20,
                'FIELD_NAME': 'A79nHik4',
                'FIELD_PRECISION': 10,
                'FIELD_TYPE': 0,  # Float
                'FORMULA': '$area',
                'INPUT': outputs['RemoveNullGeometries']['OUTPUT'],
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['FieldCalculator'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(10)
            if feedback.isCanceled():
                return {}

            # Extract by attribute (remove geometries with areas less than or equal to zero)
            alg_params = {
                'FIELD': 'A79nHik4',
                'INPUT': outputs['FieldCalculator']['OUTPUT'],
                'OPERATOR': 2,  # >
                'VALUE': 0.01,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }
            outputs['ExtractByAttribute'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(11)
            if feedback.isCanceled():
                return {}

            # Drop field(s)
            alg_params = {
                'COLUMN': 'A79nHik4',
                'INPUT': outputs['ExtractByAttribute']['OUTPUT'],
                'OUTPUT': ProjectPath + 'Intersected'+timeString+'.shp'
            }
            outputs['DropFields'] = processing.runAndLoadResults('native:deletecolumn', alg_params, context=context, feedback=feedback)
        
        if not find3:
            return results

# *************************************************   Section3: Dissolve overlaps   **************************************************************

        if find3:    # if user also selected option 'Dissolve overlaps'

            # Select by attribute
            alg_params = {
                'FIELD': 'Id_SI Inte',
                'INPUT': outputs['DropFields']['OUTPUT'],
                'METHOD': 0,  # creating new selection
                'OPERATOR': 7,  # Contains
                'VALUE': '|'
            }
            outputs['SelectByAttribute'] = processing.run('qgis:selectbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

            feedback.setCurrentStep(12)
            if feedback.isCanceled():
                return {}

            # Eliminate selected polygons
            Param1 = parameters['DPI']
            alg_params = {
                'INPUT': outputs['SelectByAttribute']['OUTPUT'],
                'MODE': Param1,
                'OUTPUT': ProjectPath + 'Dissolved'+timeString+'.shp'
            }
            outputs['EliminateSelectedPolygons'] = processing.runAndLoadResults('qgis:eliminateselectedpolygons', alg_params, context=context, feedback=feedback)

            feedback.setCurrentStep(13)
            if feedback.isCanceled():
                return {}

        return results

    def name(self):
        return 'DissectAndDissolveOverlaps'

    def displayName(self):
        return 'Dissect and dissolve overlaps Ver. 0.5'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return DissectAndDissolveOverlapsAlgorithm()
