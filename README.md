# uro-telemed
Parsing data for a urology telemedicine project


# Data Values

## MRN

| Variable         | Type             | Default    | Description  |
| -------------------------------------------- | ---------------- | ---------- | ----------------------------------------------------------------- |
| provider\_list  | list of strings  | Empty list | list of all providers linked to a MRN |
| icd\_list | list of strings  | Empty list | list of all icd codes linked to a MRN   |
| encounters        | list of objects  | Empty list | list of all encounter objects linked to a MRN |
| referral\_list  | list of DateTime | Empty list | list of all referral dates linked to a MRN |
| has\_procedure | boolean          | FALSE      | TRUE if completed procedure encounter exists |
| has\_phone | boolean          | FALSE      | TRUE if completed phone encounter exists|
| has\_virtual  | boolean          | FALSE      | TRUE if completed virtual encounter exists |
| has\_any\_completed\_visit                   | boolean          | FALSE      | TRUE if a completed encounter exists|
| has\_completed\_new\_vist                    | boolean          | FALSE      | TRUE if completed new encounter exists |
| has\_any\_new\_visit                         | boolean          | FALSE      | TRUE if \_\_any\_\_ new encounter exists (some patients have new type that never reached completed status) |
| earliest\_new\_date                          | DateTime         | Empty      | Earliest date of completed new encounter for MRN  |
| earliest\_virtual\_date                      | DateTime         | Empty      | Earliest date of completed virtual encounter for MRN |
| earliest\_procedure\_date                    | DateTime         | Empty      | Earliest date of completed procedure encounter for MRN |
| earliest\_phone\_date  | DateTime         | Empty      | Earliest date of completed phone encounter for MRN|
| earliest\_office\_date | DateTime         | Empty      | Earliest date of completed office encounter for MRN |
| earliest\_completed\_date  | DateTime         | Empty      | Earliest date of any completed encounter for MRN|
| earliest\_referral\_date | DateTime         | Empty      | Earliest referral date across all MRN encounters |
| earliest\_scheduling\_date  | DateTime         | Empty      | Earliest scheduled date across encounters, complete or incomplete                 |
| earliest\_new\_id | integer          | Empty      | internal reference id linking encounter object to master dataframe                 |
| earliest\_virtual\_id | integer          | Empty      | internal reference id linking encounter object to master dataframe |
| earliest\_procedure\_id                      | integer | Empty      | internal reference id linking encounter object to master dataframe|
| earliest\_referral\_id| integer          | Empty      | internal reference id linking encounter object to master dataframe|
| earliest\_phone\_id| integer          | Empty      | internal reference id linking encounter object to master dataframe|
| earliest\_scheduling\_id                     | integer          | Empty      | internal reference id linking encounter object to master dataframe|
| earliest\_office\_id                         | integer          | Empty      | internal reference id linking encounter object to master dataframe|
| earliest\_completed\_id                      | integer          | Empty      | internal reference id linking encounter object to master dataframe|
| earliest\_new\_type| string           | Empty      | visit type of earliest completed new encounter|
| earliest\_completed\_type                    | string           | Empty      | visit type of earliest completed encounter|
| conv\_virtual\_to\_office  | boolean          | FALSE      | TRUE if there is an office encounter date after the earliest virtual encounter date |
| conv\_virtual\_to\_phone | boolean          | FALSE      | TRUE if there is a phone encounter date after the earliest virtual encounter date |
| conv\_office\_to\_phone | boolean          | FALSE      | TRUE if there is an office encounter date after the earliest phone encounter date |
| conv\_office\_to\_virtual                    | boolean          | FALSE      | TRUE if there is an office encounter date after the earliest office encounter date |
| conv\_phone\_to\_office | boolean          | FALSE      | TRUE if there is a phone encounter date after the earliest office encounter date |
| conv\_phone\_to\_virtual                     | boolean          | FALSE      | TRUE if if there is a phone encounter date after the earliest virtual encounter date |
| referral\_to\_earliest\_new\_encounter       | days             | None       | count of days between earliest referral date and earliest new date. --> Selected any new encounter, can be changed to earliest \_\_completed\_\_ new encounter |
| referral\_to\_earliest\_completed\_encounter | days             | None       | count of days between earliest referral date and earliest completed encounter of any type |
| referral\_to\_earliest\_completed\_virtual   | days             | None       | count of days between earliest referral date and earliest completed virtual encouner |
| referral\_to\_earliest\_completed\_phone     | days             | None       | count of days between earliest referral date and earliest completed phone encounter |
| new\_visit\_count | integer          | 0          | count of encounters with type new linked to MRN|
| complete\_new\_visit\_count                  | integer          | 0          | count of completed encounters with type new linked to MRN      |
| total\_visit\_count | integer          | 0          | count of all encounters linked to MRN|
| complete\_visit\_count | integer          | 0          | count of all completed encounters linked to MRN|

## Encounter

| Variable name       | type     | Description                   |
| ------------------- | -------- | ------------------------------------------------------ |
| mrn                 | integer  | pulled directly from spreadsheet |
| pt\_name            | string   | pulled directly from spreadsheet |
| id                  | integer  | pulled directly from spreadsheet |
| provider            | string   | pulled directly from spreadsheet |
| department          | string   | pulled directly from spreadsheet |
| type                | string   | pulled directly from spreadsheet |
| date                | DateTime | pulled directly from spreadsheet |
| month               | integer  | pulled directly from spreadsheet |
| status              | string   | pulled directly from spreadsheet |
| is\_procedure       | boolean  | TRUE if row's visit\_category == "Procedure"           |
| is\_visit           | boolean  | TRUE if row's visit\_category == "Office Visit"        |
| is\_completed       | boolean  | TRUE if row's visit\_status == "Completed"             |
| is\_incomplete      | boolean  | FALSE if row's visit\_status == "Completed"            |
| is\_new             | boolean  | TRUE if row's new\_patient == "Yes"                    |
| is\_virtual         | boolean  | TRUE if row's visit\_type is in config virtual\_types  |
| is\_phone           | boolean  | TRUE if row's visit\_type is in config phone\_types    |
| is\_office          | boolean  | TRUE if is\_visit and not virtual, phone, or procedure |
| is\_cancelled       | boolean  | TRUE if row's status == "Completed"                    |
| scheduling\_date    | DateTime | pulled directly from spreadsheet |
| icd\_id             | string   | pulled directly from spreadsheet |
| icd\_name           | string   | pulled directly from spreadsheet |
| referral\_date      | DateTime | pulled directly from spreadsheet |
| referral\_provider  | string   | pulled directly from spreadsheet |
| referral\_specialty | string   | pulled directly from spreadsheet |
| referral\_service   | string   | pulled directly from spreadsheet |
| payor               | string   | pulled directly from spreadsheet |