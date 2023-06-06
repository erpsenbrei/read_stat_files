# read_stat_files
Read SAP stat files and convert them into CSV or Excel file format

The SAP work processes write metrics for every executed SAP transaction into the stat files. These stat files are kept for 48 hours in the data directory of a SAP instance. Regularly they get uploaded into the SAP system and condensed into table MONI. There are various ABAP interfaces to read out the stat files, most notably transaction STAD. However, if you want to evaluate performance metrics without any ABAP coding or logging on to a SAP system, it would be helpful to decode the stat files independently of a SAP system.

The script read_stat_files.py is a partial solution to this. You can run it to extract at least some subset of the information from the SAP stat files.

Goal:
Provide as many metrics as possible from the SAP stat files in a human-readable format.
The stat files can be converted into CSV (= default) or Excel format.

Example Execution:
Just put the script read_stat_files.py into the data directory of your SAP instance and run it without any options. It will then create one CSV file per stat file:

$ cd /usr/sap/SID/DVEBMGS00/data

$ python read_stat_files.py


Current limitations:
- many interessting metrics like e.g. the database response time or the overall runtime are not yet available
- only the main record is decoded, optional sections like details on the database activity are currently ignored
- the stat file format is very messy, and the script cannot correctly decipher all records
- the processing of large stat files is somewhat slow
- SAP uses a proprietary number format, so there are small rounding effects


Any feedback on how to improve the script is highly appreciated!
