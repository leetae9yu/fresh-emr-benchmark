import hashlib
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import Final

from pydantic import TypeAdapter
from sqlglot import exp, parse_one
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, traverse_scope

from src.types import Task


class DatabaseSchema(StrEnum):
    MIMIC_IV = "mimic_iv"
    EICU = "eicu"


@dataclass(frozen=True)
class TableRename:
    original_table: str
    columns: dict[str, str]


def _table(original_table: str, **columns: str) -> TableRename:
    return TableRename(original_table=original_table, columns=columns)


MIMIC_IV_RENAMES: Final = {
    "demographics": _table(
        "patients",
        recordid="row_id",
        patientid="subject_id",
        gender="gender",
        dateofbirth="dob",
        dateofdeath="dod",
    ),
    "hospitaladmissions": _table(
        "admissions",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        admitdatetime="admittime",
        dischargedatetime="dischtime",
        admissiontype="admission_type",
        admitsource="admission_location",
        dischargedestination="discharge_location",
        insurancetype="insurance",
        language="language",
        maritalstatus="marital_status",
        age="age",
    ),
    "diagnosiscodes": _table(
        "d_icd_diagnoses",
        recordid="row_id",
        icdcode="icd_code",
        codeversion="icd_version",
        description="long_title",
    ),
    "procedurecodes": _table(
        "d_icd_procedures",
        recordid="row_id",
        icdcode="icd_code",
        codeversion="icd_version",
        description="long_title",
    ),
    "labtesttypes": _table(
        "d_labitems",
        recordid="row_id",
        itemcode="itemid",
        itemname="label",
    ),
    "clinicalitemtypes": _table(
        "d_items",
        recordid="row_id",
        itemcode="itemid",
        itemname="label",
        abbreviation="abbreviation",
        itemtype="linksto",
    ),
    "admissiondiagnoses": _table(
        "diagnoses_icd",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        icdcode="icd_code",
        codeversion="icd_version",
        recordeddatetime="charttime",
    ),
    "admissionprocedures": _table(
        "procedures_icd",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        icdcode="icd_code",
        codeversion="icd_version",
        recordeddatetime="charttime",
    ),
    "labresults": _table(
        "labevents",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        itemcode="itemid",
        resultdatetime="charttime",
        resultvalue="valuenum",
        resultunit="valueuom",
    ),
    "medicationorders": _table(
        "prescriptions",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        startdatetime="starttime",
        enddatetime="stoptime",
        medicationname="drug",
        dosevalue="dose_val_rx",
        doseunit="dose_unit_rx",
        administrationroute="route",
    ),
    "costrecords": _table(
        "cost",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        eventtype="event_type",
        costid="event_id",
        costdatetime="chargetime",
        costamount="cost",
    ),
    "clinicalevents": _table(
        "chartevents",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        icuadmissionid="stay_id",
        itemcode="itemid",
        recordeddatetime="charttime",
        value="valuenum",
        unit="valueuom",
    ),
    "intakerecords": _table(
        "inputevents",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        icuadmissionid="stay_id",
        startdatetime="starttime",
        itemcode="itemid",
        totalvolume="totalamount",
        volumeunit="totalamountuom",
    ),
    "outputrecords": _table(
        "outputevents",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        icuadmissionid="stay_id",
        recordeddatetime="charttime",
        itemcode="itemid",
        volume="value",
        volumeunit="valueuom",
    ),
    "microbiologyresults": _table(
        "microbiologyevents",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        collecteddatetime="charttime",
        specimentype="spec_type_desc",
        testname="test_name",
        organismname="org_name",
    ),
    "icuepisodes": _table(
        "icustays",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        icuadmissionid="stay_id",
        initialcareunit="first_careunit",
        finalcareunit="last_careunit",
        admitdatetime="intime",
        dischargedatetime="outtime",
    ),
    "patienttransfers": _table(
        "transfers",
        recordid="row_id",
        patientid="subject_id",
        admissionid="hadm_id",
        transferid="transfer_id",
        transfertype="eventtype",
        careunit="careunit",
        transferindatetime="intime",
        transferoutdatetime="outtime",
    ),
}

EICU_RENAMES: Final = {
    "icupatient": _table(
        "patient",
        patient_id="uniquepid",
        hosp_id="patienthealthsystemstayid",
        unit_id="patientunitstayid",
        gender="gender",
        age="age",
        ethnicity="ethnicity",
        hospital_id="hospitalid",
        ward_id="wardid",
        height_admission="admissionheight",
        weight_admission="admissionweight",
        weight_discharge="dischargeweight",
        hospital_admit_time="hospitaladmittime",
        hospital_admission_source="hospitaladmitsource",
        unit_admit_time="unitadmittime",
        unit_discharge_time="unitdischargetime",
        hospital_discharge_time="hospitaldischargetime",
        hospital_discharge_status="hospitaldischargestatus",
    ),
    "condition": _table(
        "diagnosis",
        condition_id="diagnosisid",
        unit_id="patientunitstayid",
        condition_name="diagnosisname",
        condition_time="diagnosistime",
        icd9_code="icd9code",
    ),
    "treatment": _table(
        "treatment",
        treatment_id="treatmentid",
        unit_id="patientunitstayid",
        treatment_name="treatmentname",
        treatment_time="treatmenttime",
    ),
    "lab": _table(
        "lab",
        lab_id="labid",
        unit_id="patientunitstayid",
        lab_name="labname",
        lab_result="labresult",
        lab_result_time="labresulttime",
    ),
    "prescription": _table(
        "medication",
        prescription_id="medicationid",
        unit_id="patientunitstayid",
        drug_name="drugname",
        dosage="dosage",
        administration_route="routeadmin",
        medication_start_time="drugstarttime",
        medication_stop_time="drugstoptime",
    ),
    "cost": _table(
        "cost",
        cost_id="costid",
        hosp_id="patienthealthsystemstayid",
        unit_id="patientunitstayid",
        event_type="eventtype",
        event_id="eventid",
        cost_time="chargetime",
        cost_amount="cost",
    ),
    "allergy_reaction": _table(
        "allergy",
        allergy_id="allergyid",
        unit_id="patientunitstayid",
        drug_name="drugname",
        allergy_name="allergyname",
        allergy_time="allergytime",
    ),
    "fluid_balance": _table(
        "intakeoutput",
        fluid_balance_id="intakeoutputid",
        unit_id="patientunitstayid",
        fluid_path="cellpath",
        fluid_label="celllabel",
        fluid_value_numeric="cellvaluenumeric",
        fluid_balance_time="intakeoutputtime",
    ),
    "microbiology": _table(
        "microlab",
        microbiology_id="microlabid",
        unit_id="patientunitstayid",
        culture_site="culturesite",
        organism="organism",
        culture_taken_time="culturetakentime",
    ),
    "vital_signs": _table(
        "vitalperiodic",
        vital_sign_id="vitalperiodicid",
        unit_id="patientunitstayid",
        temperature="temperature",
        sao2="sao2",
        heart_rate="heartrate",
        respiration_rate="respiration",
        systolic_bp="systemicsystolic",
        diastolic_bp="systemicdiastolic",
        mean_bp="systemicmean",
        vital_time="observationtime",
    ),
    "hospital": _table(
        "hospital",
        hospital_id="hospitalid",
        bed_capacity_category="numbedscategory",
        teaching_status="teachingstatus",
        region="region",
    ),
}

RENAMES: Final = {
    DatabaseSchema.MIMIC_IV: MIMIC_IV_RENAMES,
    DatabaseSchema.EICU: EICU_RENAMES,
}
TASKS_ADAPTER: Final = TypeAdapter(tuple[Task, ...])
ORIGINAL_DATABASE_SHA256: Final = {
    DatabaseSchema.MIMIC_IV: (
        "7b946db855ccaba0a810a297e8c623ed89bb9d8fdc2a7f097dc82101b1ee265d"
    ),
    DatabaseSchema.EICU: (
        "2996caf0f598f18beeb65fd37c5947608c551bdc3093bd1d23df1f23023e5c3d"
    ),
}


def _resolve_source(scope: Scope, alias: str) -> exp.Table | Scope | None:
    current: Scope | None = scope
    while current is not None:
        source = current.sources.get(alias)
        if source is not None:
            return source
        current = current.parent
    return None


def convert_gold_sql(sql: str, database: DatabaseSchema) -> str:
    renames = RENAMES[database]
    schema = {
        table_name: {column_name: "TEXT" for column_name in table.columns}
        for table_name, table in renames.items()
    }
    qualified = qualify(
        parse_one(sql, read="sqlite"),
        dialect="sqlite",
        schema=schema,
        validate_qualify_columns=False,
        quote_identifiers=False,
    )

    table_nodes: dict[int, tuple[exp.Table, TableRename]] = {}
    converted_columns: set[int] = set()
    for scope in traverse_scope(qualified):
        for source in scope.sources.values():
            if not isinstance(source, exp.Table):
                continue
            table_rename = renames.get(source.name)
            if table_rename is None:
                raise ValueError(f"Unknown Star table: {source.name}")
            table_nodes[id(source)] = (source, table_rename)

        for column in scope.columns:
            if id(column) in converted_columns or not column.table:
                continue
            source = _resolve_source(scope, column.table)
            if source is None or not isinstance(source, exp.Table):
                continue
            star_table = source.name
            table_rename = renames[star_table]
            original_column = table_rename.columns.get(column.name)
            if original_column is None:
                raise ValueError(
                    f"Unknown Star column: {star_table}.{column.name}"
                )
            column.set("this", exp.to_identifier(original_column))
            converted_columns.add(id(column))

    for table_node, table_rename in table_nodes.values():
        table_node.set("this", exp.to_identifier(table_rename.original_table))

    return qualified.sql(dialect="sqlite")


@cache
def derive_original_tasks(
    star_evaluation_path: str,
    database: DatabaseSchema,
    db_id: str,
) -> tuple[Task, ...]:
    star_tasks = TASKS_ADAPTER.validate_json(
        Path(star_evaluation_path).read_text()
    )
    return tuple(
        task.model_copy(
            update={
                "db_id": db_id,
                "gold_sql": convert_gold_sql(task.gold_sql, database),
            }
        )
        for task in star_tasks
    )


@cache
def verify_original_database(
    database_path: str,
    database: DatabaseSchema,
) -> None:
    digest = hashlib.sha256()
    with open(database_path, "rb") as database_file:
        for chunk in iter(lambda: database_file.read(1024 * 1024), b""):
            digest.update(chunk)
    actual_hash = digest.hexdigest()
    expected_hash = ORIGINAL_DATABASE_SHA256[database]
    if actual_hash != expected_hash:
        raise ValueError(
            f"Unexpected {database.value} database hash: {actual_hash}"
        )
