#!/user/bin/env python3 -tt
"""
Filtering and sorting to organize a large spreadsheet of urology telemedicine encounter information.

Organizes into a dictionary of patient objects storing/sorting encounter objects
"""
# Ongoing Questions
# - What to do for patients with no completed encounters

## Imports
import sys
import os
import pandas as pd
import numpy as np
import pdb
import pickle
import csv
import time
import datetime

## Class declarations
class Config(object):
    """Renaming and sorting conventions for this spreadsheet"""
    def __init__(self):        
        self.columns = {
            'Patient OHSU MRN': 'mrn',
            'Patient Name': 'pt_name',
            'Visit Type': 'visit_type',
            'Appointment Status': 'status',
            'Reason Appointment was Canceled': 'cancel_reason',
            'Visit Type Category Name': 'visit_category',
            'Is New Patient Visit Type?': 'new_patient',
            'Appointment Fiscal Month': 'fiscal_month',
            'Encounter Date (Sorting)': 'encounter_date',
            'Appointment Creation Date (Sorting)': 'creation_date',
            'Primary Diagnosis ICD-10 Code': 'icd',
            'Primary Diagnosis ICD-10 Description': 'icd_name',
            'Primary Visit Provider Name': 'provider',
            'Payor Name': 'payor',
            'Referral Creation Date': 'referral_date',
            'Referred By Provider Name': 'referral_provider',
            'Referred By Provider Primary Specialty (at time of referral)': 'referral_specialty',
            'Referred By Place of Service Name': 'referral_service',
            'Visit Department Name': 'dept'
            }
        
        self.virtual_types = [
            'NEW VIRTUAL VISIT',
            'VIRTUAL VISIT',
            'TELEMED HOME'
            ]
        self.phone_types = [
            'PHONE VISIT',
            'NEW PHONE VISIT'
        ]
        self.column_drops = [
            'Unnamed: 0'
            ]
        
        self.provider_drops = [
            'URO RN',
            'SCULL, DORIAN',
            'KEESLAR, MATTHEW',
            'OLSON, ASHLEY J',
            'LANGMESSER, LISA M',
            'SHREVES, HILARY A']

        self.target_fiscal_month = 0 # March = 9, 0 = off

        self.date_variables = [
            'earliest_new_date',
            'earliest_virtual_date',
            'earliest_procedure_date',
            'earliest_referral_date',
            'earliest_phone_date',
            'earliest_scheduling_date',
            'earliest_office_date',
            'earliest_completed_date']

        self.list_variables = [
        'visit_types',
        'provider_list',
        'icd_list' ]

class MRN(object):
    """Top-level patient organization"""
    def __init__(self, df, config):
        super(MRN, self).__init__()
        builder = df.iloc[0]
        self.mrn = builder.mrn
        self.pt_name = builder.pt_name
        self.visit_types = df.visit_type.dropna().unique()
        self.provider_list = df.provider.dropna().unique()
        self.icd_list = df.icd.dropna().unique()


        self.encounters = {}
        self.referral_list = []
        
        self.has_procedure = False
        self.has_phone = False
        self.has_office = False
        self.has_completed_virtual = False
        self.has_any_completed_visit = False
        self.has_completed_new_vist = False
        self.has_any_new_visit = False


        self.earliest_new_date = None
        self.earliest_virtual_date = None
        self.earliest_procedure_date = None
        self.earliest_referral_date = None
        self.earliest_phone_date = None
        self.earliest_scheduling_date = None
        self.earliest_office_date = None
        self.earliest_completed_date = None
        
        self.earliest_new_id = None
        self.earliest_virtual_id = None
        self.earliest_procedure_id = None
        self.earliest_referral_id = None
        self.earliest_phone_id = None
        self.earliest_scheduling_id = None
        self.earliest_office_id = None
        self.earliest_completed_id = None

        self.earliest_new_type = None
        self.earliest_completed_type = None
        
        self.earliest_new_icd = None
        self.earliest_phone_icd = None
        self.earliest_procedure_icd = None
        self.earliest_office_icd = None
        self.earliest_referral_icd= None
        self.earliest_scheduling_icd = None
        self.earliest_virtual_icd = None

        self.earliest_new_icd_name = None
        self.earliest_phone_icd_name = None
        self.earliest_procedure_icd_name = None
        self.earliest_office_icd_name = None
        self.earliest_referral_icd_name = None
        self.earliest_scheduling_icd_name = None
        self.earliest_virtual_icd_name = None

        self.conv_virtual_to_office = False
        self.conv_virtual_to_phone = False
        self.conv_office_to_phone = False
        self.conv_office_to_virtual = False
        self.conv_phone_to_office = False
        self.conv_phone_to_virtual = False

        self.referral_to_earliest_new_encounter = None
        self.referral_to_earliest_completed_encounter = None
        self.referral_to_earliest_completed_virtual = None
        self.referral_to_earliest_completed_phone = None

        self.new_visit_count = 0
        self.complete_new_visit_count = 0
        self.total_visit_count = 0
        self.complete_visit_count = 0
        self.cancellation_count = 0
        self.complete_phone_visit_count = 0
        self.cancelled_phone_visit_count = 0
        self.complete_office_visit_count = 0
        self.cancelled_office_visit_count = 0
        self.complete_virtual_visit_count = 0
        self.cancelled_virtual_visit_count = 0
        self.complete_procedure_visit_count = 0
        self.cancelled_procedure_visit_count = 0
        
        self.total_phone_visit_count = 0
        self.total_office_visit_count = 0
        self.total_virtual_visit_count = 0
        self.total_procedure_visit_count = 0

        self.payor_name = None
        self.primary_diagnosis_icd = None # ICD diagnosis id of the earliest visit
        self.primary_diagnosis_icd_name = None # ICD diagnosis name of the earliest visit

        
        self.create_encounters(df)
        self.analyze_encounters(df)

    def create_encounters(self, df):
        """
        MRN
        - earliest_completed_id
        - earliest_completed_date
        - earliest_completed_type

        - has_any_new_visit
        - has_completed_new_visit
        
        - new_visit_count
        - complete_new_visit_count
        - complete_visit_count
        - total_visit_count
        - cancellation_count

        """
        for index, row in df.iterrows():
            encounter = Encounter(row)

            self.payor_name = encounter.payor

            visit_type = self.determine_visit_type(encounter)

            if self.earliest_completed_id == None and encounter.is_completed:
                self.earliest_completed_id = encounter.id
                self.earliest_completed_date = encounter.date
                self.earliest_completed_type = visit_type
                self.primary_diagnosis_icd = encounter.icd_id
                self.primary_diagnosis_icd_name = encounter.icd_name

            self.has_any_completed_visit = self.has_any_completed_visit or encounter.is_completed
            
            if encounter.is_new:
                self.has_any_new_visit = True
                if encounter.is_completed:
                    self.has_completed_new_vist = True

            self.determine_dates(encounter)

            self.update_visit_counts(encounter, visit_type)

            if row.referral_date not in self.referral_list:
                self.referral_list.append(row.referral_date)

            if encounter.is_new:
                self.new_visit_count += 1
                if encounter.is_completed:
                    self.complete_new_visit_count += 1

            if encounter.is_completed:
                self.complete_visit_count += 1

            if encounter.is_cancelled:
                self.cancellation_count += 1

            self.total_visit_count += 1

            self.encounters[encounter.id] = encounter
        
    def determine_visit_type(self, encounter):
        """
        Encounter
        - is_phone
        - is_procedure
        - is_virtual
        """
        if encounter.is_virtual:
            return 'virtual'
        elif encounter.is_phone:
            return 'phone'
        elif encounter.is_procedure:
            return 'procedure'
        else:
            return 'office'

    def update_visit_counts(self, encounter, visit_type):
        if encounter.is_completed:
            if visit_type == 'virtual':
                self.complete_virtual_visit_count += 1
            elif visit_type == 'phone':
                self.complete_phone_visit_count += 1
            elif visit_type == 'procedure':
                self.complete_procedure_visit_count += 1
            elif visit_type == 'office':
                self.complete_office_visit_count += 1
        elif encounter.is_cancelled:
            if visit_type == 'virtual':
                self.cancelled_virtual_visit_count += 1
            elif visit_type == 'phone':
                self.cancelled_phone_visit_count += 1
            elif visit_type == 'procedure':
                self.cancelled_procedure_visit_count += 1
            elif visit_type == 'office':
                self.cancelled_office_visit_count += 1
        
        if visit_type == 'virtual':
            self.total_virtual_visit_count += 1
        elif visit_type == 'phone':
            self.total_phone_visit_count += 1
        elif visit_type == 'procedure':
            self.total_procedure_visit_count += 1
        elif visit_type == 'office':
            self.total_office_visit_count += 1

    def analyze_encounters(self, df):
        """
        MRN
        - earliest_new_type
        """
        if self.has_any_new_visit:
            if self.earliest_new_date == self.earliest_virtual_date:
                self.earliest_new_type = 'virtual'
            elif self.earliest_new_date == self.earliest_procedure_date:
                self.earliest_new_type = 'procedure'
            elif self.earliest_new_date == self.earliest_phone_date:
                self.earliest_new_type = 'phone'
            else:
                # This is an unvetted assumption
                self.earliest_new_type = 'office'

        self.determine_conversions()
        self.compare_dates()
        self.set_binaries()
        return

    def set_binaries(self):
        self.has_completed_office = self.complete_office_visit_count > 0
        self.has_completed_procedure = self.complete_procedure_visit_count > 0
        self.has_completed_virtual = self.complete_virtual_visit_count > 0
        self.has_completed_phone = self.complete_phone_visit_count > 0

        self.has_cancelled_office = self.cancelled_office_visit_count > 0
        self.has_cancelled_procedure = self.cancelled_procedure_visit_count > 0
        self.has_cancelled_virtual = self.cancelled_virtual_visit_count > 0
        self.has_cancelled_phone = self.cancelled_phone_visit_count > 0

        self.has_any_office = self.total_office_visit_count > 0
        self.has_any_procedure = self.total_procedure_visit_count > 0
        self.has_any_virtual = self.total_virtual_visit_count > 0
        self.has_any_phone = self.total_phone_visit_count > 0

    def compare_dates(self):
        """
        MRN
        - referral_to_earliest_new_encounter
        - referral_to_earliest_completed_encounter
        - referral_to_earliest_completed_virtual
        - referral_to_earliest_completed_phone
        """

        if self.has_completed_new_vist:
            self.referral_to_earliest_new_encounter = (self.earliest_new_date - self.earliest_referral_date).days
        if self.has_any_completed_visit:
            self.referral_to_earliest_completed_encounter = (self.earliest_completed_date - self.earliest_referral_date).days
        if self.has_completed_virtual and self.has_any_completed_visit:
            self.referral_to_earliest_completed_virtual = (self.earliest_virtual_date - self.earliest_referral_date).days
        if self.has_phone and self.has_any_completed_visit:
            self.referral_to_earliest_completed_phone = (self.earliest_phone_date - self.earliest_referral_date).days
        return

    def determine_conversions(self):
        """
        MRN
        - conv_virtal_to_office
        - conv_virtual_to_phone
        - conv_phone_to_office
        - conv_phone_to_virtual
        - conv_office_to_virtual
        - conv_office_to_phone
        """
        for encounter_id in self.encounters:
            encounter = self.encounters[encounter_id]
            if encounter.is_office and encounter.is_completed:
                if self.has_completed_virtual:
                    if self.earliest_virtual_date < encounter.date:
                        self.conv_virtual_to_office = True
                    else:
                        self.conv_office_to_virtual = True

                if self.has_phone:
                    if self.earliest_phone_date < encounter.date:
                        self.conv_phone_to_office = True
                    else:
                        self.conv_office_to_phone = True

            if encounter.is_virtual and encounter.is_completed:
                if self.has_phone:
                    if self.earliest_phone_date < encounter.date:
                        self.conv_phone_to_virtual = True
                    else:
                        self.conv_virtual_to_phone = True
        return

    def determine_dates(self, encounter):
        """
        MRN
        - earliest_procedure_date
        - earliest_procedure_id
        - earliest_phone_date
        - earliset_phone_id
        - earliest_phone_icd
        - earliest_phone_icd_name
        - earliest_referral_date
        - earliest_referral_id
        - earliest_referral_icd
        - earliest_referral_icd_name
        - earliest_new_date
        - earliest_new_id
        - earliest_new_icd
        - earliest_scheduling_date
        - earliest_scheduling_id
        - earliest_scheduling_icd
        - earliest_scheduling_icd_name
        - earliest_virtual_date
        - earliest_virtual_id
        - earliest_virtual_icd
        - earliest_virtual_icd_name
        - has_procedure
        - has_phone
        - has_completed_virtual
        - cancellation_count
        """
        if encounter.is_completed:
                # Determine if this is the earliest virtual encounter
                if encounter.is_virtual:
                    if self.earliest_virtual_date is None:
                        self.earliest_virtual_date = encounter.date
                        self.earliest_virtual_id = encounter.id
                        self.earliest_virtual_icd = encounter.icd_id
                        self.earliest_virtual_icd_name = encounter.icd_name
                        self.has_completed_virtual = True
                    else:
                        if encounter.date < self.earliest_virtual_date:
                            self.earliest_virtual_date = encounter.date
                            self.earliest_virtual_id = encounter.id
                            self.earliest_virtual_icd = encounter.icd_id
                            self.earliest_virtual_icd_name = encounter.icd_name
                            
                # Determine if this is the earliest procedure
                if encounter.is_procedure:
                    if self.earliest_procedure_date is None:
                        self.earliest_procedure_date = encounter.date
                        self.earliest_procedure_id = encounter.id
                        self.earliest_procedure_icd = encounter.icd_id
                        self.earliest_procedure_icd_name = encounter.icd_name
                        self.has_procedure = True
                    else:
                        if encounter.date < self.earliest_procedure_date:
                            self.earliest_procedure_date = encounter.date
                            self.earliest_procedure_id = encounter.id
                            self.earliest_procedure_icd = encounter.icd_id
                            self.earliest_procedure_icd_name = encounter.icd_name
                # Determine if this is the earliest new visit
                if encounter.is_new:
                    if self.earliest_new_date is None:
                        self.earliest_new_date = encounter.date
                        self.earliest_new_id = encounter.id
                        self.earliest_new_icd = encounter.icd_id
                        self.earliest_new_icd_name = encounter.icd_name
                        self.has_any_new_visit = True
                    else:
                        self.earliest_new_date = min(encounter.date, self.earliest_new_date)
                        self.earliest_new_id = encounter.id
                        self.earliest_new_icd = encounter.icd_id
                        self.earliest_new_icd_name = encounter.icd_name

                # Determine if this is the earliest phone visit
                if encounter.is_phone:
                    if self.earliest_phone_date is None:
                        self.earliest_phone_date = encounter.date
                        self.earliest_phone_id = encounter.id
                        self.earliest_phone_icd = encounter.icd_id
                        self.earliest_phone_icd_name = encounter.icd_name
                        self.has_phone = True
                    else:
                        if encounter.date < self.earliest_phone_date:
                            self.earliest_phone_date = encounter.date
                            self.earliest_phone_id = encounter.id
                            self.earliest_phone_icd = encounter.icd_id
                            self.earliest_phone_icd_name = encounter.icd_name

                # Determine if this is the earliest phone visit
                if encounter.is_office:
                    if self.earliest_office_date is None:
                        self.earliest_office_date = encounter.date
                        self.earliest_office_id = encounter.id
                        self.earliest_office_icd = encounter.icd_id
                        self.earliest_office_icd_name = encounter.icd_name
                        self.has_office = True
                    else:
                        if encounter.date < self.earliest_office_date:
                            self.earliest_office_date = encounter.date
                            self.earliest_office_id = encounter.id
                            self.earliest_office_icd = encounter.icd_id
                            self.earliest_office_icd_name = encounter.icd_name

        if encounter.is_cancelled:
            self.cancellation_count += 1

        # Determine if this is the earliest referral
        if self.earliest_referral_date is None:
            self.earliest_referral_date = encounter.referral_date
            self.earliest_referral_id = encounter.id
            self.earliest_referral_icd = encounter.icd_id
            self.earliest_referral_icd_name = encounter.icd_name
        else:
            if encounter.referral_date < self.earliest_referral_date:
                self.earliest_referral_date = encounter.referral_date
                self.earliest_referral_id = encounter.id
                self.earliest_referral_icd = encounter.icd_id
                self.earliest_referral_icd_name = encounter.icd_name
        
        # Determine if this is the earliest scheduling date
        if self.earliest_scheduling_date is None:
            self.earliest_scheduling_date = encounter.scheduling_date
            self.earliest_scheduling_id = encounter.id
            self.earliest_scheduling_icd = encounter.icd_id
            self.earliest_scheduling_icd_name = encounter.icd_name
        else:
            if encounter.scheduling_date < self.earliest_scheduling_date:
                self.earliest_scheduling_date = encounter.scheduling_date
                self.earliest_scheduling_id = encounter.id
                self.earliest_scheduling_icd = encounter.icd_id
                self.earliest_scheduling_icd_name = encounter.icd_name

class Encounter(object):
    """One row in the original spreadsheet"""
    def __init__(self, row):
        super(Encounter, self).__init__()

        self.mrn = row.mrn
        self.pt_name = row.pt_name
        self.id = row.encounter_id
        self.provider = row.provider
        self.department = row.dept
        self.type = row.visit_type
        self.date = row.encounter_date
        self.month = row.fiscal_month
        self.status = row.status
        
        self.is_procedure = row.visit_category == 'Procedure'
        self.is_visit = row.visit_category == 'Office Visit'
        self.is_completed = row.status == 'Completed'
        self.is_incomplete = not self.is_completed
        self.is_new = row.new_patient == 'Yes'
        self.is_virtual = row.is_virtual == 1
        self.is_phone = row.is_phone == 1
        self.is_office = self.is_visit and not self.is_virtual and not self.is_phone
        self.is_cancelled = row.status == 'Canceled'
        
        self.scheduling_date = row.creation_date
        self.icd_id = row.icd
        self.icd_name = row.icd_name
        
        self.referral_date = row.referral_date
        self.referral_provider = row.referral_provider
        self.referral_specialty = row.referral_specialty
        self.referral_service = row.referral_service
        self.payor = row.payor
        
## Function declarations
def apply_config(df, config):
    # Apply naming conventions
    df = df.rename(columns=config.columns)
    
    # Drop unused columns
    df = df.drop(config.column_drops, axis=1)
    
    # Drop unused providers
    for provider in config.provider_drops:
        df = df[df.provider != provider]
    
    # Sort first by mrn, then by encounter date
    df.sort_values(['mrn', 'encounter_date'], inplace=True)
    
    # Create basic values
    df['referral_to_encounter'] = (df['encounter_date'] - df['referral_date']).dt.days
    df['creation_to_encounter'] = (df['encounter_date'] - df['creation_date']).dt.days
    df['is_virtual'] = df.visit_type.isin(config.virtual_types).astype(int)
    df['is_phone'] = df.visit_type.isin(config.phone_types).astype(int)
    df['encounter_id'] = df.index + 1

    # to be filled in
    df['virtual_before_procedure'] = 0
    
    return df

def build_mrns(df, config):
    # Main engine for organzing data
    mrns = df.mrn.unique()
    patients = {}
    for mrn in mrns:
        visits = df[df.mrn == mrn]
        if (config.target_fiscal_month in visits.fiscal_month.values) or config.target_fiscal_month == 0:
            patient = MRN(visits, config)
            patients[mrn] = patient
    return patients

def write_summary_csv(patients, config):
    # Currently very coarse, can improve to be more readable
    pt = next(iter(patients.values()))
    fieldnames = [*vars(pt).keys()]
    fieldnames.remove('encounters')
    with open('data/summary.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for pt in patients:
            di = vars(patients[pt])
            del di['encounters']
            di = adjust_fields(di, config.date_variables, config.list_variables)
            
            writer.writerow(di)
    return

def adjust_fields(di, date_vars, list_vars):
    try:
        for date_var in date_vars:
            if di[date_var] is not None:
                di[date_var] = str(di[date_var]).split()[0]
        for list_var in list_vars:
            list_str = [str(element) for element in di[list_var]]
            joined = ", ".join(list_str)
            di[list_var] = joined
        for key, item in di.items():
            if type(item) is list:
                if type(item[0]) is not str and type(item[0]) is not int:
                    new_item = []
                    for el in item:
                        el = str(di[date_var]).split()[0]
                        new_item.append(el)
                    item = new_item
                list_str = [str(element) for element in item]
                joined = ", ".join(list_str)
                di[key] = joined
    except:
        pdb.set_trace()
    return di

def pt_satisfaction_csv(patients):

    header = ['mrn', 'name', 'start_date', 'end_date']
    with open('data/satisfaction_mrns.csv', 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        for pt in patients:
            earliest_enc_date = None
            latest_enc_date = None
            for enc in patients[pt].encounters:
                encounter = patients[pt].encounters[enc]
                count = 0
                if earliest_enc_date is None:
                    earliest_enc_date = encounter.date
                    latest_enc_date = encounter.date
                    count += 1
                else:
                    count += 1
                    try:
                        earliest_enc_date = min(encounter.date, earliest_enc_date)
                        latest_enc_date = max(encounter.date, latest_enc_date)
                    except:
                        pdb.set_trace()
            writer.writerow([patients[pt].mrn, patients[pt].pt_name, str(earliest_enc_date).split()[0], str(latest_enc_date).split()[0]])
    return

def update_fields(patients):
    pt = next(iter(patients.values()))
    fieldnames = [*vars(pt).keys()]

    for pt in patients:
        k = patients[pt]
        ref_list = k.referral_list
        refs = []
        for ref in ref_list:
            rewrite = str(ref).split()[0]
            refs.append(rewrite)
        k.referral_list = refs
        for attr, value in k.__dict__.items():
            pdb.set_trace()
            print(attr, value)

        pdb.set_trace()

def main():
    ##
    ## Use the defined functions
    ##

    # change this filepath string depending on where the original spreadsheet resides
    df = pd.read_excel('data/sheet.xlsx')

    # Apply filtering and renaming rules (config)
    config = Config()
    df = apply_config(df, config)

    # Build and sort patient objects, dump them into a dictionary
    patients = build_mrns(df, config)

    # Save data off so the sorting and filtering only has to occur once
    with open('data/dump.pickle', 'wb') as f:
        pickle.dump(patients, f, pickle.HIGHEST_PROTOCOL)

    # Write summary output
    pt_satisfaction_csv(patients)
    # update_fields(patients)
    write_summary_csv(patients, config)

# Main body
if __name__ == '__main__':
    main()