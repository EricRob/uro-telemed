#!/user/bin/env python3 -tt
"""
Module documentation.
"""

# Imports
import sys
import os
import pandas as pd
import numpy as np
import pdb

# Global variables

# Class declarations

# Function declarations

# df_test['Difference'] = (df_test['First_Date'] - df_test['Second Date']).dt.days

def drop_columns(df):
	drops = [
	'Unnamed: 0'
	]
	df = df.drop(drops, axis=1)
	return df

def rename_columns(df):
	columns = {
	'Patient OHSU MRN': 'mrn',
	'Patient Name': 'name',
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

	df = df.rename(columns=columns)
	return df

def drop_rows(df):
	# remove PAs and RNs
	providers = ['URO RN', 'SCULL, DORIAN', 'KEESLAR, MATTHEW', 'OLSON, ASHLEY J']
	for provider in providers:
		df = df[df.provider != provider]

	# remove procedures
	# idk if i want to do this, I want to keep the procedure dates?
	return df

def add_columns(df):
	df['referral_to_encounter'] = (df['encounter_date'] - df['referral_date']).dt.days
	df['creation_to_encounter'] = (df['encounter_date'] - df['creation_date']).dt.days
	return df
	# determine if mrn has encounter in target month


df = pd.read_excel('data/sheet.xlsx')
df = drop_columns(df)
df = rename_columns(df)
df = drop_rows(df)
df = add_columns(df)
pdb.set_trace()
