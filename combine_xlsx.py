#!/user/bin/env python3 -tt
"""
Module documentation.
"""

# Imports
import sys
import os
import pandas as pd
import numpy as np
from openpyxl import load_workbook
import pdb
import re
import warnings
warnings.simplefilter("ignore")
source_path = os.path.join("/Users/ericrobinson/Documents/GitHub/uro-telemed/r_output")
output_name = 'r_output.xlsx'
output_path = os.path.join(source_path,output_name)
final_summary_name = 'summary.xlsx'
final_summary_path = os.path.join(source_path, final_summary_name)
final_writer = pd.ExcelWriter(final_summary_path, engine = 'xlsxwriter')

for root, dirs, files in os.walk(source_path):
    writer = pd.ExcelWriter(output_path, engine = 'xlsxwriter')
    df_cross4 = pd.DataFrame()
    df_summ4 = pd.DataFrame()
    df_age4_data = pd.DataFrame()
    df_summ5 = pd.DataFrame()
    idx_tbl4_summ = [[], []]
    idx_tbl4_ages = [[],[]]
    idx_tbl4_zips = [[],[]]
    idx_tbl5_summ = [[], []]
    idx_tbl5_ages = [[],[]]
    idx_tbl5_zips = [[],[]]
    col_heads = ['office', 'virtual', 'p-value']
    for file in sorted(files):
        if '.xlsx' in file and output_name not in file and final_summary_name not in file:
            # Sheet merging
            print(f'writing sheet {file}')
            df = pd.read_excel(os.path.join(root,file), engine="openpyxl")
            del df['Unnamed: 0']
            df.to_excel(writer, index = False, sheet_name = file.split('.')[0], engine="openpyxl")
            if file in ['tbl1.xlsx', 'tbl2.xlsx', 'tbl3.xlsx']:
                df.to_excel(final_writer, index = False, sheet_name = file.split('.')[0], engine='openpyxl')
            # Reformatting
            if 'tbl4cross' in file:
                df_cross4 = pd.concat([df_cross4, df], ignore_index=True)
            if 'tbl4summary' in file:
                category = file.split('summary_')[1].split('.')[0]
                row_name = ""
                tbl = ""
                vals = []
                ids = []
                for index, row in df.iterrows():
                    current_row_id = row['**Characteristic**'].split(' - ')[1]
                    if row_name != current_row_id:
                        if len(vals) > 0:
                            if type(tbl) is str:
                                tbl = np.array([arr])
                            else:
                                tbl = np.r_[tbl,[arr]]
                        row_name = current_row_id
                        arr = np.array([row_name], dtype=object)
                        
                    current_val = row['**Characteristic**'].split(' - ')[0]
                    arr = np.append(arr, row[1:].values)
                    if current_row_id not in ids:
                        idx_tbl4_summ[0].append(category)
                        idx_tbl4_summ[1].append(current_row_id)
                        ids.append(current_row_id)
                    if current_val not in vals:
                        vals.append(current_val)
                tbl = np.r_[tbl,[arr]]
                columns = []
                for i in range(len(vals)):
                    columns = columns + col_heads
                upper_idx = np.repeat(vals,3)
                arrays = [upper_idx, np.array(columns)]
                df_q = pd.DataFrame(tbl[:,1:], index=tbl[:,0], columns=arrays)
                df_summ4 = pd.concat([df_summ4, df_q])

            if 'tbl5summary' in file:
                category = file.split('summary_')[1].split('.')[0]
                row_name = ""
                tbl = ""
                vals = []
                ids = []
                for index, row in df.iterrows():
                    current_row_id = row['**Characteristic**'][row['**Characteristic**'].index(' ')+1:]
                    if row_name != current_row_id:
                        if len(vals) > 0:
                            temp = []
                            for x in arr:
                                if type(x) is str and ' - ' in x:
                                    new = x.split(' - ')
                                    # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                                    ret = f'{new[0]} ({new[1]})'
                                    temp.append(ret)
                                else:
                                    temp.append(x)
                            if type(tbl) is str:
                                tbl = np.array([np.array(temp)])
                            else:
                                tbl = np.r_[tbl,[np.array(temp)]]
                        row_name = current_row_id
                        arr = np.array([row_name], dtype=object)
                        
                    current_val = row['**Characteristic**'].split()[0]
                    arr = np.append(arr, row[1:].values)
                    if current_row_id not in ids:
                        idx_tbl5_summ[0].append(category)
                        idx_tbl5_summ[1].append(current_row_id)
                        ids.append(current_row_id)
                    if current_val not in vals:
                        vals.append(current_val)
                temp = []
                for x in arr:
                    if type(x) is str and " - " in x:
                        new = x.split(' - ')
                        # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                        ret = f'{new[0]} ({new[1]})'
                        temp.append(ret)
                    else:
                        temp.append(x)
                tbl= np.r_[tbl, [np.array(temp)]]
                columns = []
                for i in range(len(vals)):
                    columns = columns + col_heads
                upper_idx = np.repeat(vals,3)
                arrays = [upper_idx, np.array(columns)]
                df_q = pd.DataFrame(tbl[:,1:], index=tbl[:,0], columns=arrays)
                df_summ5 = pd.concat([df_summ5, df_q])

            if 'tbl4age' in file:
                tbl_age4_cross = pd.DataFrame(data={'**Characteristic**' : ['__ages__'],
                'office': [''],
                'virtual': [''],
                '**Total**': [''],
                '**p-value**': ['']})
                
                vals = []
                ids = []
                row_name = ''
                arr_cross = ''
                tbl_age = ''
                arr_age = ''
                for index, row in df.iterrows():
                    if 'ages NA' in row['**Characteristic**']:
                        break
                    age_range = re.findall('\d+', row['**Characteristic**'])
                    age_str = f'{age_range[0]}-{age_range[1]}'
                    if 'ages' in row['**Characteristic**']:
                        row_vals = row.values
                        int1 = int(re.findall('\d+', row_vals[1])[0])
                        int2 = int(re.findall('\d+', row_vals[2])[0])
                        arr_cross = {'**Characteristic**' : [age_str],
                        'office': [int1],
                        'virtual': [int2],
                        '**Total**': [int1 + int2],
                        '**p-value**': ['']}

                        tbl_age4_cross = pd.concat([tbl_age4_cross, pd.DataFrame(data=arr_cross)])
                    else:
                        current_val = row['**Characteristic**'].split(' - ')[0]
                        current_row_id = age_str

                        if row_name != current_row_id:
                            if len(vals) > 0:
                                if type(tbl_age) is str:
                                    tbl_age = np.array([arr_age])
                                else:
                                    tbl_age = np.r_[tbl_age, [arr_age]]
                            row_name = current_row_id
                            arr_age = np.array([row_name], dtype=object)

                        if current_val not in vals:
                            vals.append(current_val)
                        
                        if current_row_id not in ids:
                            idx_tbl4_summ[0].append('age')
                            idx_tbl4_summ[1].append(current_row_id)
                            idx_tbl4_ages[0].append('age')
                            idx_tbl4_ages[1].append(current_row_id)
                            ids.append(current_row_id)

                        arr_age = np.append(arr_age, row[1:].values)
                tbl_age = np.r_[tbl_age, [arr_age]]
                columns = []
                for i in range(len(vals)):
                    columns = columns + col_heads
                upper_idx = np.repeat(vals,3)
                arrays = [upper_idx, np.array(columns)]
                df_age4 = pd.DataFrame(tbl_age[:,1:], index=tbl_age[:,0], columns=arrays)
            
            if 'tbl4zip' in file:
                tbl_zip4_cross = pd.DataFrame(data={'**Characteristic**' : ['__zipcode ranges__'],
                'office': [''],
                'virtual': [''],
                '**Total**': [''],
                '**p-value**': ['']})
                
                vals = []
                ids = []
                row_name = ""
                arr_cross = ''
                tbl_zip = ''
                arr_zip = ''
                for index, row in df.iterrows():
                    if 'Zipcode Distance NA' in row['**Characteristic**']:
                        break
                    zip_range = re.findall('\d+', row['**Characteristic**'])
                    zip_str = f'{zip_range[0]}-{zip_range[1]}'
                    if 'Zipcode Distance' in row['**Characteristic**']:
                        row_vals = row.values
                        int1 = int(re.findall('\d+', row_vals[1])[0])
                        int2 = int(re.findall('\d+', row_vals[2])[0])
                        arr_cross = {'**Characteristic**' : [zip_str],
                        'office': [int1],
                        'virtual': [int2],
                        '**Total**': [int1 + int2],
                        '**p-value**': ['']}

                        tbl_zip4_cross = pd.concat([tbl_zip4_cross, pd.DataFrame(data=arr_cross)])
                    else:
                        current_val = row['**Characteristic**'].split(' - ')[0]
                        current_row_id = zip_str

                        if row_name != current_row_id:
                            if len(vals) > 0:
                                if type(tbl_zip) is str:
                                    tbl_zip = np.array([arr_zip])
                                else:
                                    tbl_zip = np.r_[tbl_zip, [arr_zip]]
                            row_name = current_row_id
                            arr_zip = np.array([row_name], dtype=object)

                        if current_val not in vals:
                            vals.append(current_val)
                        
                        if current_row_id not in ids:
                            idx_tbl4_summ[0].append('zipcode range')
                            idx_tbl4_summ[1].append(current_row_id)
                            idx_tbl4_zips[0].append('zipcode range')
                            idx_tbl4_zips[1].append(current_row_id)
                            ids.append(current_row_id)

                        arr_zip = np.append(arr_zip, row[1:].values)
                tbl_zip = np.r_[tbl_zip, [arr_zip]]
                columns = []
                for i in range(len(vals)):
                    columns = columns + col_heads
                upper_idx = np.repeat(vals,3)
                arrays = [upper_idx, np.array(columns)]
                df_zip4 = pd.DataFrame(tbl_zip[:,1:], index=tbl_zip[:,0], columns=arrays)

            if 'tbl5age' in file:
                tbl_age5_cross = pd.DataFrame(data={'**Characteristic**' : ['__ages__'],
                'office': [''],
                'virtual': [''],
                '**Total**': [''],
                '**p-value**':row['**p-value**']})
                
                vals = []
                ids = []
                row_name = ""
                arr_cross = ''
                tbl_age = ''
                arr_age = ''
                for index, row in df.iterrows():
                    if 'ages NA' in row['**Characteristic**']:
                        break
                    if 'ages' in row['**Characteristic**']:
                        continue
                    age_range = re.findall('\d+', row['**Characteristic**'])
                    age_str = f'{age_range[0]}-{age_range[1]}'
                    current_val = row['**Characteristic**'].split()[0]
                    current_row_id = age_str

                    if row_name != current_row_id:
                        if len(vals) > 0:
                            if type(tbl_age) is str:
                                temp = []
                                for x in arr_age:
                                    if type(x) is str and " - " in x:
                                        new = x.split(' - ')
                                        # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                                        ret = f'{new[0]} ({new[1]})'
                                        temp.append(ret)
                                    else:
                                        temp.append(x)
                                arr_age = np.array(temp)
                                tbl_age = np.array([arr_age])
                            else:
                                temp = []
                                for x in arr_age:
                                    if type(x) is str and " - " in x:
                                        new = x.split(' - ')
                                        # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                                        ret = f'{new[0]} ({new[1]})'
                                        temp.append(ret)
                                    else:
                                        temp.append(x)
                                arr_age = np.array(temp)
                                # pdb.set_trace()
                                tbl_age = np.r_[tbl_age, [arr_age]]
                        row_name = current_row_id
                        arr_age = np.array([row_name], dtype=object)

                    if current_val not in vals:
                        vals.append(current_val)
                    
                    if current_row_id not in ids:
                        idx_tbl5_summ[0].append('age')
                        idx_tbl5_summ[1].append(current_row_id)
                        idx_tbl5_ages[0].append('age')
                        idx_tbl5_ages[1].append(current_row_id)
                        ids.append(current_row_id)

                    arr_age = np.append(arr_age, row[1:].values)
                temp = []
                for x in arr_age:
                    if type(x) is str and " - " in x:
                        new = x.split(' - ')
                        # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                        ret = f'{new[0]} ({new[1]})'
                        temp.append(ret)
                    else:
                        temp.append(x)
                tbl_age = np.r_[tbl_age, [np.array(temp)]]
                columns = []
                for i in range(len(vals)):
                    columns = columns + col_heads
                upper_idx = np.repeat(vals,3)
                arrays = [upper_idx, np.array(columns)]
                df_age5 = pd.DataFrame(tbl_age[:,1:], index=tbl_age[:,0], columns=arrays)

            if 'tbl5zip' in file:                
                vals = []
                ids = []
                row_name = ""
                arr_cross = ''
                tbl_zip = ''
                arr_zip = ''
                for index, row in df.iterrows():
                    if 'Zipcode range NA' in row['**Characteristic**']:
                        break
                    if 'Zipcode range' in row['**Characteristic**']:
                        continue
                    zip_range = re.findall('\d+', row['**Characteristic**'])
                    zip_str = f'{zip_range[0]}-{zip_range[1]}'
                    current_val = row['**Characteristic**'].split()[0]
                    current_row_id = zip_str

                    if row_name != current_row_id:
                        if len(vals) > 0:
                            if type(tbl_zip) is str:
                                temp = []
                                for x in arr_zip:
                                    if type(x) is str and " - " in x:
                                        new = x.split(' - ')
                                        # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                                        ret = f'{new[0]} ({new[1]})'
                                        temp.append(ret)
                                    else:
                                        temp.append(x)
                                arr_zip = np.array(temp)
                                tbl_zip = np.array([arr_zip])
                            else:
                                temp = []
                                for x in arr_zip:
                                    if type(x) is str and " - " in x:
                                        new = x.split(' - ')
                                        # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                                        ret = f'{new[0]} ({new[1]})'
                                        temp.append(ret)
                                    else:
                                        temp.append(x)
                                arr_zip = np.array(temp)
                                # pdb.set_trace()
                                tbl_zip = np.r_[tbl_zip, [arr_zip]]
                        row_name = current_row_id
                        arr_zip = np.array([row_name], dtype=object)

                    if current_val not in vals:
                        vals.append(current_val)
                    
                    if current_row_id not in ids:
                        idx_tbl5_summ[0].append('zipcode range')
                        idx_tbl5_summ[1].append(current_row_id)
                        idx_tbl5_zips[0].append('zipcode range')
                        idx_tbl5_zips[1].append(current_row_id)
                        ids.append(current_row_id)

                    arr_zip = np.append(arr_zip, row[1:].values)
                temp = []
                for x in arr_zip:
                    if type(x) is str and " - " in x:
                        new = x.split(' - ')
                        # ret = f'{new[0]} ({new[1]}) [{new[2]}]'
                        ret = f'{new[0]} ({new[1]})'
                        temp.append(ret)
                    else:
                        temp.append(x)
                tbl_zip = np.r_[tbl_zip, [np.array(temp)]]
                columns = []
                for i in range(len(vals)):
                    columns = columns + col_heads
                upper_idx = np.repeat(vals,3)
                arrays = [upper_idx, np.array(columns)]
                df_zip5 = pd.DataFrame(tbl_zip[:,1:], index=tbl_zip[:,0], columns=arrays)

                
df4_cross = pd.concat([tbl_age4_cross, df_cross4, tbl_zip4_cross])
df4_cross = df4_cross.fillna('-')
df4_cross.to_excel(writer, index = False, sheet_name = "tbl4cross", engine='openpyxl')
df4_cross.to_excel(final_writer, index = False, sheet_name = "tbl4counts", engine='openpyxl')

df4 = pd.concat([df_age4, df_summ4, df_zip4])
df4.index = idx_tbl4_summ
df4 = df4.fillna('-')
df4.to_excel(final_writer, sheet_name = "tbl4", engine='openpyxl')
df5 = pd.concat([df_age5, df_summ5, df_zip5])
df5.index = idx_tbl5_summ
df5 = df5.fillna('-')
df5.to_excel(final_writer, sheet_name = "tbl5", engine='openpyxl')
writer.save()
final_writer.save()


# Global variables

# Class declarations

# Function declarations
