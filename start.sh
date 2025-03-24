#!/bin/bash

# Start of the script

# Copy request.json to ID_generator/request_template.json
cp "request.json" "ID_generator/request_template.json"

# Run the Python script make_task.py with the specified argument
python3 ID_generator/make_task.py -f ID_generator/request_template.json

# Copy ID_generator/request_template.xml to request_template.xml
cp "ID_generator/request_template.xml" "request_template.xml"

# Run the Python script PDAPlanner.py with the specified arguments
python3 PDAPlanner.py -f request_template.xml -o result

# Copy result/request_template_report.xml to report.xml
cp "result/request_template_report.xml" "report.xml"

# Make JSON output file
python3 VD_jsonify.py report.xml report.json

# Remove request_template.xml
rm request_template.xml

# Remove ID_generator/request_template.xml
rm "ID_generator/request_template.xml"

# Remove the result directory and its contents
rm -r result

# End of the script