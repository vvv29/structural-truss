#! python3
# r: compas

"""
COMPAS Wood Truss Network Extractor - V5 PRODUCTION
Works in Rhino 8 Script Editor (CPython)
Phase 1: Extract axis lines → Network topology (13 nodes, 12 edges)
"""

import compas
from compas.datastructures import Network
import Rhino
import rhinoscriptsyntax as rs
import os
import json
from Rhino.Geometry import Point3d

print("=" * 60)
print("COMPAS WOOD TRUSS NETWORK EXTRACTOR - V5")
print("=" * 60)

# STEP 1: Get user selection
print("\nStep 1: Selecting geometry from Rhino...")
print("Please select all your truss axis lines in Rhino...")

selected_ids = rs.GetObjects("Select truss axis lines", 4)

if not selected_ids:
    print("No objects selected. Exiting.")
    exit()

print("Selected {} lines".format(len(selected_ids)))

# STEP 2: Extract line geometry
print("\nStep 2: Converting Rhino curves to coordinates...")

lines_data = []
for obj_id in selected_ids:
    start = rs.CurveStartPoint(obj_id)
    end = rs.CurveEndPoint(obj_id)
    
    lines_data.append({
        'start': (start[0], start[1], start[2]),
        'end': (end[0], end[1], end[2]),
        'id': obj_id
    })

print("Converted {} lines".format(len(lines_data)))

# STEP 3: Build Network from lines
print("\nStep 3: Building COMPAS Network...")

network = Network()
tolerance = 0.1

vertex_map = {}

def get_or_create_vertex(point_tuple, tolerance=0.1):
    """Create vertex, or return existing if point is close enough"""
    x, y, z = point_tuple
    
    for existing_key, existing_coords in vertex_map.items():
        ex, ey, ez = existing_coords
        distance = ((x - ex)**2 + (y - ey)**2 + (z - ez)**2) ** 0.5
        if distance < tolerance:
            return existing_key
    
    v_key = network.add_node(x=x, y=y, z=z)
    vertex_map[v_key] = (x, y, z)
    return v_key

print("Adding edges...")
for i, line in enumerate(lines_data):
    v_start = get_or_create_vertex(line['start'], tolerance)
    v_end = get_or_create_vertex(line['end'], tolerance)
    
    if v_start != v_end:
        network.add_edge(v_start, v_end)
        print("  Edge {}: Node {} -> Node {}".format(i+1, v_start, v_end))

print("\nOK Network: {} nodes, {} edges".format(network.number_of_nodes(), network.number_of_edges()))

# STEP 4: Analyze joints
print("\nStep 4: Analyzing joints...")

joint_summary = {'end': 0, 'two_way': 0, 'multi_way': 0}

for node in network.nodes():
    neighbors = list(network.neighbors(node))
    degree = len(neighbors)
    
    if degree == 1:
        joint_summary['end'] += 1
        print("  Node {}: END POINT (1 member)".format(node))
    elif degree == 2:
        joint_summary['two_way'] += 1
        print("  Node {}: 2-WAY (2 members)".format(node))
    else:
        joint_summary['multi_way'] += 1
        print("  Node {}: {}-WAY ({} members)".format(node, degree, degree))

# STEP 5: Save network to JSON
print("\nStep 5: Saving network data...")

network_data = {
    'nodes': {},
    'edges': [],
    'statistics': {
        'total_nodes': network.number_of_nodes(),
        'total_edges': network.number_of_edges()
    }
}

for node in network.nodes():
    coords = network.node_coordinates(node)
    neighbors = list(network.neighbors(node))
    network_data['nodes'][str(node)] = {
        'x': coords[0],
        'y': coords[1],
        'z': coords[2],
        'degree': len(neighbors)
    }

# Add text labels to nodes in Rhino
for node in network.nodes():
    coords = network.node_coordinates(node)
    pt = Point3d(coords[0], coords[1], coords[2])
    Rhino.RhinoDoc.ActiveDoc.Objects.AddTextDot(f"N{node}", pt)

for edge in network.edges():
    network_data['edges'].append({
        'start': edge[0],
        'end': edge[1]
    })

network_json_str = json.dumps(network_data, indent=2)

output_dir = "V:\compas"
output_filename = "truss_network.json"
filepath = os.path.join(output_dir, output_filename)

print("Attempting to save to: {}".format(filepath))

if not os.path.exists(output_dir):
    print("\nWARNING: {} does not exist!".format(output_dir))
    alternative_paths = [
        os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", output_filename),
        os.path.join(os.environ.get("USERPROFILE", ""), "Documents", output_filename),
        os.path.join(os.environ.get("USERPROFILE", ""), output_filename),
        output_filename
    ]
    
    filepath = None
    for alt_path in alternative_paths:
        try:
            with open(alt_path, 'w') as f:
                f.write(network_json_str)
            filepath = alt_path
            print("OK Successfully saved to: {}".format(filepath))
            break
        except Exception as e:
            print("  Trying: {} ... Failed".format(alt_path))
    
    if filepath is None:
        print("ERROR: Could not save file!")
        exit()
else:
    try:
        with open(filepath, 'w') as f:
            f.write(network_json_str)
        print("OK Successfully saved to: {}".format(filepath))
    except Exception as e:
        print("Error: {}".format(str(e)))
        fallback_path = os.path.join(os.environ.get("USERPROFILE", ""), output_filename)
        try:
            with open(fallback_path, 'w') as f:
                f.write(network_json_str)
            filepath = fallback_path
            print("OK Saved to fallback: {}".format(filepath))
        except Exception as e2:
            print("FAILED: {}".format(str(e2)))
            exit()

# STEP 6: Summary
print("\n" + "=" * 60)
print("NETWORK ANALYSIS COMPLETE!")
print("=" * 60)

print("\nJoint Summary:")
print("  * End points: {}".format(joint_summary['end']))
print("  * 2-way connections: {}".format(joint_summary['two_way']))
print("  * Multi-way junctions: {}".format(joint_summary['multi_way']))
print("  * TOTAL JOINTS: {}".format(network.number_of_nodes()))
print("  * TOTAL MEMBERS: {}".format(network.number_of_edges()))

print("\n" + "=" * 60)
print("OK FILE LOCATION:")
print("  {}".format(filepath))
print("=" * 60)

print("\nNEXT STEP: Run Script 2")
print("\n" + "=" * 60)
