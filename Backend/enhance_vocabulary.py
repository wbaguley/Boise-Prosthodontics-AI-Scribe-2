import requests

# Prosthodontics-specific vocabulary
vocabulary = {
    "procedures": [
        "crown lengthening", "veneer preparation", "implant placement",
        "abutment connection", "bite registration", "final impression",
        "provisional fabrication", "try-in", "final cementation"
    ],
    "materials": [
        "zirconia", "lithium disilicate", "PFM", "e.max", "gold alloy",
        "composite resin", "polyvinylsiloxane", "polyether"
    ],
    "conditions": [
        "bruxism", "TMD", "occlusal trauma", "peri-implantitis",
        "cement failure", "open margin", "food impaction"
    ],
    "measurements": [
        "vertical dimension", "centric relation", "maximum intercuspation",
        "overjet", "overbite", "freeway space"
    ]
}

# Send to backend
for category, terms in vocabulary.items():
    print(f"Adding {category} vocabulary...")
    # This would connect to your backend's vocabulary endpoint