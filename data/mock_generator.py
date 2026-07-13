import os
import json
import sqlite3

MOCK_ENCOUNTERS = [
    {
        "record_id": "REC001",
        "patient_id": "PT101",
        "encounter_id": "ENC201",
        "specialty": "Cardiology",
        "note_text": (
            "CHIEF COMPLAINT:\n"
            "Worsening shortness of breath, orthopnea, and severe bilateral lower extremity edema.\n\n"
            "HISTORY OF PRESENT ILLNESS:\n"
            "The patient is a 67-year-old male with a history of long-standing coronary artery disease, "
            "status-post coronary artery bypass graft (CABG) surgery in 2018, who presents with a three-week "
            "history of progressive dyspnea on exertion. He reports needing to sleep on three pillows "
            "due to orthopnea. On physical exam, there is marked jugular venous distention and 3+ pitting "
            "edema bilaterally up to the mid-calf. This is consistent with an acute exacerbation of chronic "
            "systolic heart failure, NYHA Class III, Stage C. During this admission, a diagnostic cardiac "
            "catheterization was performed to evaluate graft patency, alongside a separate comprehensive "
            "cardiovascular evaluation.\n\n"
            "CURRENT MEDICATIONS:\n"
            "1. Lisinopril 10 mg PO daily for blood pressure control and afterload reduction."
        ),
        "note_section": "Discharge Summary",
        "ground_truth_codes": "I50.23,93451,99213",
        "ground_truth_modifiers": "99213:25",
        "v1_codes": "I50.23,93451,99213",
        "v1_modifiers": "99213:25",
        "v1_conf": "0.95,0.91,0.89",
        "v2_codes": "I50.9,93451,99213",  # Regression: general heart failure instead of chronic systolic
        "v2_modifiers": "99213",        # Regression: Missing modifier 25
        "v2_conf": "0.85,0.92,0.88"
    },
    {
        "record_id": "REC002",
        "patient_id": "PT102",
        "encounter_id": "ENC202",
        "specialty": "Endocrinology",
        "note_text": (
            "REASON FOR VISIT:\n"
            "Routine follow-up evaluation for chronic hypothyroidism and thyroid hormone replacement titration.\n\n"
            "CLINICAL ASSESSMENT:\n"
            "The patient is a 45-year-old female who was diagnosed with primary hypothyroidism six years ago. "
            "She reports some improvement in her global symptoms, though she still complains of occasional "
            "afternoon fatigue, mild cold intolerance, and xerosis. Her latest thyroid-stimulating hormone (TSH) "
            "level was slightly elevated at 5.2 mIU/L, indicating inadequate replacement.\n\n"
            "PLAN & MEDICATION DISPOSITION:\n"
            "We will adjust her thyroid hormone replacement strategy. She will continue taking levothyroxine "
            "at the slightly adjusted dosage of 100 mcg daily. We will repeat her TSH and free T4 levels "
            "in approximately six to eight weeks."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "E03.9",
        "ground_truth_modifiers": "",
        "v1_codes": "E03.9",
        "v1_modifiers": "",
        "v1_conf": "0.98",
        "v2_codes": "E03.9",
        "v2_modifiers": "",
        "v2_conf": "0.97",
    },
    {
        "record_id": "REC003",
        "patient_id": "PT103",
        "encounter_id": "ENC203",
        "specialty": "Orthopedics",
        "note_text": (
            "POSTOPERATIVE CLINICAL PROGRESS NOTE:\n"
            "The patient is a 54-year-old male who is currently six weeks status-post left knee arthroscopy "
            "with partial medial meniscectomy for a chronic meniscus tear. Overall, he is progressing well. "
            "Active range of motion is 0 to 115 degrees with mild discomfort at terminal flexion. "
            "He will proceed with structured physical therapy and active rehabilitation exercises twice a week.\n\n"
            "COMORBIDITIES MANAGEMENT:\n"
            "The patient's co-existing diabetic mellitus type 2 remains stable. He reports compliance with "
            "his oral hypoglycemic agents and denies any neuropathic symptoms or visual changes."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "M23.22,E11.9",
        "ground_truth_modifiers": "",
        "v1_codes": "M23.22,E11.9",
        "v1_modifiers": "",
        "v1_conf": "0.94,0.90",
        "v2_codes": "M23.22",  # Regression: missed HCC code (E11.9)
        "v2_modifiers": "",
        "v2_conf": "0.95"
    },
    {
        "record_id": "REC004",
        "patient_id": "PT104",
        "encounter_id": "ENC204",
        "specialty": "Cardiology",
        "note_text": (
            "ADMISSION NOTE:\n"
            "The patient is an 81-year-old female admitted with a two-day history of worsening orthopnea and paroxysmal "
            "nocturnal dyspnea. Echocardiogram reveals an ejection fraction of 55% with marked diastolic dysfunction, "
            "consistent with an acute exacerbation of chronic diastolic heart failure. An intravenous infusion of "
            "furosemide was initiated to promote diuresis.\n\n"
            "DISCHARGE MEDICATION REGIMEN:\n"
            "1. Lisinopril 20 mg PO daily for hypertensive and cardiac remodeling management."
        ),
        "note_section": "Discharge Summary",
        "ground_truth_codes": "I50.33",
        "ground_truth_modifiers": "",
        "v1_codes": "I50.33",
        "v1_modifiers": "",
        "v1_conf": "0.93",
        "v2_codes": "I50.33",
        "v2_modifiers": "",
        "v2_conf": "0.94"
    },
    {
        "record_id": "REC005",
        "patient_id": "PT105",
        "encounter_id": "ENC205",
        "specialty": "Orthopedics",
        "note_text": (
            "REHABILITATION SESSION SUMMARY:\n"
            "The patient attended a scheduled physical therapy evaluation today to address range of motion limitations "
            "following left hip arthroplasty. A series of therapeutic exercises were initiated. Unfortunately, "
            "due to a billing database duplication error, duplicate codes 97110 and 97110 were registered for the "
            "same physical therapy session."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "97110",
        "ground_truth_modifiers": "",
        "v1_codes": "97110",
        "v1_modifiers": "",
        "v1_conf": "0.96",
        "v2_codes": "97110,97110",  # Regression: Duplicate codes
        "v2_modifiers": "",
        "v2_conf": "0.95,0.85"
    },
    {
        "record_id": "REC006",
        "patient_id": "PT106",
        "encounter_id": "ENC206",
        "specialty": "Gastroenterology",
        "note_text": (
            "PROCEDURE REPORT:\n"
            "The patient underwent a scheduled diagnostic colonoscopy today to investigate a history of lower "
            "abdominal discomfort. The scope was advanced successfully to the cecum. A history of mild "
            "gastroesophageal reflux disease (GERD) was also noted during the pre-operative history and physical."
        ),
        "note_section": "Procedure Note",
        "ground_truth_codes": "45378,K21.9",
        "ground_truth_modifiers": "",
        "v1_codes": "45378,K21.9",
        "v1_modifiers": "",
        "v1_conf": "0.95,0.92",
        "v2_codes": "45378,K21.9",
        "v2_modifiers": "",
        "v2_conf": "0.94,0.93"
    },
    {
        "record_id": "REC007",
        "patient_id": "PT107",
        "encounter_id": "ENC207",
        "specialty": "Neurology",
        "note_text": (
            "NEUROLOGICAL CONSULTATION:\n"
            "The patient is a 29-year-old female presenting with a history of recurrent, unilateral migraine headaches "
            "associated with photophobia and nausea. Symptoms are partially relieved by sleep. We will initiate a trial "
            "of sumatriptan 50 mg PO at the onset of migraine symptoms."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "G43.909",
        "ground_truth_modifiers": "",
        "v1_codes": "G43.909",
        "v1_modifiers": "",
        "v1_conf": "0.97",
        "v2_codes": "G43.909",
        "v2_modifiers": "",
        "v2_conf": "0.96"
    },
    {
        "record_id": "REC008",
        "patient_id": "PT108",
        "encounter_id": "ENC208",
        "specialty": "Pulmonology",
        "note_text": (
            "CLINICAL PROGRESS NOTE:\n"
            "The patient is an 64-year-old male with a history of tobacco abuse who is evaluated today for progressive "
            "dyspnea. Pulmonary function tests demonstrate airflow obstruction consistent with chronic obstructive "
            "pulmonary disease (COPD). The patient will be started on an albuterol rescue inhaler as needed."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "J44.9",
        "ground_truth_modifiers": "",
        "v1_codes": "J44.9",
        "v1_modifiers": "",
        "v1_conf": "0.94",
        "v2_codes": "J44.9",
        "v2_modifiers": "",
        "v2_conf": "0.95"
    },
    {
        "record_id": "REC009",
        "patient_id": "PT109",
        "encounter_id": "ENC209",
        "specialty": "Nephrology",
        "note_text": (
            "NEPHROLOGY CLINICAL PROGRESS NOTE:\n"
            "The patient is an 72-year-old male with a history of hypertension and vascular disease who is seen for "
            "follow-up of chronic kidney disease, stage 3. Latest metabolic panel shows a stable creatinine level of "
            "1.8 mg/dL with a calculated eGFR of 38 mL/min/1.73m2."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "N18.3",
        "ground_truth_modifiers": "",
        "v1_codes": "N18.3",
        "v1_modifiers": "",
        "v1_conf": "0.93",
        "v2_codes": "N18.3",
        "v2_modifiers": "",
        "v2_conf": "0.94"
    },
    {
        "record_id": "REC010",
        "patient_id": "PT110",
        "encounter_id": "ENC210",
        "specialty": "Oncology",
        "note_text": (
            "ONCOLOGY CONSULTATION NOTE:\n"
            "The patient is a 61-year-old female diagnosed with invasive ductal carcinoma of the breast, stage II. "
            "We discussed active adjuvant chemotherapy strategies and scheduled her first cycle for next week."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "C50.919",
        "ground_truth_modifiers": "",
        "v1_codes": "C50.919",
        "v1_modifiers": "",
        "v1_conf": "0.96",
        "v2_codes": "C50.919",
        "v2_modifiers": "",
        "v2_conf": "0.95"
    },
    {
        "record_id": "REC011",
        "patient_id": "PT111",
        "encounter_id": "ENC211",
        "specialty": "Pediatrics",
        "note_text": (
            "PEDIATRIC OUTPATIENT NOTE:\n"
            "The patient is a 4-year-old female presenting with a 2-day history of right ear pain, "
            "irritability, and subjective low-grade fevers. Physical exam shows an erythematous, bulging tympanic "
            "membrane with middle ear effusion, consistent with acute otitis media.\n\n"
            "PLAN:\n"
            "Start amoxicillin suspension 400 mg PO twice daily. Dosage checked by pediatrician."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "H66.001",
        "ground_truth_modifiers": "",
        "v1_codes": "H66.001",
        "v1_modifiers": "",
        "v1_conf": "0.96",
        "v2_codes": "H66.001", # Regression: unit confusion E/M dosage unit error in audit mapping
        "v2_modifiers": "",
        "v2_conf": "0.94"
    },
    {
        "record_id": "REC012",
        "patient_id": "PT112",
        "encounter_id": "ENC212",
        "specialty": "Gastroenterology",
        "note_text": (
            "PROCEDURE REPORT:\n"
            "The patient was scheduled for a diagnostic colonoscopy and diagnostic flexible sigmoidoscopy to investigate "
            "intermittent rectal bleeding. A colonoscopy (45378) was advanced successfully to the cecum. A separate "
            "sigmoidoscopy (45330) was performed on the same day.\n\n"
            "COMMENTS:\n"
            "Per NCCI guidelines, CPT 45330 is mutually exclusive and bundled into 45378, causing a billing conflict "
            "if coded together without clinical justification."
        ),
        "note_section": "Procedure Note",
        "ground_truth_codes": "45378",
        "ground_truth_modifiers": "",
        "v1_codes": "45378",
        "v1_modifiers": "",
        "v1_conf": "0.95",
        "v2_codes": "45378,45330",  # Regression: NCCI billing conflict violation
        "v2_modifiers": "",
        "v2_conf": "0.94,0.88"
    },
    {
        "record_id": "REC013",
        "patient_id": "PT113",
        "encounter_id": "ENC213",
        "specialty": "Family Medicine",
        "note_text": (
            "FAMILY MEDICINE CLINICAL ENCOUNTER:\n"
            "The patient is a 64-year-old male presenting for follow-up of type 2 diabetes mellitus with diabetic nephropathy "
            "and chronic kidney disease stage 4 (eGFR is stable at 24 mL/min/1.73m2). He is compliant with insulin and oral agents.\n\n"
            "IMPRESSION:\n"
            "1. Type 2 diabetes with chronic kidney disease (E11.22)\n"
            "2. Stage 4 Chronic Kidney Disease (N18.4)"
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "E11.22,N18.4",
        "ground_truth_modifiers": "",
        "v1_codes": "E11.22,N18.4",
        "v1_modifiers": "",
        "v1_conf": "0.93,0.91",
        "v2_codes": "E11.9",  # Regression: missed diabetic nephropathy and CKD HCC codes (undercoding)
        "v2_modifiers": "",
        "v2_conf": "0.85"
    },
    {
        "record_id": "REC014",
        "patient_id": "PT114",
        "encounter_id": "ENC214",
        "specialty": "Radiology",
        "note_text": (
            "EXAMINATION: CHEST X-RAY 2 VIEWS\n\n"
            "CLINICAL INDICATION:\n"
            "74-year-old male with chronic cough and history of COPD. Rule out active consolidation.\n\n"
            "FINDINGS:\n"
            "Lung volumes are hyperexpanded with flattening of the hemidiaphragms, consistent with emphysema. "
            "No focal consolidation, pneumothorax, or large pleural effusion."
        ),
        "note_section": "Procedure Note",
        "ground_truth_codes": "71046,J43.9",
        "ground_truth_modifiers": "",
        "v1_codes": "71046,J43.9",
        "v1_modifiers": "",
        "v1_conf": "0.97,0.94",
        "v2_codes": "71045,J44.9",  # Regression: incorrect procedure code and general COPD instead of emphysema
        "v2_modifiers": "",
        "v2_conf": "0.87,0.89"
    },
    {
        "record_id": "REC015",
        "patient_id": "PT115",
        "encounter_id": "ENC215",
        "specialty": "Urgent Care",
        "note_text": (
            "URGENT CARE ENCOUNTER:\n"
            "The patient is a 32-year-old female presenting with a deep laceration of the right forearm sustained from broken glass. "
            "A layered intermediate repair of the 5.0 cm forearm wound was performed (CPT 12032).\n\n"
            "EVALUATION:\n"
            "An independent comprehensive E/M evaluation was also performed to address systemic complaints and tetnus status check."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "12032,99213",
        "ground_truth_modifiers": "99213:25",
        "v1_codes": "12032,99213",
        "v1_modifiers": "99213:25",
        "v1_conf": "0.94,0.91",
        "v2_codes": "12032,99213",  # Regression: Missing modifier 25 on office visit
        "v2_modifiers": "",
        "v2_conf": "0.93,0.88"
    },
    {
        "record_id": "REC016",
        "patient_id": "PT116",
        "encounter_id": "ENC216",
        "specialty": "Gynecology",
        "note_text": (
            "GYNECOLOGY WELLNESS ENCOUNTER:\n"
            "The patient is a 35-year-old female presenting for her annual wellness preventive exam (CPT 99395). "
            "A screening Pap smear was obtained during the examination (Q0091)."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "99395,Q0091",
        "ground_truth_modifiers": "",
        "v1_codes": "99395,Q0091",
        "v1_modifiers": "",
        "v1_conf": "0.96,0.92",
        "v2_codes": "99395",  # Regression: missed screening code Q0091 (undercoding leakage)
        "v2_modifiers": "",
        "v2_conf": "0.95"
    },
    {
        "record_id": "REC017",
        "patient_id": "PT117",
        "encounter_id": "ENC217",
        "specialty": "Cardiology",
        "note_text": (
            "CARDIOLOGY ENCOUNTER SUMMARY:\n"
            "The patient is a 72-year-old female presenting with chronic chest pain and dyspnea on exertion. "
            "We performed a cardiovascular stress test using treadmill exercise and continuous ECG recording (CPT 93015) "
            "to evaluate ischemia. Additionally, an office E/M level 4 service was completed for medication titration."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "93015,99214",
        "ground_truth_modifiers": "99214:25",
        "v1_codes": "93015,99214",
        "v1_modifiers": "99214:25",
        "v1_conf": "0.95,0.92",
        "v2_codes": "93015,99214",  # Regression: missing modifier 25 on E/M visit
        "v2_modifiers": "",
        "v2_conf": "0.93,0.87"
    },
    {
        "record_id": "REC018",
        "patient_id": "PT118",
        "encounter_id": "ENC218",
        "specialty": "Internal Medicine",
        "note_text": (
            "INTERNAL MEDICINE PROGRESS NOTE:\n"
            "The patient is an 80-year-old male with a history of severe persistent asthma and acute exacerbation of chronic "
            "obstructive pulmonary disease (COPD). The patient was started on a course of systemic prednisone 40 mg PO daily."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "J44.1,J45.50",
        "ground_truth_modifiers": "",
        "v1_codes": "J44.1,J45.50",
        "v1_modifiers": "",
        "v1_conf": "0.94,0.91",
        "v2_codes": "J44.9",  # Regression: missed acute exacerbation detail and persistent asthma HCC code
        "v2_modifiers": "",
        "v2_conf": "0.86"
    },
    {
        "record_id": "REC019",
        "patient_id": "PT119",
        "encounter_id": "ENC219",
        "specialty": "Endocrinology",
        "note_text": (
            "ENDOCRINE CLINICAL SUMMARY:\n"
            "The patient is a 52-year-old male with type 1 diabetes mellitus presenting with severe diabetic retinopathy "
            "complication. He is managed with insulin pump therapy."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "E10.319",
        "ground_truth_modifiers": "",
        "v1_codes": "E10.319",
        "v1_modifiers": "",
        "v1_conf": "0.95",
        "v2_codes": "E10.9",  # Regression: undercoded to uncomplicated T1D, leaking diabetic retinopathy HCC code
        "v2_modifiers": "",
        "v2_conf": "0.85"
    },
    {
        "record_id": "REC020",
        "patient_id": "PT120",
        "encounter_id": "ENC220",
        "specialty": "Orthopedics",
        "note_text": (
            "POSTOPERATIVE DISCHARGE SUMMARY:\n"
            "The patient is a 45-year-old male discharged following a successful arthroscopic rotator cuff repair (29827). "
            "Physical therapy scheduled. Prescription given for oxycodone 5 mg PO q4h as needed for severe pain."
        ),
        "note_section": "Discharge Summary",
        "ground_truth_codes": "29827",
        "ground_truth_modifiers": "",
        "v1_codes": "29827",
        "v1_modifiers": "",
        "v1_conf": "0.96",
        "v2_codes": "29827,29827",  # Regression: duplicate procedural codes registered
        "v2_modifiers": "",
        "v2_conf": "0.95,0.82"
    },
    {
        "record_id": "REC021",
        "patient_id": "PT121",
        "encounter_id": "ENC221",
        "specialty": "Pediatrics",
        "note_text": (
            "PEDIATRIC PROGRESS NOTE:\n"
            "A 6-year-old boy presenting with streptococcal pharyngitis confirmed via rapid strep test. "
            "Prescribed penicillin V potassium oral suspension 250 mg PO twice daily for 10 days."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "J02.0",
        "ground_truth_modifiers": "",
        "v1_codes": "J02.0",
        "v1_modifiers": "",
        "v1_conf": "0.98",
        "v2_codes": "J02.0",  # Regression: unit confusion dosage mapping error (audit check)
        "v2_modifiers": "",
        "v2_conf": "0.97"
    },
    {
        "record_id": "REC022",
        "patient_id": "PT122",
        "encounter_id": "ENC222",
        "specialty": "Gastroenterology",
        "note_text": (
            "PROCEDURE ENCOUNTER:\n"
            "Outpatient diagnostic esophagogastroduodenoscopy (EGD) (CPT 43235) was performed to evaluate reflux. "
            "Additionally, an active esophageal biopsy was obtained (CPT 43239) on the same day.\n\n"
            "COMMENTS:\n"
            "CPT 43235 is mutually exclusive and bundled under CPT 43239 per NCCI rules."
        ),
        "note_section": "Procedure Note",
        "ground_truth_codes": "43239",
        "ground_truth_modifiers": "",
        "v1_codes": "43239",
        "v1_modifiers": "",
        "v1_conf": "0.95",
        "v2_codes": "43239,43235",  # Regression: NCCI bundling conflict violation
        "v2_modifiers": "",
        "v2_conf": "0.94,0.86"
    },
    {
        "record_id": "REC023",
        "patient_id": "PT123",
        "encounter_id": "ENC223",
        "specialty": "Family Medicine",
        "note_text": (
            "FAMILY MEDICINE CLINICAL ENCOUNTER:\n"
            "A 68-year-old male with chronic gout, vascular disease, and Stage 4 chronic kidney disease. "
            "Allopurinol dosage managed."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "M1A.9XX0,N18.4",
        "ground_truth_modifiers": "",
        "v1_codes": "M1A.9XX0,N18.4",
        "v1_modifiers": "",
        "v1_conf": "0.93,0.91",
        "v2_codes": "M10.9",  # Regression: undercoded gout detail and missed CKD stage 4 HCC code
        "v2_modifiers": "",
        "v2_conf": "0.82"
    },
    {
        "record_id": "REC024",
        "patient_id": "PT124",
        "encounter_id": "ENC224",
        "specialty": "Radiology",
        "note_text": (
            "PROCEDURE: CT SCAN HEAD W/O CONTRAST\n\n"
            "INDICATIONS:\n"
            "60-year-old male post-fall. Evaluate for acute subdural hematoma.\n\n"
            "FINDINGS:\n"
            "No acute intracranial hemorrhage, midline shift, or mass effect."
        ),
        "note_section": "Procedure Note",
        "ground_truth_codes": "70450",
        "ground_truth_modifiers": "",
        "v1_codes": "70450",
        "v1_modifiers": "",
        "v1_conf": "0.98",
        "v2_codes": "70460",  # Regression: coded CT head WITH contrast, which is incorrect
        "v2_modifiers": "",
        "v2_conf": "0.89"
    },
    {
        "record_id": "REC025",
        "patient_id": "PT125",
        "encounter_id": "ENC225",
        "specialty": "Urgent Care",
        "note_text": (
            "URGENT CARE VISIT:\n"
            "A 40-year-old male presenting with a closed fracture of the distal clavicle. "
            "Treatment consisted of closed application of a shoulder sling. Separate outpatient E/M level 3 visit."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "23500,99213",
        "ground_truth_modifiers": "99213:25",
        "v1_codes": "23500,99213",
        "v1_modifiers": "99213:25",
        "v1_conf": "0.94,0.92",
        "v2_codes": "23500,99213",  # Regression: missing modifier 25 on E/M
        "v2_modifiers": "",
        "v2_conf": "0.93,0.85"
    },
    {
        "record_id": "REC026",
        "patient_id": "PT126",
        "encounter_id": "ENC226",
        "specialty": "Gynecology",
        "note_text": (
            "OBGYN VISIT:\n"
            "A 28-year-old female presenting for preventive routine gynecological exam (99395) and screening pap smear (Q0091)."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "99395,Q0091",
        "ground_truth_modifiers": "",
        "v1_codes": "99395,Q0091",
        "v1_modifiers": "",
        "v1_conf": "0.97,0.93",
        "v2_codes": "99395",  # Regression: undercoded Q0091
        "v2_modifiers": "",
        "v2_conf": "0.96"
    },
    {
        "record_id": "REC027",
        "patient_id": "PT127",
        "encounter_id": "ENC227",
        "specialty": "Cardiology",
        "note_text": (
            "CARDIAC CLINICAL ENCOUNTER:\n"
            "A 69-year-old male with stable angina presenting for medication reviews. "
            "An office E/M level 3 was completed, alongside a separate electrocardiogram (ECG) 12-lead (CPT 93000)."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "93000,99213",
        "ground_truth_modifiers": "99213:25",
        "v1_codes": "93000,99213",
        "v1_modifiers": "99213:25",
        "v1_conf": "0.96,0.91",
        "v2_codes": "93000,99213",  # Regression: missing modifier 25
        "v2_modifiers": "",
        "v2_conf": "0.94,0.85"
    },
    {
        "record_id": "REC028",
        "patient_id": "PT128",
        "encounter_id": "ENC228",
        "specialty": "Internal Medicine",
        "note_text": (
            "INTERNAL MEDICINE CONSULTATION:\n"
            "A 75-year-old female with chronic kidney disease stage 4 (eGFR is stable at 26 mL/min/1.73m2) "
            "and hypertensive heart disease. Losinopril adjusted."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "I11.9,N18.4",
        "ground_truth_modifiers": "",
        "v1_codes": "I11.9,N18.4",
        "v1_modifiers": "",
        "v1_conf": "0.94,0.92",
        "v2_codes": "I10",  # Regression: missed hypertensive heart disease and CKD stage 4 HCC code
        "v2_modifiers": "",
        "v2_conf": "0.83"
    },
    {
        "record_id": "REC029",
        "patient_id": "PT129",
        "encounter_id": "ENC229",
        "specialty": "Endocrinology",
        "note_text": (
            "ENDOCRINOLOGY EVALUATION:\n"
            "A 45-year-old female diagnosed with Hashimoto's thyroiditis and chronic primary hypothyroidism. "
            "Levothyroxine adjusted."
        ),
        "note_section": "Consultation",
        "ground_truth_codes": "E06.3,E03.9",
        "ground_truth_modifiers": "",
        "v1_codes": "E06.3,E03.9",
        "v1_modifiers": "",
        "v1_conf": "0.96,0.93",
        "v2_codes": "E03.9",  # Regression: missed Hashimoto's E06.3 code
        "v2_modifiers": "",
        "v2_conf": "0.94"
    },
    {
        "record_id": "REC030",
        "patient_id": "PT130",
        "encounter_id": "ENC230",
        "specialty": "Orthopedics",
        "note_text": (
            "ORTHOPEDICS PROGRESS ENCOUNTER:\n"
            "A 50-year-old female post left knee total replacement. Outpatient rehabilitation physical therapy session completed today."
        ),
        "note_section": "Progress Note",
        "ground_truth_codes": "97110",
        "ground_truth_modifiers": "",
        "v1_codes": "97110",
        "v1_modifiers": "",
        "v1_conf": "0.97",
        "v2_codes": "97110,97110",  # Regression: duplicate physical therapy codes registered
        "v2_modifiers": "",
        "v2_conf": "0.95,0.81"
    }
]

def generate_db(db_path="data/synapse_audit.db"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clinical_encounters (
        record_id TEXT PRIMARY KEY,
        patient_id TEXT NOT NULL,
        encounter_id TEXT NOT NULL,
        specialty TEXT NOT NULL,
        note_text TEXT NOT NULL,
        note_section TEXT NOT NULL,
        ground_truth_codes TEXT NOT NULL,
        ground_truth_modifiers TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_predictions (
        prediction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT REFERENCES clinical_encounters(record_id),
        model_version TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        predicted_codes TEXT NOT NULL,
        predicted_modifiers TEXT,
        confidence_scores TEXT,
        token_attributions TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compliance_audit_results (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id TEXT REFERENCES clinical_encounters(record_id),
        model_version TEXT NOT NULL,
        prompt_version TEXT NOT NULL,
        error_type TEXT NOT NULL,
        risk_score REAL NOT NULL,
        details TEXT
    );
    """)

    cursor.execute("DELETE FROM compliance_audit_results")
    cursor.execute("DELETE FROM model_predictions")
    cursor.execute("DELETE FROM clinical_encounters")

    for r in MOCK_ENCOUNTERS:
        cursor.execute("""
        INSERT INTO clinical_encounters (record_id, patient_id, encounter_id, specialty, note_text, note_section, ground_truth_codes, ground_truth_modifiers)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (r["record_id"], r["patient_id"], r["encounter_id"], r["specialty"], r["note_text"], r["note_section"], r["ground_truth_codes"], r["ground_truth_modifiers"]))

        cursor.execute("""
        INSERT INTO model_predictions (record_id, model_version, prompt_version, predicted_codes, predicted_modifiers, confidence_scores, token_attributions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (r["record_id"], "clinical-nlp-v1", "baseline_prompt", r["v1_codes"], r["v1_modifiers"], r["v1_conf"], "{}"))

        cursor.execute("""
        INSERT INTO model_predictions (record_id, model_version, prompt_version, predicted_codes, predicted_modifiers, confidence_scores, token_attributions)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (r["record_id"], "clinical-nlp-v2", "candidate_prompt", r["v2_codes"], r["v2_modifiers"], r["v2_conf"], "{}"))

    conn.commit()
    conn.close()
    print(f"Mock database populated successfully at {db_path}!")

if __name__ == "__main__":
    generate_db()
