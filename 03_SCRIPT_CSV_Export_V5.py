#! python3
# r: compas

"""
COMPAS Export to CSV - V5 PRODUCTION
Phase 3: Export → Fabrication-ready CSV files
"""

import os
import json
import csv

print("=" * 70)
print("CONNECTOR DATA EXPORT - V5")
print("=" * 70)

# STEP 0: Set paths
output_dir = "V:\\"
spec_filename = "truss_connector_spec.json"
spec_filepath = os.path.join(output_dir, spec_filename)

print("\nLooking for: {}".format(spec_filepath))

if not os.path.exists(output_dir):
    print("WARNING: {} not found, using fallback...".format(output_dir))
    output_dir = os.environ.get("USERPROFILE", "")
    spec_filepath = os.path.join(output_dir, spec_filename)
    print("Using: {}".format(output_dir))

# STEP 1: Load specifications
print("\nStep 1: Loading connector specifications...")

if not os.path.exists(spec_filepath):
    print("ERROR: Spec file not found!")
    print("Expected: {}".format(spec_filepath))
    print("Run Script 2 first!")
    exit()

try:
    with open(spec_filepath, 'r') as f:
        spec_data = json.load(f)
    print("OK Loaded specifications")
except Exception as e:
    print("Error: {}".format(str(e)))
    exit()

stats = spec_data['statistics']
connectors = spec_data['connectors']

# STEP 2: Display summary
print("\n" + "=" * 70)
print("PROJECT SUMMARY")
print("=" * 70)

print("\nStructure Information:")
print("  Total connectors needed: {}".format(stats['total_connectors']))
print("  End connectors: {}".format(stats['end_connectors']))
print("  Linear/splice connectors: {}".format(stats['splice_connectors']))
print("  Y-way junctions (3 members): {}".format(stats['y_joints']))
print("  Complex junctions (4+ members): {}".format(stats['complex_joints']))

print("\nFastener Requirements:")
print("  RED Total 8mm threaded rods needed: {}".format(stats['total_rods_8mm']))
print("  Estimated nuts required: {}".format(stats['total_rods_8mm'] * 2))
print("  Estimated washers required: {}".format(stats['total_rods_8mm'] * 2))

# STEP 3: Create connector list
print("\nStep 2: Creating connector list...")

connector_list = []
for key, connector_data in connectors.items():
    connector_list.append({
        'Connector_ID': key,
        'Node_ID': connector_data['node_id'],
        'Type': connector_data['type'],
        'Degree': connector_data['degree'],
        'Members': connector_data['member_count'],
        'Rods_Required': connector_data['rod_count'],
        'Position_X': round(connector_data['position'][0], 2),
        'Position_Y': round(connector_data['position'][1], 2),
        'Position_Z': round(connector_data['position'][2], 2)
    })

connector_list.sort(key=lambda x: (x['Type'], x['Connector_ID']))

print("OK Created list of {} connectors".format(len(connector_list)))

# STEP 4: Export to CSV files
print("\nStep 3: Exporting to CSV files...")

csv_file1 = os.path.join(output_dir, "truss_connectors_detail.csv")
print("\nExporting: truss_connectors_detail.csv")

try:
    with open(csv_file1, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=connector_list[0].keys())
        writer.writeheader()
        writer.writerows(connector_list)
    print("OK Created: {}".format(csv_file1))
except Exception as e:
    print("Error: {}".format(str(e)))

csv_file2 = os.path.join(output_dir, "truss_material_summary.csv")
print("Exporting: truss_material_summary.csv")

material_data = [
    {'Item': '8mm Threaded Rods (Varillas Roscada)', 'Quantity': stats['total_rods_8mm'], 'Unit': 'pieces'},
    {'Item': '8mm Hex Nuts', 'Quantity': stats['total_rods_8mm'] * 2, 'Unit': 'pieces'},
    {'Item': 'Washers (Diameter 8mm)', 'Quantity': stats['total_rods_8mm'] * 2, 'Unit': 'pieces'},
    {'Item': 'Connector blocks', 'Quantity': stats['total_connectors'], 'Unit': 'pieces'},
]

try:
    with open(csv_file2, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['Item', 'Quantity', 'Unit'])
        writer.writeheader()
        writer.writerows(material_data)
    print("OK Created: {}".format(csv_file2))
except Exception as e:
    print("Error: {}".format(str(e)))

csv_file3 = os.path.join(output_dir, "truss_connector_types.csv")
print("Exporting: truss_connector_types.csv")

type_summary = [
    {
        'Connector_Type': 'END_CONNECTOR',
        'Count': stats['end_connectors'],
        'Rods_Per_Connector': 2,
        'Total_Rods': stats['end_connectors'] * 2,
        'Description': 'Single member termination'
    },
    {
        'Connector_Type': 'LINEAR_SPLICE',
        'Count': stats['splice_connectors'],
        'Rods_Per_Connector': 3,
        'Total_Rods': stats['splice_connectors'] * 3,
        'Description': 'Two member splice or knee joint'
    },
    {
        'Connector_Type': 'Y_JOINT',
        'Count': stats['y_joints'],
        'Rods_Per_Connector': 4,
        'Total_Rods': stats['y_joints'] * 4,
        'Description': 'Three-way junction'
    },
    {
        'Connector_Type': 'COMPLEX_JOINT',
        'Count': stats['complex_joints'],
        'Rods_Per_Connector': 6,
        'Total_Rods': stats['complex_joints'] * 6,
        'Description': 'Four or more way junction'
    },
]

try:
    with open(csv_file3, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=type_summary[0].keys())
        writer.writeheader()
        writer.writerows(type_summary)
    print("OK Created: {}".format(csv_file3))
except Exception as e:
    print("Error: {}".format(str(e)))

print("\n" + "=" * 70)
print("EXPORT COMPLETE!")
print("=" * 70)

print("\nFiles created in: {}".format(output_dir))

print("\nCSV Files Created:")
print("  OK truss_connectors_detail.csv")
print("  OK truss_material_summary.csv")
print("  OK truss_connector_types.csv")

print("\n" + "=" * 70)
print("QUICK MATERIAL REFERENCE")
print("=" * 70)

print("\nFor procurement/fabrication:")
print("\nPRIMARY FASTENERS (8mm Threaded Rod System)")
print("  RED 8mm x 100-120mm threaded rods: {} units".format(stats['total_rods_8mm']))
print("  RED 8mm hex nuts: {} units".format(stats['total_rods_8mm'] * 2))
print("  RED 8mm washers (Diameter 12/24mm): {} units".format(stats['total_rods_8mm'] * 2))

print("\nCONNECTOR BLOCKS")
print("  * Total blocks needed: {} units".format(stats['total_connectors']))

print("\n" + "=" * 70)
print("OK ALL EXPORTS COMPLETE!")
print("=" * 70)

print("\nNEXT STEP: Run Script 4a (Half-Lap Detector)")
print("\n" + "=" * 70)
