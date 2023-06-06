# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
# Author: erpsenbrei on GitHub
# Date: 2023-06-06

from datetime import datetime
import pandas as pd
from io import StringIO
import argparse
import os

# global variables used for processing the stat records line by line
record_old = ""
record_new = ""
row_num = 0
       
def convert_sap_number(four_bytes_input):
    # sap uses a strange legacy number format in the stat files
    if four_bytes_input[0]=='4':                # the first character is always 4
        exponent= int(four_bytes_input[1:3],16) # second and third character are the exponent
        factor1 = int(four_bytes_input[3:5],16) # fourth and fifth character are factor1
        factor2 = int(four_bytes_input[5],16)   # sixth  character is factor2
        factor3 = int(four_bytes_input[6],16)   # seventh character is factor3          
        factor4 = int(four_bytes_input[7],16)   # eigth character is factor4
        result = 2**(exponent+1) + 2**(exponent-7)*factor1 + 2**(exponent-11)*factor2 + 2**(exponent-25)*factor3 + 2**(exponent-29)*factor4
    else:
        result=0
    return str(round(result/1000)) # sometimes the result needs to be divided by 1024, don't ask me why, but the error is minuscule.

def add_generic(number_of_bytes, relevant):
    # add a column by simply writing the bytes values
    global record_old
    global record_new
    if args.columns=="all" or relevant==1:
        record_new = record_new + record_old[0:number_of_bytes].lstrip("0") + ","
    record_old=record_old[number_of_bytes:]

def add_date(number_of_bytes, relevant):
    # the three date columns are stored as unix ticks
    global record_old
    global record_new
    if args.columns=="all" or relevant==1:
        date_object = datetime.fromtimestamp(int(record_old[0:8],16))
        record_new = record_new + str(date_object) + ","
    record_old = record_old[8:]

def add_sap_number(number_of_bytes, relevant):
    # this function allows to use a one-liner in the main routine for adding a number
    global record_old
    global record_new
    if args.columns=="all" or relevant==1:
        record_new = record_new + convert_sap_number(record_old[0:8]) + ","
    record_old = record_old[8:]

def find_delimiter(record):
    # this function is used to write a variable length column which is the last column before the SAP username.
    # there are certain delimiters which reliably indicate the end of this variable length column.
    # the record might start with 0e0100000000, that could produce a false positive first finding,
    # therefore remove the first 4 characters to prevent that false positive
    record=record[4:]
    lowest_position = 9999
    # this routine is the most time consuming, so the number of string searches should be minimized.
    # the most frequent patterns are checked first, to prevent spending much time on searching.
    search_index = record.find("0900000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
        return lowest_position+4
    search_index = record.find("1500000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
        return lowest_position+4
    search_index = record.find("0b00000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
        return lowest_position+4
    search_index = record.find("1600000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
        return lowest_position+4
    search_index = record.find("0200000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
        return lowest_position+4
    search_index = record.find("0400000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
        return lowest_position+4
    search_index = record.find("0800000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
        return lowest_position+4
    # in >99.9% of the cases one of the patterns above will have already matched.
    # the following patterns occur only rarely, so these can all be checked. that won't slow down the function signficantly.
    search_index = record.find("6600000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index  
    search_index = record.find("0900000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index                
    search_index = record.find("0900000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index  
    search_index = record.find("6500000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index             
    search_index = record.find("0400000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("6600000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("0100000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("6500000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("0200000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("1600000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("0100000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("0800000100")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("0f00000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("0c00000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    search_index = record.find("6501000000")
    if search_index>=0 and record[search_index+12:search_index+14]=="00" and search_index<lowest_position:
        lowest_position=search_index
    return lowest_position+4

def read_stat_file(file_name):
    # this function reads in a single stat file and converts it to human-readable output
    global record_old
    global record_new
    global row_num
    delimiter = '002a00530041002a' # the records in the stat files start with this prefix, SA or "Satz Anfang", and end with 1402092a00530045002a (SE or "Satz Ende")
    with open(file_name,'rb') as f:
         data = f.read()
    data_hex = data.hex()
    records = data_hex.split(delimiter)
    row_num = 0
    csv_string = "" # this string will collect all records of the stat file in human-readable format

    for record in records:
        if record.startswith("0380"): # only evaluate the main section of the record, which starts with the prefix 0380, and not the optional parts
            row_num = row_num+1
            record_old=str(record)
            record_new = ""
            # PART 1
            # the stat file record begins with a fixed width section containing many numbers and some strings.
            # here things are still very orderly and easy to decipher.
            if args.columns=="all":
                record_new = record_new + str(row_num) + ","
            add_generic(4,0)               # prefix 0380
            add_generic(4,0)               # this could be the modus ?
            add_generic(4,0)               # some constant FF03
            add_generic(12,0)              # 8 zeros and some time offset
            add_generic(4,1)               # number of optional subsections following the main record
            for i in range(8):             # calday field
                record_new = record_new + record_old[i*4+3]
            record_new = record_new + ","
            record_old = record_old[32:]
            add_generic(2,0)               # unknown field
            record_old = record_old[2:]    # skip two zeros
            add_date(8,1)                  # transaction start time
            add_generic(8,0)               # unknown column
            add_date(8,1)                  # transaction end time
            add_generic(8,0)               # unknown column)
            add_sap_number(8,1)            # Processing time
            add_generic(8,0)               # unknown column
            add_sap_number(8,1)            # Roll wait time
            add_generic(8,0)               # unknown column             
            add_sap_number(8,1)            # CPU time
            add_generic(8,0)               # unknown column             
            add_sap_number(8,1)            # Wait for work process
            add_generic(8,0)               # unknown column             
            add_sap_number(8,1)            # GUI time
            add_generic(8,0)               # unknown column             
            add_generic(8,1)               # Frontend roundtrips
            add_generic(8,0)               # unknown column             
            add_sap_number(8,1)            # Net time
            add_generic(8,0)               # unknown column     
            add_date(8,1)                  # timestamp of previously executed transaction
            add_generic(8,0)               # unknown column     

            # PART 2
            # from here on the stat files get messy. there are various columns of varying length.
            # things will remain chaotic until the SAP user name field
            #
            # optional number column: RFC+CPIC time 
            # if there is a 40 or 41, then print that SAP number, or 0 else
            if record_old[0:2] == "40" or record_old[0:2]=="41":
                record_new = record_new + convert_sap_number(record_old[0:8]) + ","
                record_old=record_old[8:]
                # there can be two or four surplus bytes after that number which need to be ignored
                if record_old[2:6] == "1402":
                    record_old=record_old[2:]
                if record_old[4:8] == "1402":
                    record_old=record_old[4:]
            else:
                record_new = record_new + str("0,")
            if record_old[0:2] == "02":
                record_old = "14" + record_old
            # unknown column of variable length
            # search for the pattern 1402...0300004 as the delimiter
            i=0
            found=0
            while found==0:
                if record_old[i:i+4] == "1402": 
                    if record_old[i+6:i+13]  == "0300004" or record_old[i+6:i+13]  == "0100004" or record_old[i+10:i+17] == "0300004" or record_old[i+12:i+19] == "0300004" or record_old[i+14:i+21] == "0300004" or record_old[i+16:i+23] == "0300004" or record_old[i+12:i+19]=="0000004":
                        if record_old[i+4:i+8] != "1402" and record_old[i+6:i+10] != "1402" and record_old[i+8:i+12] != "1402" and record_old[i+10:i+14] != "1402":
                            found=1
                i=i+2
                if i==len(record_old):
                    found=1
            if args.columns=="all":
                column_content = record_old[4:i-2] + ","
                column_content = column_content.replace("1402","|")
                record_new = record_new + column_content
            record_old = record_old[i+2:]
            # unknown_0d03: search for 00004, that is where the next column (a sap number) will begin
            i=0
            while record_old[i:i+5] != "00004" and i<len(record_old):
                i=i+2
            if args.columns=="all":
                record_new = record_new + record_old[0:i] + ","
            record_old = record_old[i+4:] # remove four zeros
            # unknown SAP number
            add_sap_number(8,0)
            if record_old[2:6]=="1402":
                record_old=record_old[2:] # ignore two surplus bytes after the number
            if record_old[4:8]=="1402":
                record_old=record_old[4:] # ignore four surplus bytes after the number
            # unknown_0b: the next entry usually starts with 14020b41
            if record_old[0:4]=="1402":
                record_old = record_old[4:]
            if record_old[0:4]=="1402":
                record_old = record_old[4:]
            if record_old[0:4]=="1480":
                record_old = record_old[4:]
            if record_old[0:4]=="1402":
                record_old = record_old[4:]
            # this column is fixed length: 2 bytes (usually 0b or 0c), then 8 bytes sap number, then eight zeros,
            # then another 8 bytes sap number, then eight zeros, then 8 bytes sap number (and maybe a 80 at the end)
            if args.columns=="all":
                record_new = record_new + record_old[0:2] + ","
            record_old = record_old[2:]
            add_sap_number(8,1)
            record_old = record_old[8:] # after the sap number there will be either 00000000 or 80000000, ignore that
            add_sap_number(8,1)
            record_old = record_old[8:] # after the sap number there will be either 00000000 or 80000000, ignore that
            add_sap_number(8,1)
            # remove the delimiter 1402
            if record_old[0:4]=="1402":
                record_old=record_old[4:]
            if record_old[2:6]=="1402":
                record_old=record_old[6:]
            empty_username = 0
            # the next fields are variable in size and number
            # all content until the SAP username is simply put into one large column
            # there is some standard delimiter which always precedes the SAP username,
            # this prefix is now searched:
            if record_old[0:4]=="1402":
                record_old=record_old[4:]
            index  = record_old.find("14010c00") # this pattern means that the username is empty
            if index<0 or index>100:
                index = record_old.find("14010b00") # this pattern also means that the username is empty
            if index<0 or index>100:
                index = record_old.find("14010f00") # this pattern also means that the username is empty
            if index<0 or index>100:
                index = record_old.find("14010600") # this pattern also means that the username is empty
            if index>0 and index<100:
                empty_username=1
                if args.columns=="all":
                    column_content = record_old[0:index+6] + ","
                    column_content = column_content.replace("1402","|")
                    record_new = record_new + column_content
                record_old=record_old[index+6:]
            else:
                index=find_delimiter(record_old[0:180]) # to speed up search, only use the first 180 characters of the record
                if args.columns=="all":
                    column_content = record_old[0:index+8] + ","
                    column_content = column_content.replace("1402","|")
                    record_new = record_new + column_content
                record_old=record_old[index+8:]

            # the next field is the SAP username
            if empty_username==0:
                i=0
                while record_old[i:i+4] != "1401" and len(record_old)>0 and i<48: # max length of SAP usernames is 12 characters
                    record_new = record_new + chr(int(record_old[i+2:i+4],16))
                    i=i+4
                record_new = record_new + ","
                record_old = record_old[i:]
                while record_old[0:4]=="0020": # ignore trailing blanks in the username
                    record_old = record_old[4:]
            else:
                record_new = record_new + ","
            if record_old[0:4] == "1401": # skip 6 bytes delimiter if present
                record_old = record_old[6:]
            # the next field is the 3 digits SAP client / Mandant
            i=0
            while i<3 and i*4<len(record_old):
                record_new = record_new + record_old[i*4+3]
                i=i+1
            record_new = record_new + ","
            record_old = record_old[12:]  
            # the next field is the transaction id
            for i in range(32):                          
                value =  record_old[i*4+2:i*4+4]
                try:
                    int(value,16)
                    record_new = record_new + (chr(int(value,16)))
                except ValueError:
                    record_new = record_new + "?"
            record_new = record_new + ","
            record_old = record_old[128:]  
            # the next field is the session id
            for i in range(40):
                value =  record_old[i*4+2:i*4+4]
                try:
                    int(value,16)
                    record_new = record_new + (chr(int(value,16)))
                except ValueError:
                    record_new = record_new + "?"
            record_new = record_new + ","
            record_old = record_old[160:]  
            # the next field starts with 140205
            if args.columns=="all":
                record_new = record_new + record_old[4:8] + "," # unknown field with prefix 05xx
            if record_old[0:10] == "1402051414": # ignore the surplus 14 in this special case
                record_old = record_old[10:]
            else:
                record_old = record_old[8:]
            # the next field is the network client name (can be a hostname, IP or FQDN)
            i=0
            if record_old[0:2]=="14":
               record_new = record_new + " " # the client field is empty
            else:
                if record_old[0:2] != "00": # ignore a special character at the beginning
                    record_old=record_old[4:]
                while record_old[i:i+2] != "14" and i<80:  # client limit of 20 characters
                    value =  record_old[i+2:i+4]
                    try:
                        int(value,16)
                        record_new = record_new + (chr(int(value,16)))
                    except ValueError:
                        record_new = record_new + "?"
                    i=i+4
            record_new = record_new + ","
            if i==80:
                i=i-2
            record_old = record_old[i+2:]
            # the next field is the SAP task type: dialog, batch, spool, ...
            transaction_type=record_old[0:4]
            if record_old[0:2]=="01":    
                if record_old[2:4]=="0c" or record_old[2:4]=="0a":
                    transaction_type='D'
                elif record_old[2:4]=="14":
                    transaction_type='B'
                elif record_old[2:4]=="09":
                    transaction_type='U'
                elif record_old[2:4]=="07":
                    transaction_type='T'
                elif record_old[2:4]=="0b" or record_old[2:4]=="0d" or record_old[2:4]=="08":
                    transaction_type='2'
            if record_old[0:2]=="00":
                if record_old[2:4]=="53" or record_old[2:4]=="72":
                    transaction_type='R'
                if record_old[2:4]=="52":
                    transaction_type='2'
            record_old = record_old[4:]
            record_new = record_new + transaction_type + ","
            # the next field is the program
            i=0
            while record_old[i:i+2] != "14" and i<len(record_old):
                value =  record_old[i+2:i+4]
                try:
                    int(value,16)
                    record_new = record_new + (chr(int(value,16)))
                except ValueError:
                    record_new = record_new + "?"
                i=i+4
            record_new = record_new + ","
            record_old = record_old[i+2:]
            # some unknown field
            if args.columns=="all":
                record_new = record_new + record_old[0:4] + ","
            record_old = record_old[4:]
            if record_old[0:4] == "1402":
                record_old = record_old[4:]
            # the next field might be the screen?
            i=0
            column_content=''
            while i<5 and i*4+3<len(record_old):
                column_content = column_content + record_old[i*4+3]
                i=i+1
            if args.columns=="all":
                record_new = record_new + column_content + ","
            record_old = record_old[16:]
            # the next field is the transaction
            if record_old[0:4]=="0000":
                record_new = record_new + ","  # empty transaction name, do not shorten record_old in this case
            else:
                i=0
                while record_old[i:i+2] != "14" and i+2<len(record_old): # transaction
                    record_new = record_new + chr(int(record_old[i+2:i+4],16))
                    i=i+4
                record_new = record_new + ","
                record_old = record_old[i+2:]
            # some unknown field
            if args.columns=="all":
                record_new = record_new + record_old[0:4] + ","
            record_old = record_old[4:]   
            # the next field is the previous report
            if record_old[0:2] == "00":
                i=0
                while record_old[i:i+2] != "14" and i<len(record_old): # previous report
                    record_new = record_new + chr(int(record_old[i+2:i+4],16))
                    i=i+4
            # do a plausibility check:
            # only use the row if a delimiter was found in function find_delimiter
            # and the SAP transaction type is known
            # otherwise ignore the record because it was not decoded correctly 
            # (feel free to improve the script!)
            if index<999 and len(transaction_type)==1:
                csv_string = csv_string + record_new + "\n"
    return csv_string

# define three command line arguments
parser = argparse.ArgumentParser(description='The conversion script allows three command line arguments: --file --columns --output_format')
parser.add_argument('--file', default='all', help='Which file(s) to process. Specify the file name or simply process all.')
parser.add_argument('--columns', default='relevant', help='Print out either all or only relevant columns. Many columns meanings are not yet known, these columns are omitted.')
parser.add_argument('--output_format', default='csv', help='Write files either in csv or xls format.')
args = parser.parse_args()

if args.file=="all":
    prefix = 'stat'
else:
    prefix = args.file

# define the column headers for the CSV or XLSX files
if args.columns=="all":
    columns_list = ["Rownum","Recordtype", "unknown", "FF03", "unknown", "Sections","Calday","unknown","Starttime","unknown","Endtime","unknown","Processing time","unknown","Roll wait time","unknown","CPU time","unknown","Wait for work process","unknown","GUI time","unknown","Frontend roundtrips","unknown","Net time","unknown","Previous timestamp","unknown","RFC+CPIC time","unknown_var_length","unknown_0d03","unknown_number","unknown_0b","Total memory used","Max EM used in transaction","Max EM used in dia step","unknwon_0e","Username","Client","Transactionid","Sessionid","unknown","Client","Task type","Report","unknown","unknown","Transaction","unknown","Prev Report"]
else:
    columns_list = [                                                     "Sections","Calday",          "Starttime",          "Endtime",          "Processing time",          "Roll wait time",          "CPU time",          "Wait for work process",          "GUI time",          "Frontend roundtrips",          "Net time",          "Previous timestamp",          "RFC+CPIC time",                                                                  "Total memory used","Max EM used in transaction","Max EM used in dia step",             "Username","Client","Transactionid","Sessionid",          "Client","Task type","Report",                    "Transaction",          "Prev Report"]
if args.output_format != "csv" and args.output_format != "xls":
    print("Only output formats csv or xls are possible. Invalid option: " + str(args.output_format))

# get a list of all matching stat files and process them sequentially
for file_name in os.listdir('.'):
    csv_result = ""
    if file_name.startswith(prefix) and (file_name[-1].isdigit() or len(file_name)==4):
        csv_result = read_stat_file(file_name) # read in one stat file and convert it to multiple lines in CSV format
        if args.output_format=="csv":
            output_file = file_name + ".txt"
            separator = ','
            columns_string = separator.join(columns_list) + "\n" 
            lines = csv_result.count('\n')-1
            with open(output_file, mode='w', encoding="utf-8") as f:
                f.write(columns_string)
                f.write(csv_result)
            timestamp = datetime.now()
            formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            print("Wrote file " + output_file + " with " + str(lines) + " lines of " + str(row_num) + " records from stat file at " + formatted_timestamp) # provide detailed feedback on each processed stat file
        if args.output_format=="xls":
            output_file = file_name + ".xlsx"
            df = pd.read_csv(StringIO(csv_result), engine='python', on_bad_lines='skip')
            df.columns = columns_list
            df.to_excel(output_file, index=False)
            timestamp = datetime.now()
            formatted_timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            print("Wrote file " + output_file + " with " + str(df.shape[0]) + " lines of " + str(row_num) + " records from stat file at " + formatted_timestamp) # provide detailed feedback on each processed stat file
