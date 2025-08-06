import importlib
from enum import Enum
from typing import Mapping, Any
from bdikit.standards.base import BaseStandard


class Standards(Enum):
    GDC = ("gdc", "bdikit.standards.gdc.GDC")
    SYNAPSE = ("synapse", "bdikit.standards.synapse.Synapse")
    CDS = ("cds", "bdikit.standards.cds.CDS")
    GC = ("gc", "bdikit.standards.gc.GC")
    SAGE_RNASEQ = ("sage_rnaseq", "bdikit.standards.sage_rna_seq_template.SageRNASeqTemplate")
    SAGE_IMAGINGASSAY = ("sage_imagingassay", "bdikit.standards.sage_imaging_assay_template.ImagingAssayTemplate")
    SAGE_CLINICALASSAY = ("sage_clinicalassay", "bdikit.standards.sage_clinical_assay_template.ClinicalAssayTemplate")
    SAGE_CHIPSEQ = ("sage_chipseq", "bdikit.standards.sage_chip_seq_template.ChIPSeqTemplate")
    CCDI = ("ccdi", "bdikit.standards.ccdi.CCDI")

    def __init__(self, standard_name: str, standard_path: str):
        self.standard_name = standard_name
        self.standard_path = standard_path

    @staticmethod
    def get_standard(
        standard_name: str, **standard_kwargs: Mapping[str, Any]
    ) -> BaseStandard:
        if standard_name not in standards:
            names = ", ".join(list(standards.keys()))
            raise ValueError(
                f"The {standard_name} standard is not supported. "
                f"Supported standards are: {names}"
            )
        # Load the class dynamically
        module_path, class_name = standards[standard_name].rsplit(".", 1)
        module = importlib.import_module(module_path)

        return getattr(module, class_name)(**standard_kwargs)


standards = {standard.standard_name: standard.standard_path for standard in Standards}
