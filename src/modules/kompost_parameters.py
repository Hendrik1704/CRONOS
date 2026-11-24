"""Input parameters of the KoMPoST and KoMPoST-3D versions that CRONOS builds.

Both read an INI file with INIReader (src/Main.cpp, src/EventInput.cpp),
which ignores keys it does not read and uses defaults for missing ones, so a
misspelled key would be ignored without a warning. check_settings uses these
lists to reject such keys, and the modules write every key into its section.

Generated from KoMPoST 5d35aed and KoMPoST-3D d330786 (commented-out reads
excluded; external_codes/GetModulesFromGit.sh). Update them when a pin
changes; tests/test_kompost_parameters.py compares them with the sources.
"""

# Parameter -> INI section, for the parameters KoMPoST reads. INIReader
# compares the names case-insensitively, CRONOS requires the spelling used in
# the source.
KOMPOST_PARAMETERS = {
    "InputFile": "KoMPoSTInputs",
    "OutputFileTag": "KoMPoSTInputs",
    "tIn": "KoMPoSTInputs",
    "tOut": "KoMPoSTInputs",
    "WriteTmunuBackup": "KoMPoSTInputs",
    "ENERGY_PERTURBATIONS": "KoMPoSTParameters",
    "EtaOverS": "KoMPoSTParameters",
    "EtaOverSTemperatureScale": "KoMPoSTParameters",
    "EVOLUTION_MODE": "KoMPoSTParameters",
    "MOMENTUM_PERTURBATIONS": "KoMPoSTParameters",
    "NuEffective": "KoMPoSTParameters",
    "Regulator": "KoMPoSTParameters",
    "afm": "EventInput",
    "normFactor": "EventInput",
    "Ns": "EventInput",
    "xEND": "EventInput",
    "xSTART": "EventInput",
    "yEND": "EventInput",
    "ySTART": "EventInput",
}

# Parameter -> INI section, for the parameters KoMPoST-3D reads
KOMPOST3D_PARAMETERS = {
    "InputFile": "KoMPoSTInputs",
    "OutputFileTag": "KoMPoSTInputs",
    "tIn": "KoMPoSTInputs",
    "tOut": "KoMPoSTInputs",
    "WriteTmunuBackup": "KoMPoSTInputs",
    "ENERGY_PERTURBATIONS": "KoMPoSTParameters",
    "EtaOverS": "KoMPoSTParameters",
    "EtaOverSTemperatureScale": "KoMPoSTParameters",
    "EVOLUTION_MODE": "KoMPoSTParameters",
    "MOMENTUM_PERTURBATIONS": "KoMPoSTParameters",
    "NuEffective": "KoMPoSTParameters",
    "Regulator": "KoMPoSTParameters",
    "afm": "EventInput",
    "deta": "EventInput",
    "etaEND": "EventInput",
    "etaSTART": "EventInput",
    "Neta": "EventInput",
    "normFactor": "EventInput",
    "Ns": "EventInput",
    "xEND": "EventInput",
    "xSTART": "EventInput",
    "yEND": "EventInput",
    "ySTART": "EventInput",
}

# Order of the sections in the parameter file
KOMPOST_SECTIONS = ("KoMPoSTInputs", "KoMPoSTParameters", "EventInput")

# Parameters CRONOS sets itself when it writes the parameter file
KOMPOST_CRONOS_CONTROLLED_PARAMETERS = (
    "InputFile",
    "OutputFileTag",
    "WriteTmunuBackup",
)


def format_kompost_value(value):
    """Format a configuration value for the KoMPoST parameter file.

    INIReader reads integers with strtol, so booleans are written as 0 or 1.
    """
    if isinstance(value, bool):
        return str(int(value))
    return str(value)


def write_kompost_parameters(path, parameters, known_parameters):
    """Write the parameters into their sections of a KoMPoST INI file.

    Raises:
        ValueError: For a parameter KoMPoST does not read (check_settings
            rejects these before a run).
    """
    unknown = sorted(set(parameters) - set(known_parameters))
    if unknown:
        raise ValueError(f"KoMPoST does not read the parameters {unknown}.")
    with open(path, "w") as f:
        for section in KOMPOST_SECTIONS:
            f.write(f"[{section}]\n")
            for key, value in parameters.items():
                if known_parameters[key] == section:
                    f.write(f"{key} = {format_kompost_value(value)}\n")
            f.write("\n")
