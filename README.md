# SAP Stat File Reader
Read SAP stat files and convert them into CSV or Excel file format. The script opens up this treasure trove of data, independently from the SAP system.

# Overview
The SAP work processes write metrics for every executed SAP transaction into the stat files. These stat files are kept for 48 hours in the data directory of a SAP instance. Regularly they get uploaded into the SAP system and condensed into table MONI. There are various ABAP interfaces to read out the stat files, most notably transaction STAD. However, if you want to evaluate performance metrics without any ABAP coding or logging on to a SAP system, it would be helpful to decode the stat files independently of a SAP system.

The script ```read_stat_files.py``` is a partial solution to this. You can run it to extract at least some subset of the information from the SAP stat files.

# Goal
Provide as many metrics as possible from the SAP stat files in a human-readable format. The published version is already usable, but should be improved over time to decipher even more metrics.

# Example Execution
Just put the script read_stat_files.py into the data directory of your SAP instance and run it without any options. It will then create one CSV file per stat file:
```
$ cd /usr/sap/SID/DVEBMGS00/data
$ python read_stat_files.py
```
Or another example to create an Excel file for one specific stat file and include all columns (i.e. even the ones with unknown meaning):
```
$ python read_stat_files.py --file=stat120 --columns=all --output_format=xls
```

# List of decoded columns
This is the list of the columns with a known meaning:
- Sections: number of subsections following the main record
- Calday: calender day on which the transaction was executed
- Starttime: bein of the transaction (no subseconds available)
- Endtime: end of the transaction (no subseconds available)
- Processing time: this is not the total response time, but defined as 
                   *total response time - wait time - enqueue time - database request time*
- Roll wait time: high roll wait times can indicate a communication problem with the SAPGUI,
                  or a communication problem with an external system
                  or a large amount of data was requested
- CPU time: self explanatory, that is mostly ABAP processing
- Wait for work process: this time can be increased if no work process was available
- GUI time: not part of the SAP response time because this happens on the client side
- Frontend roundtrips: how often was data sent back and forth between the SAP system and the SAPGUI
- Net time: time needed for network transfer, only indirectly measured
- Previous timestamp: timestamp of the previous transaction (if any)
- RFC+CPIC time: time for RFC processing
- Total memory used
- Max EM used in transaction (modern SAP systems use almost exclusively SAP Extended Memory)
- Max EM used in dia step (usually almost the same as the previous metric)
- Username (12 characters maximum)
- Client (always 3 numeric characters, every SAP system has got a client 000)
- Transactionid: some SAP identifier of 32 chars
- Sessionid: some SAP identifier of 40 chars
- (Network) Client: can be a hostname, IP or FQDN
- Task type: usually D for dialog, B for batch or R for RFC
- Report: the ABAP report which was executed
- Transaction: the SAP transaction code with was used
- Prev Report: the previous ABAP report (if any)

# Current Limitations
- Many interesting metrics like e.g. the database response time or the overall runtime are not yet available.
- Only the main record is decoded, optional sections like details on the database activity are currently ignored.
- The stat file format is very messy, and the script cannot correctly decipher all records.
- The processing of large stat files is somewhat slow. SAP uses a proprietary number format, so there are small rounding effects.

# Feedback
Any feedback on how to improve the script is highly appreciated! If you are looking for a reverse engineering challenge, then you are in for a treat.
