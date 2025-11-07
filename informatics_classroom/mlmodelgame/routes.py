from flask import request, render_template, jsonify
import pandas as pd
from informatics_classroom.mlmodelgame import mlmodel_bp
from informatics_classroom.config import Keys

# ML Model Game routes removed - feature was using Azure Table Storage
# which has been deprecated in favor of PostgreSQL
# This feature can be re-implemented if needed using the database adapter pattern
