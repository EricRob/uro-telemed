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
            'OLSON, ASHLEY J']

        self.target_fiscal_month = 9 # March

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
        self.has_virtual = False
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

        self.create_encounters(df)
        self.analyze_encounters(df)

    def create_encounters(self, df):
        for index, row in df.iterrows():
            encounter = Encounter(row)

            if self.earliest_completed_id == None and encounter.is_completed:
                self.earliest_completed_id = encounter.id
                self.earliest_completed_date = encounter.date
                self.earliest_completed_type = self.determine_visit_type(encounter)

            self.has_any_completed_visit = self.has_any_completed_visit or encounter.is_completed
            
            if encounter.is_new:
                self.has_any_new_visit = True
                if encounter.is_completed:
                    self.has_completed_new_vist = True

            self.determine_dates(encounter)
            if row.referral_date not in self.referral_list:
                self.referral_list.append(row.referral_date)

            if encounter.is_new:
                self.new_visit_count += 1
                if encounter.is_completed:
                    self.complete_new_visit_count += 1

            if encounter.is_completed:
                self.complete_visit_count += 1

            self.total_visit_count += 1

            self.encounters[encounter.id] = encounter
        
    def determine_visit_type(self, encounter):
        if encounter.is_virtual:
            return 'virtual'
        elif encounter.is_phone:
            return 'phone'
        elif encounter.is_procedure:
            return 'procedure'
        else:
            return 'office'

    def analyze_encounters(self, df):
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
        return

    def compare_dates(self):
        if self.has_completed_new_vist:
            self.referral_to_earliest_new_encounter = (self.earliest_new_date - self.earliest_referral_date).days
        if self.has_any_completed_visit:
            self.referral_to_earliest_completed_encounter = (self.earliest_completed_date - self.earliest_referral_date).days
        if self.has_virtual and self.has_any_completed_visit:
            self.referral_to_earliest_completed_virtual = (self.earliest_virtual_date - self.earliest_referral_date).days
        if self.has_phone and self.has_any_completed_visit:
            self.referral_to_earliest_completed_phone = (self.earliest_phone_date - self.earliest_referral_date).days
        return

    def determine_conversions(self):
        for encounter_id in self.encounters:
            encounter = self.encounters[encounter_id]
            if encounter.is_office and encounter.is_completed:
                if self.has_virtual:
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
        if encounter.is_completed:
                # Determine if this is the earliest virtual encounter
                if encounter.is_virtual:
                    if self.earliest_virtual_date is None:
                        self.earliest_virtual_date = encounter.date
                        self.earliest_virtual_id = encounter.id
                        self.has_virtual = True
                    else:
                        if encounter.date < self.earliest_virtual_date:
                            self.earliest_virtual_date = encounter.date
                            self.earliest_virtual_id = encounter.id

                # Determine if this is the earliest procedure
                if encounter.is_procedure:
                    if self.earliest_procedure_date is None:
                        self.earliest_procedure_date = encounter.date
                        self.earliest_procedure_id = encounter.id
                        self.has_procedure = True
                    else:
                        if encounter.date < self.earliest_procedure_date:
                            self.earliest_procedure_date = encounter.date
                            self.earliest_procedure_id = encounter.id

                # Determine if this is the earliest new visit
                if encounter.is_new:
                    if self.earliest_new_date is None:
                        self.earliest_new_date = encounter.date
                        self.has_new = True
                    else:
                        self.earliest_new_date = min(encounter.date, self.earliest_new_date)

                # Determine if this is the earliest phone visit
                if encounter.is_phone:
                    if self.earliest_phone_date is None:
                        self.earliest_phone_date = encounter.date
                        self.earliest_phone_id = encounter.id
                        self.has_phone = True
                    else:
                        if encounter.date < self.earliest_phone_date:
                            self.earliest_phone_date = encounter.date
                            self.earliest_phone_id = encounter.id

        # Determine if this is the earliest referral
        if self.earliest_referral_date is None:
            self.earliest_referral_date = encounter.referral_date
            self.earliest_referral_id = encounter.id
        else:
            if encounter.referral_date < self.earliest_referral_date:
                self.earliest_referral_date = encounter.referral_date
                self.earliest_referral_id = encounter.id
        
        # Determine if this is the earliest scheduling date
        if self.earliest_scheduling_date is None:
            self.earliest_scheduling_date = encounter.scheduling_date
            self.earliest_scheduling_id = encounter.id
        else:
            if encounter.scheduling_date < self.earliest_scheduling_date:
                self.earliest_scheduling_date = encounter.scheduling_date
                self.earliest_scheduling_id = encounter.id

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
        if config.target_fiscal_month in visits.fiscal_month.values:
            patient = MRN(visits, config)
            patients[mrn] = patient
    return patients

def write_summary_csv(patients):
    # Currently very coarse, can improve to be more readable
    pt = next(iter(patients.values()))
    fieldnames = [*vars(pt).keys()]
    with open('data/summary.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for pt in patients:
            writer.writerow(vars(patients[pt]))
        
    return


def main()
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
    write_summary_csv(patients)

# Main body
if __name__ == '__main__':
    main()