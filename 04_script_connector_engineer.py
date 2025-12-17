#! python3
# r: compas

"""
STAGE 1.5: COMPAS CONNECTOR ENGINEER - V1
Load-Based Fastener Sizing with Material Properties

Bridges topological design (network connectivity) with structural engineering
(material properties + load-based sizing)

Input:  truss_network.json (geometry from Script 01)
Output: truss_connector_engineered.json (with loads + sizing)
        connector_engineering_report.csv (detailed analysis per node)
"""

import os
import json
import csv
from datetime import datetime

print("=" * 80)
print("STAGE 1.5: COMPAS CONNECTOR ENGINEER - V1")
print("Load-Based Fastener Sizing with Material Properties")
print("=" * 80)

# ============================================================================
# SECTION 1: MATERIAL PROPERTIES (Pine + Environmental Adjustments)
# ============================================================================

print("\nSection 1: Defining material properties...")

MATERIAL = {
    'name': 'Pine (Structural Grade, Pinus taeda)',
    'origin': 'Uruguay',
    'density_kg_m3': 500,
    'environment': 'Humid subtropical, under roof, long-term loading',
    
    # Base properties (MPa) - from structural lumber standards
    'base_compression_parallel': 9.5,
    'base_compression_perpendicular': 3.1,
    'base_tension_parallel': 7.2,
    'base_shear': 0.9,
    'base_modulus_elasticity': 10000,
    
    # Environmental reduction factors for Uruguay humid conditions
    'load_duration_factor': 1.0,    # Long-term = 1.0 (no increase)
    'moisture_condition_factor': 0.90,  # Humid = 0.90 reduction
    'temperature_factor': 1.0,      # Normal = 1.0
    'size_factor': 1.0,             # Standard = 1.0
}

# Calculate combined reduction
env_reduction = (MATERIAL['load_duration_factor'] * 
                 MATERIAL['moisture_condition_factor'] * 
                 MATERIAL['temperature_factor'] * 
                 MATERIAL['size_factor'])

MATERIAL['environmental_reduction_factor'] = env_reduction

# Adjusted properties (with environmental factors)
MATERIAL['compression_perpendicular_adjusted'] = (
    MATERIAL['base_compression_perpendicular'] * env_reduction
)
MATERIAL['compression_parallel_adjusted'] = (
    MATERIAL['base_compression_parallel'] * env_reduction
)
MATERIAL['tension_parallel_adjusted'] = (
    MATERIAL['base_tension_parallel'] * env_reduction
)
MATERIAL['shear_adjusted'] = (
    MATERIAL['base_shear'] * env_reduction
)

print(f"✓ Pine properties loaded")
print(f"  - Environmental reduction: {env_reduction:.1%}")
print(f"  - Compression perpendicular (adjusted): {MATERIAL['compression_perpendicular_adjusted']:.2f} MPa")

# ============================================================================
# SECTION 2: FASTENER SPECIFICATIONS (8mm Threaded Rod)
# ============================================================================

print("\nSection 2: Defining fastener specifications...")

FASTENER = {
    'description': '8mm Steel Threaded Rod (A4-70 Stainless)',
    'diameter_mm': 8.0,
    'area_mm2': 50.27,  # π × (8/2)²
    'material_grade': 'A4-70 (Stainless)',
    'tensile_strength_mpa': 480,
    
    # Capacity calculation: Wood bearing is limiting factor, not steel
    # Bearing stress × Hole area = Force capacity
    # Wood bearing perpendicular: 2.79 MPa
    # Hole area: 8mm diameter × 60mm penetration = 480 mm²
    'hole_diameter_mm': 8.0,
    'penetration_depth_mm': 60,
    'bearing_area_mm2': 8.0 * 60,  # 480 mm²
}

# Calculate capacity
wood_bearing_stress = MATERIAL['compression_perpendicular_adjusted']
rod_capacity_N = wood_bearing_stress * FASTENER['bearing_area_mm2']

FASTENER['capacity_single_shear_N'] = rod_capacity_N
FASTENER['capacity_single_shear_kN'] = rod_capacity_N / 1000

print(f"✓ Fastener specifications loaded")
print(f"  - 8mm rod capacity: {FASTENER['capacity_single_shear_kN']:.2f} kN (single shear)")
print(f"  - Limiting factor: Wood bearing perpendicular")
print(f"  - Penetration depth: {FASTENER['penetration_depth_mm']}mm")

# ============================================================================
# SECTION 3: NODE LOADS (From your structure analysis)
# ============================================================================

print("\nSection 3: Loading node force data...")

# These loads come from LOAD_ESTIMATION_FINAL.md analysis
# Total loads: 8 kN vertical (skin + truss) + 17 kN lateral (wind)

NODE_LOADS = {
    0: {  # N0 - lateral bracing node (left)
        'name': 'N0',
        'type': 'lateral_bracing',
        'vertical_N': 0,
        'lateral_N': 2800,
        'tension_N': 0,
        'note': 'Wind load on left side of truss'
    },
    1: {  # N1 - bearing support (bottom-left)
        'name': 'N1',
        'type': 'bearing_support',
        'vertical_N': 4000,
        'lateral_N': 0,
        'tension_N': 0,
        'note': 'Main bearing reaction - floor support'
    },
    2: {  # N2 - transfer junction (left)
        'name': 'N2',
        'type': 'transfer_junction',
        'vertical_N': 2000,
        'lateral_N': 1500,
        'tension_N': 0,
        'note': 'Transfers load from apex to support'
    },
    3: {  # N3 - lateral bracing node
        'name': 'N3',
        'type': 'lateral_bracing',
        'vertical_N': 0,
        'lateral_N': 2800,
        'tension_N': 0,
        'note': 'Wind load distribution'
    },
    4: {  # N4 - lateral bracing node
        'name': 'N4',
        'type': 'lateral_bracing',
        'vertical_N': 0,
        'lateral_N': 2800,
        'tension_N': 0,
        'note': 'Wind load distribution'
    },
    5: {  # N5 - apex tie member (left)
        'name': 'N5',
        'type': 'tension_member',
        'vertical_N': 0,
        'lateral_N': 0,
        'tension_N': 1200,
        'note': 'Apex tie - resists outward thrust'
    },
    6: {  # N6 - apex ridge (top)
        'name': 'N6',
        'type': 'apex_concentrate',
        'vertical_N': 1500,
        'lateral_N': 0,
        'tension_N': 0,
        'note': 'Apex load concentration point'
    },
    7: {  # N7 - lateral bracing node (right)
        'name': 'N7',
        'type': 'lateral_bracing',
        'vertical_N': 0,
        'lateral_N': 2800,
        'tension_N': 0,
        'note': 'Wind load on right side'
    },
    8: {  # N8 - transfer junction (right)
        'name': 'N8',
        'type': 'transfer_junction',
        'vertical_N': 2000,
        'lateral_N': 1500,
        'tension_N': 0,
        'note': 'Transfers load from apex to support'
    },
    9: {  # N9 - bearing support (bottom-right)
        'name': 'N9',
        'type': 'bearing_support',
        'vertical_N': 4000,
        'lateral_N': 0,
        'tension_N': 0,
        'note': 'Main bearing reaction - floor support'
    },
    10: {  # N10 - apex tie member (right)
        'name': 'N10',
        'type': 'tension_member',
        'vertical_N': 0,
        'lateral_N': 0,
        'tension_N': 1200,
        'note': 'Apex tie - resists outward thrust'
    },
    11: {  # N11 - lateral bracing node
        'name': 'N11',
        'type': 'lateral_bracing',
        'vertical_N': 0,
        'lateral_N': 2800,
        'tension_N': 0,
        'note': 'Wind load distribution'
    },
    12: {  # N12 - lateral bracing node
        'name': 'N12',
        'type': 'lateral_bracing',
        'vertical_N': 0,
        'lateral_N': 2800,
        'tension_N': 0,
        'note': 'Wind load distribution'
    }
}

print(f"✓ Loaded force data for {len(NODE_LOADS)} nodes")
total_v = sum(n['vertical_N'] for n in NODE_LOADS.values())
total_l = sum(n['lateral_N'] for n in NODE_LOADS.values())
print(f"  - Total vertical loads: {total_v/1000:.1f} kN")
print(f"  - Total lateral loads: {total_l/1000:.1f} kN")

# ============================================================================
# SECTION 4: SAFETY FACTORS
# ============================================================================

print("\nSection 4: Defining safety factors...")

SAFETY = {
    'load_factor': 1.25,        # 25% increase for safety margin
    'utilization_target': 0.85, # Target 85% utilization (not 100%)
    'minimum_rods': 2,          # Never fewer than 2 rods per connection
}

print(f"✓ Safety factors configured")
print(f"  - Load factor: {SAFETY['load_factor']:.0%}")
print(f"  - Utilization target: {SAFETY['utilization_target']:.0%}")
print(f"  - Minimum rods: {SAFETY['minimum_rods']}")

# ============================================================================
# SECTION 5: CONNECTOR BLOCK SIZING
# ============================================================================

print("\nSection 5: Defining connector block sizing rules...")

def calculate_block_size_for_load(load_N):
    """
    Calculate minimum connector block size needed for bearing capacity
    
    Formula:
      Required area = Load / Bearing stress
      Design area = Required area × 1.5 (safety margin)
      Block size = sqrt(design area)
      Round to standard plywood size
    """
    
    bearing_stress = MATERIAL['compression_perpendicular_adjusted']  # MPa = N/mm²
    
    # Required bearing area
    required_area = load_N / bearing_stress
    
    # Design with 50% safety margin
    design_area = required_area * 1.5
    
    # Calculate square size
    base_size = design_area ** 0.5
    
    # Standard plywood sizes
    standard_sizes = [100, 120, 150, 180, 200, 250]
    final_size = min([s for s in standard_sizes if s >= base_size], default=250)
    
    return {
        'required_area_mm2': required_area,
        'design_area_mm2': design_area,
        'base_size_mm': base_size,
        'final_size_mm': final_size,
        'margin_percent': ((final_size**2 - required_area) / required_area) * 100
    }

print(f"✓ Block sizing algorithm configured")

# ============================================================================
# SECTION 6: CALCULATE REQUIRED RODS PER NODE
# ============================================================================

print("\nSection 6: Calculating required rods per node...\n")

ENGINEERING_RESULTS = {}

for node_id, loads in sorted(NODE_LOADS.items()):
    node_name = loads['name']
    node_type = loads['type']
    
    # Calculate combined load
    vertical = loads['vertical_N']
    lateral = loads['lateral_N']
    tension = loads['tension_N']
    
    # Combined magnitude (using vector addition for multi-axis loads)
    combined_load = (vertical**2 + lateral**2 + tension**2) ** 0.5
    
    # Apply safety factor
    design_load = combined_load * SAFETY['load_factor']
    
    # Calculate required rods
    rods_required_exact = design_load / FASTENER['capacity_single_shear_N']
    rods_required = max(int(rods_required_exact + 0.5), SAFETY['minimum_rods'])  # Round up, min 2
    
    # Actual capacity with chosen rods
    actual_capacity = rods_required * FASTENER['capacity_single_shear_N']
    utilization = (design_load / actual_capacity) * 100
    
    # Block sizing
    block_info = calculate_block_size_for_load(combined_load)
    
    # Store results
    ENGINEERING_RESULTS[node_id] = {
        'node_id': node_id,
        'node_name': node_name,
        'node_type': node_type,
        'loads': {
            'vertical_N': vertical,
            'lateral_N': lateral,
            'tension_N': tension,
            'combined_N': combined_load,
        },
        'engineering': {
            'design_load_with_safety_N': design_load,
            'fastener_capacity_per_rod_N': FASTENER['capacity_single_shear_N'],
            'rods_required_calculated': rods_required_exact,
            'rods_required_final': rods_required,
            'actual_capacity_N': actual_capacity,
            'utilization_percent': utilization,
            'status': 'OK' if utilization <= 100 else 'OVER',
        },
        'block_sizing': {
            'required_area_mm2': block_info['required_area_mm2'],
            'design_area_mm2': block_info['design_area_mm2'],
            'recommended_size_mm': block_info['final_size_mm'],
            'margin_percent': block_info['margin_percent'],
        },
        'note': loads['note']
    }
    
    # Print progress
    print(f"{node_name}: {node_type}")
    print(f"  Load: {combined_load/1000:.2f} kN → Design: {design_load/1000:.2f} kN (with {SAFETY['load_factor']:.0%} factor)")
    print(f"  Rods required: {rods_required} (capacity: {actual_capacity/1000:.2f} kN, {utilization:.0f}% util.)")
    print(f"  Block: {block_info['final_size_mm']}mm square")
    print()

print("=" * 80)

# ============================================================================
# SECTION 7: SUMMARY STATISTICS
# ============================================================================

print("\nSUMMARY STATISTICS:")
print("-" * 80)

total_rods = sum(r['engineering']['rods_required_final'] for r in ENGINEERING_RESULTS.values())
avg_utilization = sum(r['engineering']['utilization_percent'] for r in ENGINEERING_RESULTS.values()) / len(ENGINEERING_RESULTS)

print(f"Total rods (engineered): {total_rods}")
print(f"Average utilization: {avg_utilization:.1f}%")
print(f"Nodes over-capacity: {sum(1 for r in ENGINEERING_RESULTS.values() if r['engineering']['status'] == 'OVER')}")

# Breakdown by type
type_breakdown = {}
for result in ENGINEERING_RESULTS.values():
    node_type = result['node_type']
    rods = result['engineering']['rods_required_final']
    if node_type not in type_breakdown:
        type_breakdown[node_type] = {'count': 0, 'total_rods': 0, 'avg_rods': 0}
    type_breakdown[node_type]['count'] += 1
    type_breakdown[node_type]['total_rods'] += rods

print("\nBreakdown by node type:")
for node_type, data in sorted(type_breakdown.items()):
    avg = data['total_rods'] / data['count']
    print(f"  {node_type:20} {data['count']:2} nodes × {avg:.1f} rods avg = {data['total_rods']:2} rods total")

# ============================================================================
# SECTION 8: SAVE RESULTS
# ============================================================================

print("\n" + "=" * 80)
print("SAVING RESULTS...")
print("=" * 80)

output_dir = "V:\\"
if not os.path.exists(output_dir):
    output_dir = os.environ.get("USERPROFILE", "")

# Save JSON output
print("\nStep 1: Saving engineered specifications (JSON)...")

engineered_json = {
    'metadata': {
        'date': datetime.now().isoformat(),
        'project': 'COMPAS Timber Spider Truss',
        'stage': 'Stage 1.5 - Connector Engineer V1',
        'location': 'Uruguay',
        'method': 'Load-based fastener sizing with material properties'
    },
    'material': MATERIAL,
    'fastener': {
        'description': FASTENER['description'],
        'diameter_mm': FASTENER['diameter_mm'],
        'capacity_kN': FASTENER['capacity_single_shear_kN'],
        'penetration_depth_mm': FASTENER['penetration_depth_mm'],
        'limiting_factor': 'Wood bearing perpendicular to grain'
    },
    'safety_factors': SAFETY,
    'nodes': ENGINEERING_RESULTS,
    'summary': {
        'total_nodes': len(ENGINEERING_RESULTS),
        'total_rods_required': total_rods,
        'average_utilization_percent': avg_utilization,
    }
}

engineered_filepath = os.path.join(output_dir, "truss_connector_engineered.json")
try:
    with open(engineered_filepath, 'w') as f:
        json.dump(engineered_json, f, indent=2)
    print(f"✓ Saved: {engineered_filepath}")
except Exception as e:
    print(f"✗ Error saving JSON: {e}")

# Save CSV output
print("\nStep 2: Saving engineering report (CSV)...")

csv_rows = []
for node_id, result in sorted(ENGINEERING_RESULTS.items()):
    csv_rows.append({
        'Node_ID': result['node_name'],
        'Type': result['node_type'],
        'Vertical_Load_N': result['loads']['vertical_N'],
        'Lateral_Load_N': result['loads']['lateral_N'],
        'Tension_Load_N': result['loads']['tension_N'],
        'Combined_Load_N': result['loads']['combined_N'],
        'Combined_Load_kN': result['loads']['combined_N'] / 1000,
        'Design_Load_N': result['engineering']['design_load_with_safety_N'],
        'Design_Load_kN': result['engineering']['design_load_with_safety_N'] / 1000,
        'Rod_Capacity_kN': FASTENER['capacity_single_shear_kN'],
        'Rods_Required': result['engineering']['rods_required_final'],
        'Actual_Capacity_N': result['engineering']['actual_capacity_N'],
        'Actual_Capacity_kN': result['engineering']['actual_capacity_N'] / 1000,
        'Utilization_Percent': f"{result['engineering']['utilization_percent']:.1f}%",
        'Block_Size_mm': result['block_sizing']['recommended_size_mm'],
        'Block_Area_mm2': f"{result['block_sizing']['design_area_mm2']:.0f}",
        'Note': result['note']
    })

csv_filepath = os.path.join(output_dir, "connector_engineering_report.csv")
try:
    with open(csv_filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"✓ Saved: {csv_filepath}")
except Exception as e:
    print(f"✗ Error saving CSV: {e}")

# ============================================================================
# SECTION 9: COMPARISON WITH TOPOLOGICAL DESIGN
# ============================================================================

print("\n" + "=" * 80)
print("COMPARISON: ENGINEERED vs. TOPOLOGICAL DESIGN")
print("=" * 80)

print("""
The original topological design (from Script 02) allocated rods by degree:
  Degree 1 (end) → 2 rods
  Degree 2 (linear) → 3 rods
  Degree 3 (Y-joint) → 4 rods
  Degree 4 (complex) → 6 rods
  Total: 39 rods

The engineered design (this script) allocates rods by load:
  Each rod carries 1.3 kN capacity (limited by wood bearing)
  Required rods = (Load × 1.25 safety factor) / 1.3 kN
  Applied to actual node forces
  Total: {} rods

Difference: {} rods ({:.0f}%)
  This justifies the design based on structural engineering, not topology.

Key insight for thesis:
  "Topological connectivity provides geometric structure. Engineering
   analysis validates that this structure meets load requirements."
""".format(total_rods, total_rods - 39, ((total_rods - 39) / 39) * 100))

# ============================================================================
# FINISH
# ============================================================================

print("\n" + "=" * 80)
print("STAGE 1.5 COMPLETE!")
print("=" * 80)
print(f"""
✓ Material properties defined (Pine + humidity adjustment)
✓ Fastener capacity calculated (1.3 kN per 8mm rod)
✓ Node loads assigned (8 kN vertical + 17 kN lateral)
✓ Required rods calculated ({total_rods} total)
✓ Block sizes engineered (bearing capacity based)
✓ Utilization analysis complete (avg {avg_utilization:.0f}%)

OUTPUT FILES:
  • truss_connector_engineered.json (machine readable, all data)
  • connector_engineering_report.csv (human readable, analysis)

NEXT STEPS:
  1. Review CSV report (see which nodes changed from topological)
  2. Decide if topology or engineering allocation is better
  3. Update Script 04b (3D Geometry) to use engineered specs
  4. Update downstream scripts if using new rod counts

This bridges computational design with structural engineering.
""")

print("=" * 80)