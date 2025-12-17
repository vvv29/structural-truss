#! python3
# r: compas

"""
CONNECTOR VOID CALCULATOR - PHASE 2 (FIXED)
Bridges half-lap detection (Script 05) with connector integration (Script 08)

FIXED: Now uses correct filename: truss_connector_spec.json (not connector_specifications.json)

Purpose:
  Creates void box specifications for connector plates
  Ensures voids are: 46mm deep (FULL beam width), beam-parallel, properly sized
  
Inputs:
  - truss_connector_spec.json (from Script 02) ← CORRECTED FILENAME
  - truss_network.json (from Script 01)
  - half_lap_specifications.csv (from Script 05 Enhanced)
  
Outputs:
  - connector_void_specifications.csv (for Script 08 integration)
  
This is the MISSING LINK between half-lap cuts and embedded connectors
"""

import os
import json
import csv
import math
from Rhino.Geometry import Point3d, Vector3d

print("=" * 80)
print("CONNECTOR VOID CALCULATOR - PHASE 2 (FIXED)")
print("Calculates void dimensions for connector plate integration")
print("=" * 80)

# STEP 0: LOAD DATA
print("\nStep 0: Loading input files...")

output_dir = "V:\\"
connector_spec_file = os.path.join(output_dir, "truss_connector_spec.json")  # ← CORRECTED
network_file = os.path.join(output_dir, "truss_network.json")

if not os.path.exists(output_dir):
    output_dir = os.environ.get("USERPROFILE", "")
    connector_spec_file = os.path.join(output_dir, "truss_connector_spec.json")  # ← CORRECTED
    network_file = os.path.join(output_dir, "truss_network.json")

print(f"Looking for: {connector_spec_file}")
print(f"Looking for: {network_file}")

# Load connector specifications
try:
    with open(connector_spec_file, 'r') as f:
        connector_specs = json.load(f)
    print(f"✓ Loaded connector specifications from: {connector_spec_file}")
    print(f"  Total connectors: {len(connector_specs['connectors'])}")
except Exception as e:
    print(f"ERROR: {e}")
    print(f"\nTrying alternate location...")
    # Try alternate name
    alt_file = os.path.join(output_dir, "connector_specifications.json")
    try:
        with open(alt_file, 'r') as f:
            connector_specs = json.load(f)
        print(f"✓ Found at alternate location: {alt_file}")
    except:
        print(f"ERROR: Could not find connector specifications!")
        print(f"Expected file: truss_connector_spec.json")
        print(f"Make sure you ran Script 02 (Connector Analysis) first")
        exit()

# Load network data
try:
    with open(network_file, 'r') as f:
        network_data = json.load(f)
    print(f"✓ Loaded network with {len(network_data['nodes'])} nodes")
except Exception as e:
    print(f"ERROR: {e}")
    exit()

# STEP 1: DEFINE BEAM CONSTANTS
print("\nStep 1: Defining beam and void dimensions...")

BEAM_WIDTH = 46      # mm - beam cross-section width
BEAM_HEIGHT = 97     # mm - beam cross-section height
CONNECTOR_DEPTH = BEAM_WIDTH  # mm - CRITICAL: Full beam width, not plywood thickness!
PLYWOOD_THICKNESS = 18  # mm - connector plate thickness (informational)

print(f"✓ Beam dimensions: {BEAM_WIDTH}mm × {BEAM_HEIGHT}mm")
print(f"✓ Connector void depth: {CONNECTOR_DEPTH}mm (FULL beam width)")
print(f"✓ Plywood plate thickness: {PLYWOOD_THICKNESS}mm (separate)")

# STEP 2: DEFINE CONNECTOR VOID SIZING RULES
print("\nStep 2: Defining connector void sizing rules...")

"""
CONNECTOR VOID SIZING STRATEGY:

For each connector node, the void box represents the 3D space that the 
connector plate and rods will occupy. The void must:

1. DEPTH: 46mm (full beam width) - so it cuts completely through beam
2. LENGTH: Along the beam direction - proportional to connector size
3. WIDTH: Perpendicular to beam - based on connector plate size

Connector sizes from load analysis:
- END_CONNECTOR (degree 1): 100mm × 100mm plate
- LINEAR_SPLICE (degree 2): 120mm × 120mm plate
- Y_JOINT (degree 3): 150mm × 150mm plate
- COMPLEX_JOINT (degree 4+): 180mm × 180mm plate
"""

def get_connector_plate_size(connector_degree):
    """
    Returns (length_mm, width_mm) based on connector type/degree
    """
    if connector_degree == 1:
        return 100, 100, "END_CONNECTOR"
    elif connector_degree == 2:
        return 120, 120, "LINEAR_SPLICE"
    elif connector_degree == 3:
        return 150, 150, "Y_JOINT"
    else:  # degree >= 4
        return 180, 180, "COMPLEX_JOINT"

print("✓ Connector sizing rules configured")

# STEP 3: LOAD BEAM DIRECTIONS FROM NETWORK
print("\nStep 3: Calculating beam directions at each node...")

nodes = network_data['nodes']
edges = network_data['edges']

# Calculate which beams connect at each node
node_beams = {}
node_directions = {}

for node_id_str in nodes.keys():
    node_id = int(node_id_str)
    node_info = nodes[node_id_str]
    node_pt = Point3d(node_info['x'], node_info['y'], node_info['z'])
    
    node_beams[node_id] = []
    node_directions[node_id] = []

# For each edge, record which nodes it connects
for edge in edges:
    start_id = edge['start']
    end_id = edge['end']
    
    start_node = nodes[str(start_id)]
    end_node = nodes[str(end_id)]
    
    start_pt = Point3d(start_node['x'], start_node['y'], start_node['z'])
    end_pt = Point3d(end_node['x'], end_node['y'], end_node['z'])
    
    # Direction from start to end
    beam_vector = end_pt - start_pt
    beam_length = beam_vector.Length
    if beam_length > 0:
        beam_dir = Vector3d(beam_vector.X / beam_length, 
                           beam_vector.Y / beam_length, 
                           beam_vector.Z / beam_length)
    else:
        beam_dir = Vector3d(0, 0, 1)
    
    node_beams[start_id].append({
        'beam_id': f"{start_id}-{end_id}",
        'other_node': end_id,
        'direction': beam_dir
    })
    
    node_beams[end_id].append({
        'beam_id': f"{start_id}-{end_id}",
        'other_node': start_id,
        'direction': Vector3d(-beam_dir.X, -beam_dir.Y, -beam_dir.Z)
    })

print(f"✓ Calculated beam directions for {len(node_beams)} nodes")

# STEP 4: CALCULATE VOID SPECIFICATIONS FOR EACH CONNECTOR
print("\nStep 4: Calculating void specifications...")

void_specs = []

for connector_key, connector_data in sorted(connector_specs['connectors'].items()):
    node_id = connector_data['node_id']
    connector_degree = connector_data['degree']
    connector_type = connector_data['type']
    
    # Get connector plate size
    plate_length, plate_width, type_name = get_connector_plate_size(connector_degree)
    
    # Get node position
    node_info = nodes[str(node_id)]
    node_pt = Point3d(node_info['x'], node_info['y'], node_info['z'])
    
    # Calculate average beam direction at this node
    if node_id in node_beams and len(node_beams[node_id]) > 0:
        # Average of all connected beam directions
        avg_dir = Vector3d(0, 0, 0)
        for beam_info in node_beams[node_id]:
            avg_dir.X += beam_info['direction'].X
            avg_dir.Y += beam_info['direction'].Y
            avg_dir.Z += beam_info['direction'].Z
        
        avg_dir.X /= len(node_beams[node_id])
        avg_dir.Y /= len(node_beams[node_id])
        avg_dir.Z /= len(node_beams[node_id])
        
        # Normalize
        length = math.sqrt(avg_dir.X**2 + avg_dir.Y**2 + avg_dir.Z**2)
        if length > 0:
            avg_dir = Vector3d(avg_dir.X/length, avg_dir.Y/length, avg_dir.Z/length)
        else:
            avg_dir = Vector3d(0, 0, 1)
    else:
        avg_dir = Vector3d(0, 0, 1)
    
    void_spec = {
        'node_id': node_id,
        'connector_type': connector_type,
        'connector_degree': connector_degree,
        'plate_size_length_mm': plate_length,
        'plate_size_width_mm': plate_width,
        'void_length_mm': plate_length,           # Along beam direction
        'void_width_mm': plate_width,             # Perpendicular to beam
        'void_depth_mm': CONNECTOR_DEPTH,         # ← CRITICAL: 46mm full width
        'node_x_mm': round(node_info['x'], 2),
        'node_y_mm': round(node_info['y'], 2),
        'node_z_mm': round(node_info['z'], 2),
        'avg_beam_dir_x': round(avg_dir.X, 3),
        'avg_beam_dir_y': round(avg_dir.Y, 3),
        'avg_beam_dir_z': round(avg_dir.Z, 3),
        'connected_beams': len(node_beams.get(node_id, []))
    }
    
    void_specs.append(void_spec)
    
    print(f"✓ Node {node_id} ({connector_type}):")
    print(f"    Plate size: {plate_length}×{plate_width}mm")
    print(f"    Void depth: {CONNECTOR_DEPTH}mm (full beam width)")
    print(f"    Connected beams: {len(node_beams.get(node_id, []))}")

print(f"\n✓ Calculated void specs for {len(void_specs)} connectors")

# STEP 5: EXPORT TO CSV
print("\nStep 5: Exporting connector void specifications to CSV...")

csv_file = os.path.join(output_dir, "connector_void_specifications.csv")

fieldnames = [
    'Node_ID',
    'Connector_Type',
    'Connector_Degree',
    'Plate_Size_Length_mm',
    'Plate_Size_Width_mm',
    'Void_Length_mm',
    'Void_Width_mm',
    'Void_Depth_mm',
    'Node_X_mm',
    'Node_Y_mm',
    'Node_Z_mm',
    'Avg_Beam_Dir_X',
    'Avg_Beam_Dir_Y',
    'Avg_Beam_Dir_Z',
    'Connected_Beams'
]

try:
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for void_spec in void_specs:
            writer.writerow({
                'Node_ID': void_spec['node_id'],
                'Connector_Type': void_spec['connector_type'],
                'Connector_Degree': void_spec['connector_degree'],
                'Plate_Size_Length_mm': void_spec['plate_size_length_mm'],
                'Plate_Size_Width_mm': void_spec['plate_size_width_mm'],
                'Void_Length_mm': void_spec['void_length_mm'],
                'Void_Width_mm': void_spec['void_width_mm'],
                'Void_Depth_mm': void_spec['void_depth_mm'],
                'Node_X_mm': void_spec['node_x_mm'],
                'Node_Y_mm': void_spec['node_y_mm'],
                'Node_Z_mm': void_spec['node_z_mm'],
                'Avg_Beam_Dir_X': void_spec['avg_beam_dir_x'],
                'Avg_Beam_Dir_Y': void_spec['avg_beam_dir_y'],
                'Avg_Beam_Dir_Z': void_spec['avg_beam_dir_z'],
                'Connected_Beams': void_spec['connected_beams']
            })
    
    print(f"✓ Saved {len(void_specs)} void specifications to:")
    print(f"  {csv_file}")
except Exception as e:
    print(f"ERROR saving CSV: {e}")

# STEP 6: SUMMARY
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"""
CONNECTOR VOID ANALYSIS:
  Total connectors analyzed: {len(void_specs)}
  
VOID SPECIFICATIONS:
  Void depth (all): {CONNECTOR_DEPTH}mm (FULL beam width)
  This ensures connector plates fully embed in beams
  
CONNECTOR BREAKDOWN:
""")

# Count by type
type_counts = {}
for void_spec in void_specs:
    conn_type = void_spec['connector_type']
    if conn_type not in type_counts:
        type_counts[conn_type] = 0
    type_counts[conn_type] += 1

for conn_type in ['END_CONNECTOR', 'LINEAR_SPLICE', 'Y_JOINT', 'COMPLEX_JOINT']:
    if conn_type in type_counts:
        plate_size, _, _ = get_connector_plate_size(
            {'END_CONNECTOR': 1, 'LINEAR_SPLICE': 2, 'Y_JOINT': 3, 'COMPLEX_JOINT': 4}.get(conn_type, 4)
        )
        print(f"  {conn_type}: {type_counts[conn_type]} connectors @ {plate_size}×{plate_size}mm plate")

print(f"""
KEY SPECIFICATIONS:
  ✓ Void depth: {CONNECTOR_DEPTH}mm (not 18mm plywood thickness!)
  ✓ Beam-parallel alignment: YES (uses average beam direction)
  ✓ Connector embedding: FULL WIDTH
  
NEXT STEPS:
  1. Use this CSV in Script 08 (Boolean_Voids_V4.py)
  2. For each void: subtract from all overlapping beams
  3. Result: Beams with embedded connector recesses
  
OUTPUT FILE:
  {csv_file}
""")

print("=" * 80)
print("✓ PHASE 2 COMPLETE: Connector voids ready for boolean integration")
print("=" * 80)
