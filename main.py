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
import argparse
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu, f_oneway

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
        self.completed_encounter_dates = []
        
        self.has_procedure = False
        self.has_phone = False
        self.has_office = False
        self.has_completed_virtual = False
        self.has_any_completed_visit = False
        self.has_completed_new_visit = False
        self.has_new = False

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

        - has_new
        - has_completed_new_visit
        
        - new_visit_count
        - complete_new_visit_count
        - complete_visit_count
        - total_visit_count

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
            elif encounter.is_completed and encounter.date < self.earliest_completed_date:
                pdb.set_trace()
                self.earliest_completed_id = encounter.id
                self.earliest_completed_date = encounter.date
                self.earliest_completed_type = visit_type
                self.primary_diagnosis_icd = encounter.icd_id
                self.primary_diagnosis_icd_name = encounter.icd_name                

            self.has_any_completed_visit = self.has_any_completed_visit or encounter.is_completed
            
            if encounter.is_new:
                self.has_new = True
                if encounter.is_completed:
                    self.has_completed_new_visit = True

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
        if self.has_new:
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

        if self.has_completed_new_visit:
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
                
                if encounter.date not in self.completed_encounter_dates:
                    self.completed_encounter_dates.append(encounter.date)

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
                        self.has_new = True
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

class PtClass(object):
    """docstring for PtClass"""
    def __init__(self, pt_dict, visit_type, config):
        self.type = visit_type
        self.pt_dict = pt_dict
        self.pt_count = len(pt_dict)
        self.config = config
        self.patients_with_canceled_procedure = 0
        self.patients_with_completed_procedure = 0
        self.patients_with_completed_after_cancelled_procedure = 0
        self.first_visit_to_first_procedure_days = self.calc_first_visit_to_first_procedure_days()
        self.referral_to_first_visit_days = self.calc_referral_to_first_visit_days()
        self.referral_to_first_procedure_days = self.calc_referral_to_first_procedure_days()
        self.scheduling_to_first_visit_days = self.calc_scheduling_to_first_visit_days()
        self.scheduling_to_first_procedure_days = self.calc_scheduling_to_first_procedure_days()
        self.cancelled_appointments = self.calc_cancelled_appointments()
        self.cancelled_procedures = self.calc_cancelled_procedures()
        self.completed_appointments, self.total_appointments = self.calc_completed_appointments()

        self.total_procedures = self.calc_total_procedures()
        self.total_cancelled_procedures = sum(self.cancelled_procedures)

        self.visits_until_first_procedure_count = self.calc_visits_until_first_procedure()
        self.conversions_to_in_person = self.calc_conversions_to_in_person()

    def calc_conversions_to_in_person(self):
        count = 0
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            if self.type == 'virtual':
                if pt.conv_virtual_to_office:
                    count += 1
            elif self.type == 'phone':
                if pt.conv_phone_to_office:
                    count += 1
        return count


    def calc_completed_appointments(self):
        values_one = []
        values_two = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            visits_count = 0
            for encounter in pt.encounters:
                if pt.encounters[encounter].is_completed:
                    visits_count += 1
            values_one.append(visits_count)
            values_two.append(len(pt.encounters))
        return values_one, values_two

    def calc_visits_until_first_procedure(self):
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            earliest_visit_date = None
            visits_count = 0
            if pt.has_procedure:
                looping = True
                for encounter in pt.encounters:
                    if looping:
                        enc = pt.encounters[encounter]
                        if enc.is_visit and enc.is_completed:
                            if earliest_visit_date:
                                if enc.date < earliest_visit_date:
                                    earliest_visit_date = enc.date
                            else:
                                earliest_visit_date = enc.date
                            visits_count += 1
                        elif enc.is_procedure and enc.is_completed:
                            values.append(visits_count)
                            looping = False
            values.append(visits_count)
        return values

    def calc_first_visit_to_first_procedure_days(self):
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            if pt.has_procedure:
                earliest_visit = pt.earliest_completed_date
                first_procedure = pt.earliest_procedure_date
                values.append((first_procedure - earliest_visit).days)
        return values

    def calc_referral_to_first_visit_days(self):
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            if pt.has_any_completed_visit:
                visit = pt.earliest_completed_date
                referral_date = pt.earliest_referral_date
                values.append((visit - referral_date).days)
        return values

    def calc_referral_to_first_procedure_days(self):
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            if pt.has_procedure:
                self.patients_with_completed_procedure += 1
                referral_date = pt.earliest_referral_date
                first_procedure = pt.earliest_procedure_date
                values.append((first_procedure - referral_date).days)
        return values

    def calc_scheduling_to_first_visit_days(self):
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            if pt.has_procedure:
                scheduling_date = pt.earliest_scheduling_date
                visit = pt.earliest_completed_date
                values.append((visit - scheduling_date).days)
        return values

    def calc_scheduling_to_first_procedure_days(self):
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            if pt.has_procedure:
                scheduling_date = pt.earliest_scheduling_date
                first_procedure = pt.earliest_procedure_date
                values.append((first_procedure - scheduling_date).days)
        return values

    def calc_cancelled_appointments(self):
        #All cancellations, not just of the initial type
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            values.append(pt.cancellation_count)
        return values

    def calc_cancelled_procedures(self):
        values = []
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            values.append(pt.cancelled_procedure_visit_count)
            if pt.cancelled_procedure_visit_count > 0:
                self.patients_with_canceled_procedure += 1

        return values

    def calc_total_procedures(self):
        total_procedures = 0
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            for encounter in pt.encounters:
                if pt.encounters[encounter].is_procedure:
                    total_procedures += 1
        return total_procedures

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

def sort_patients(patients, config):
    no_new_visits = []
    virtual_new = []
    office_new = []
    phone_new = []

    for mrn in patients:
        pt = patients[mrn]
        if pt.has_new:
            if pt.earliest_completed_type == 'virtual':
                virtual_new.append(mrn)
            elif pt.earliest_completed_type == 'office':
                office_new.append(mrn)
            elif pt.earliest_completed_type == 'phone':
                phone_new.append(mrn)
        else:
            no_new_visits.append(mrn)

    virtual = PtClass({key: patients[key] for key in virtual_new}, 'virtual', config)
    office = PtClass({key: patients[key] for key in office_new}, 'office', config)
    phone = PtClass({key: patients[key] for key in phone_new}, 'phone', config)
    no_new = PtClass({key: patients[key] for key in no_new_visits}, 'no_new', config)

    return virtual, office, phone, no_new

def compare_groups(virtual, office, phone):
    fig, axs = plt.subplots(3,2, tight_layout=True)
    labels = ['virtual', 'office', 'phone']



    # Number of days from referral to first completed visit
    draw_hist(axs[0,0],
        virtual.first_visit_to_first_procedure_days,
        office.first_visit_to_first_procedure_days,
        phone.first_visit_to_first_procedure_days,
        labels, 100, 'First visit to first procedure', 'Days', bins=25)
    draw_hist(axs[0,1],
        virtual.referral_to_first_procedure_days,
        office.referral_to_first_procedure_days,
        phone.referral_to_first_procedure_days,
        labels, 200, 'Referral to first procedure', 'Days')
    draw_hist(axs[1,0],
        virtual.scheduling_to_first_visit_days,
        office.scheduling_to_first_visit_days,
        phone.scheduling_to_first_visit_days,
        labels, 110, 'Scheduling to first visit', 'Days')
    draw_hist(axs[1,1],
        virtual.referral_to_first_visit_days,
        office.referral_to_first_visit_days,
        phone.referral_to_first_visit_days,
        labels, 400,'Referral to first visit', 'Days')
    draw_hist(axs[2,0],
        virtual.scheduling_to_first_procedure_days,
        office.scheduling_to_first_procedure_days,
        phone.scheduling_to_first_procedure_days,
        labels, 200,'Scheduling to first procedure', 'Days')
    axs[0,1].legend(loc='upper right')
    
    columns = labels
    rows = [
    'Pts with cancelled procedure (%)',
    'Pts with procedure (%)',
    'Pts with cancelled appts (%)',
    'Visits until first procedure',
    'Conversions to in-person'
    ]

    cellText = []
    
    cancelled_procedures = [
    np.count_nonzero(virtual.cancelled_procedures) / len(virtual.cancelled_procedures),
    np.count_nonzero(office.cancelled_procedures) / len(office.cancelled_procedures),
    np.count_nonzero(phone.cancelled_procedures) / len(phone.cancelled_procedures)
    ]
    cancelled_procedures = [f'{i*100:.1f}%' for i in cancelled_procedures]

    patients_with_procedure =[
    virtual.patients_with_completed_procedure / virtual.pt_count,
    office.patients_with_completed_procedure / office.pt_count,
    phone.patients_with_completed_procedure / phone.pt_count,
    ]

    patients_with_procedure = [f'{i*100:.1f}%' for i in patients_with_procedure]
    patients_with_cancelled_appts = [
    np.count_nonzero(virtual.cancelled_appointments) / len(virtual.cancelled_appointments),
    np.count_nonzero(office.cancelled_appointments) / len(office.cancelled_appointments),
    np.count_nonzero(phone.cancelled_appointments) / len(phone.cancelled_appointments)
    ]
    patients_with_cancelled_appts = [f'{i*100:.2f}%' for i in patients_with_cancelled_appts]

    a = np.array(virtual.visits_until_first_procedure_count)
    b = np.array(office.visits_until_first_procedure_count)
    c = np.array(phone.visits_until_first_procedure_count)

    # pdb.set_trace()

    visits_until_first_procedure = [
    a[np.nonzero(a)].mean(),
    b[np.nonzero(b)].mean(),
    c[np.nonzero(c)].mean()
    ]

    visits_until_first_procedure = [f'{i:.2f}' for i in visits_until_first_procedure]

    conversions_to_in_person = [
    virtual.conversions_to_in_person / virtual.pt_count,
    office.conversions_to_in_person / office.pt_count,
    phone.conversions_to_in_person / phone.pt_count
    ]

    conversions_to_in_person = [f'{i*100:.2f}%' for i in conversions_to_in_person]
    conversions_to_in_person[1] = '-'

    cellText = [
    cancelled_procedures,
    patients_with_procedure,
    patients_with_cancelled_appts,
    visits_until_first_procedure,
    conversions_to_in_person
    ]

    axs[2,1].table(cellText=cellText, rowLabels=rows, colLabels=columns, loc='center')
    axs[2,1].axis('off')
    plt.show()

def draw_hist(ax, g1, g2, g3, labels, xlim, title, y_label, x_label='', bins=40):
    ax.set_xlabel = x_label
    ax.set_ylabel = y_label
    ax.hist(g1, alpha=0.5, color='gold', bins=bins, label=labels[0])
    ax.hist(g2, alpha=0.5, color='teal', bins=bins, label=labels[1])
    # ax.hist(g3, alpha=0.5, color='green', bins=bins, label=labels[2])
    U, p1 = mannwhitneyu(g1, g2)
    anova, p2 = f_oneway(g1, g2)
    ax.text(0.7, 0.6, f'p={round(p2,3)}', horizontalalignment='center', verticalalignment='center', transform=ax.transAxes)
    ax.set_xlim([0,xlim])
    ax.set_title(title)

def main(args):
    ##
    ## Use the defined functions
    ##

    config = Config()
    if args.load:
        with open('data/dump.pickle', 'rb') as f:
            print('--> Loading from pickled data')
            patients = pickle.load(f)
        # with open('data/sorted_patients.pickle', 'rb') as f:
        #     sorted_patients = pickle.load(f)
        # virtual = sorted_patients[0]
        # office = sorted_patients[1]
        # phone = sorted_patients[2]
        # no_new = sorted_patients[3]
    else:
        print('Processing telehealth data...')
        # change this filepath string depending on where the original spreadsheet resides
        df = pd.read_excel('data/sheet.xlsx')
        # Apply filtering and renaming rules (confi
        df = apply_config(df, config)

        # Build and sort patient objects, dump them into a dictionary
        patients = build_mrns(df, config)

        # Save data off so the sorting and filtering only has to occur once
        with open('data/dump.pickle', 'wb') as f:
            print('Pickling summary data...')
            pickle.dump(patients, f, pickle.HIGHEST_PROTOCOL)
        
        print('Sorting patient data by visit type...')
    virtual, office, phone, no_new = sort_patients(patients, config)
        # sorted_patients = [virtual, office, phone, no_new]
        # with open('data/sorted_patients.pickle', 'wb') as f:
        #     print('Pickling sorted data...')
        #     pickle.dump(sorted_patients, f, pickle.HIGHEST_PROTOCOL)
    compare_groups(virtual, office, phone)
    pdb.set_trace()

    if args.o:
        print('Summarizing data...')
        # Write summary output
        pt_satisfaction_csv(patients)
        # update_fields(patients)
        write_summary_csv(patients, config)
    else:
        print('exiting without summary csv')

# Main body
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse a bunch of urology telehealth visit information')
    parser.add_argument('--load', action='store_true', default=False, help='Load pickled data to reduce processing time')
    parser.add_argument('-o', action='store_true', default=False, help='Output summary csv')
    ars = parser.parse_args()
    main(ars)