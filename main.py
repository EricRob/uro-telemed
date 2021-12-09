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
import requests
import re
import json
from scipy.stats import mannwhitneyu, f_oneway
from prettytable import PrettyTable

API_KEY = 'AIzaSyCpTf0wX7W76TAaA8BkcIcOfzDQb1raXOc'

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

        self.cancel_drops = [
            'Practice Moves',
            'Weather',
            'Deceased'
            # 'Practice Moves',
            # 'Weather',
            # 'Short Notice < 24 Hours-Patient',
            # 'Patient Request',
            # 'HouseCalls-Canceled',
            # 'Provider Request',
            # 'Scheduling error',
            # 'Scheduled From Wait List',
            # 'Short Notice <24 Hours-Provider',
            # 'Technical Issues',
            # 'Insurance issues',
            # 'Patient Condition Change',
            # 'Call Center-Canceled',
            # 'Patient is Inpatient/Inhouse',
            # 'Call Center-Canceled <24 Hours',
            # 'Deceased',
            # 'Payment issue'
        ]

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
        'icd_list',
        'icd_name_list'
        ]

        self.zip_distances_filename = 'data/zip_distances.csv'
        self.zip_distances = pd.read_csv(self.zip_distances_filename, usecols=[1,2,3])
        self.zip_incomes_filename = 'data/zip_incomes.csv'
        incomes = {}
        with open(self.zip_incomes_filename, 'r') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            for row in reader:
                if row[1] == '' or int(row[1]) < 0:
                    row[1] = -1
                zipcode = f'{int(row[0]):05}'
                income = int(row[1])
                incomes[zipcode] = income
        self.zip_incomes = incomes

        self.diagnosis_categories_filename = 'data/originals/diagnosis_categories.xlsx'
        self.diagnosis_categories = pd.read_excel(self.diagnosis_categories_filename)
        self.need_more_info = self.diagnosis_categories.loc[self.diagnosis_categories['need_more_info'] == 1]['icd_name'].values.tolist()
        self.dx_category_list = list(self.diagnosis_categories['category'].unique())
        self.dx_category_list.append('Unclassified')
        self.diagnosis_categories = dict(zip(self.diagnosis_categories['icd_name'], self.diagnosis_categories['category']))
        self.surgeries_filename = 'data/surgeries.csv'
        self.surgeries = pd.read_csv(self.surgeries_filename)
        self.procedure_list = []
        self.cpt_dict = {}
        for idx, row in self.surgeries.iterrows():
            procs = row.all_procedures.split(']')
            for proc in procs:
                if proc == '':
                    continue
                if proc[0] == ',':
                    proc = proc[2:]
                try:
                    var = proc.split('[')
                    proc = var[0][:-1]
                    cpt = var[1]
                    if cpt not in self.cpt_dict:
                        self.cpt_dict[cpt] = proc
                except:
                    pdb.set_trace()
        with open('data/procedure_list.csv', 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['cpt_code', 'procedure_name'])
            for cpt in self.cpt_dict:
                writer.writerow([cpt, self.cpt_dict[cpt]])

    def sort_surgeries(self):
        self.surgeries_raw_filename = 'data/originals/surgeries.xlsx'
        self.surgeries_raw = pd.read_excel(self.surgeries_raw_filename)
        self.surgeries = pd.DataFrame()
        for idx, row in self.surgeries_raw.iterrows():
            mrn = re.search(r"\[([A-Za-z0-9_]+)\]",row['Patient Name']).group(1)
            lead_surgeon = row['Lead Surgeon'].split(',')[0]
            surgeons = row['Surgeons'].split('\n')[:-1]
            df_add = {'mrn':mrn, 'lead_surgeon':lead_surgeon, 'surgery_date':row.Date, 'all_procedures':row['Case Procedures']}
            all_surgeons = ''
            for k, surg in enumerate(surgeons):
                surg = surg.split('(')[0][:-1]
                var = f'surgeon{k+1}'
                df_add[var] = surg
                if k > 0:
                    all_surgeons = all_surgeons + ', '
                all_surgeons = all_surgeons + surg
            df_add['all_surgeons'] = all_surgeons
            procedures = row['Case Procedures'].split(']')
            procedure_string = ''
            for k, proc in enumerate(procedures):
                proc = proc.split(',')
                var = f'procedure{k+1}'
                df_add[var] = proc
            df = pd.DataFrame(data=df_add)
            self.surgeries = self.surgeries.append(df, ignore_index=True)
            pdb.set_trace()
        cols = ['mrn', 'surgery_date', 'lead_surgeon','all_surgeons', 'surgeon1', 'surgeon2', 'surgeon3','surgeon4','all_procedures', 'procedure1', 'procedure2', 'procedure3', 'procedure4', 'procedure5', 'procedure6', 'procedure7', 'procedure8', 'procedure9', 'procedure10']
        self.surgeries = self.surgeries[cols]
        self.surgeries.to_csv('data/surgeries.csv', index=False)


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
        self.icd_name_list = df.icd_name.dropna().unique()


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
        if type(self.primary_diagnosis_icd_name) != float and self.primary_diagnosis_icd_name in config.diagnosis_categories:
            self.dx_cat = config.diagnosis_categories[self.primary_diagnosis_icd_name]
        else:
            self.dx_cat = None


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
        self.completed_procedures_by_cat = {}
        self.canceled_procedures_by_cat = {}
        self.surgeries_by_cat = {}
        for dx_cat in self.config.dx_category_list:            
            self.surgeries_by_cat[dx_cat] = {}
            self.surgeries_by_cat[dx_cat]['total'] = 0
            self.surgeries_by_cat[dx_cat]['count'] = 0

            self.completed_procedures_by_cat[dx_cat] = {}
            self.completed_procedures_by_cat[dx_cat]['total'] = 0
            self.completed_procedures_by_cat[dx_cat]['count'] = 0

            self.canceled_procedures_by_cat[dx_cat] = {}
            self.canceled_procedures_by_cat[dx_cat]['total'] = 0
            self.canceled_procedures_by_cat[dx_cat]['count'] = 0

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
        self.organize_demographics()
        self.organize_surgeries()

    def organize_surgeries(self):
        self.pt_with_surgery = 0
        for mrn in self.pt_dict:
            pt = self.pt_dict[mrn]
            if pt.has_surgery:
                if pt.dx_cat == None:
                    pt.dx_cat = 'Unclassified'
                self.pt_with_surgery += 1
                self.surgeries_by_cat[pt.dx_cat]['total'] += 1
                self.surgeries_by_cat[pt.dx_cat]['count'] += len(pt.all_surg_cpts)

        return

    def organize_demographics(self):
            # pt.has_demo = True
            # pt_demo = df.loc[df['MRN'] == demo_mrn].iloc[0]
            # pt.race = pt_demo['Race']
            # pt.zipcode = pt_demo['Postal Code']
            # pt.marital_status = pt_demo['Marital Status']
            # pt.language = pt_demo['Language']
            # pt.county = pt_demo['County']
            # pt.gender = pt_demo['Gender Identity']
            # pt.age = pt_demo['Age in Years']
            # pt.age_in_days = pt_demo['Age in Days']
            # pt.birth_sex = pt_demo['Sex Assigned at Birth']
            # pt.legal_sex = pt_demo['Legal Sex']
            # pt.ethnic_group = pt_demo['Ethnic Group']
        self.genders = []
        self.zipcodes = []
        self.zip_df = self.config.zip_distances
        self.zip_distances = []
        self.zip_durations = []
        self.zip_incomes = []
        self.ages = []
        self.languages = []
        self.marital_status = []
        self.raw_marital_status = []
        self.unique_race_list = []
        self.races = []
        self.legal_sex = []
        self.ethnic_group = []
        self.diagnosis_cats = {}
        for dx in self.config.dx_category_list:
            self.diagnosis_cats[dx] = 0
        self.race_count = 0
        self.surgery_count = 0
        self.pt_count = 0
        self.demo_count = 0
        self.cat_count = 0
        self.legal_sex_count = 0
        for mrn in self.pt_dict:
            self.pt_count += 1
            pt = self.pt_dict[mrn]
            if pt.has_demo:
                self.demo_count += 1
                self.calculate_distances(pt)
                if pt.zip_distance != 999999:
                    self.zip_distances.append(int(pt.zip_distance))
                    self.zip_durations.append(int(pt.zip_duration))
                self.ages.append(pt.age)
                self.sort_race(pt)
                self.languages.append(self.sort_language(pt))
                self.marital_status.append(self.sort_marital_status(pt))
                self.raw_marital_status.append(pt.marital_status)
                # self.marital_status.append(pt.marital_status)
                self.legal_sex.append(pt.legal_sex)
                self.legal_sex_count += 1
                self.ethnic_group.append(pt.ethnic_group)
                if str(pt.zipcode) in self.config.zip_incomes:
                    self.zip_incomes.append(self.config.zip_incomes[str(pt.zipcode)])
                
                if type(pt.primary_diagnosis_icd_name) != float and pt.primary_diagnosis_icd_name in self.config.diagnosis_categories:
                    dx_cat = self.config.diagnosis_categories[pt.primary_diagnosis_icd_name]
                    self.cat_count += 1
                    self.diagnosis_cats[dx_cat] += 1
            else:
                self.legal_sex.append('Unknown')
                self.legal_sex_count += 1
                self.raw_marital_status.append('Unknown')
                self.ethnic_group.append('Unknown')
                self.languages.append('Unknown')
                self.races.append('Unknown')

        self.config.zip_distances = self.zip_df
        self.lang_count = len(self.languages)
        self.language_portions = [
        self.languages.count(0)/self.lang_count,
        self.languages.count(1)/self.lang_count,
        self.languages.count(2)/self.lang_count,
        ]
        self.legal_sex_portions = [
        self.legal_sex.count('Male')/self.legal_sex_count,
        self.legal_sex.count('Female')/self.legal_sex_count
        ]
        
        if -1 in self.marital_status:
            self.marital_count = len(self.marital_status.remove(-1))
        else:
            self.marital_count = len(self.marital_status)
        self.marital_portions = [
        self.marital_status.count(0)/self.marital_count,
        self.marital_status.count(1)/self.marital_count,
        self.marital_status.count(2)/self.marital_count,
        ]

        self.race_portions  = {}
        for race in self.unique_race_list:
            self.race_portions[race] = self.races.count(race) / self.race_count

    def sort_race(self, pt):
        if type(pt.race) is float:
            return -1
        else:
            self.race_count += 1
            races = pt.race.split('\n')
            self.races.append(races[0])
            for race in races:
                if race not in self.unique_race_list:
                    self.unique_race_list.append(race)

    def sort_legal_sex(self, pt):
        return

    def sort_language(self, pt):
        if pt.language != 'English' and pt.language != 'Spanish':
            return 'Other'
        else:
            return pt.language

    def sort_marital_status(self, pt):
        if pt.marital_status != 'Single' and pt.marital_status != 'Married':
            return 'Unknown'
        else:
            return pt.marital_status


    def calculate_distances(self, pt):
        if str(pt.zipcode) in self.zip_df['zipcode'].values:
            row = self.zip_df.loc[self.zip_df['zipcode'] == str(pt.zipcode)]
            pt.zip_distance = int(row.distance.values[0])
            pt.zip_duration = int(row.duration.values[0])
        else:
            url = f'https://maps.googleapis.com/maps/api/directions/json?origin={pt.zipcode}&destination=OHSU&key={API_KEY}'
            print(f'new zip: {pt.zipcode}')
            payload={}
            headers = {}
            response = requests.request("GET", url, headers=headers, data=payload)
            output = json.loads(response.text)
            if len(output['routes']) > 0:
                pt.zip_distance = output['routes'][0]['legs'][0]['distance']['value']
                pt.zip_duration = output['routes'][0]['legs'][0]['duration']['value']
            else:
                pt.zip_distance = 999999
                pt.zip_duration = 999999
            d_add = {'zipcode': [str(pt.zipcode)], 'distance': [pt.zip_distance], 'duration': [pt.zip_duration]}
            df_add = pd.DataFrame(data=d_add)
            self.zip_df = self.zip_df.append(df_add, ignore_index=True)
            self.zip_df.to_csv(self.config.zip_distances_filename)
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
            if pt.dx_cat == None:
                pt.dx_cat = 'Unclassified'
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
            if pt.dx_cat != None:
                self.completed_procedures_by_cat[pt.dx_cat]['total'] += 1
            if pt.has_procedure:
                self.patients_with_completed_procedure += 1
                if pt.dx_cat != None:
                    self.completed_procedures_by_cat[pt.dx_cat]['count'] += 1
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
            if pt.has_any_procedure:
                self.canceled_procedures_by_cat[pt.dx_cat]['total'] += 1
            if pt.cancelled_procedure_visit_count > 0:
                self.patients_with_canceled_procedure += 1
                self.canceled_procedures_by_cat[pt.dx_cat]['count'] += 1

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
        self.cancel_reason = row.cancel_reason
        
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

    for cancel_reason in config.cancel_drops:
        df = df[df.cancel_reason != cancel_reason]
    
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
    pt_iterator = iter(patients.values())
    pt = next(pt_iterator)
    while(not pt.has_demo):
        pt = next(pt_iterator)
        print(pt.mrn)
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

def virtual_cancellations(virtual, config):
    procedure_minus_office = {'with_cancel': [], 'no_cancel': []}
    procedure_plus_office = {'with_cancel': [], 'no_cancel': []}
    no_proc_minus_office = []
    no_proc_plus_office = []
    for mrn in virtual.pt_dict:
        pt = virtual.pt_dict[mrn]
        encs = pt.encounters
        first_date = None
        first_visit = True
        proc_visit = False
        has_in_person = False
        with_cancel = False
        for key, enc in sorted(encs.items()):
            if first_visit:
                if enc.is_visit and enc.is_completed:
                    first_date = enc.date
                    first_visit = False
            else:
                if not proc_visit:
                    if enc.is_visit:
                        if pt.has_any_procedure:
                            if not enc.is_virtual:
                                has_in_person = True
                    elif enc.is_procedure:
                        if enc.is_completed:
                            proc_visit = True
                            if has_in_person:
                                if with_cancel:
                                    procedure_plus_office['with_cancel'].append(mrn)
                                else:
                                    procedure_plus_office['no_cancel'].append(mrn)
                            else:
                                if with_cancel:
                                    procedure_minus_office['with_cancel'].append(mrn)
                                else:
                                    procedure_minus_office['no_cancel'].append(mrn)
                        else:
                            if enc.is_cancelled:
                                with_cancel = True
        if pt.complete_procedure_visit_count == 0 and pt.cancelled_procedure_visit_count > 0:
            if has_in_person:
                no_proc_plus_office.append(mrn)
            else:
                no_proc_minus_office.append(mrn)

    return

def adjust_fields(di, date_vars, list_vars):
    for date_var in date_vars:
        if di[date_var] is not None:
            di[date_var] = str(di[date_var]).split()[0]
    for list_var in list_vars:
        list_str = [str(element) for element in di[list_var]]
        joined = ", ".join(list_str)
        di[list_var] = joined
    for key, item in di.items():
        if type(item) is list:
            try:
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

def link_demographics(patients, df, config):
    demo_mrns = df['MRN'].unique()
    for mrn in patients:
        pt = patients[mrn]
        demo_mrn = f'{mrn:08}'
        if demo_mrn in demo_mrns:
            pt.has_demo = True
            pt_demo = df.loc[df['MRN'] == demo_mrn].iloc[0]
            pt.race = pt_demo['Race']
            pt.zipcode = pt_demo['Postal Code']
            pt.marital_status = pt_demo['Marital Status']
            pt.language = pt_demo['Language']
            pt.county = pt_demo['County']
            pt.gender = pt_demo['Gender Identity']
            pt.age = pt_demo['Age in Years']
            pt.age_in_days = pt_demo['Age in Days']
            pt.birth_sex = pt_demo['Sex Assigned at Birth']
            pt.legal_sex = pt_demo['Legal Sex']
            pt.ethnic_group = pt_demo['Ethnic Group']
        else:
            pt.has_demo = False

        patients[mrn] = pt
    # return patients

def demographics_table(virtual, office, phone, config):
    header = ['virtual', 'office', 'phone']
    empty_row = [['', '', '']]
    rows = ['Age', 'Mean (SD)', 'Median (IQR)', 'Range', '',
    'Legal Sex, n (%)', 'Male', 'Female', 'Unknown', '',
    'Marital Status, n (%)', 'Single', 'Married', 'Other', 'Unknown', '',
    'Ethnic Group, n (%)', 'Hispanic', 'Non-hispanic', 'Declined / Unknown', '',
    'Race, n (%)', 'White', 'Black', 'Asian', 'Pacific Islander', 'Native American', 'Declined / Unknown', '',
    'Language, n (%)', 'English', 'Spanish', 'Other', 'Unknown'
    ]

    # 'Age', 'Mean (SD)', 'Median (IQR)', 'Range',
    v_age = np.array(virtual.ages)
    o_age = np.array(office.ages)
    p_age = np.array(phone.ages)
    age_data = [
    [f'{v_age.mean():.1f} ({v_age.std():.1f})', f'{o_age.mean():.1f} ({o_age.std():.1f})', f'{p_age.mean():.1f} ({p_age.std():.1f})'],
    [f'{np.median(v_age)} ({np.percentile(v_age, 25)}—{np.percentile(v_age, 75)})', f'{np.median(o_age)} ({np.percentile(o_age, 25)}—{np.percentile(o_age, 75)})', f'{np.median(p_age)} ({np.percentile(p_age, 25)}—{np.percentile(p_age, 75)})'],
    [f'{v_age.min()}—{v_age.max()}', f'{o_age.min()}—{o_age.max()}', f'{p_age.min()}—{p_age.max()}']
    ]

    v_sex = np.array(virtual.legal_sex)
    o_sex = np.array(office.legal_sex)
    p_sex = np.array(phone.legal_sex)

    unique, v_counts = np.unique(v_sex, return_counts=True)
    unique, o_counts = np.unique(o_sex, return_counts=True)
    unique, p_counts = np.unique(p_sex, return_counts=True)

    # 'Legal Sex, n (%)', 'Male', 'Female', 'Unknown',
    legal_sex_data = [
    [f'{v_counts[1]} ({v_counts[1]*100  / v_sex.size:.1f}%)',
    f'{o_counts[1]} ({o_counts[1]*100  / o_sex.size:.1f}%)',
    f'{p_counts[1]} ({p_counts[1]*100  / p_sex.size:.1f}%)'],

    [f'{v_counts[0]} ({v_counts[0]*100  / v_sex.size:.1f}%)',
    f'{o_counts[0]} ({o_counts[0]*100  / o_sex.size:.1f}%)',
    f'{p_counts[0]} ({p_counts[0]*100  / p_sex.size:.1f}%)'],

    [f'{v_counts[2]} ({v_counts[2]*100  / v_sex.size:.1f}%)',
    f'{o_counts[2]} ({o_counts[2]*100  / o_sex.size:.1f}%)',
    f'{p_counts[2]} ({p_counts[2]*100  / p_sex.size:.1f}%)']
    ]

    v_marital = np.array(virtual.raw_marital_status)
    o_marital = np.array(office.raw_marital_status)
    p_marital = np.array(phone.raw_marital_status)

    v_unique, v_counts = np.unique(v_marital, return_counts=True)
    o_unique, o_counts = np.unique(o_marital, return_counts=True)
    p_unique, p_counts = np.unique(p_marital, return_counts=True)
    # 'Marital Status, n (%)', 'Single', 'Married', 'Other', 'Unknown',
    marital_status_data = [
    [f'{v_counts[1]} ({v_counts[1]*100  / v_marital.size:.1f}%)',
    f'{o_counts[2]} ({o_counts[2]*100  / o_marital.size:.1f}%)',
    f'{p_counts[1]} ({p_counts[1]*100  / p_marital.size:.1f}%)'],

    [f'{v_counts[0]} ({v_counts[0]*100  / v_marital.size:.1f}%)',
    f'{o_counts[0]} ({o_counts[0]*100  / o_marital.size:.1f}%)',
    f'{p_counts[0]} ({p_counts[0]*100  / p_marital.size:.1f}%)'],

    [f'{v_counts[3]} ({v_counts[3]*100  / v_marital.size:.1f}%)',
    f'{o_counts[1] + o_counts[4]} ({(o_counts[1] + o_counts[4])*100  / o_marital.size:.1f}%)',
    f'{p_counts[3]} ({p_counts[3]*100  / p_marital.size:.1f}%)'],

    [f'{v_counts[2]} ({v_counts[2]*100  / v_marital.size:.1f}%)',
    f'{o_counts[3] + o_counts[5]} ({(o_counts[3] + o_counts[5])*100  / o_marital.size:.1f}%)',
    f'{p_counts[2]} ({p_counts[2]*100  / p_marital.size:.1f}%)']
    ]

    # 'Ethnic Group', 'Hispanic', 'Non-hispanic', 'Declined / Unknown',
    v_ethnic = np.array(virtual.ethnic_group)
    o_ethnic = np.array(office.ethnic_group)
    p_ethnic = np.array(phone.ethnic_group)

    v_unique, v_counts = np.unique(v_ethnic, return_counts=True)
    o_unique, o_counts = np.unique(o_ethnic, return_counts=True)
    p_unique, p_counts = np.unique(p_ethnic, return_counts=True)

    ethnic_group_data = [
    [f'{v_counts[1]} ({v_counts[1]*100  / v_ethnic.size:.1f}%)',
    f'{o_counts[1]} ({o_counts[1]*100  / o_ethnic.size:.1f}%)',
    f'{p_counts[1]} ({p_counts[1]*100  / p_ethnic.size:.1f}%)'],

    [f'{v_counts[0]} ({v_counts[0]*100  / v_ethnic.size:.1f}%)',
    f'{o_counts[0]} ({o_counts[0]*100  / o_ethnic.size:.1f}%)',
    f'{p_counts[0]} ({p_counts[0]*100  / p_ethnic.size:.1f}%)'],

    [f'{v_counts[0] + v_counts[3] + v_counts[4]} ({(v_counts[0] + v_counts[3] + v_counts[4])*100  / v_ethnic.size:.1f}%)',
    f'{o_counts[0] + o_counts[3] + o_counts[4]} ({(o_counts[0] + o_counts[3] + o_counts[4])*100  / o_ethnic.size:.1f}%)',
    f'{p_counts[0] + p_counts[3] + p_counts[4]} ({(p_counts[0] + p_counts[3] + p_counts[4])*100  / p_ethnic.size:.1f}%)']
    ]

    # 'Race, n (%)', 'White', 'Black', 'Asian', 'Pacific Islander', 'Native American', 'Declined / Unknown'
    v_race = np.array(virtual.races)
    o_race = np.array(office.races)
    p_race = np.array(phone.races)

    v_unique, v_counts = np.unique(v_race, return_counts=True)
    v_unique = np.insert(v_unique, 4, 'Native Hawaiian')
    v_counts = np.insert(v_counts, 4, 0)
    o_unique, o_counts = np.unique(o_race, return_counts=True)
    p_unique, p_counts = np.unique(o_race, return_counts=True)

    race_data = [
    [f'{v_counts[7]} ({v_counts[7]*100  / v_race.size:.1f}%)',
    f'{o_counts[7]} ({o_counts[7]*100  / o_race.size:.1f}%)',
    f'{p_counts[7]} ({p_counts[7]*100  / p_race.size:.1f}%)'],

    [f'{v_counts[2]} ({v_counts[2]*100  / v_race.size:.1f}%)',
    f'{o_counts[2]} ({o_counts[2]*100  / o_race.size:.1f}%)',
    f'{p_counts[2]} ({p_counts[2]*100  / p_race.size:.1f}%)'],

    [f'{v_counts[1]} ({v_counts[1]*100  / v_race.size:.1f}%)',
    f'{o_counts[1]} ({o_counts[1]*100  / o_race.size:.1f}%)',
    f'{p_counts[1]} ({p_counts[1]*100  / p_race.size:.1f}%)'],

    [f'{(v_counts[5] + v_counts[4])} ({(v_counts[5] + v_counts[4])*100  / v_race.size:.1f}%)',
    f'{(o_counts[5] + o_counts[4])} ({(o_counts[5] + o_counts[4])*100  / o_race.size:.1f}%)',
    f'{(p_counts[5] + p_counts[4])} ({(p_counts[5] + p_counts[4])*100  / p_race.size:.1f}%)'],

    [f'{v_counts[0]} ({v_counts[0]*100  / v_race.size:.1f}%)',
    f'{o_counts[0]} ({o_counts[0]*100  / o_race.size:.1f}%)',
    f'{p_counts[0]} ({p_counts[0]*100  / p_race.size:.1f}%)'],

    [f'{(v_counts[3] + v_counts[6])} ({(v_counts[3] + v_counts[6])*100  / v_race.size:.1f}%)',
    f'{(o_counts[3] + o_counts[6])} ({(o_counts[3] + o_counts[6])*100  / o_race.size:.1f}%)',
    f'{(p_counts[3] + p_counts[6])} ({(p_counts[3] + p_counts[6])*100  / p_race.size:.1f}%)']
    ]

    # 'Language', 'English', 'Spanish', 'Other', 'Unknown'
    v_lang = np.array(virtual.languages)
    o_lang = np.array(office.languages)
    p_lang = np.array(phone.languages)

    v_unique, v_counts = np.unique(v_lang, return_counts=True)
    o_unique, o_counts = np.unique(o_lang, return_counts=True)
    p_unique, p_counts = np.unique(p_lang, return_counts=True)

    language_data = [
    [f'{v_counts[0]} ({v_counts[0]*100  / v_lang.size:.1f}%)',
    f'{o_counts[0]} ({o_counts[0]*100  / o_lang.size:.1f}%)',
    f'{p_counts[0]} ({p_counts[0]*100  / p_lang.size:.1f}%)'],

    [f'{v_counts[2]} ({v_counts[2]*100  / v_lang.size:.1f}%)',
    f'{o_counts[2]} ({o_counts[2]*100  / o_lang.size:.1f}%)',
    f'{p_counts[1]} ({p_counts[1]*100  / p_lang.size:.1f}%)'],

    [f'{v_counts[1]} ({v_counts[1]*100  / v_lang.size:.1f}%)',
    f'{o_counts[1]} ({o_counts[1]*100  / o_lang.size:.1f}%)',
    f'0 (0%)'],

    [f'{v_counts[3]} ({v_counts[3]*100  / v_lang.size:.1f}%)',
    f'{o_counts[3]} ({o_counts[3]*100  / o_lang.size:.1f}%)',
    f'{p_counts[2]} ({p_counts[2]*100  / p_lang.size:.1f}%)']
    ]

    body = empty_row + age_data + empty_row
    body += empty_row + legal_sex_data + empty_row
    body += empty_row + marital_status_data+ empty_row
    body += empty_row + ethnic_group_data + empty_row
    body += empty_row + race_data + empty_row
    body += empty_row + language_data

    write_output_csv(body, rows, header, title='demographics_table')
    return

def link_surgeries(patients, df, config):
    surg_mrns = df['mrn'].unique().tolist()
    # surg_mrns = []
    # for mrn in surg_mrns_raw:
    #     surg_mrns.append(f'{mrn:08}')

    for mrn in patients:
        pt = patients[mrn]
        # mrn = f'{mrn:08}'
        if mrn in surg_mrns:
            pt.has_surgery = True
            surg = df.loc[df['mrn'] == mrn].iloc[0]
            pt.surgery_date = surg.surgery_date
            pt.lead_surgeon = surg.lead_surgeon
            pt.all_surg_names = surg.all_procedures
            pt.all_surg_cpts = re.findall(r"\[(\w+)\]", surg.all_procedures)
        else:
            pt.has_surgery = False
            pt.surgery_date = None
            pt.lead_surgeon = None
            pt.all_surg_names = None
            pt.all_surg_cpts = None

        patients[mrn] = pt

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
    # fig, axs = plt.subplots(1,1, tight_layout=True)
    labels = ['virtual', 'office', 'phone']

    # Number of days from referral to first completed visit
    draw_hist(axs[0,0],
        virtual.first_visit_to_first_procedure_days,
        office.first_visit_to_first_procedure_days,
        phone.first_visit_to_first_procedure_days,
        labels, 100, 'First visit to first procedure', 'Days', bins=25)
    # draw_hist(axs[0,1],
    #     virtual.referral_to_first_procedure_days,
    #     office.referral_to_first_procedure_days,
    #     phone.referral_to_first_procedure_days,
    #     labels, 200, 'Referral to first procedure', 'Days')
    draw_hist(axs[1,0],
        virtual.scheduling_to_first_visit_days,
        office.scheduling_to_first_visit_days,
        phone.scheduling_to_first_visit_days,
        labels, 110, 'Scheduling to first visit', 'Days')
    # draw_hist(axs[1,1],
    #     virtual.referral_to_first_visit_days,
    #     office.referral_to_first_visit_days,
    #     phone.referral_to_first_visit_days,
    #     labels, 400,'Referral to first visit', 'Days')
    draw_hist(axs[2,0],
        virtual.scheduling_to_first_procedure_days,
        office.scheduling_to_first_procedure_days,
        phone.scheduling_to_first_procedure_days,
        labels, 200,'Scheduling to first procedure', 'Days')
    axs[0,1].legend(loc='upper right')
    

    # axs[2,1].table(cellText=cellText, rowLabels=rows, colLabels=columns, loc='center')
    # axs[2,1].axis('off')
    # axs.table(cellText=cellText, rowLabels=rows, colLabels=columns, loc='center')
    # axs.axis('off')

    # self.language_portions
    # self.marital_portions
    # self.race_portions
    lang_labels = ['English', 'Spanish', 'Other']
    marital_labels = ['Single', 'Married', 'Other']
    legal_sex_labels = ['Male', 'Female']

    draw_barchart_three(axs[2,1], virtual.language_portions, office.language_portions, phone.language_portions, labels, lang_labels, 'Language portions')
    draw_barchart_three(axs[1,1], virtual.marital_portions, office.marital_portions, phone.marital_portions, labels, marital_labels, 'Marital Status Portions')

    draw_barchart_two(axs[0,1], virtual.legal_sex_portions, office.legal_sex_portions, phone.legal_sex_portions, labels, legal_sex_labels, "Legal sex portions")
    # plt.show()

def add_categories_to_list(rows, name, cat_list, suffix = ''):
    rows.append(name)
    for dx_cat in cat_list:
        rows.append('>>' + dx_cat + ' ' + suffix)
    rows.append('')
    return rows

def bad_divide(x,y):
    return x/y if y else 0

def summary_table(virtual, office, phone, config):
    plt.clf()
    fig, axs = plt.subplots(1,1, tight_layout=True)
    labels = [f'virtual (N={virtual.pt_count})', f'office (N={office.pt_count})', f'phone (N={phone.pt_count})']
    columns = labels
    empty_row = ['', '', '']
    rows = []
    # rows = add_categories_to_list(rows, 'Pts with cancelled procedure (% of total)', config.dx_category_list, suffix='(% of category)')
    # rows = add_categories_to_list(rows, 'Pts with procedure (% of total)', config.dx_category_list, suffix='(% of category)')
    
    rows = add_categories_to_list(rows, 'Pts w/cancelled office procedure', config.dx_category_list)
    rows = add_categories_to_list(rows, 'Pts w/office procedure', config.dx_category_list)
    rows = add_categories_to_list(rows, 'Pts w/surgery', config.dx_category_list)

    
    rows = rows + ['Pts with cancelled appts',
    'Visits until first procedure',
    'Conversions to in-person',
    'Avg income (std)',
    'Avg distance (std)',
    'Avg duration (std)',
    'Avg age (std)',
    '~~ Diagnosis Categories ~~',
    'Totals'
    ]
    for dx_cat in config.dx_category_list:
        # rows.append(dx_cat + ' (% of column)')
        rows.append(dx_cat)


    cellText = []
    
    # cancelled_procedures = [
    # np.count_nonzero(virtual.cancelled_procedures) / len(virtual.cancelled_procedures),
    # np.count_nonzero(office.cancelled_procedures) / len(office.cancelled_procedures),
    # np.count_nonzero(phone.cancelled_procedures) / len(phone.cancelled_procedures)
    # ]
    # cancelled_procedures = [f'{i*100:.1f}%' for i in cancelled_procedures]

    cancelled_procedures = [
    virtual.patients_with_canceled_procedure,
    office.patients_with_canceled_procedure,
    phone.patients_with_canceled_procedure,
    ]
    
    cancelled_cat_list = []
    for dx_cat in config.dx_category_list:
        # new_row = [
        # bad_divide(virtual.canceled_procedures_by_cat[dx_cat]['count'], virtual.diagnosis_cats[dx_cat]),
        # bad_divide(office.canceled_procedures_by_cat[dx_cat]['count'], office.diagnosis_cats[dx_cat]),
        # bad_divide(phone.canceled_procedures_by_cat[dx_cat]['count'], phone.diagnosis_cats[dx_cat])
        # ]
        # new_row = [f'{i*100:.1f}%' for i in new_row]
        new_row = [
        virtual.canceled_procedures_by_cat[dx_cat]['count'],
        office.canceled_procedures_by_cat[dx_cat]['count'],
        phone.canceled_procedures_by_cat[dx_cat]['count']
        ]
        cancelled_cat_list.append(new_row)

    # patients_with_procedure =[
    # virtual.patients_with_completed_procedure / virtual.pt_count,
    # office.patients_with_completed_procedure / office.pt_count,
    # phone.patients_with_completed_procedure / phone.pt_count,
    # ]
    # patients_with_procedure = [f'{i*100:.1f}%' for i in patients_with_procedure]
    patients_with_procedure =[
    virtual.patients_with_completed_procedure,
    office.patients_with_completed_procedure,
    phone.patients_with_completed_procedure
    ]

    procedure_cat_list = []
    for dx_cat in config.dx_category_list:
        # new_row = [
        # bad_divide(virtual.completed_procedures_by_cat[dx_cat]['count'], virtual.diagnosis_cats[dx_cat]),
        # bad_divide(office.completed_procedures_by_cat[dx_cat]['count'], office.diagnosis_cats[dx_cat]),
        # bad_divide(phone.completed_procedures_by_cat[dx_cat]['count'], phone.diagnosis_cats[dx_cat])
        # ]
        # new_row = [f'{i*100:.1f}%' for i in new_row]
        new_row = [
        virtual.completed_procedures_by_cat[dx_cat]['count'],
        office.completed_procedures_by_cat[dx_cat]['count'],
        phone.completed_procedures_by_cat[dx_cat]['count']
        ]
        procedure_cat_list.append(new_row)

    patients_with_surgery = [
    virtual.pt_with_surgery,
    office.pt_with_surgery,
    phone.pt_with_surgery
    ]

    surgery_cat_list = []
    for dx_cat in config.dx_category_list:
        new_row = [
        virtual.surgeries_by_cat[dx_cat]['total'],
        office.surgeries_by_cat[dx_cat]['total'],
        phone.surgeries_by_cat[dx_cat]['total']
        ]
        surgery_cat_list.append(new_row)
    # patients_with_cancelled_appts = [
    # np.count_nonzero(virtual.cancelled_appointments) / len(virtual.cancelled_appointments),
    # np.count_nonzero(office.cancelled_appointments) / len(office.cancelled_appointments),
    # np.count_nonzero(phone.cancelled_appointments) / len(phone.cancelled_appointments)
    # ]
    # patients_with_cancelled_appts = [f'{i*100:.2f}%' for i in patients_with_cancelled_appts]

    patients_with_cancelled_appts = [
    np.count_nonzero(virtual.cancelled_appointments),
    np.count_nonzero(office.cancelled_appointments),
    np.count_nonzero(phone.cancelled_appointments)
    ]

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

    # conversions_to_in_person = [
    # virtual.conversions_to_in_person / virtual.pt_count,
    # office.conversions_to_in_person / office.pt_count,
    # phone.conversions_to_in_person / phone.pt_count
    # ]

    # conversions_to_in_person = [f'{i*100:.2f}%' for i in conversions_to_in_person]
    # conversions_to_in_person[1] = '-'
    
    conversions_to_in_person = [
        virtual.conversions_to_in_person,
        '-',
        phone.conversions_to_in_person
    ]

    avg_income = [
    f'{np.array(virtual.zip_incomes).mean()/1000:.1f} ({np.array(virtual.zip_incomes).std()/1000:.1f})',
    f'{np.array(office.zip_incomes).mean()/1000:.1f} ({np.array(office.zip_incomes).std()/1000:.1f})',
    f'{np.array(phone.zip_incomes).mean()/1000:.1f} ({np.array(phone.zip_incomes).std()/1000:.1f})'
    ]

    avg_distance = [
    f'{np.array(virtual.zip_distances).mean()/1000:.1f} ({np.array(virtual.zip_distances).std()/1000:.1f})',
    f'{np.array(office.zip_distances).mean()/1000:.1f} ({np.array(office.zip_distances).std()/1000:.1f})',
    f'{np.array(phone.zip_distances).mean()/1000:.1f} ({np.array(phone.zip_distances).std()/1000:.1f})'
    ]

    avg_duration = [
    f'{np.array(virtual.zip_durations).mean()/60:.1f} ({np.array(virtual.zip_durations).std()/60:.1f})',
    f'{np.array(office.zip_durations).mean()/60:.1f} ({np.array(office.zip_durations).std()/60:.1f})',
    f'{np.array(phone.zip_durations).mean()/60:.1f} ({np.array(phone.zip_durations).std()/60:.1f})'
    ]

    avg_age = [
    f'{np.array(virtual.ages).mean():.1f} ({np.array(virtual.ages).std():.1f})',
    f'{np.array(office.ages).mean():.1f} ({np.array(office.ages).std():.1f})',
    f'{np.array(phone.ages).mean():.1f} ({np.array(phone.ages).std():.1f})'
    ]


    cellText = [cancelled_procedures]
    for canc in cancelled_cat_list:
        cellText.append(canc)
    cellText.append(empty_row)
    cellText.append(patients_with_procedure)
    for proc in procedure_cat_list:
        cellText.append(proc)
    cellText.append(empty_row)
    cellText.append(patients_with_surgery)
    for surg in surgery_cat_list:
        cellText.append(surg)
    cellText.append(empty_row)
    cellText = cellText + [patients_with_cancelled_appts,
    visits_until_first_procedure,
    conversions_to_in_person,
    avg_income,
    avg_distance,
    avg_duration,
    avg_age,
    ['', '', ''],
    [f'{virtual.cat_count}', f'{office.cat_count}', f'{phone.cat_count}']
    ]

    for dx_cat in config.dx_category_list:
        cellText.append([
            # f'{virtual.diagnosis_cats[dx_cat] / virtual.pt_count*100:.1f}%',
            # f'{office.diagnosis_cats[dx_cat] / office.pt_count*100:.1f}%',
            # f'{phone.diagnosis_cats[dx_cat] / phone.pt_count*100:.1f}%'
            f'{virtual.diagnosis_cats[dx_cat]}',
            f'{office.diagnosis_cats[dx_cat]}',
            f'{phone.diagnosis_cats[dx_cat]}'
            ])
    
    table = axs.table(cellText=cellText, rowLabels=rows, colLabels=columns, loc='center')
    write_output_csv(cellText, rows, columns)
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    axs.axis('off')
    # plt.show()

def write_output_csv(body, rows, columns, title='output'):
    x = PrettyTable()

    header = [' '] + columns
    x.field_names = header
    with open(f'{title}.csv', 'w') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(header)
        try:
            for k, row in enumerate(rows):
                w = [row] + body[k]
                x.add_row(w)
                writer.writerow(w)
        except:
            pdb.set_trace()
    print(x)

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

def draw_barchart_three(ax, g1, g2, g3, xlabels, labels, title):
    rects1 = [g1[0], g2[0], g3[0]]
    rects2 = [g1[1], g2[1], g3[1]]
    rects3 = [g1[2], g2[2], g3[2]]

    x = np.arange(3)
    width = 0.2

    ax.bar(x - width, rects1, width, label=labels[0])
    ax.bar(x, rects2, width, label=labels[1])
    ax.bar(x + width, rects3, width, label=labels[2])
    ax.set_xticks(x)
    ax.set_xticklabels(xlabels)
    ax.legend()

    ax.set_title(title)

def draw_barchart_two(ax, g1, g2, g3, xlabels, labels, title):
    rects1 = [g1[0], g2[0], g3[0]]
    rects2 = [g1[1], g2[1], g3[1]]

    x = np.arange(3)
    width = 0.2

    ax.bar(x - width/2, rects1, width, label=labels[0])
    ax.bar(x + width/2, rects2, width, label=labels[1])
    ax.set_xticks(x)
    ax.set_xticklabels(xlabels)
    ax.legend()

    ax.set_title(title)

def grouped_barchart(ax, g1, g2, xlabels, labels, title):

    return

def need_more_info(patients, config):
    max_prov = 0
    max_icd = 0
    more_info = pd.DataFrame()
    mrn_list = []
    for mrn in patients:
        pt = patients[mrn]
        if pt.primary_diagnosis_icd_name in config.need_more_info:
            df_add = {'mrn': f'{mrn:08}', 'primary_diagnosis':pt.primary_diagnosis_icd_name, 'lead_surgeon':pt.lead_surgeon, 'all_surgeries':pt.all_surg_names}
            for k, icd in enumerate(pt.icd_name_list):
                var = f'icd{k+1}'
                df_add[var] = icd
            for k, provider in enumerate(pt.provider_list):
                var = f'prov{k+1}'
                df_add[var] = provider
            more_info = more_info.append(df_add, ignore_index=True)
            mrn_list.append(f'{mrn:08}')
    print('writing more info...')
    cols = ['mrn', 'primary_diagnosis', 'lead_surgeon', 'all_surgeries', 'icd1', 'icd2', 'icd3', 'icd4', 'prov1', 'prov2', 'prov3']
    more_info = more_info[cols]
    more_info.to_csv('more_info_needed.csv', index=False)

# def understand_practice_moves(patients,config):
#     for mrn in patients:
#         pt = patients[mrn]
#         encs = pt.encounters
#         if pt.has_cancelled_procedure:
#             for key, enc in sorted(encs.items()):
#                 if enc.is_procedure and enc.is_cancelled:
#                     print(f'Name: {pt.pt_name}')
#                     print(f'Complete Procedure ct: {pt.complete_procedure_visit_count}')
#                     print(f'Cancelled Procedure ct: {pt.cancelled_procedure_visit_count}')
#                     print(f'Cancellation Reason: {enc.cancel_reason}')
#                     pdb.set_trace()
#     return

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
        df = pd.read_excel('data/originals/sheet.xlsx')
        # Apply filtering and renaming rules (confi
        df = apply_config(df, config)

        # Build and sort patient objects, dump them into a dictionary
        patients = build_mrns(df, config)

        # Import demographic data spreadsheet
        demo_df = pd.read_excel('data/originals/demographics.xlsx')
        link_demographics(patients, demo_df, config)

        # Import surgery data spreadsheet
        surg_df = pd.read_csv('data/surgeries.csv')
        link_surgeries(patients, surg_df, config)

        # Save data off so the sorting and filtering only has to occur once
        with open('data/dump.pickle', 'wb') as f:
            print('Pickling summary data...')
            pickle.dump(patients, f, pickle.HIGHEST_PROTOCOL)
        
        print('Sorting patient data by visit type...')
    print('---after load point---')
    # understand_practice_moves(patients,config)
    virtual, office, phone, no_new = sort_patients(patients, config)
        # sorted_patients = [virtual, office, phone, no_new]
        # with open('data/sorted_patients.pickle', 'wb') as f:
        #     print('Pickling sorted data...')
        #     pickle.dump(sorted_patients, f, pickle.HIGHEST_PROTOCOL)
    need_more_info(patients, config)
    virtual_cancellations(virtual, config)
    compare_groups(virtual, office, phone)
    summary_table(virtual, office, phone, config)
    demographics_table(virtual, office, phone, config)

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