#! python3
# r: compas

"""
COMPAS 3D GEOMETRY - V15 ENGINEERED + BEAM ALIGNED
Combines:
- Engineered data (load-based rod counts from Script 06)
- Beam-parallel plates (exact approach from V9 SIMPLE FIX)
- Spheres for rod visualization
"""

import os
import json
import math
import Rhino
from System.Drawing import Color
from Rhino.Geometry import Box, Plane, Point3d, Vector3d, Sphere, Interval, Brep

print("=" * 80)
print("COMPAS 3D GEOMETRY - V15 ENGINEERED + BEAM ALIGNED")
print("Load-Based Connectors with Beam-Parallel Plates")
print("=" * 80)

# ============================================================================
# STEP 1: LOAD DATA
# ============================================================================

print("\nStep 1: Loading data...")

output_dir = "V:\\"
engineered_file = "truss_connector_engineered.json"
network_file = "truss_network.json"

engineered_path = os.path.join(output_dir, engineered_file)
network_path = os.path.join(output_dir, network_file)

if not os.path.exists(output_dir):
    output_dir = os.environ.get("USERPROFILE", "")
    engineered_path = os.path.join(output_dir, engineered_file)
    network_path = os.path.join(output_dir, network_file)

# Load engineered data
try:
    with open(engineered_path, 'r') as f:
        engineered_data = json.load(f)
    print("✓ Engineered data loaded")
    print(f"  Total rods (engineered): {engineered_data['summary']['total_rods_required']}")
except:
    print("✗ Engineered data not found - run Script 06 first")
    exit()

# Load network
try:
    with open(network_path, 'r') as f:
        network_data = json.load(f)
    print("✓ Network data loaded")
except:
    print("✗ Network data not found")
    exit()

nodes = network_data['nodes']
edges = network_data['edges']

# ============================================================================
# STEP 2: EXTRACT ENGINEERED SPECS
# ============================================================================

print("\nStep 2: Processing engineered connector specifications...")

connectors = {}

for node_id_str, node_data in engineered_data['nodes'].items():
    node_id = int(node_id_str)
    
    if str(node_id) not in nodes:
        continue
    
    position = [
        nodes[str(node_id)]['x'],
        nodes[str(node_id)]['y'],
        nodes[str(node_id)]['z']
    ]
    
    connectors[node_id] = {
        'node_id': node_id,
        'name': node_data['node_name'],
        'type': node_data['node_type'],
        'position': position,
        'rods_required': node_data['engineering']['rods_required_final'],
        'block_size': node_data['block_sizing']['recommended_size_mm'],
    }

print(f"✓ Processed {len(connectors)} connectors")

# ============================================================================
# STEP 3: DEFINE DIMENSIONS AND PATTERNS
# ============================================================================

print("\nStep 3: Defining geometry parameters...")

PLYWOOD_THICK = 18  # mm
ROD_DIAMETER = 8    # mm
BEAM_WIDTH = 46  # mm
BEAM_HEIGHT = 97

def get_rod_positions(num_rods, block_size):
    """Rod hole positions based on NUMBER of rods (engineered)"""
    center = block_size / 2
    
    if num_rods == 1:
        return [(center, center)]
    elif num_rods == 2:
        return [(center - 25, center), (center + 25, center)]
    elif num_rods == 3:
        return [(center - 40, center), (center, center), (center + 40, center)]
    elif num_rods == 4:
        return [
            (center, center - 35),
            (center - 35, center + 20),
            (center + 35, center + 20),
            (center, center + 45),
        ]
    else:
        radius = 40
        positions = []
        for i in range(num_rods):
            angle = (i * 360 / num_rods) * math.pi / 180
            x = center + radius * math.cos(angle)
            y = center + radius * math.sin(angle)
            positions.append((x, y))
        return positions

print("✓ Geometry parameters configured")

# ============================================================================
# STEP 4: CALCULATE BEAM DIRECTIONS (FROM V9 SIMPLE FIX)
# ============================================================================

print("\nStep 4: Calculating beam directions for plate orientation...")

def normalize_vector(v):
    l = math.sqrt(v.X**2 + v.Y**2 + v.Z**2)
    if l < 0.001:
        return Vector3d(0, 0, 1)
    return Vector3d(v.X/l, v.Y/l, v.Z/l)

def cross_product(v1, v2):
    return Vector3d(
        v1.Y*v2.Z - v1.Z*v2.Y,
        v1.Z*v2.X - v1.X*v2.Z,
        v1.X*v2.Y - v1.Y*v2.X
    )

# Build node positions
node_points = {}
for node_id_str, node_info in nodes.items():
    node_id = int(node_id_str)
    node_points[node_id] = Point3d(node_info['x'], node_info['y'], node_info['z'])

# Build edge list
edge_list = []
for edge in edges:
    edge_list.append((edge['start'], edge['end']))

# Calculate beam directions for each node
node_beam_dirs = {}

for node_id in node_points.keys():
    # Find connected beams
    connected = []
    for e_start, e_end in edge_list:
        if e_start == node_id:
            connected.append(e_end)
        elif e_end == node_id:
            connected.append(e_start)
    
    # Get beam directions
    beam_dirs = []
    for c_id in connected:
        start_pt = node_points[node_id]
        end_pt = node_points[c_id]
        direction = Vector3d(
            end_pt.X - start_pt.X,
            end_pt.Y - start_pt.Y,
            end_pt.Z - start_pt.Z
        )
        direction = normalize_vector(direction)
        beam_dirs.append(direction)
    
    # Average direction = what the plate should be parallel to
    if beam_dirs:
        avg_dir = Vector3d(0, 0, 0)
        for d in beam_dirs:
            avg_dir = Vector3d(avg_dir.X + d.X, avg_dir.Y + d.Y, avg_dir.Z + d.Z)
        avg_dir = normalize_vector(avg_dir)
    else:
        avg_dir = Vector3d(0, 0, 1)
    
    # Plate is PARALLEL to this direction
    # So plate normal is perpendicular to beam direction
    if abs(avg_dir.Z) < 0.9:
        ref = Vector3d(0, 0, 1)
    else:
        ref = Vector3d(1, 0, 0)
    
    # plate_normal: perpendicular to avg_dir
    plate_normal = cross_product(avg_dir, ref)
    plate_normal = normalize_vector(plate_normal)
    
    # plate_y: also perpendicular to avg_dir
    plate_y = cross_product(plate_normal, avg_dir)
    plate_y = normalize_vector(plate_y)
    
    node_beam_dirs[node_id] = {
        'avg_dir': avg_dir,
        'plate_normal': plate_normal,
        'plate_y': plate_y
    }

print(f"✓ Beam directions calculated for all nodes")

# ============================================================================
# STEP 5: CREATE LAYER
# ============================================================================

layer_name = "COMPAS_Connectors_V15"
try:
    Rhino.RhinoDoc.ActiveDoc.Layers.Add(layer_name, Color.FromArgb(100, 180, 255))
except:
    pass

# ============================================================================
# STEP 6: GENERATE CONNECTOR GEOMETRY
# ============================================================================

print("\nStep 5: Creating beam-aligned connector blocks...\n")

total_blocks = 0
total_rods = 0

for node_id, connector_data in sorted(connectors.items()):
    position = connector_data['position']
    node_name = connector_data['name']
    node_type = connector_data['type']
    rods_required = connector_data['rods_required']
    block_size = connector_data['block_size']
    
    print(f"{node_name}: {node_type}")
    print(f"  Position: ({position[0]:.0f}, {position[1]:.0f}, {position[2]:.0f})")
    print(f"  Block: {block_size}mm, Rods: {rods_required}")
    
    try:
        base_x = position[0]
        base_y = position[1]
        base_z = position[2]
        
        # Get plate orientation from beam directions
        if node_id in node_beam_dirs:
            info = node_beam_dirs[node_id]
            avg_dir = info['avg_dir']          # Plate PARALLEL to this
            plate_normal = info['plate_normal'] # Normal to plate
            plate_y = info['plate_y']           # Y direction on plate
        else:
            avg_dir = Vector3d(0, 0, 1)
            plate_normal = Vector3d(1, 0, 0)
            plate_y = Vector3d(0, 1, 0)
        
        # Create plane for box
        # X direction: avg_dir (along beam)
        # Y direction: plate_y (on plate, perpendicular to beam)
        plane = Plane(Point3d(base_x, base_y, base_z), avg_dir, plate_y)
        
        # Box dimensions: length, width, height (thickness)
        length = float(block_size)
        width = float(block_size)
        height = float(PLYWOOD_THICK)
        
        half_len = length / 2.0
        half_wid = width / 2.0
        half_hei = height / 2.0
        
        box = Box(plane, 
                  Interval(-half_len, half_len),   # Along avg_dir (X)
                  Interval(-half_wid, half_wid),   # Along plate_y (Y)
                  Interval(-half_hei, half_hei))   # Thickness (Z)
        
        block_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddBox(box)
        
        if block_id:
            obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(block_id)
            if obj:
                layer_index = Rhino.RhinoDoc.ActiveDoc.Layers.Find(layer_name, True)
                obj.Attributes.LayerIndex = layer_index
                obj.Attributes.ObjectColor = Color.FromArgb(100, 180, 255)
                obj.Attributes.Name = f"Block_{node_name}"
                Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(obj, obj.Attributes, True)
            
            total_blocks += 1
            
            # Add rod holes - SPHERES on plate surface
            rod_positions = get_rod_positions(rods_required, block_size)
            
            for rod_idx, (rod_x_local, rod_y_local) in enumerate(rod_positions):
                try:
                    half_length = length / 2.0
                    half_width = width / 2.0
                    
                    # Position on plate surface
                    # rod_x_local is along avg_dir (beam direction)
                    # rod_y_local is along plate_y (perpendicular to beam on plate)
                    world_x = base_x + (rod_x_local - half_length) * avg_dir.X + (rod_y_local - half_width) * plate_y.X
                    world_y = base_y + (rod_x_local - half_length) * avg_dir.Y + (rod_y_local - half_width) * plate_y.Y
                    world_z = base_z + (rod_x_local - half_length) * avg_dir.Z + (rod_y_local - half_width) * plate_y.Z
                    
                    # Sphere representing drill hole location
                    rod_sphere = Sphere(Point3d(world_x, world_y, world_z), float(ROD_DIAMETER))
                    rod_brep = rod_sphere.ToBrep()
                    
                    rod_id = Rhino.RhinoDoc.ActiveDoc.Objects.AddBrep(rod_brep)
                    
                    if rod_id:
                        rod_obj = Rhino.RhinoDoc.ActiveDoc.Objects.FindId(rod_id)
                        if rod_obj:
                            layer_index = Rhino.RhinoDoc.ActiveDoc.Layers.Find(layer_name, True)
                            rod_obj.Attributes.LayerIndex = layer_index
                            rod_obj.Attributes.ObjectColor = Color.FromArgb(255, 100, 100)
                            rod_obj.Attributes.Name = f"Rod_{node_name}_{rod_idx+1}"
                            Rhino.RhinoDoc.ActiveDoc.Objects.ModifyAttributes(rod_obj, rod_obj.Attributes, True)
                        total_rods += 1
                except:
                    pass
            
            print(f"  ✓ {len(rod_positions)} rod spheres added\n")
    
    except Exception as e:
        print(f"  ✗ Error: {str(e)}\n")

# Refresh viewport
Rhino.RhinoDoc.ActiveDoc.Views.Redraw()

# ============================================================================
# SUMMARY
# ============================================================================

print("=" * 80)
print("COMPLETE!")
print("=" * 80)

print(f"\n✓ Geometry Created:")
print(f"  - Connector blocks: {total_blocks}")
print(f"  - Rod spheres: {total_rods}")

print(f"\n✓ Approach:")
print(f"  - Plates PARALLEL to beam directions (rotated)")
print(f"  - Rod counts based on LOADS (engineered)")
print(f"  - Block sizes based on BEARING CAPACITY")
print(f"  - Spheres show rod hole positions")

print(f"\n✓ Layer: {layer_name}")
print(f"✓ Use Ctrl+Shift+F to zoom fit in Rhino")

print("\n" + "=" * 80)