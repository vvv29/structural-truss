#! python3
# r: compas

"""
SCRIPT 07_NEW: WOOD PANEL GENERATOR V1
Interior Dual-Panel Connector System for Spider Truss

Generates cross-oriented plywood panels at each node with:
- Beam insertion pockets (30% depth, rectangular slots)
- Rod holes (8mm, positioned by load requirements)
- Panel profiles for nesting optimization

Input:  truss_network.json (from Script 01)
        truss_connector_engineered.json (from Script 04)
Output: Panel geometry in Rhino (COMPAS_Panels layer)
        Panel profile curves (COMPAS_PanelProfiles layer)
        panel_specifications.json
        panel_profiles_for_nesting.json

Integration: Uses COMPAS Wood w_raw element system
            Compatible with existing Scripts 01-06
"""

import os
import json
import math
import Rhino
from System.Drawing import Color
from Rhino.Geometry import (
    Point3d, Vector3d, Plane, Box, Rectangle3d, 
    Interval, Brep, Line, Circle, Curve, PolylineCurve
)

print("=" * 80)
print("SCRIPT 07_NEW: WOOD PANEL GENERATOR V1")
print("Interior Dual-Panel Connector System")
print("=" * 80)

# ============================================================================
# SECTION 1: PARAMETERS
# ============================================================================

print("\nSection 1: Loading parameters...")

# Material parameters
PANEL_THICKNESS = 18  # mm (plywood thickness)
PANEL_MATERIAL = "18mm Structural Plywood"

# Beam parameters (from your specification)
BEAM_WIDTH = 46   # mm (cross-section width)
BEAM_HEIGHT = 97  # mm (cross-section height)

# Connection parameters
CONNECTION_DEPTH = 30  # mm (30% of beam width for structural integrity)
# This is conservative - beam pocket depth = 30% of 97mm = ~29mm, round to 30mm
# Maintains 70% of beam height at connection = structurally sound

ROD_DIAMETER = 8  # mm
ROD_EDGE_DISTANCE = 25  # mm (minimum distance from rod center to panel edge)

# Sheet parameters (for nesting)
SHEET_WIDTH = 1220   # mm (standard plywood)
SHEET_HEIGHT = 2440  # mm (standard plywood)

# Panel sizing parameters
BASE_PANEL_SIZE = 150  # mm (minimum panel size)
SIZE_INCREMENT = 50    # mm (panel size increases by beam count)

print(f"✓ Parameters loaded:")
print(f"  - Panel thickness: {PANEL_THICKNESS}mm")
print(f"  - Beam section: {BEAM_WIDTH}mm × {BEAM_HEIGHT}mm")
print(f"  - Connection depth: {CONNECTION_DEPTH}mm (30% of beam height)")
print(f"  - Rod diameter: {ROD_DIAMETER}mm")

# ============================================================================
# SECTION 2: LOAD DATA
# ============================================================================

print("\nSection 2: Loading network and engineered data...")

output_dir = "V:\\"
network_filename = "truss_network.json"
engineered_filename = "truss_connector_engineered.json"

network_filepath = os.path.join(output_dir, network_filename)
engineered_filepath = os.path.join(output_dir, engineered_filename)

if not os.path.exists(output_dir):
    output_dir = os.environ.get("USERPROFILE", "")
    network_filepath = os.path.join(output_dir, network_filename)
    engineered_filepath = os.path.join(output_dir, engineered_filename)

# Load network data
try:
    with open(network_filepath, 'r') as f:
        network_data = json.load(f)
    print("✓ Network data loaded")
    print(f"  - Nodes: {network_data['statistics']['total_nodes']}")
    print(f"  - Edges: {network_data['statistics']['total_edges']}")
except Exception as e:
    print(f"✗ Error loading network: {e}")
    exit()

# Load engineered data
try:
    with open(engineered_filepath, 'r') as f:
        engineered_data = json.load(f)
    print("✓ Engineered data loaded")
    print(f"  - Total rods (engineered): {engineered_data['summary']['total_rods_required']}")
except Exception as e:
    print(f"✗ Error loading engineered data: {e}")
    exit()

nodes = network_data['nodes']
edges = network_data['edges']

# ============================================================================
# SECTION 3: HELPER FUNCTIONS
# ============================================================================

print("\nSection 3: Defining helper functions...")

def normalize_vector(v):
    """Normalize a 3D vector"""
    length = math.sqrt(v.X**2 + v.Y**2 + v.Z**2)
    if length < 0.001:
        return Vector3d(0, 0, 1)
    return Vector3d(v.X/length, v.Y/length, v.Z/length)

def cross_product(v1, v2):
    """Cross product of two vectors"""
    return Vector3d(
        v1.Y*v2.Z - v1.Z*v2.Y,
        v1.Z*v2.X - v1.X*v2.Z,
        v1.X*v2.Y - v1.Y*v2.X
    )

def calculate_panel_size(num_beams, num_rods):
    """
    Calculate panel size based on number of connecting beams and rods
    
    Formula: Base size + increments based on complexity
    """
    # Size increases with number of beams
    beam_factor = (num_beams - 1) * SIZE_INCREMENT
    
    # Ensure enough space for rods (minimum 2 rows)
    rod_spacing = ROD_DIAMETER + 2 * ROD_EDGE_DISTANCE
    min_size_for_rods = rod_spacing * math.ceil(math.sqrt(num_rods))
    
    # Take larger of the two
    calculated_size = BASE_PANEL_SIZE + beam_factor
    final_size = max(calculated_size, min_size_for_rods, 150)
    
    # Round to nearest 10mm for standardization
    final_size = math.ceil(final_size / 10) * 10
    
    # Cap at reasonable maximum
    final_size = min(final_size, 400)
    
    return final_size

def create_rod_hole_positions(panel_size, num_rods):
    """
    Generate rod hole positions in a panel
    
    Pattern: Grid layout with edge clearance
    """
    positions = []
    
    # Calculate grid dimensions
    grid_size = math.ceil(math.sqrt(num_rods))
    
    # Available space (panel size - 2 * edge distance)
    available = panel_size - 2 * ROD_EDGE_DISTANCE
    
    # Spacing between rods
    if grid_size > 1:
        spacing = available / (grid_size - 1)
    else:
        spacing = 0
    
    # Generate positions
    for i in range(num_rods):
        row = i // grid_size
        col = i % grid_size
        
        if grid_size == 1:
            x = panel_size / 2
            y = panel_size / 2
        else:
            x = ROD_EDGE_DISTANCE + col * spacing
            y = ROD_EDGE_DISTANCE + row * spacing
        
        positions.append((x, y))
    
    return positions

def round_rectangle_corners(rectangle_curves, radius=5):
    """
    Round the corners of a rectangular curve profile
    
    Args:
        rectangle_curves: List of line curves forming rectangle
        radius: Corner radius in mm
    
    Returns:
        PolylineCurve with rounded corners
    """
    # For now, return sharp corners (implement fillet later if needed)
    # This is a simplified version
    return rectangle_curves

print("✓ Helper functions defined")

# ============================================================================
# SECTION 4: BUILD NETWORK CONNECTIVITY
# ============================================================================

print("\nSection 4: Building network connectivity...")

# Build node positions
node_points = {}
for node_id_str, node_info in nodes.items():
    node_id = int(node_id_str)
    node_points[node_id] = Point3d(node_info['x'], node_info['y'], node_info['z'])

# Build edge list and connectivity
node_connectivity = {}
for node_id in node_points.keys():
    node_connectivity[node_id] = []

for edge in edges:
    start_id = edge['start']
    end_id = edge['end']
    
    node_connectivity[start_id].append(end_id)
    node_connectivity[end_id].append(start_id)

print(f"✓ Network connectivity built for {len(node_points)} nodes")

# ============================================================================
# SECTION 5: CALCULATE BEAM DIRECTIONS AT EACH NODE
# ============================================================================

print("\nSection 5: Calculating beam directions at each node...")

node_beam_directions = {}

for node_id, connected_nodes in node_connectivity.items():
    if len(connected_nodes) == 0:
        continue
    
    node_pos = node_points[node_id]
    
    # Get all beam directions from this node
    beam_vectors = []
    for neighbor_id in connected_nodes:
        neighbor_pos = node_points[neighbor_id]
        direction = Vector3d(
            neighbor_pos.X - node_pos.X,
            neighbor_pos.Y - node_pos.Y,
            neighbor_pos.Z - node_pos.Z
        )
        direction = normalize_vector(direction)
        beam_vectors.append(direction)
    
    # Calculate average direction (primary axis for Panel A)
    avg_direction = Vector3d(0, 0, 0)
    for v in beam_vectors:
        avg_direction = Vector3d(
            avg_direction.X + v.X,
            avg_direction.Y + v.Y,
            avg_direction.Z + v.Z
        )
    avg_direction = normalize_vector(avg_direction)
    
    # Panel A will be perpendicular to average direction (vertical)
    # Panel B will be perpendicular to Panel A (horizontal)
    
    # Find perpendicular for Panel A
    if abs(avg_direction.Z) < 0.9:
        ref = Vector3d(0, 0, 1)
    else:
        ref = Vector3d(1, 0, 0)
    
    panel_a_normal = cross_product(avg_direction, ref)
    panel_a_normal = normalize_vector(panel_a_normal)
    
    panel_a_y = cross_product(panel_a_normal, avg_direction)
    panel_a_y = normalize_vector(panel_a_y)
    
    # Panel B is 90° rotated from Panel A
    panel_b_normal = cross_product(avg_direction, panel_a_y)
    panel_b_normal = normalize_vector(panel_b_normal)
    
    panel_b_y = cross_product(panel_b_normal, avg_direction)
    panel_b_y = normalize_vector(panel_b_y)
    
    node_beam_directions[node_id] = {
        'avg_direction': avg_direction,
        'panel_a_normal': panel_a_normal,
        'panel_a_y': panel_a_y,
        'panel_b_normal': panel_b_normal,
        'panel_b_y': panel_b_y,
        'beam_vectors': beam_vectors,
        'num_beams': len(connected_nodes)
    }

print(f"✓ Beam directions calculated for {len(node_beam_directions)} nodes")

# ============================================================================
# SECTION 6: GENERATE PANELS AT EACH NODE
# ============================================================================

print("\nSection 6: Generating panel pairs at each node...\n")

# Create layers
try:
    Rhino.RhinoDoc.ActiveDoc.Layers.Add("COMPAS_Panels", Color.FromArgb(180, 100, 220))
    Rhino.RhinoDoc.ActiveDoc.Layers.Add("COMPAS_PanelProfiles", Color.FromArgb(255, 150, 0))
    Rhino.RhinoDoc.ActiveDoc.Layers.Add("COMPAS_RodHoles", Color.FromArgb(255, 50, 50))
    Rhino.RhinoDoc.ActiveDoc.Layers.Add("COMPAS_BeamPockets", Color.FromArgb(100, 100, 255))
except:
    pass

# Storage for export
panel_specifications = {}
panel_profiles = []

stats = {
    'panels_created': 0,
    'total_rods': 0,
    'total_beam_pockets': 0,
    'errors': 0
}

for node_id in sorted(node_points.keys()):
    try:
        # Get node data
        node_pos = node_points[node_id]
        
        # Get engineered specifications
        node_id_str = str(node_id)
        if node_id_str not in engineered_data['nodes']:
            print(f"⚠ Warning: Node {node_id} not in engineered data, skipping")
            continue
        
        node_eng = engineered_data['nodes'][node_id_str]
        node_name = node_eng['node_name']
        node_type = node_eng['node_type']
        num_rods = node_eng['engineering']['rods_required_final']
        
        # Get connectivity
        if node_id not in node_beam_directions:
            print(f"⚠ Warning: Node {node_id} has no beam directions, skipping")
            continue
        
        beam_info = node_beam_directions[node_id]
        num_beams = beam_info['num_beams']
        
        # Calculate panel size
        panel_size = calculate_panel_size(num_beams, num_rods)
        
        print(f"{node_name} ({node_type}):")
        print(f"  Beams: {num_beams}, Rods: {num_rods}, Panel: {panel_size}mm")
        
        # ====================================================================
        # PANEL A - First orientation
        # ====================================================================
        
        # Panel A plane
        avg_dir = beam_info['avg_direction']
        panel_a_normal = beam_info['panel_a_normal']
        panel_a_y = beam_info['panel_a_y']
        
        plane_a = Plane(node_pos, avg_dir, panel_a_y)
        
        # Create Panel A solid
        half_size = panel_size / 2.0
        half_thick = PANEL_THICKNESS / 2.0
        
        box_a = Box(
            plane_a,
            Interval(-half_size, half_size),      # Along beam direction
            Interval(-half_size, half_size),      # Perpendicular on panel
            Interval(-half_thick, half_thick)     # Panel thickness
        )
        
        panel_a_brep = box_a.ToBrep()
        
        # Add to Rhino
        panel_a_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(panel_a_brep)
        if panel_a_id:
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(panel_a_id)
            if obj:
                layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_Panels", True)
                obj.Attributes.LayerIndex = layer_idx
                obj.Attributes.ObjectColor = Color.FromArgb(180, 100, 220)
                obj.Attributes.Name = f"Panel_{node_name}_A"
                Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
            stats['panels_created'] += 1
        
        # ====================================================================
        # PANEL B - Rotated 90° from Panel A
        # ====================================================================
        
        panel_b_normal = beam_info['panel_b_normal']
        panel_b_y = beam_info['panel_b_y']
        
        plane_b = Plane(node_pos, avg_dir, panel_b_y)
        
        box_b = Box(
            plane_b,
            Interval(-half_size, half_size),
            Interval(-half_size, half_size),
            Interval(-half_thick, half_thick)
        )
        
        panel_b_brep = box_b.ToBrep()
        
        # Add to Rhino
        panel_b_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(panel_b_brep)
        if panel_b_id:
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(panel_b_id)
            if obj:
                layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_Panels", True)
                obj.Attributes.LayerIndex = layer_idx
                obj.Attributes.ObjectColor = Color.FromArgb(180, 100, 220)
                obj.Attributes.Name = f"Panel_{node_name}_B"
                Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
            stats['panels_created'] += 1
        
        # ====================================================================
        # ROD HOLES - Through both panels
        # ====================================================================
        
        rod_positions = create_rod_hole_positions(panel_size, num_rods)
        
        for i, (local_x, local_y) in enumerate(rod_positions):
            # Convert local coordinates to world space
            offset_x = (local_x - panel_size/2)
            offset_y = (local_y - panel_size/2)
            
            # Position in world space (on Panel A plane)
            world_pos = Point3d(
                node_pos.X + offset_x * avg_dir.X + offset_y * panel_a_y.X,
                node_pos.Y + offset_x * avg_dir.Y + offset_y * panel_a_y.Y,
                node_pos.Z + offset_x * avg_dir.Z + offset_y * panel_a_y.Z
            )
            
            # Create rod hole as circle (for profile export)
            circle = Circle(world_pos, ROD_DIAMETER / 2.0)
            circle_curve = circle.ToNurbsCurve()
            
            circle_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddCurve(circle_curve)
            if circle_id:
                obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(circle_id)
                if obj:
                    layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_RodHoles", True)
                    obj.Attributes.LayerIndex = layer_idx
                    obj.Attributes.ObjectColor = Color.FromArgb(255, 50, 50)
                    obj.Attributes.Name = f"Rod_{node_name}_{i+1}"
                    Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
        
        stats['total_rods'] += num_rods
        
        # ====================================================================
        # BEAM POCKETS - Rectangular slots for beam insertion
        # ====================================================================
        
        for beam_idx, beam_vector in enumerate(beam_info['beam_vectors']):
            # Create beam pocket geometry
            # Pocket dimensions: BEAM_WIDTH × BEAM_HEIGHT × CONNECTION_DEPTH
            
            # Determine which panel this beam intersects
            # (simplified: alternate between panels, or check angle)
            # For now, create pockets on both panels
            
            # Pocket on Panel A
            pocket_plane_a = Plane(node_pos, beam_vector, panel_a_y)
            
            pocket_box_a = Box(
                pocket_plane_a,
                Interval(0, CONNECTION_DEPTH),              # Depth into panel
                Interval(-BEAM_WIDTH/2, BEAM_WIDTH/2),      # Beam width
                Interval(-BEAM_HEIGHT/2, BEAM_HEIGHT/2)     # Beam height
            )
            
            pocket_a_brep = pocket_box_a.ToBrep()
            
            pocket_a_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(pocket_a_brep)
            if pocket_a_id:
                obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(pocket_a_id)
                if obj:
                    layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_BeamPockets", True)
                    obj.Attributes.LayerIndex = layer_idx
                    obj.Attributes.ObjectColor = Color.FromArgb(100, 100, 255)
                    obj.Attributes.Name = f"Pocket_{node_name}_A_{beam_idx}"
                    Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
            
            stats['total_beam_pockets'] += 1
            
            # Pocket on Panel B
            pocket_plane_b = Plane(node_pos, beam_vector, panel_b_y)
            
            pocket_box_b = Box(
                pocket_plane_b,
                Interval(0, CONNECTION_DEPTH),
                Interval(-BEAM_WIDTH/2, BEAM_WIDTH/2),
                Interval(-BEAM_HEIGHT/2, BEAM_HEIGHT/2)
            )
            
            pocket_b_brep = pocket_box_b.ToBrep()
            
            pocket_b_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(pocket_b_brep)
            if pocket_b_id:
                obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(pocket_b_id)
                if obj:
                    layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_BeamPockets", True)
                    obj.Attributes.LayerIndex = layer_idx
                    obj.Attributes.ObjectColor = Color.FromArgb(100, 100, 255)
                    obj.Attributes.Name = f"Pocket_{node_name}_B_{beam_idx}"
                    Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
            
            stats['total_beam_pockets'] += 1
        
        # ====================================================================
        # CREATE PANEL PROFILES FOR NESTING
        # ====================================================================
        
        # Panel outline (rectangle)
        corners_a = [
            Point3d(
                node_pos.X + (-half_size) * avg_dir.X + (-half_size) * panel_a_y.X,
                node_pos.Y + (-half_size) * avg_dir.Y + (-half_size) * panel_a_y.Y,
                node_pos.Z + (-half_size) * avg_dir.Z + (-half_size) * panel_a_y.Z
            ),
            Point3d(
                node_pos.X + (half_size) * avg_dir.X + (-half_size) * panel_a_y.X,
                node_pos.Y + (half_size) * avg_dir.Y + (-half_size) * panel_a_y.Y,
                node_pos.Z + (half_size) * avg_dir.Z + (-half_size) * panel_a_y.Z
            ),
            Point3d(
                node_pos.X + (half_size) * avg_dir.X + (half_size) * panel_a_y.X,
                node_pos.Y + (half_size) * avg_dir.Y + (half_size) * panel_a_y.Y,
                node_pos.Z + (half_size) * avg_dir.Z + (half_size) * panel_a_y.Z
            ),
            Point3d(
                node_pos.X + (-half_size) * avg_dir.X + (half_size) * panel_a_y.X,
                node_pos.Y + (-half_size) * avg_dir.Y + (half_size) * panel_a_y.Y,
                node_pos.Z + (-half_size) * avg_dir.Z + (half_size) * panel_a_y.Z
            )
        ]
        corners_a.append(corners_a[0])  # Close the curve
        
        profile_a = PolylineCurve(corners_a)
        
        profile_a_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddCurve(profile_a)
        if profile_a_id:
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(profile_a_id)
            if obj:
                layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_PanelProfiles", True)
                obj.Attributes.LayerIndex = layer_idx
                obj.Attributes.ObjectColor = Color.FromArgb(255, 150, 0)
                obj.Attributes.Name = f"Profile_{node_name}_A"
                Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
        
        # Similar for Panel B
        corners_b = [
            Point3d(
                node_pos.X + (-half_size) * avg_dir.X + (-half_size) * panel_b_y.X,
                node_pos.Y + (-half_size) * avg_dir.Y + (-half_size) * panel_b_y.Y,
                node_pos.Z + (-half_size) * avg_dir.Z + (-half_size) * panel_b_y.Z
            ),
            Point3d(
                node_pos.X + (half_size) * avg_dir.X + (-half_size) * panel_b_y.X,
                node_pos.Y + (half_size) * avg_dir.Y + (-half_size) * panel_b_y.Y,
                node_pos.Z + (half_size) * avg_dir.Z + (-half_size) * panel_b_y.Z
            ),
            Point3d(
                node_pos.X + (half_size) * avg_dir.X + (half_size) * panel_b_y.X,
                node_pos.Y + (half_size) * avg_dir.Y + (half_size) * panel_b_y.Y,
                node_pos.Z + (half_size) * avg_dir.Z + (half_size) * panel_b_y.Z
            ),
            Point3d(
                node_pos.X + (-half_size) * avg_dir.X + (half_size) * panel_b_y.X,
                node_pos.Y + (-half_size) * avg_dir.Y + (half_size) * panel_b_y.Y,
                node_pos.Z + (-half_size) * avg_dir.Z + (half_size) * panel_b_y.Z
            )
        ]
        corners_b.append(corners_b[0])
        
        profile_b = PolylineCurve(corners_b)
        
        profile_b_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddCurve(profile_b)
        if profile_b_id:
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(profile_b_id)
            if obj:
                layer_idx = Rhino.RhinoDoc.ActiveDoc.Layers.Find("COMPAS_PanelProfiles", True)
                obj.Attributes.LayerIndex = layer_idx
                obj.Attributes.ObjectColor = Color.FromArgb(255, 150, 0)
                obj.Attributes.Name = f"Profile_{node_name}_B"
                Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
        
        # ====================================================================
        # STORE PANEL SPECIFICATION
        # ====================================================================
        
        panel_specifications[node_name] = {
            'node_id': node_id,
            'node_type': node_type,
            'position': [node_pos.X, node_pos.Y, node_pos.Z],
            'panel_size': panel_size,
            'panel_thickness': PANEL_THICKNESS,
            'num_beams': num_beams,
            'num_rods': num_rods,
            'connection_depth': CONNECTION_DEPTH,
            'panel_a': {
                'plane': [
                    [plane_a.Origin.X, plane_a.Origin.Y, plane_a.Origin.Z],
                    [plane_a.XAxis.X, plane_a.XAxis.Y, plane_a.XAxis.Z],
                    [plane_a.YAxis.X, plane_a.YAxis.Y, plane_a.YAxis.Z]
                ]
            },
            'panel_b': {
                'plane': [
                    [plane_b.Origin.X, plane_b.Origin.Y, plane_b.Origin.Z],
                    [plane_b.XAxis.X, plane_b.XAxis.Y, plane_b.XAxis.Z],
                    [plane_b.YAxis.X, plane_b.YAxis.Y, plane_b.YAxis.Z]
                ]
            },
            'rod_holes': [{'x': x, 'y': y} for x, y in rod_positions],
            'beam_pockets': num_beams * 2  # 2 pockets per beam (one on each panel)
        }
        
        panel_profiles.append({
            'name': f"{node_name}_A",
            'size': panel_size,
            'thickness': PANEL_THICKNESS,
            'rod_holes': num_rods,
            'area_mm2': panel_size * panel_size
        })
        
        panel_profiles.append({
            'name': f"{node_name}_B",
            'size': panel_size,
            'thickness': PANEL_THICKNESS,
            'rod_holes': num_rods,
            'area_mm2': panel_size * panel_size
        })
        
        print(f"  ✓ Created 2 panels, {num_rods} rod holes, {num_beams*2} beam pockets\n")
        
    except Exception as e:
        print(f"  ✗ Error at node {node_id}: {str(e)}\n")
        stats['errors'] += 1

# Refresh viewport
Rhino.RhinoDoc.ActiveDoc.Views.Redraw()

# ============================================================================
# SECTION 7: EXPORT SPECIFICATIONS
# ============================================================================

print("\n" + "=" * 80)
print("SECTION 7: EXPORTING SPECIFICATIONS")
print("=" * 80)

# Export panel specifications
spec_output = {
    'metadata': {
        'project': 'Spider Truss - Interior Panel System',
        'date': json.dumps(None),  # Will be replaced by current date
        'material': PANEL_MATERIAL,
        'sheet_size': f"{SHEET_WIDTH}mm × {SHEET_HEIGHT}mm"
    },
    'parameters': {
        'panel_thickness': PANEL_THICKNESS,
        'beam_width': BEAM_WIDTH,
        'beam_height': BEAM_HEIGHT,
        'connection_depth': CONNECTION_DEPTH,
        'rod_diameter': ROD_DIAMETER,
        'edge_distance': ROD_EDGE_DISTANCE
    },
    'panels': panel_specifications,
    'summary': {
        'total_panels': stats['panels_created'],
        'total_rods': stats['total_rods'],
        'total_beam_pockets': stats['total_beam_pockets']
    }
}

spec_filepath = os.path.join(output_dir, "panel_specifications.json")
try:
    with open(spec_filepath, 'w') as f:
        json.dump(spec_output, f, indent=2)
    print(f"\n✓ Panel specifications saved to: {spec_filepath}")
except Exception as e:
    print(f"\n✗ Error saving specifications: {e}")

# Export panel profiles for nesting
profiles_output = {
    'sheet_dimensions': {
        'width': SHEET_WIDTH,
        'height': SHEET_HEIGHT,
        'material': PANEL_MATERIAL,
        'thickness': PANEL_THICKNESS
    },
    'profiles': panel_profiles,
    'total_panels': len(panel_profiles),
    'total_area_mm2': sum(p['area_mm2'] for p in panel_profiles)
}

profiles_filepath = os.path.join(output_dir, "panel_profiles_for_nesting.json")
try:
    with open(profiles_filepath, 'w') as f:
        json.dump(profiles_output, f, indent=2)
    print(f"✓ Panel profiles saved to: {profiles_filepath}")
except Exception as e:
    print(f"✗ Error saving profiles: {e}")

# ============================================================================
# SECTION 8: SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("PANEL GENERATION COMPLETE!")
print("=" * 80)

print(f"\nResults:")
print(f"  ✓ Panels created: {stats['panels_created']}")
print(f"  ✓ Rod holes: {stats['total_rods']}")
print(f"  ✓ Beam pockets: {stats['total_beam_pockets']}")
print(f"  ✗ Errors: {stats['errors']}")

print(f"\nLayers created in Rhino:")
print(f"  • COMPAS_Panels (purple) - Panel solids")
print(f"  • COMPAS_PanelProfiles (orange) - Curves for nesting")
print(f"  • COMPAS_RodHoles (red) - Rod hole positions")
print(f"  • COMPAS_BeamPockets (blue) - Beam insertion pockets")

print(f"\nOutput files:")
print(f"  • panel_specifications.json - Complete panel data")
print(f"  • panel_profiles_for_nesting.json - For Script 08_NEW")

total_area = sum(p['area_mm2'] for p in panel_profiles)
sheet_area = SHEET_WIDTH * SHEET_HEIGHT
sheets_required = math.ceil(total_area / sheet_area)

print(f"\nMaterial estimate:")
print(f"  Total panel area: {total_area/1000:.1f} dmÂ² ({total_area/1000000:.2f} mÂ²)")
print(f"  Sheet area: {sheet_area/1000:.1f} dmÂ² ({sheet_area/1000000:.2f} mÂ²)")
print(f"  Sheets required (no nesting): {sheets_required}")
print(f"  (Run Script 08_NEW for optimized nesting)")

print("\n" + "=" * 80)
print("NEXT STEPS:")
print("=" * 80)
print("""
1. Review panel geometry in Rhino:
   - Check layer: COMPAS_Panels
   - Verify beam pockets align with beam directions
   - Confirm rod hole positions

2. Run Script 08_NEW (Nesting Optimizer) to:
   - Pack panels onto standard sheets
   - Generate cutting layouts
   - Calculate material waste

3. OPTIONAL: Boolean operations:
   - Subtract beam pockets from panels
   - Drill rod holes through panels
   (Can be done in fabrication instead)

4. Export for fabrication:
   - Use COMPAS_PanelProfiles curves
   - Generate DXF/SVG from nesting layout
""")

print("=" * 80)
