#! python3
# r: compas

"""
HALF-LAP CUTTER V2 - FIXED BOOLEAN OPERATIONS
Creates beam geometry with proper half-lap cuts
"""

import os
import json 
import csv
import math
import Rhino
from System.Drawing import Color
from Rhino.Geometry import (
    Box, Plane, Point3d, Vector3d, 
    Interval, Brep, Line, Transform,
    Cylinder, BoundingBox
)

print("=" * 80)
print("HALF-LAP CUTTER V2 - FIXED BOOLEAN OPERATIONS")
print("=" * 80)

# Load data
output_dir = "V:\\"
network_file = os.path.join(output_dir, "truss_network.json")
halflap_file = os.path.join(output_dir, "half_lap_specifications.csv")

if not os.path.exists(output_dir):
    output_dir = os.environ.get("USERPROFILE", "")
    network_file = os.path.join(output_dir, "truss_network.json")
    halflap_file = os.path.join(output_dir, "half_lap_specifications.csv")

print("\nStep 1: Loading data...")

with open(network_file, 'r') as f:
    network_data = json.load(f)

nodes = network_data['nodes']
edges = network_data['edges']

# Load half-lap specs
halflap_specs = []
if os.path.exists(halflap_file):
    with open(halflap_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            halflap_specs.append(row)
    print(f"✓ Loaded {len(halflap_specs)} half-lap intersections")
else:
    print("⚠ No half-lap file found, creating beams without cuts")

# Beam dimensions
BEAM_WIDTH = 46  # mm
BEAM_HEIGHT = 97  # mm
TOLERANCE = 0.001  # For boolean operations

print("\nStep 2: Creating solid beam geometry...")

# Helper functions
def normalize_vector(v):
    length = math.sqrt(v.X**2 + v.Y**2 + v.Z**2)
    if length < 0.001:
        return Vector3d(0, 0, 1)
    return Vector3d(v.X/length, v.Y/length, v.Z/length)

def create_beam_solid(start_pt, end_pt, width=BEAM_WIDTH, height=BEAM_HEIGHT):
    """Create a solid beam Brep between two points"""
    
    # Calculate beam direction
    beam_vector = end_pt - start_pt
    beam_length = beam_vector.Length
    beam_dir = normalize_vector(beam_vector)
    
    # Find perpendicular vectors for beam cross-section
    if abs(beam_dir.Z) < 0.9:
        perp1 = Vector3d.CrossProduct(beam_dir, Vector3d(0, 0, 1))
    else:
        perp1 = Vector3d.CrossProduct(beam_dir, Vector3d(1, 0, 0))
    perp1 = normalize_vector(perp1)
    
    perp2 = Vector3d.CrossProduct(beam_dir, perp1)
    perp2 = normalize_vector(perp2)
    
    # Create beam as box
    beam_plane = Plane(start_pt, beam_dir, perp1)
    
    # Create interval for box
    length_interval = Interval(0, beam_length)
    width_interval = Interval(-width/2, width/2)
    height_interval = Interval(-height/2, height/2)
    
    beam_box = Box(beam_plane, length_interval, width_interval, height_interval)
    
    # Convert to Brep (solid)
    beam_brep = beam_box.ToBrep()
    
    # Make sure it's a solid
    if beam_brep and beam_brep.IsSolid:
        return beam_brep
    else:
        # Fallback: create manually
        return Brep.CreateFromBox(beam_box)

# Create all beams
print("\nStep 3: Building beam solids...")
beam_solids = {}
beam_data = {}

for edge in edges:
    start_id = edge['start']
    end_id = edge['end']
    
    start_node = nodes[str(start_id)]
    end_node = nodes[str(end_id)]
    
    start_pt = Point3d(start_node['x'], start_node['y'], start_node['z'])
    end_pt = Point3d(end_node['x'], end_node['y'], end_node['z'])
    
    beam_key = f"{start_id}-{end_id}"
    
    # Create solid beam
    beam_solid = create_beam_solid(start_pt, end_pt)
    
    if beam_solid:
        beam_solids[beam_key] = beam_solid
        beam_data[beam_key] = {
            'start': start_pt,
            'end': end_pt,
            'vector': normalize_vector(end_pt - start_pt)
        }
        print(f"  Created beam {beam_key}")

print(f"✓ Created {len(beam_solids)} beam solids")

# Step 4: Apply half-lap cuts if we have intersections
if halflap_specs:
    print("\nStep 4: Creating half-lap cuts...")
    
    cuts_applied = 0
    
    for spec in halflap_specs:
        try:
            # Get beam keys
            beam1_key = f"{spec['Beam1_Start_Node']}-{spec['Beam1_End_Node']}"
            beam2_key = f"{spec['Beam2_Start_Node']}-{spec['Beam2_End_Node']}"
            
            # Try both orientations
            if beam1_key not in beam_solids:
                beam1_key = f"{spec['Beam1_End_Node']}-{spec['Beam1_Start_Node']}"
            if beam2_key not in beam_solids:
                beam2_key = f"{spec['Beam2_End_Node']}-{spec['Beam2_Start_Node']}"
            
            if beam1_key in beam_solids and beam2_key in beam_solids:
                # Get intersection point
                inter_pt = Point3d(
                    float(spec['Intersection_X_mm']),
                    float(spec['Intersection_Y_mm']),
                    float(spec['Intersection_Z_mm'])
                )
                
                # Get beam vectors
                beam1_vec = beam_data[beam1_key]['vector']
                beam2_vec = beam_data[beam2_key]['vector']
                
                # Calculate cut normal (perpendicular to both beams)
                cut_normal = Vector3d.CrossProduct(beam1_vec, beam2_vec)
                if cut_normal.Length < 0.001:
                    # Beams are parallel, use default
                    cut_normal = Vector3d(0, 0, 1)
                else:
                    cut_normal = normalize_vector(cut_normal)
                
                # Create cutting boxes
                cut_depth = BEAM_WIDTH / 2  # Half the beam width

                if 'cut_length' in row:
                    cut_size = float(row['cut_length'])
                else:
                # Default: minimum 2× beam width
                    cut_size = max(BEAM_WIDTH * 2, 120)
                cut_size = min(cut_size, 200)
                
                # BEAM 1: Cut from top half
                cut_plane1 = Plane(inter_pt, beam1_vec, cut_normal)
                cut_box1 = Box(
                    cut_plane1,
                    Interval(-cut_size/2, cut_size/2),  # Along beam
                    Interval(0, cut_depth),              # Cut depth (top half)
                    Interval(-cut_size/2, cut_size/2)   # Width
                )
                cut_brep1 = cut_box1.ToBrep()
                
                # Perform boolean difference for beam 1
                result1 = Brep.CreateBooleanDifference(
                    [beam_solids[beam1_key]], 
                    [cut_brep1], 
                    TOLERANCE
                )
                
                if result1 and len(result1) > 0:
                    beam_solids[beam1_key] = result1[0]
                    print(f"  ✓ Cut applied to beam {beam1_key}")
                
                # BEAM 2: Cut from bottom half  
                cut_plane2 = Plane(inter_pt, beam2_vec, cut_normal)
                cut_box2 = Box(
                    cut_plane2,
                    Interval(-cut_size/2, cut_size/2),   # Along beam
                    Interval(-cut_depth, 0),             # Cut depth (bottom half)
                    Interval(-cut_size/2, cut_size/2)    # Width
                )
                cut_brep2 = cut_box2.ToBrep()
                
                # Perform boolean difference for beam 2
                result2 = Brep.CreateBooleanDifference(
                    [beam_solids[beam2_key]], 
                    [cut_brep2], 
                    TOLERANCE
                )
                
                if result2 and len(result2) > 0:
                    beam_solids[beam2_key] = result2[0]
                    print(f"  ✓ Cut applied to beam {beam2_key}")
                
                cuts_applied += 1
                
        except Exception as e:
            print(f"  ⚠ Error processing intersection: {str(e)[:50]}")
    
    print(f"✓ Applied {cuts_applied} half-lap cuts")

# Step 5: Add to Rhino
print("\nStep 5: Adding geometry to Rhino...")

# Create layers
try:
    Rhino.RhinoDoc.ActiveDoc.Layers.Add("COMPAS_Beams_HalfLap", Color.FromArgb(139, 69, 19))
except:
    pass

# Add cut boxes layer for debugging
try:
    Rhino.RhinoDoc.ActiveDoc.Layers.Add("COMPAS_CutBoxes_Debug", Color.FromArgb(255, 0, 0))
except:
    pass

# Add beams to document
beams_added = 0
for beam_key, beam_brep in beam_solids.items():
    if beam_brep and beam_brep.IsValid:
        beam_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(beam_brep)
        if beam_id:
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(beam_id)
            if obj:
                layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_Beams_HalfLap", True)
                obj.Attributes.LayerIndex = layer_idx
                obj.Attributes.ObjectColor = Color.FromArgb(139, 69, 19)  # Brown
                obj.Attributes.Name = f"Beam_{beam_key}_HalfLap"
                Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
                beams_added += 1

# Also add debug cut boxes (optional - comment out if not needed)
if halflap_specs and False:  # Set to True to see cut boxes
    for i, spec in enumerate(halflap_specs):
        inter_pt = Point3d(
            float(spec['Intersection_X_mm']),
            float(spec['Intersection_Y_mm']),
            float(spec['Intersection_Z_mm'])
        )
        
        # Add a small sphere at intersection point
        sphere = Rhino.Geometry.Sphere(inter_pt, 10)
        sphere_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddSphere(sphere)
        if sphere_id:
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(sphere_id)
            layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_CutBoxes_Debug", True)
            obj.Attributes.LayerIndex = layer_idx
            obj.Attributes.ObjectColor = Color.FromArgb(255, 0, 0)
            Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)

Rhino.RhinoDoc.ActiveDoc.Views.Redraw()

print("\n" + "=" * 80)
print("HALF-LAP CUTS COMPLETE!")
print("=" * 80)
print(f"\nResults:")
print(f"  ✓ Beams created: {len(beam_solids)}")
print(f"  ✓ Beams added to Rhino: {beams_added}")
if halflap_specs:
    print(f"  ✓ Half-lap cuts attempted: {len(halflap_specs)}")
    print(f"  ✓ Successful cuts: {cuts_applied}")
print(f"\nLayer: COMPAS_Beams_HalfLap (brown)")
print("\nNote: If cuts are not visible:")
print("  1. Check that half_lap_specifications.csv exists")
print("  2. Verify intersection coordinates are correct")
print("  3. Try adjusting TOLERANCE value (currently {TOLERANCE})")
print("=" * 80)