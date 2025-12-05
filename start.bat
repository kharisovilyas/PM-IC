@echo off
REM Start of the script

REM Copy request.json to ID_generator/request_template.json
COPY "request.json" "ID_generator\request_template.json"

REM Run the Python script make_task.py with the specified argument
python ID_generator/make_task.py -f ID_generator/request_template.json

REM Copy ID_generator/request_template.xml to request_template.xml
COPY "ID_generator\request_template.xml" "request_template.xml"

REM Run the Python script PDAPlanner.py with the specified arguments
python PDAPlanner.py -f request_template.xml -o result -t 300

REM Copy result/request_template_report.xml to report.xml
COPY "result\request_template_report.xml" "report.xml"

REM Remove request_template.xml
DEL request_template.xml

REM Remove ID_generator/request_template.xml
DEL ID_generator\request_template.xml

REM Remove the result directory and its contents
RMDIR result /s /q

REM Convert report to json
python report_converter.py

REM Generate report from json to xlsx
REM python generate_report.py

REM End of the script