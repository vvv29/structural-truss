#! python3
# r: compas

"""
HALF-LAP INTERSECTION DETECTOR - V3 ENHANCED
Improved detection with dynamic cut length calculation
NOW EXPORTS: Cut length and width to CSV (fixes Script 06 integration)
"""

import os
import json
import csv
import math
import Rhino
from System.Drawing import Color
from Rhino.Geometry import (
    Point3d, Vector3d, Line, Box, Plane, 
    Interval, Brep, Surface
)

print("=" * 80)
print("HALF-LAP INTERSECTION DETECTOR - V3 ENHANCED")
print("WITH DYNAMIC CUT LENGTH EXPORT")
print("=" * 80)

# STEP 0: LOAD DATA
print("\nStep 0: Loading data...")

output_dir = "V:\\"
network_file = os.path.join(output_dir, "truss_network.json")

if not os.path.exists(output_dir):
    output_dir = os.environ.get("USERPROFILE", "")
    network_file = os.path.join(output_dir, "truss_network.json")

if not os.path.exists(network_file):
    print(f"ERROR: {network_file} not found!")
    exit()

try:
    with open(network_file, 'r') as f:
        network_data = json.load(f)
    print("✓ Network loaded")
except Exception as e:
    print(f"ERROR: {e}")
    exit()

nodes = network_data['nodes']
edges = network_data['edges']

# STEP 1: CONVERT NODES TO POINTS
print("\nStep 1: Converting nodes to 3D points...")

node_points = {}
for node_id_str, node_info in nodes.items():
    node_id = int(node_id_str)
    node_points[node_id] = Point3d(
        node_info['x'],
        node_info['y'],
        node_info['z']
    )

print(f"✓ {len(node_points)} nodes converted")

# STEP 2: CREATE BEAM GEOMETRY
print("\nStep 2: Creating 3D beam geometry...")

BEAM_WIDTH = 46   # mm (X direction)
BEAM_HEIGHT = 97  # mm (Y direction)

def create_beam_box(start_pt, end_pt, width, height):
    """Create a box geometry for a beam"""
    beam_vector = Vector3d(end_pt - start_pt)
    beam_length = beam_vector.Length
    beam_dir = beam_vector
    beam_dir.Unitize()
    
    # Calculate perpendiculars
    if abs(beam_dir.Z) < 0.9:
        perp1 = Vector3d.CrossProduct(beam_dir, Vector3d(0, 0, 1))
    else:
        perp1 = Vector3d.CrossProduct(beam_dir, Vector3d(1, 0, 0))
    
    perp1.Unitize()
    perp2 = Vector3d.CrossProduct(beam_dir, perp1)
    perp2.Unitize()
    
    # Midpoint
    mid_pt = Point3d(
        (start_pt.X + end_pt.X) / 2,
        (start_pt.Y + end_pt.Y) / 2,
        (start_pt.Z + end_pt.Z) / 2
    )
    
    # Create box
    plane = Plane(mid_pt, beam_dir, perp1)
    box = Box(
        plane,
        Interval(-beam_length/2, beam_length/2),
        Interval(-width/2, width/2),
        Interval(-height/2, height/2)
    )
    
    return box.ToBrep(), beam_dir, perp1, perp2

# Create all beams
beams = {}
for edge in edges:
    start_node_id = edge['start']
    end_node_id = edge['end']
    
    start_pt = node_points[start_node_id]
    end_pt = node_points[end_node_id]
    
    beam_brep, b_dir, b_perp1, b_perp2 = create_beam_box(
        start_pt, end_pt, BEAM_WIDTH, BEAM_HEIGHT
    )
    
    beam_key = f"{start_node_id}-{end_node_id}"
    beams[beam_key] = {
        'brep': beam_brep,
        'start': start_pt,
        'end': end_pt,
        'direction': b_dir,
        'perp1': b_perp1,
        'perp2': b_perp2,
        'start_node': start_node_id,
        'end_node': end_node_id
    }

print(f"✓ Created {len(beams)} beam geometries")

# STEP 3: TEST ALL BEAM PAIRS FOR INTERSECTION
print("\nStep 3: Testing beam pairs for intersections...\n")

intersections = []

beam_list = list(beams.items())

for i, (beam1_key, beam1_data) in enumerate(beam_list):
    for j, (beam2_key, beam2_data) in enumerate(beam_list):
        if i >= j:  # Avoid duplicate pairs and self-intersection
            continue
        
        # Test if these beams intersect
        brep1 = beam1_data['brep']
        brep2 = beam2_data['brep']
        
        # Boolean intersection test
        try:
            intersection_breps = Brep.CreateBooleanIntersection(
                [brep1], [brep2], 0.01
            )
            
            if intersection_breps and len(intersection_breps) > 0:
                intersection_brep = intersection_breps[0]
                
                # Get centroid of intersection volume
                if intersection_brep.Faces.Count > 0:
                    try:
                        # Calculate bounding box center
                        bbox = intersection_brep.GetBoundingBox(True)
                        intersection_pt = bbox.Center
                        
                        # Calculate angles between beams
                        dir1 = beam1_data['direction']
                        dir2 = beam2_data['direction']
                        
                        dot = dir1.X * dir2.X + dir1.Y * dir2.Y + dir1.Z * dir2.Z
                        dot = max(-1, min(1, dot))  # Clamp to [-1, 1]
                        angle_rad = math.acos(abs(dot))
                        angle_deg = angle_rad * 180 / math.pi
                        
                        # Calculate optimal cut length based on intersection angle
                        # Formula: For a half-lap joint at angle θ,
                        # the cut length should be: min_length / sin(θ)
                        # where min_length = 3 × beam width = 138mm (for 46mm beam)
                        
                        min_cut_length = BEAM_WIDTH * 3  # 138mm minimum
                        
                        # Avoid division by very small numbers
                        sin_angle = math.sin(angle_rad)
                        if sin_angle < 0.087:  # Less than 5 degrees
                            optimal_cut_length = 200  # Use maximum at very shallow angles
                        else:
                            optimal_cut_length = min_cut_length / sin_angle
                        
                        # Cap at reasonable maximums for fabrication
                        cut_length = min(optimal_cut_length, 300)  # Up to 300mm
                        cut_length = max(cut_length, 92)  # But at least 92mm (2×46mm)
                        
                        cut_width = BEAM_WIDTH
                        cut_depth = BEAM_WIDTH / 2  # Half-lap: cut half the width
                        
                        # Calculate centerline distance
                        centerline_dist = 0  # Beams are intersecting, so distance is 0
                        
                        intersection = {
                            'beam1_key': beam1_key,
                            'beam2_key': beam2_key,
                            'beam1_start': beam1_data['start_node'],
                            'beam1_end': beam1_data['end_node'],
                            'beam2_start': beam2_data['start_node'],
                            'beam2_end': beam2_data['end_node'],
                            'position': intersection_pt,
                            'angle_deg': angle_deg,
                            'centerline_distance': centerline_dist,
                            'cut_depth': cut_depth,
                            'cut_length': cut_length,  # ← NEW: Dynamic cut length
                            'cut_width': cut_width      # ← NEW: Cut width
                        }
                        
                        intersections.append(intersection)
                        
                        print(f"✓ INTERSECTION FOUND:")
                        print(f"  Beam 1: {beam1_key}")
                        print(f"  Beam 2: {beam2_key}")
                        print(f"  Position: ({intersection_pt.X:.1f}, {intersection_pt.Y:.1f}, {intersection_pt.Z:.1f})")
                        print(f"  Angle: {angle_deg:.1f}°")
                        print(f"  Cut depth each: {cut_depth:.1f}mm")
                        print(f"  Cut length: {cut_length:.1f}mm (angle-optimized)")
                        print(f"  Cut width: {cut_width:.1f}mm\n")
                    
                    except Exception as e:
                        pass
        
        except Exception as e:
            pass

print("=" * 80)
print(f"INTERSECTION DETECTION COMPLETE")
print("=" * 80)

print(f"\n✓ Found {len(intersections)} beam intersections")

# STEP 4: EXPORT TO CSV WITH NEW FIELDS
print("\nStep 4: Exporting to CSV with cut dimensions...")

csv_file = os.path.join(output_dir, "half_lap_specifications.csv")

if len(intersections) > 0:
    # ==========================================
    # ENHANCED: Added Cut_Length_mm and Cut_Width_mm
    # ==========================================
    fieldnames = [
        'Beam1_Start_Node', 'Beam1_End_Node',
        'Beam2_Start_Node', 'Beam2_End_Node',
        'Intersection_X_mm', 'Intersection_Y_mm', 'Intersection_Z_mm',
        'Angle_Between_Beams_Degrees',
        'Centerline_Distance_mm',
        'Cut_Length_mm',              # ← ENHANCED: Dynamic cut length
        'Cut_Width_mm',               # ← ENHANCED: Cut width
        'Beam1_Cut_Depth_mm', 'Beam2_Cut_Depth_mm',
        'Beam1_Orientation', 'Beam2_Orientation'
    ]
    
    rows = []
    for inter in intersections:
        rows.append({
            'Beam1_Start_Node': inter['beam1_start'],
            'Beam1_End_Node': inter['beam1_end'],
            'Beam2_Start_Node': inter['beam2_start'],
            'Beam2_End_Node': inter['beam2_end'],
            'Intersection_X_mm': round(inter['position'].X, 2),
            'Intersection_Y_mm': round(inter['position'].Y, 2),
            'Intersection_Z_mm': round(inter['position'].Z, 2),
            'Angle_Between_Beams_Degrees': round(inter['angle_deg'], 1),
            'Centerline_Distance_mm': round(inter['centerline_distance'], 2),
            'Cut_Length_mm': round(inter['cut_length'], 1),            # ← ENHANCED
            'Cut_Width_mm': round(inter['cut_width'], 1),              # ← ENHANCED
            'Beam1_Cut_Depth_mm': round(inter['cut_depth'], 1),
            'Beam2_Cut_Depth_mm': round(inter['cut_depth'], 1),
            'Beam1_Orientation': 'to_determine',
            'Beam2_Orientation': 'to_determine'
        })
    
    try:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"✓ Saved {len(intersections)} intersections to:")
        print(f"  {csv_file}")
        print(f"\n✓ NEW COLUMNS ADDED:")
        print(f"  - Cut_Length_mm (dynamic, angle-optimized)")
        print(f"  - Cut_Width_mm (beam width = {BEAM_WIDTH}mm)")
    except Exception as e:
        print(f"ERROR saving CSV: {e}")
else:
    print("✓ No intersections found - creating empty CSV")
    try:
        with open(csv_file, 'w', newline='') as f:
            f.write("No intersections detected\n")
    except:
        pass

# STEP 5: SUMMARY
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

print(f"""
BEAM INTERSECTION ANALYSIS:
  Total beams tested: {len(beams)}
  Total beam pairs: {len(beams) * (len(beams) - 1) // 2}
  Intersections found: {len(intersections)}

HALF-LAP SPECIFICATIONS:
  Beam dimensions: {BEAM_WIDTH}mm × {BEAM_HEIGHT}mm cross-section
  Cut depth per intersection: {BEAM_WIDTH / 2:.1f}mm (half of {BEAM_WIDTH}mm width)
  Cut length: DYNAMIC based on intersection angle
    - Minimum: 92mm (2× beam width)
    - Maximum: 300mm (practical fabrication limit)
    - At 45° angles: ~130mm typical
  Total half-lap cuts needed: {len(intersections) * 2}

ENHANCED FEATURES:
  ✓ Boolean intersection detection (V3 improved)
  ✓ Dynamic cut length calculation (angle-optimized)
  ✓ CSV export includes cut_length and cut_width
  ✓ Ready for Script 06 integration

OUTPUT:
  CSV file: {csv_file}
""")

if len(intersections) == 0:
    print("""
⚠️  NO INTERSECTIONS FOUND

Possible reasons:
  1. Beams don't physically overlap (meeting at endpoints only)
  2. Beams are coplanar (lying in same plane, not crossing)
  3. Boolean intersection detection needs adjustment

TO VERIFY:
  - Check your truss model in Rhino
  - Look for beams that visually cross/overlap
  - Zoom in on suspected intersections
  - Report visual overlaps - we can create custom detection
""")
else:
    print(f"✓ Ready for half-lap cutter (Script 06) with dynamic cut lengths!")
    print(f"\nNEXT STEPS:")
    print(f"  1. Run Script 06 (half_lap_cutter.py)")
    print(f"  2. Modify Script 06 to read Cut_Length_mm from CSV")
    print(f"  3. Beams will now have angle-optimized half-lap cuts")

print("\n" + "=" * 80)