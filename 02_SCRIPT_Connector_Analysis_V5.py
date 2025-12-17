#! python3
# r: compas

"""
COMPAS Connector Generator - V5 PRODUCTION
Phase 2: Analyze network → Generate connector specifications (39 rods)
"""

import os
import json

print("=" * 60)
print("COMPAS CONNECTOR GENERATOR - V5")
print("=" * 60)

# STEP 0: Set paths
output_dir = "V:\\"
network_filename = "truss_network.json"
spec_filename = "truss_connector_spec.json"

network_filepath = os.path.join(output_dir, network_filename)
spec_filepath = os.path.join(output_dir, spec_filename)

print("\nInput file: {}".format(network_filepath))
print("Output file: {}".format(spec_filepath))

if not os.path.exists(output_dir):
    print("\nWARNING: {} not found, using fallback...".format(output_dir))
    output_dir = os.environ.get("USERPROFILE", "")
    network_filepath = os.path.join(output_dir, network_filename)
    spec_filepath = os.path.join(output_dir, spec_filename)
    print("New locations: {}".format(output_dir))

# STEP 1: Load network
print("\nStep 1: Loading network data...")

if not os.path.exists(network_filepath):
    print("ERROR: Network file not found!")
    print("Expected: {}".format(network_filepath))
    print("\nMake sure you ran Script 1 first and saved to V:\\")
    exit()

try:
    with open(network_filepath, 'r') as f:
        network_data = json.load(f)
    
    print("OK Loaded network data")
    print("  Nodes: {}".format(network_data['statistics']['total_nodes']))
    print("  Edges: {}".format(network_data['statistics']['total_edges']))
    
except Exception as e:
    print("Error loading network: {}".format(str(e)))
    exit()

# STEP 2: Extract node information
print("\nStep 2: Extracting node connectivity...")

nodes = network_data['nodes']
edges = network_data['edges']

node_degrees = {}
node_neighbors = {}

for node_id_str, node_info in nodes.items():
    node_id = int(node_id_str)
    node_degrees[node_id] = node_info['degree']
    node_neighbors[node_id] = []

for edge in edges:
    node_a = edge['start']
    node_b = edge['end']
    if node_a not in node_neighbors:
        node_neighbors[node_a] = []
    if node_b not in node_neighbors:
        node_neighbors[node_b] = []
    node_neighbors[node_a].append(node_b)
    node_neighbors[node_b].append(node_a)

print("OK Extracted connectivity")

# STEP 3: Analyze connectors
print("\nStep 3: Analyzing connector types...")

connector_types = {}

for node_id_str, node_info in nodes.items():
    node_id = int(node_id_str)
    degree = node_degrees[node_id]
    
    connector_key = "joint_{}".format(node_id)
    
    connector_types[connector_key] = {
        'node_id': node_id,
        'position': [node_info['x'], node_info['y'], node_info['z']],
        'degree': degree,
        'member_count': degree,
        'members': node_neighbors.get(node_id, [])
    }
    
    if degree == 1:
        connector_types[connector_key]['type'] = "END_CONNECTOR"
        connector_types[connector_key]['rod_count'] = 2
        connector_types[connector_key]['description'] = "End plate connector"
        
    elif degree == 2:
        connector_types[connector_key]['type'] = "LINEAR_SPLICE"
        connector_types[connector_key]['rod_count'] = 3
        connector_types[connector_key]['description'] = "Linear splice or knee joint"
        
    elif degree == 3:
        connector_types[connector_key]['type'] = "Y_JOINT"
        connector_types[connector_key]['rod_count'] = 4
        connector_types[connector_key]['description'] = "Y-shaped junction (3 members)"
        
    elif degree >= 4:
        connector_types[connector_key]['type'] = "COMPLEX_JOINT"
        connector_types[connector_key]['rod_count'] = 6
        connector_types[connector_key]['description'] = "{}-way junction".format(degree)

print("OK Analyzed {} connectors".format(len(connector_types)))

# STEP 4: Count connector types
print("\nConnector Summary:")
print("-" * 60)

end_connectors = [c for c in connector_types.values() if c['type'] == "END_CONNECTOR"]
splice_connectors = [c for c in connector_types.values() if c['type'] == "LINEAR_SPLICE"]
y_joints = [c for c in connector_types.values() if c['type'] == "Y_JOINT"]
complex_joints = [c for c in connector_types.values() if c['type'] == "COMPLEX_JOINT"]

print("End connectors: {}".format(len(end_connectors)))
print("Linear/splice connectors: {}".format(len(splice_connectors)))
print("Y-joints (3-way): {}".format(len(y_joints)))
print("Complex joints (4+ way): {}".format(len(complex_joints)))

total_rods = (
    len(end_connectors) * 2 +
    len(splice_connectors) * 3 +
    len(y_joints) * 4 +
    len(complex_joints) * 6
)

print("\nRED Estimated 8mm threaded rods needed: {}".format(total_rods))

# STEP 5: Create specifications
print("\nStep 4: Creating connector specifications...")

connector_spec = {
    'connectors': connector_types,
    'statistics': {
        'total_connectors': len(connector_types),
        'end_connectors': len(end_connectors),
        'splice_connectors': len(splice_connectors),
        'y_joints': len(y_joints),
        'complex_joints': len(complex_joints),
        'total_rods_8mm': total_rods
    },
    'materials': {
        'wood_width_mm': 89,
        'wood_height_mm': 38,
        'plywood_thickness_mm': 18,
        'rod_diameter_mm': 8
    }
}

# STEP 6: Save specifications
print("\nStep 5: Saving specifications...")

try:
    spec_json = json.dumps(connector_spec, indent=2)
    with open(spec_filepath, 'w') as f:
        f.write(spec_json)
    print("OK SUCCESS! Saved to:")
    print("  {}".format(spec_filepath))
except Exception as e:
    print("ERROR: {}".format(str(e)))
    exit()

# STEP 7: Summary
print("\n" + "=" * 60)
print("CONNECTOR SPECIFICATION COMPLETE!")
print("=" * 60)

print("\nConnector Breakdown:")
print("  * End connectors: {} @ 2 rods = {} rods".format(len(end_connectors), len(end_connectors)*2))
print("  * Splice connectors: {} @ 3 rods = {} rods".format(len(splice_connectors), len(splice_connectors)*3))
print("  * Y-junctions: {} @ 4 rods = {} rods".format(len(y_joints), len(y_joints)*4))
print("  * Complex joints: {} @ 6 rods = {} rods".format(len(complex_joints), len(complex_joints)*6))

print("\nRED TOTAL 8MM THREADED RODS NEEDED: {}".format(total_rods))

print("\nTotal Connectors: {}".format(len(connector_types)))

print("\n" + "=" * 60)
print("OK FILE LOCATION:")
print("  {}".format(spec_filepath))
print("=" * 60)

print("\nNEXT STEP: Run Script 3")
print("\n" + "=" * 60)
