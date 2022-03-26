---
title: "Telemedicine Stats"
output: raw_stats
---
```{r include = FALSE}
library(tidyverse)
library(dplyr)
library(ggplot2)
library(gtsummary)
```

md <- read_csv("Documents/GitHub/uro-telemed/helpers/all_patients.csv", 
                        col_types = cols(age = col_integer(), 
                        new_visit_date = col_date(format = "%Y-%m-%d"),
                        scheduling_date = col_date(format = "%Y-%m-%d"),
                        procedure_date = col_date(format = "%Y-%m-%d"),
                        referral_to_first_procedure = col_integer(),
                        first_visit_to_first_procedure = col_integer(),
                        first_visit_to_surgery = col_integer()))
md$marital_status[md$marital_status=="Unknown"] <- NA
md$sex[md$sex=="Unknown"] <- NA
md$race[md$race=="Declined / Unknown"] <- NA
md$language[md$language=="Declined / Unknown"] <- NA


# ggplot(data = md) + geom_bar(mapping = aes(x = new_visit_type, fill = has_procedure), position="fill")

# by_type <- group_by(md, new_visit_type)
# by_race <- group_by(md, race)


# Table 1 
# md %>%
#   group_by(new_visit_type) %>%
#   summarise(age.mean = mean(age, na.rm = TRUE), age.std = sd(age, na.rm=TRUE))
# md %>%
#   summarise(age.mean = mean(age, na.rm = TRUE), age.std = sd(age, na.rm=TRUE))
age_intervals = c(18, 30, 45, 60, 75, 1000)
md2 <- md %>% select(new_visit_type, diagnosis_category, age, sex, marital_status, race, language, ruca)
md2 %>% tbl_summary(
  by = new_visit_type,
  statistic = list(all_continuous() ~ "{mean} ({sd})",
                   all_categorical() ~ "{n} ({p}%)"),
  digits = all_continuous() ~ 1,
  missing_text = "(Missing)") %>% 
  add_overall() %>%
  add_n() %>%
  add_p()

# Table 2
table(md$new_visit_type, md$appt_cancellation > 0)
chisq.test(md$new_visit_type, md$appt_cancellation > 0)

table(md$new_visit_type, md$has_procedure)
chisq.test(md$new_visit_type, md$has_procedure)

table(md$new_visit_type, md$procedure_cancellation)
chisq.test(md$new_visit_type, md$procedure_cancellation)

table(md$new_visit_type, md$has_surgery)
chisq.test(md$new_visit_type, md$has_surgery)

# Table 3
md3 <- md %>% 
  select(new_visit_type, referral_to_first_visit, scheduling_to_first_visit, scheduling_to_first_procedure, referral_to_first_procedure, first_visit_to_first_procedure)
md3 %>% tbl_summary(
  by=new_visit_type,
  statistic = list(all_continuous() ~ "{mean} ({sd})"),
  digits = all_continuous() ~ 1,
  missing_text = "no procedure") %>%
  add_p()

```{r}
# Table 4

md %>% 
  mutate(age_groups = cut(age, age_intervals, include.lowest = TRUE, right = FALSE)) %>%
  group_by(age_groups, new_visit_type) %>%
  summarise("has appt cancellation" = sum(appt_cancellation > 0),
            "has procedure" = sum(has_procedure),
            "has procedure cancellation" = sum(procedure_cancellation),
            "has surgery" = sum(has_surgery)) %>%
  arrange(new_visit_type)


age1 <- filter(md, age >= age_intervals[1] & age < age_intervals[2])
age2 <- filter(md, age >= age_intervals[2] & age < age_intervals[3])
age3 <- filter(md, age >= age_intervals[3] & age < age_intervals[4])
age4 <- filter(md, age >= age_intervals[4] & age < age_intervals[5])
age5 <- filter(md, age >= age_intervals[5])
ages = list(age1, age2, age3, age4, age5)
for (i in 1:length(ages)) {
  writeLines("*******************************************\nAge interval starting with:")
  print(age_intervals[i])
  writeLines("~~~HAS APPOINTMENT CANCELLATION~~~")
  print(table(ages[[i]]$new_visit_type, ages[[i]]$appt_cancellation > 0))
  print(paste("p = ", chisq.test(ages[[i]]$new_visit_type, ages[[i]]$appt_cancellation > 0)$p.value))
  
  writeLines("~~~HAS PROCEDURE CANCELLATION~~~")
  with_proc <- filter(ages[[i]], has_procedure)
  print(table(with_proc$new_visit_type, with_proc$procedure_cancellation > 0))
  print(paste("p = ", chisq.test(with_proc$new_visit_type, with_proc$procedure_cancellation > 0)$p.value))
  
  writeLines("~~~HAS PROCEDURE~~~")
  print(table(ages[[i]]$new_visit_type, ages[[i]]$has_procedure))
  print(paste("p = ", chisq.test(ages[[i]]$new_visit_type, ages[[i]]$has_procedure)$p.value))
  
  writeLines("~~~HAS SURGERY~~~")
  print(table(ages[[i]]$new_visit_type, ages[[i]]$has_surgery))
  print(paste("p = ", chisq.test(ages[[i]]$new_visit_type, ages[[i]]$has_surgery)$p.value))
}

zip_intervals <- c(0, 25, 50, 100, 1000000)
zip1 <- filter(md, zipcode_distance >= zip_intervals[1] & zipcode_distance < zip_intervals[2])
zip2 <- filter(md, zipcode_distance >= zip_intervals[2] & zipcode_distance < zip_intervals[3])
zip3 <- filter(md, zipcode_distance >= zip_intervals[3] & zipcode_distance < zip_intervals[4])
zip4 <- filter(md, zipcode_distance >= zip_intervals[4])
zips = list(zip1, zip2, zip3, zip4)
for (i in 1:length(zips)) {
  writeLines("*******************************************\nZip interval starting with:")
  print(zip_intervals[i])
  writeLines("~~~HAS APPOINTMENT CANCELLATION~~~")
  print(table(zips[[i]]$new_visit_type, zips[[i]]$appt_cancellation > 0))
  print(paste("p = ", chisq.test(zips[[i]]$new_visit_type, zips[[i]]$appt_cancellation > 0)$p.value))
  
  writeLines("~~~HAS PROCEDURE CANCELLATION~~~")
  with_proc <- filter(zips[[i]], has_procedure)
  print(table(with_proc$new_visit_type, with_proc$procedure_cancellation > 0))
  print(paste("p = ", chisq.test(with_proc$new_visit_type, with_proc$procedure_cancellation > 0)$p.value))
  
  writeLines("~~~HAS PROCEDURE~~~")
  print(table(zips[[i]]$new_visit_type, zips[[i]]$has_procedure))
  print(paste("p = ", chisq.test(zips[[i]]$new_visit_type, zips[[i]]$has_procedure)$p.value))
  
  writeLines("~~~HAS SURGERY~~~")
  print(table(zips[[i]]$new_visit_type, zips[[i]]$has_surgery))
  print(paste("p = ", chisq.test(zips[[i]]$new_visit_type, zips[[i]]$has_surgery)$p.value))
}

table4stats <- function(val) {
  md %>%
    group_by(!!as.name(val), new_visit_type) %>%
    summarise("has appt cancellation" = sum(appt_cancellation > 0),
              "has procedure" = sum(has_procedure),
              "has procedure cancellation" = sum(procedure_cancellation),
              "has surgery" = sum(has_surgery)) %>%
    arrange(new_visit_type)
  unique_vals = unique(na.omit(md[[val]]))
  for (i in 1:length(unique_vals)) {
    vals <- md %>% filter(!!as.name(val) == unique_vals[[i]])
    writeLines("*******************************************")
    print(paste(val, ":"))
    print(unique_vals[[i]])
    writeLines("~~~HAS APPOINTMENT CANCELLATION~~~")
    print(table(vals$new_visit_type, vals$appt_cancellation > 0))
    possibleError <- tryCatch(
      print(paste(
        "p = ",
        chisq.test(vals$new_visit_type, vals$appt_cancellation > 0)$p.value
      )),
      error = function(e) {
        1
      }
    )
    
    writeLines("~~~HAS PROCEDURE CANCELLATION~~~")
    with_proc <- filter(vals, has_procedure)
    print(table(
      with_proc$new_visit_type,
      with_proc$procedure_cancellation > 0
    ))
    possibleError <- tryCatch(
      print(paste(
        "p = ",
        chisq.test(
          with_proc$new_visit_type,
          with_proc$procedure_cancellation > 0
        )$p.value
      )),
      error = function(e) {
        1
      }
    )
    
    writeLines("~~~HAS PROCEDURE~~~")
    print(table(vals$new_visit_type, vals$has_procedure))
    possibleError <- tryCatch(
      print(paste(
        "p = ",
        chisq.test(vals$new_visit_type, vals$has_procedure)$p.value
      )),
      error = function(e) {
        1
      }
    )
    writeLines("~~~HAS SURGERY~~~")
    print(table(vals$new_visit_type, vals$has_surgery))
    possibleError <-
      tryCatch(
        print(paste(
          "p = ",
          chisq.test(vals$new_visit_type, vals$has_surgery)$p.value)),
        error = function(e) {
          1
        }
      )
  }
}
dem_vars <-
  list("sex",
       "marital_status",
       "language",
       "diagnosis_category",
       "ruca",
       "race")
for (dem_var in dem_vars) {
  table4stats(dem_var)
}

```
# Table 5
md5 <- md %>% 
  select(new_visit_type, diagnosis_category, age, sex, marital_status, race, language, ruca, referral_to_first_visit, scheduling_to_first_visit, scheduling_to_first_procedure, referral_to_first_procedure, first_visit_to_first_procedure) %>%
  group_by(new_visit_type)
t.test(age ~ new_visit_type, md)
chisq.test(md$new_visit_type, md$race)
chisq.test(md$new_visit_type, md$marital_status)
chisq.test(md$new_visit_type, md$language)
table(md$new_visit_type, md$appt_cancellation)
chisq.test(md$new_visit_type, md$has_procedure)
