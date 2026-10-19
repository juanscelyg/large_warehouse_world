#!/usr/bin/env python3
# Copyright 2026 Juan S. Cely G.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generate large_warehouse_world from the plan of the facility.

Writes:
  models/large_warehouse_building   floors, walls, doors, fences, signs and floor markings
  models/warehouse_{a,b,c}_storage  racks, shelves and stored goods of each warehouse
  models/reception_furniture        furniture of the reception and offices building
  models/loading_zone_props         cones, barriers, pallet stacks and lamp posts
  worlds/large_warehouse_world.sdf  the world (grouped models + vehicles and equipment)
  config/large_warehouse_world_zones.yaml  zones and doors of the plan

All the grouped models use world coordinates, so they are included at the origin.
The textures of the signs are drawn by scripts/generate_signs.py. Usage:

    python3 scripts/generate_signs.py && python3 scripts/generate_world.py
"""

import math
import random
from pathlib import Path
import xml.etree.ElementTree as ET

PACKAGE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = PACKAGE_DIR / 'models'
WORLDS_DIR = PACKAGE_DIR / 'worlds'
CONFIG_DIR = PACKAGE_DIR / 'config'
WORLD_NAME = 'large_warehouse_world'
AUTHOR = ('Juan S. Cely G.', 'juanscelyg@gmail.com')

PI = math.pi
rng = random.Random(2026)
# Collisions of everything but the floors start this high, so the static boxes do not touch the
# floor slabs and the physics engine does not compute thousands of static contacts every step
COLLISION_LIFT = 0.01

# ---------------------------------------------------------------------------------------------
# Plan of the facility (meters). x grows to the east and y to the north, the origin is the
# south-west corner of Warehouse A extended to the south baseline of the plan.
# ---------------------------------------------------------------------------------------------
ZONES = {
    'warehouse_a': {'name': 'Warehouse A', 'rects': [(0, 200, 200, 400)]},
    'warehouse_b': {'name': 'Warehouse B', 'rects': [(200, 100, 400, 400)]},
    'warehouse_c': {'name': 'Warehouse C', 'rects': [(400, 0, 700, 400)]},
    'reception': {'name': 'Recepcion y oficinas', 'rects': [(150, 400, 450, 450)]},
    # L shaped truck lane (20 m wide) and the truck yard south of Warehouse B
    'loading': {'name': 'Zona Carga Camiones',
                'rects': [(0, 180, 200, 200), (180, 0, 200, 180), (200, 0, 400, 100)]},
}

WALL_T = 0.4           # wall thickness
H_WAREHOUSE = 12.0     # warehouse walls
H_RECEPTION = 6.0      # reception and offices building
H_FENCE = 3.0          # fence of the loading zone
H_PARTITION = 3.5      # office partitions

# Walls: (axis, coordinate, start, end, height, kind, openings)
#   axis 'x': wall along x at y = coordinate; axis 'y': wall along y at x = coordinate
#   openings: (center along the wall, width, height, type)
DOCK = (4.0, 4.5, 'dock')
INNER = (6.0, 5.0, 'door')
PERSON = (4.0, 3.5, 'door')
WALLS = [
    # Warehouse A
    ('x', 200, 0, 200, H_WAREHOUSE, 'wall', [(x, *DOCK) for x in (15, 40, 65, 90, 115, 140, 165)]),
    ('x', 400, 0, 150, H_WAREHOUSE, 'wall', []),
    ('y', 0, 200, 400, H_WAREHOUSE, 'wall', []),
    ('y', 200, 200, 400, H_WAREHOUSE, 'wall', [(y, *INNER) for y in (255, 314, 375)]),
    # Reception <-> warehouses
    ('x', 400, 150, 450, H_WAREHOUSE, 'wall', [(x, *PERSON) for x in (175, 250, 350, 425)]),
    # Warehouse B
    ('y', 200, 100, 200, H_WAREHOUSE, 'wall', [(y, *DOCK) for y in (120, 145, 170)]),
    ('x', 100, 200, 400, H_WAREHOUSE, 'wall', [(x, *DOCK) for x in (220, 245, 270, 295, 320, 345, 370)]),
    ('y', 400, 100, 400, H_WAREHOUSE, 'wall', [(y, *INNER) for y in (140, 230, 314, 375)]),
    # Warehouse C
    ('x', 400, 450, 700, H_WAREHOUSE, 'wall', []),
    ('y', 400, 0, 100, H_WAREHOUSE, 'wall', [(y, *DOCK) for y in (20, 45, 70)]),
    ('y', 700, 0, 400, H_WAREHOUSE, 'wall', []),
    ('x', 0, 400, 700, H_WAREHOUSE, 'wall', []),
    # Reception and offices
    ('y', 150, 400, 450, H_RECEPTION, 'wall', []),
    ('y', 450, 400, 450, H_RECEPTION, 'wall', []),
    ('x', 450, 150, 450, H_RECEPTION, 'wall', [(300, 6.0, 3.2, 'entrance'), (170, 3.0, 3.0, 'entrance')]),
    # Fence of the loading zone, with the truck gates
    ('x', 0, 180, 400, H_FENCE, 'fence', [(190, 16.0, H_FENCE, 'gate'), (300, 14.0, H_FENCE, 'gate')]),
    ('y', 180, 0, 180, H_FENCE, 'fence', []),
    ('x', 180, 0, 180, H_FENCE, 'fence', []),
    ('y', 0, 180, 200, H_FENCE, 'fence', [(190, 16.0, H_FENCE, 'gate')]),
    ('y', 200, 0, 100, H_FENCE, 'fence', [(25, 12.0, H_FENCE, 'gate'), (70, 12.0, H_FENCE, 'gate')]),
]

# Partitions inside the reception building, with 3 m doorways
PARTITIONS = [('y', x, 410, 450, H_PARTITION, 'partition', [(428, 3.0, 2.6, 'door')])
              for x in (200, 260, 340, 400)]

COLORS = {
    'concrete': (0.70, 0.70, 0.68), 'office_floor': (0.80, 0.77, 0.70),
    'asphalt': (0.22, 0.22, 0.24), 'site': (0.30, 0.30, 0.31), 'grass': (0.30, 0.45, 0.22),
    'wall': (0.80, 0.82, 0.84), 'wall_band': (0.16, 0.32, 0.55), 'reception_wall': (0.93, 0.92, 0.88),
    'fence': (0.62, 0.62, 0.60), 'partition': (0.85, 0.87, 0.90), 'frame': (0.25, 0.25, 0.27),
    'yellow': (0.95, 0.75, 0.05), 'white': (0.95, 0.95, 0.95), 'green': (0.10, 0.60, 0.25),
    'black': (0.08, 0.08, 0.08), 'steel': (0.45, 0.47, 0.50), 'glass': (0.55, 0.75, 0.85),
}
ZONE_COLORS = {'warehouse_a': (0.08, 0.40, 0.75), 'warehouse_b': (0.18, 0.49, 0.20),
               'warehouse_c': (0.90, 0.32, 0.0), 'reception': (0.42, 0.11, 0.60),
               'loading': (0.98, 0.66, 0.15)}

# Bounding boxes (min, max) of the models in their own frame, used for the box collisions of
# the grouped models
BBOX = {
    'high_bay_rack': ((-1.06, -9.02, 0), (1.06, 9.02, 6.53)),
    'picking_shelf_d': ((-1.96, -0.44, 0), (1.96, 0.44, 2.61)),
    'picking_shelf_e': ((-1.96, -0.44, 0), (1.96, 0.44, 2.64)),
    'pallet_rack': ((-1.32, -0.76, 0), (1.32, 0.76, 3.06)),
    'storage_rack': ((-0.63, -0.36, 0), (0.63, 0.36, 1.74)),
    'box_pile_a': ((-1.07, -0.99, 0), (1.07, 0.99, 1.1)),
    'box_pile_c': ((-0.88, -1.02, 0), (0.88, 1.02, 1.77)),
    'box_pile_d': ((-0.5, -0.75, 0), (0.5, 0.75, 1.82)),
    'crate_stack': ((-0.47, -0.61, 0), (0.47, 0.61, 1.41)),
    'pallet_standard': ((-0.6, -0.5, 0), (0.6, 0.5, 0.15)),
    'euro_pallet': ((-0.4, -0.6, -0.07), (0.4, 0.6, 0.07)),
    'cardboard_box': ((-0.25, -0.2, -0.15), (0.25, 0.2, 0.15)),
    'large_crate': ((-0.54, -0.28, 0), (0.54, 0.27, 0.49)),
    'conveyor_block': ((-0.25, -0.25, 0), (0.25, 0.25, 0.5)),
    'table': ((-0.75, -0.4, 0), (0.75, 0.4, 1.01)),
    'metal_cabinet': ((-0.4, -0.22, 0), (0.4, 0.22, 1.68)),
    'office_desk': ((-0.45, -1.13, 0), (0.42, 1.13, 0.8)),
    'office_chair_black': ((-0.37, -0.39, 0), (0.37, 0.36, 1.25)),
    'office_chair_grey': ((-0.35, -0.25, 0), (0.36, 0.45, 1.14)),
    'visitor_chair': ((-0.35, -0.34, 0), (0.35, 0.47, 1.18)),
    'chair': ((-0.3, -0.29, 0), (0.22, 0.29, 0.82)),
    'sofa': ((-0.5, -0.9, 0), (0.54, 0.9, 0.94)),
    'mini_sofa': ((-0.36, -0.36, 0), (0.33, 0.36, 0.61)),
    'coffee_table': ((-0.36, -0.36, 0), (0.36, 0.36, 0.37)),
    'bookshelf': ((-0.46, -0.4, 0), (0.46, 0.01, 1.2)),
    'white_cabinet': ((-0.45, -0.22, 0), (0.45, 0.22, 1.08)),
    'vending_machine': ((-0.3, -0.46, 0), (0.31, 0.46, 1.83)),
    'fridge': ((-0.29, -0.27, 0), (0.29, 0.27, 1.56)),
    'kitchen_countertop': ((-0.36, -1.15, 0), (0.38, 1.15, 1.01)),
    'cafe_table': ((-0.46, -0.46, 0), (0.46, 0.46, 0.77)),
    'trash_bin': ((-0.13, -0.19, 0), (0.13, 0.19, 0.45)),
    'locker_big': ((-0.25, -4.56, 0), (0.27, 4.59, 1.6)),
    'jersey_barrier': ((-2.03, -0.41, 0), (2.03, 0.41, 1.14)),
    'construction_cone': ((-0.25, -0.25, 0), (0.25, 0.25, 1.09)),
    'lamp_post': ((-0.24, -0.24, 0), (0.24, 0.24, 9.27)),
    'extinguisher_cabinet': ((-0.1, -0.15, 1.0), (0.11, 0.16, 1.53)),
    'exit_sign': ((-0.15, -0.03, 0), (0.15, 0.03, 0.23)),
}


# ---------------------------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------------------------
def f(v):
    """Compact number formatting."""
    s = f'{v:.4f}'.rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def pose_str(p):
    return ' '.join(f(v) for v in p)


def rot(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def compose(a, b):
    """Pose b expressed in frame a -> pose in the parent frame of a."""
    ra = rot(*a[3:])
    pos = [a[i] + sum(ra[i][k] * b[k] for k in range(3)) for i in range(3)]
    m = matmul(ra, rot(*b[3:]))
    pitch = math.asin(max(-1.0, min(1.0, -m[2][0])))
    return pos + [math.atan2(m[2][1], m[2][2]), pitch, math.atan2(m[1][0], m[0][0])]


def rgb(c, a=1.0):
    return f'{f(c[0])} {f(c[1])} {f(c[2])} {f(a)}'


class ColorMaterial(str):
    """SDF material of a plain color; boxes with it can be batched in one mesh."""
    color = None


def color_material(c, emissive=None):
    e = f'<emissive>{rgb(emissive)}</emissive>' if emissive else ''
    m = ColorMaterial(f'<material><ambient>{rgb(c)}</ambient><diffuse>{rgb(c)}</diffuse>'
                      f'<specular>0.1 0.1 0.1 1</specular>{e}</material>')
    m.color = None if emissive else tuple(round(v, 3) for v in c)
    return m


# Faces of a box: vertex indices (bottom 0-3, top 4-7, counter clockwise) and normal index
BOX_FACES = [((0, 1, 5, 4), 0), ((1, 2, 6, 5), 1), ((2, 3, 7, 6), 2), ((3, 0, 4, 7), 3),
             ((4, 5, 6, 7), 4), ((0, 3, 2, 1), 5)]


def box_obj(boxes):
    """OBJ text of a list of boxes (center, size, yaw) with flat normals."""
    out = []
    for i, ((cx, cy, cz), (sx, sy, sz), yaw) in enumerate(boxes):
        c, s_ = math.cos(yaw), math.sin(yaw)
        for dz in (-sz / 2, sz / 2):
            for dx, dy in ((-sx / 2, -sy / 2), (sx / 2, -sy / 2), (sx / 2, sy / 2), (-sx / 2, sy / 2)):
                out.append(f'v {cx + c * dx - s_ * dy:.3f} {cy + s_ * dx + c * dy:.3f} {cz + dz:.3f}')
        for nx, ny, nz in ((s_, -c, 0), (c, s_, 0), (-s_, c, 0), (-c, -s_, 0), (0, 0, 1), (0, 0, -1)):
            out.append(f'vn {nx:.4f} {ny:.4f} {nz}')
        v, n = 8 * i + 1, 6 * i + 1
        for (a, b, cc, d), k in BOX_FACES:
            out.append(f'f {v + a}//{n + k} {v + b}//{n + k} {v + cc}//{n + k}')
            out.append(f'f {v + a}//{n + k} {v + cc}//{n + k} {v + d}//{n + k}')
    return '\n'.join(out) + '\n'


def texture_material(texture, emissive=False):
    tex = f'materials/textures/{texture}'
    em = f'<emissive_map>{tex}</emissive_map>' if emissive else ''
    return (f'<material><diffuse>1 1 1 1</diffuse><specular>0.1 0.1 0.1 1</specular>'
            f'<pbr><metal><albedo_map>{tex}</albedo_map>{em}<roughness>0.6</roughness>'
            f'<metalness>0</metalness></metal></pbr></material>')


def zone_at(x, y):
    for zid, z in ZONES.items():
        for (x0, y0, x1, y1) in z['rects']:
            if x0 < x < x1 and y0 < y < y1:
                return zid
    return 'outside'


class Group:
    """A static model made of visuals and box collisions in world coordinates."""

    def __init__(self, name):
        self.name = name
        self.links = {}
        self.counts = {}
        self._src = {}
        self.clusters = {}
        self.batches = {}           # (link, color) -> boxes merged in one mesh

    def _uid(self, base):
        n = self.counts.get(base, 0)
        self.counts[base] = n + 1
        return f'{base}_{n:03d}'

    def add(self, link, xml):
        self.links.setdefault(link, []).append(xml)

    def _merge(self, link, cluster, corners):
        xs, ys, zs = zip(*corners)
        box = self.clusters.setdefault((link, cluster), [1e9, 1e9, 1e9, -1e9, -1e9, -1e9])
        box[:3] = [min(box[0], min(xs)), min(box[1], min(ys)), min(box[2], min(zs))]
        box[3:] = [max(box[3], max(xs)), max(box[4], max(ys)), max(box[5], max(zs))]

    def box(self, link, base, center, size, material, yaw=0.0, collision=True, visual=True, cluster=None):
        """Box visual and collision. Collisions with the same cluster are merged in one box."""
        uid = self._uid(base)
        p = pose_str(list(center) + [0, 0, yaw])
        g = f'<geometry><box><size>{pose_str(size)}</size></box></geometry>'
        if visual and getattr(material, 'color', None) is not None:
            self.batches.setdefault((link, material.color, size[2] > 0.05), []).append((center, size, yaw))
        elif visual:
            self.add(link, f'<visual name="{uid}"><pose>{p}</pose>{g}{material}'
                           f'<cast_shadows>{"true" if size[2] > 0.05 else "false"}</cast_shadows></visual>')
        if collision and cluster is not None:
            c, s_ = math.cos(yaw), math.sin(yaw)
            self._merge(link, cluster, [(center[0] + c * dx - s_ * dy, center[1] + s_ * dx + c * dy, center[2] + dz)
                                        for dx in (-size[0] / 2, size[0] / 2) for dy in (-size[1] / 2, size[1] / 2)
                                        for dz in (-size[2] / 2, size[2] / 2)])
        elif collision:
            cz, sz = center[2], size[2]
            if link != 'floors' and cz - sz / 2 < COLLISION_LIFT:
                sz = cz + sz / 2 - COLLISION_LIFT
                cz = COLLISION_LIFT + sz / 2
            pc = pose_str([center[0], center[1], cz, 0, 0, yaw])
            gc = f'<geometry><box><size>{f(size[0])} {f(size[1])} {f(sz)}</size></box></geometry>'
            self.add(link, f'<collision name="{uid}_collision"><pose>{pc}</pose>{gc}</collision>')

    def plane(self, link, base, center, size, material, face, yaw=0.0):
        """Textured plane. face: '-y', '+y', '+x', '-x' (vertical signs) or 'up' (floor)."""
        uid = self._uid(base)
        if face == 'up':
            normal, pose = '0 0 1', list(center) + [0, 0, yaw]
        else:
            normal = '0 -1 0'
            pose = list(center) + [0, 0, {'-y': 0.0, '+y': PI, '+x': PI / 2, '-x': -PI / 2}[face]]
        self.add(link, f'<visual name="{uid}"><pose>{pose_str(pose)}</pose><geometry><plane>'
                       f'<normal>{normal}</normal><size>{f(size[0])} {f(size[1])}</size></plane>'
                       f'</geometry>{material}<cast_shadows>false</cast_shadows></visual>')

    def _source(self, model):
        """Visuals of a local model, with poses in the model frame and model:// URIs."""
        if model not in self._src:
            root = ET.fromstring((MODELS_DIR / model / 'model.sdf').read_text().strip().encode())
            m = root.find('model')
            mpose = [float(v) for v in (m.findtext('pose') or '0 0 0 0 0 0').split()]
            visuals = []
            for link in m.iter('link'):
                lpose = compose(mpose, [float(v) for v in (link.findtext('pose') or '0 0 0 0 0 0').split()])
                for vis in link.findall('visual'):
                    vpose = compose(lpose, [float(v) for v in (vis.findtext('pose') or '0 0 0 0 0 0').split()])
                    for e in vis.iter():
                        if e.tag in ('uri', 'albedo_map', 'normal_map', 'roughness_map',
                                     'metalness_map', 'emissive_map') and e.text:
                            t = e.text.strip()
                            if not t.startswith(('model://', 'http', 'file://', '/')):
                                e.text = f'model://{model}/{t}'
                    for tag in ('pose', 'meta'):
                        for e in vis.findall(tag):
                            vis.remove(e)
                    body = ''.join(ET.tostring(c, encoding='unicode') for c in vis)
                    visuals.append((vis.get('name'), vpose, ' '.join(body.split())))
            self._src[model] = visuals
        return self._src[model]

    def model(self, link, model, pose, collision=True, cluster=None):
        """Copy the visuals of a local model at pose (x, y, z, yaw) with a box collision.

        Collisions with the same cluster are merged in one axis aligned box.
        """
        x, y, z, yaw = pose
        wpose = [x, y, z, 0, 0, yaw]
        uid = self._uid(model)
        for vname, vpose, body in self._source(model):
            p = compose(wpose, vpose)
            self.add(link, f'<visual name="{uid}_{vname}"><pose>{pose_str(p)}</pose>{body}</visual>')
        if collision and model in BBOX and cluster is not None:
            (x0, y0, z0), (x1, y1, z1) = BBOX[model]
            self._merge(link, cluster, [compose(wpose, [cx, cy, cz, 0, 0, 0])[:3]
                                        for cx in (x0, x1) for cy in (y0, y1) for cz in (z0, z1)])
        elif collision and model in BBOX:
            (x0, y0, z0), (x1, y1, z1) = BBOX[model]
            z0 = max(z0, COLLISION_LIFT - z)
            c = compose(wpose, [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2, 0, 0, 0])
            self.add(link, f'<collision name="{uid}_collision"><pose>{pose_str(c)}</pose><geometry><box>'
                           f'<size>{f(x1 - x0)} {f(y1 - y0)} {f(z1 - z0)}</size></box></geometry></collision>')

    def write(self, description, extra_files=False):
        for k, ((link, cluster), b) in enumerate(sorted(self.clusters.items(), key=lambda i: str(i[0]))):
            b[2] = max(b[2], COLLISION_LIFT)
            c = [(b[0] + b[3]) / 2, (b[1] + b[4]) / 2, (b[2] + b[5]) / 2]
            self.add(link, f'<collision name="block_{k:04d}_collision"><pose>{pose_str(c + [0, 0, 0])}</pose>'
                           f'<geometry><box><size>{f(b[3] - b[0])} {f(b[4] - b[1])} {f(b[5] - b[2])}</size>'
                           f'</box></geometry></collision>')
        d = MODELS_DIR / self.name
        d.mkdir(parents=True, exist_ok=True)
        # plain color boxes: one OBJ mesh per link and color
        mesh_dir = d / 'meshes'
        for old in mesh_dir.glob('batch_*.obj'):
            old.unlink()
        for k, ((link, color, shadows), boxes) in enumerate(sorted(self.batches.items(), key=lambda i: str(i[0]))):
            mesh_dir.mkdir(exist_ok=True)
            fname = f'batch_{link}_{k:02d}.obj'
            (mesh_dir / fname).write_text(f'# {len(boxes)} boxes generated by scripts/generate_world.py\n'
                                          + box_obj(boxes))
            self.add(link, f'<visual name="batch_{link}_{k:02d}"><geometry><mesh><uri>meshes/{fname}</uri>'
                           f'</mesh></geometry>{color_material(color)}'
                           f'<cast_shadows>{"true" if shadows else "false"}</cast_shadows></visual>')
        links = '\n'.join(f'    <link name="{ln}">\n      ' + '\n      '.join(items) + '\n    </link>'
                          for ln, items in self.links.items())
        nvis = sum(1 for items in self.links.values() for i in items if i.startswith('<visual'))
        (d / 'model.sdf').write_text(
            f'<?xml version="1.0" ?>\n<!-- Generated by scripts/generate_world.py: {nvis} visuals. '
            f'Poses are in the world frame; include this model at pose 0 0 0 0 0 0. -->\n'
            f'<sdf version="1.9">\n  <model name="{self.name}">\n    <static>true</static>\n'
            f'{links}\n  </model>\n</sdf>\n')
        (d / 'model.config').write_text(
            f'<?xml version="1.0"?>\n<model>\n  <name>{self.name}</name>\n  <version>1.0</version>\n'
            f'  <sdf version="1.9">model.sdf</sdf>\n  <author>\n    <name>{AUTHOR[0]}</name>\n'
            f'    <email>{AUTHOR[1]}</email>\n  </author>\n  <description>\n    {description}\n'
            f'  </description>\n</model>\n')
        return nvis


# ---------------------------------------------------------------------------------------------
# Building: floors, walls, doors, fences, signs and markings
# ---------------------------------------------------------------------------------------------
def line(g, x0, y0, x1, y1, color='yellow', width=0.12):
    """Painted floor line between two points (axis aligned)."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    if abs(x1 - x0) >= abs(y1 - y0):
        size = (abs(x1 - x0), width, 0.01)
    else:
        size = (width, abs(y1 - y0), 0.01)
    g.box('markings', 'line', (cx, cy, 0.005), size, color_material(COLORS[color]), collision=False)


def dashed(g, x0, y0, x1, y1, dash=3.0, gap=3.0, color='white'):
    length = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    s = 0.0
    while s + dash <= length:
        line(g, x0 + ux * s, y0 + uy * s, x0 + ux * (s + dash), y0 + uy * (s + dash), color, 0.15)
        s += dash + gap


def wall_point(axis, c, a, off=0.0):
    """World xy of position `a` along a wall at coordinate c, displaced `off` across it."""
    return (a, c + off) if axis == 'x' else (c + off, a)


def build_wall(g, doors, axis, c, a0, a1, h, kind, openings):
    t = 0.15 if kind == 'partition' else WALL_T
    mat = color_material(COLORS[{'wall': 'wall', 'fence': 'fence', 'partition': 'partition'}[kind]])
    if kind == 'wall' and h == H_RECEPTION:
        mat = color_material(COLORS['reception_wall'])
    ops = sorted(openings)
    # solid segments between the openings (the ends overlap half a thickness to close corners)
    cuts = [a0 - t / 2] + [v for (oc, w, oh, ty) in ops for v in (oc - w / 2, oc + w / 2)] + [a1 + t / 2]
    for s, e in zip(cuts[0::2], cuts[1::2]):
        if e - s > 1e-3:
            x, y = wall_point(axis, c, (s + e) / 2)
            size = (e - s, t, h) if axis == 'x' else (t, e - s, h)
            g.box('walls', kind, (x, y, h / 2), size, mat)
            if kind == 'wall' and h == H_WAREHOUSE:      # colored band at the top of the facades
                size_b = (e - s, t + 0.04, 1.2) if axis == 'x' else (t + 0.04, e - s, 1.2)
                g.box('walls', 'band', (x, y, h - 0.6), size_b,
                      color_material(COLORS['wall_band']), collision=False)
    for (oc, w, oh, ty) in ops:
        # lintel above the opening
        if oh < h - 1e-3:
            x, y = wall_point(axis, c, oc)
            size = (w, t, h - oh) if axis == 'x' else (t, w, h - oh)
            g.box('walls', f'{kind}_lintel', (x, y, (oh + h) / 2), size, mat)
        neg = zone_at(*wall_point(axis, c, oc, -1.0))
        pos = zone_at(*wall_point(axis, c, oc, 1.0))
        doors.append({'center': [round(v, 2) for v in wall_point(axis, c, oc)], 'width': w,
                      'height': oh if ty != 'gate' else None, 'type': ty,
                      'axis': axis, 'connects': [neg, pos]})
        if kind == 'partition':
            continue
        door_frame(g, axis, c, oc, w, oh, h, t, ty, neg, pos)


def door_frame(g, axis, c, oc, w, oh, h, t, ty, neg, pos):
    """Jambs, signs over the opening and safety equipment next to it."""
    hazard = texture_material('hazard_stripes.png')
    frame = color_material(COLORS['frame'])
    jamb_h = oh if ty != 'gate' else 7.5
    for sgn in (-1, 1):                                        # jambs / gate posts
        x, y = wall_point(axis, c, oc + sgn * (w / 2 + 0.2))
        if ty == 'gate':
            g.box('walls', 'gate_post', (x, y, jamb_h / 2), (0.5, 0.5, jamb_h), frame)
            g.box('walls', 'gate_post_stripes', (x, y, 0.75), (0.54, 0.54, 1.5), hazard, collision=False)
        else:
            size = (0.4, t + 0.16, oh) if axis == 'x' else (t + 0.16, 0.4, oh)
            g.box('walls', 'jamb', (x, y, oh / 2), size, hazard if ty in ('dock', 'door') else frame,
                  collision=False)
    if ty == 'gate':                                           # gantry over the gate
        x, y = wall_point(axis, c, oc)
        size = (w + 1.0, 0.4, 0.5) if axis == 'x' else (0.4, w + 1.0, 0.5)
        g.box('walls', 'gantry', (x, y, 7.25), size, frame)
    if neg == pos:
        return
    # sign over the opening on each face, showing the zone on the other side
    sign_w = max(3.0, min(w, 6.0))
    sign_h = sign_w / 2
    bottom = oh + 0.3 if ty != 'gate' else 4.4
    top_limit = h - 0.15 if ty != 'gate' else 7.0
    if bottom + sign_h > top_limit:
        sign_h = top_limit - bottom
        sign_w = 2 * sign_h
    zc = bottom + sign_h / 2
    for side, here, there in ((-1, neg, pos), (1, pos, neg)):
        off = side * (t / 2 + 0.03) if ty != 'gate' else side * 0.23
        face = ('-y' if side < 0 else '+y') if axis == 'x' else ('-x' if side < 0 else '+x')
        tex = 'sign_exit.png' if there == 'outside' else f'sign_{there}.png'
        x, y = wall_point(axis, c, oc, off)
        g.plane('signs', 'door_sign', (x, y, zc), (sign_w, sign_h), texture_material(tex, True), face)
        if ty == 'gate' and here == 'outside':                # speed limit on the gate post
            x, y = wall_point(axis, c, oc - w / 2 - 0.2, side * 0.27)
            g.plane('signs', 'speed_limit', (x, y, 3.0), (1.0, 1.0), texture_material('sign_speed_limit.png'), face)
        if ty in ('door', 'dock') and here != 'outside':
            fo = side * (t / 2 + 0.03)
            # forklift warning on one side of the door
            x, y = wall_point(axis, c, oc + w / 2 + 1.6, fo)
            g.plane('signs', 'forklift_warning', (x, y, 2.4), (1.2, 1.2),
                    texture_material('sign_forklift_warning.png'), face)
            # extinguisher cabinet with its sign on the other side
            x, y = wall_point(axis, c, oc - w / 2 - 1.6, fo)
            g.plane('signs', 'extinguisher_sign', (x, y, 2.3), (0.6, 0.6),
                    texture_material('sign_extinguisher.png'), face)
            x, y = wall_point(axis, c, oc - w / 2 - 1.6, side * (t / 2 + 0.12))
            yaw = {'-y': -PI / 2, '+y': PI / 2, '-x': PI, '+x': 0.0}[face]
            g.model('safety', 'extinguisher_cabinet', (x, y, 0, yaw), collision=False)


def build_building():
    g = Group('large_warehouse_building')
    doors = []
    # Ground: grass, asphalt around the buildings and the floor of each zone
    g.box('floors', 'grass', (350, 225, -0.15), (1400, 1100, 0.2), color_material(COLORS['grass']))
    g.box('floors', 'site', (350, 215, -0.05), (860, 620, 0.06), color_material(COLORS['site']))
    floor_mat = {'warehouse_a': 'concrete', 'warehouse_b': 'concrete', 'warehouse_c': 'concrete',
                 'reception': 'office_floor', 'loading': 'asphalt'}
    for zid, z in ZONES.items():
        for (x0, y0, x1, y1) in z['rects']:
            g.box('floors', f'floor_{zid}', ((x0 + x1) / 2, (y0 + y1) / 2, -0.01),
                  (x1 - x0, y1 - y0, 0.02), color_material(COLORS[floor_mat[zid]]))
    for w in WALLS + PARTITIONS:
        build_wall(g, doors, *w)

    up = lambda zid, x, y, s, yaw=0.0: g.plane(        # noqa: E731
        'markings', 'floor_logo', (x, y, 0.012), (s, s), texture_material(f'floor_{zid}.png'), 'up', yaw)
    # Floor logos (visible from above)
    up('warehouse_a', 100, 314, 20)
    up('warehouse_a', 102.5, 216, 10)
    up('warehouse_b', 238, 356, 18)
    up('warehouse_b', 307.5, 118, 10)
    up('warehouse_c', 500, 60, 20)
    up('warehouse_c', 556, 366, 14)
    up('reception', 300, 438.5, 7, PI)
    up('loading', 335, 52, 16)
    up('loading', 12, 190, 9, -PI / 2)
    up('loading', 190, 85, 9)

    # Facade signs
    big = lambda zid, x, y, z, w, face: g.plane(       # noqa: E731
        'signs', 'facade_sign', (x, y, z), (w, w / 2), texture_material(f'sign_{zid}.png', True), face)
    big('warehouse_a', -0.23, 300, 6.4, 16, '-x')
    big('warehouse_a', 75, 400.23, 6.4, 16, '+y')
    big('warehouse_a', 102.5, 199.77, 8.3, 10, '-y')
    big('warehouse_b', 307.5, 99.77, 8.3, 10, '-y')
    big('warehouse_b', 199.77, 157.5, 8.3, 10, '-x')
    big('warehouse_c', 575, 400.23, 6.4, 16, '+y')
    big('warehouse_c', 700.23, 200, 6.4, 16, '+x')
    big('warehouse_c', 550, -0.23, 6.4, 16, '-y')
    big('warehouse_c', 399.77, 88, 8.3, 10, '-x')
    big('reception', 240, 450.23, 4.1, 5, '+y')
    big('reception', 360, 450.23, 4.1, 5, '+y')

    # Painted lines of the warehouses (main aisles and staging areas)
    for x in (93.6, 106.4):
        line(g, x, 232, x, 396)
    for y in (310.3, 317.7):
        line(g, 4, y, 196, y)
    line(g, 4, 232, 196, 232)
    for y in (139.0, 226.0, 302.0):
        line(g, 204, y, 396, y)
    line(g, 304, 139, 304, 226)
    for y in (125.0, 335.0):
        line(g, 404, y, 696, y)
    line(g, 476, 125, 476, 396)
    line(g, 587, 125, 587, 335)
    line(g, 595, 4, 595, 125, 'green')
    # Charging area of Warehouse C painted in green
    for y in range(15, 106, 7):
        g.box('markings', 'charging_bay', (695.5, y, 0.006), (7.5, 5.4, 0.012),
              color_material((0.12, 0.45, 0.2)), collision=False)
    # Dock bays: yellow lines in front of each dock door, on the truck side
    for (axis, c, a0, a1, h, kind, ops) in WALLS:
        for (oc, w, oh, ty) in ops:
            if ty != 'dock':
                continue
            sgn = -1 if zone_at(*wall_point(axis, c, oc, -1)) == 'loading' else 1
            for side in (-1, 1):
                p0 = wall_point(axis, c, oc + side * 2.6, sgn * 0.3)
                p1 = wall_point(axis, c, oc + side * 2.6, sgn * 10.0)
                line(g, *p0, *p1, 'yellow', 0.15)
                # dock bumpers
                x, y = wall_point(axis, c, oc + side * (w / 2 + 0.25), sgn * 0.3)
                size = (0.3, 0.2, 0.6) if axis == 'x' else (0.2, 0.3, 0.6)
                g.box('walls', 'dock_bumper', (x, y, 1.0), size, color_material(COLORS['black']))
    # Road markings of the truck lanes
    dashed(g, 2, 190, 178, 190)
    dashed(g, 190, 2, 190, 178)
    # Parking in front of the reception
    for row_y, depth in ((455.5, 5.5), (461.0, 5.5)):
        for k in range(105):
            x = 156 + k * 2.75
            if 288 < x < 312:
                continue
            line(g, x, row_y, x, row_y + depth, 'white')
    line(g, 156, 466.5, 444, 466.5, 'white')
    # Truck parking in the yard
    for k in range(11):
        line(g, 312 + k * 4.4, 1, 312 + k * 4.4, 15, 'white')
    # Pedestrian crossing at the main entrance
    for k in range(8):
        g.box('markings', 'crossing', (293.5 + k * 1.8 + 0.5, 461, 0.006), (0.9, 11, 0.012),
              color_material(COLORS['white']), collision=False)

    n = g.write('Structure of the large warehouse: floors, 12 m warehouse walls, 6 m reception '
                'walls, loading zone fence, door openings (all at least 3 m wide) with hazard '
                'jambs, zone signs over every door, facade signs, floor logos, safety signs, '
                'extinguisher cabinets, painted lines and parking. The extinguisher cabinet '
                'meshes are those of the local model extinguisher_cabinet (Fuel model '
                '"Extinguisher cabinet", CC BY 4.0).')
    return n, doors


# ---------------------------------------------------------------------------------------------
# Storage and furniture
# ---------------------------------------------------------------------------------------------
LOAD_COLORS = [(0.62, 0.45, 0.26), (0.55, 0.40, 0.22), (0.70, 0.55, 0.35), (0.85, 0.85, 0.82),
               (0.30, 0.42, 0.62), (0.58, 0.44, 0.30)]


WOOD = (0.58, 0.45, 0.30)


def pallet_load(g, link, x, y, z=0.0, yaw=0.0, max_h=1.2, cluster=None, h=None):
    """Pallet (deck and 3 runners, 1.2 x 1.0 m along the yaw) with a wrapped load on it."""
    c, s_ = math.cos(yaw), math.sin(yaw)
    for dy in (-0.44, 0.0, 0.44):
        g.box(link, 'pallet_runner', (x - s_ * dy, y + c * dy, z + 0.055), (1.2, 0.12, 0.11),
              color_material(WOOD), yaw, collision=False)
    g.box(link, 'pallet_deck', (x, y, z + 0.13), (1.2, 1.0, 0.04), color_material(WOOD), yaw,
          cluster=cluster)
    h = h or rng.uniform(0.6, max_h)
    g.box(link, 'load', (x, y, z + 0.15 + h / 2), (1.14, 0.96, h), color_material(rng.choice(LOAD_COLORS)),
          yaw, cluster=cluster)
    return z + 0.15 + h


def pallet_stack(g, link, x, y, yaw, cluster, levels=2):
    """Block stacked pallets (one or more loads, one on top of the other)."""
    z = 0.0
    for _ in range(rng.randint(1, levels)):
        z = pallet_load(g, link, x, y, z, yaw, cluster=cluster, h=rng.uniform(0.8, 1.1)) + 0.01


def high_bay_field(g, x_start, n_pairs, y_starts, units, skip=lambda x, y: False):
    """Rows of high bay racks (18 m long along y) placed back to back in pairs."""
    pitch = 2 * 2.12 + 3.6
    for k in range(n_pairs):
        for j, xr in enumerate((x_start + k * pitch + 1.06, x_start + k * pitch + 3.18)):
            for ys in y_starts:
                run = 0                         # one collision box per run of contiguous racks
                for u in range(units):
                    y = ys + 9.025 + u * 18.05
                    if skip(xr, y):
                        run += 1
                    else:
                        g.model('racks', 'high_bay_rack', (xr, y, 0, PI * j), cluster=(x_start, k, ys, run))


def staging(g, link, docks, axis, c, sgn, depth, n, fill=0.65):
    """Pallets waiting in front of the dock doors."""
    for oc in docks:
        for col in (-0.7, 0.7):
            for i in range(n):
                if rng.random() > fill:
                    continue
                d = 4.0 + i * 1.35
                x, y = wall_point(axis, c, oc + col, sgn * d)
                key = ('staging', axis, c, oc, col)
                if rng.random() < 0.25:
                    g.model(link, rng.choice(['crate_stack', 'box_pile_d']), (x, y, 0, rng.choice([0, PI])),
                            cluster=key)
                else:
                    pallet_load(g, link, x, y, 0, 0.0 if axis == 'y' else PI / 2, cluster=key)


def build_warehouse_a():
    g = Group('warehouse_a_storage')
    # High bay racks: 2 fields x 11 pairs, 2 blocks of 4 racks along y, with a plaza at the center
    plaza = lambda x, y: abs(x - 100) < 16 and abs(y - 314) < 16     # noqa: E731
    high_bay_field(g, 10.7, 11, (237.8, 318.0), 4, plaza)
    high_bay_field(g, 106.7, 11, (237.8, 318.0), 4, plaza)
    # Staging area in front of the 7 docks
    staging(g, 'goods', (15, 40, 65, 90, 115, 140, 165), 'x', 200, 1, 0, 11)
    # Empty pallet stacks and a box pile along the west wall
    for k in range(6):
        for lvl in range(10):
            g.model('goods', 'pallet_standard', (3.5, 240 + k * 2.0, lvl * 0.15, PI / 2), collision=False)
        g.box('goods', 'pallet_stack_collision', (3.5, 240 + k * 2.0, 0.75), (1.0, 1.2, 1.5),
              color_material((0, 0, 0)), visual=False)
    return g.write('Storage of Warehouse A (high bay storage): 18 m high bay racks in two fields '
                   'separated by a 13 m main aisle, and staged pallets in front of the docks. '
                   'Built from the local models high_bay_rack and pallet_standard.')


def build_warehouse_b():
    g = Group('warehouse_b_storage')
    # Selective pallet racks: 11 pairs of rows, 2 segments of 15 bays (2.64 m)
    for k in range(11):
        for j, y in enumerate((148 + k * 6.54 + 0.76, 148 + k * 6.54 + 2.28)):
            for x0 in (212.2, 256.2):
                for b in range(15):
                    x = x0 + 1.32 + b * 2.64
                    g.model('racks', 'pallet_rack', (x, y, 0, 0), cluster=('rack', k, x0))
                    for z, max_h in ((0.0, 1.2), (1.511, 1.2), (3.035, 1.4)):
                        for s in (-0.62, 0.62):
                            if rng.random() < 0.55:
                                pallet_load(g, 'goods', x + s, y, z, 0.0, max_h, cluster=('load', k, x0))
    # Picking shelves: 17 pairs of rows, 2 segments of 10 shelves (3.92 m)
    for k in range(17):
        for j, y in enumerate((147 + k * 4.36 + 0.44, 147 + k * 4.36 + 1.32)):
            for x0 in (309.0, 352.0):
                for b in range(10):
                    m = 'picking_shelf_d' if (k + b) % 3 else 'picking_shelf_e'
                    g.model('racks', m, (x0 + 1.96 + b * 3.92, y, 0, PI * j), cluster=('shelf', k, x0))
    # Expedition staging in front of the 7 south docks
    staging(g, 'goods', (220, 245, 270, 295, 320, 345, 370), 'x', 100, 1, 0, 18)
    # Order consolidation: rows of storage racks
    for y in (264.0, 272.0, 280.0, 288.0, 296.0):
        for k in range(33):
            if rng.random() < 0.8:
                g.model('goods', 'storage_rack', (214 + k * 2.5, y, 0, 0), cluster=('consolidation', y))
    # Block stacking lanes
    for k in range(13):
        y = 240 + k * 4.5
        if abs(y - 255) < 4:
            continue
        for i in range(33):
            if rng.random() < 0.7:
                if rng.random() < 0.25:
                    m = rng.choice(['crate_stack', 'box_pile_c', 'box_pile_d'])
                    g.model('goods', m, (312 + i * 2.4, y, 0, rng.choice([0, PI])), cluster=('lane', y))
                else:
                    pallet_stack(g, 'goods', 312 + i * 2.4, y, PI / 2, ('lane', y))
    # Packing area: 3 conveyor lines with packing tables on both sides
    for yl in (332.0, 347.0, 362.0):
        for i in range(48):
            g.model('conveyor', 'conveyor_block', (288.25 + i * 0.5, yl, 0, 0), cluster=('conveyor', yl))
        for side in (-1.4, 1.4):
            for i in range(8):
                x = 289.5 + i * 3.0
                g.model('goods', 'table', (x, yl + side, 0, 0), cluster=('tables', yl, side))
                for b in range(rng.randint(1, 3)):
                    g.model('goods', 'cardboard_box', (x - 0.45 + b * 0.5, yl + side, 1.16, 0), collision=False)
    # Shelves with packing material
    for k, y in enumerate((326.0, 334.0, 342.0, 350.0)):
        for b in range(15):
            g.model('racks', 'picking_shelf_e', (331 + 1.96 + b * 3.92, y, 0, PI * (k % 2)), cluster=('pack', y))
    # Storage racks and box piles around the packing logo
    for k in range(8):
        g.model('goods', 'storage_rack', (206, 330 + k * 2.0, 0, PI / 2))
        g.model('goods', 'box_pile_a', (258 + k * 2.6, 322, 0, 0))
    # Outbound pallets along the north wall, leaving free the doors to the reception
    for y in (384.0, 388.5):
        for i in range(98):
            x = 253 + i * 1.4
            if abs(x - 250) < 6 or abs(x - 350) < 6 or rng.random() > 0.8:
                continue
            pallet_stack(g, 'goods', x, y, PI / 2, ('outbound', y, x > 350))
    # Pallets waiting for consolidation
    for y in (236.0, 240.5, 245.0):
        for i in range(58):
            if rng.random() < 0.75:
                pallet_stack(g, 'goods', 214 + i * 1.4, y, PI / 2, ('consolidation_pallets', y))
    return g.write('Storage of Warehouse B (picking, packing and expedition): selective pallet '
                   'racks, picking shelves, order consolidation racks, block stacking lanes, '
                   'packing area with conveyors and tables, and staged pallets in front of the '
                   'docks.')


def build_warehouse_c():
    g = Group('warehouse_c_storage')
    # High bay racks: 2 fields x 12 pairs, 3 blocks of 3 racks along y
    blocks = (150.0, 214.15, 278.3)
    high_bay_field(g, 486.8, 12, blocks, 3)
    high_bay_field(g, 596.7, 12, blocks, 3)
    # Cross docking lanes in front of the docks of the truck yard
    for yd in (20, 45, 70):
        for col in (-0.7, 0.7):
            for i in range(44):
                if rng.random() < 0.8:
                    pallet_load(g, 'goods', 406 + i * 1.4, yd + col, 0, PI / 2, cluster=('xdock', yd, col))
    # Block stacking of crates and boxes
    for i in range(15):
        for j in range(48):
            if rng.random() < 0.5:
                m = rng.choice(['crate_stack', 'box_pile_c', 'box_pile_a', 'large_crate'])
                g.model('goods', m, (532 + i * 4.0, 12 + j * 2.0, 0, 0), cluster=('crates', i))
    # West block stacking lanes, leaving free the aisles in front of the doors to Warehouse B
    y = 131.0
    while y < 392:
        if all(abs(y - d) > 5.5 for d in (140, 230, 314, 375)):
            for i in range(34):
                if rng.random() < 0.15:
                    m = rng.choice(['box_pile_c', 'box_pile_d', 'crate_stack'])
                    g.model('goods', m, (412 + i * 1.6, y, 0, rng.choice([0, PI])), cluster=('west', y))
                elif rng.random() < 0.85:
                    pallet_stack(g, 'goods', 412 + i * 1.6, y, PI / 2, ('west', y), levels=3)
        y += 5.0
    # Maintenance area: charging stations, tool cabinets and racks
    for y in range(15, 106, 7):
        g.model('equipment', 'charging_station', (699.2, y, 0, 0))
    for k in range(30):
        g.model('equipment', 'metal_cabinet', (602 + k * 0.85, 0.45, 0, 0), cluster='cabinets')
    for k in range(10):
        g.model('equipment', 'storage_rack', (602 + k * 1.4, 8, 0, 0), cluster='tool_racks')
    # Quality control / returns: tables with boxes
    for yt in (352.0, 362.0, 380.0):
        for i in range(25):
            x = 610 + i * 3.2
            g.model('goods', 'table', (x, yt, 0, 0), cluster=('qc', yt))
            if rng.random() < 0.7:
                g.model('goods', 'cardboard_box', (x, yt, 1.16, rng.uniform(-0.3, 0.3)), collision=False)
    # Returns: pallet lanes north of the high bay racks, with a cross aisle at y = 375
    for y in (344.0, 348.5, 353.0, 357.5, 362.0, 366.5, 384.0, 388.5):
        for i in range(80):
            x = 483 + i * 1.4
            if (547 < x < 565 and y > 357) or (abs(x - 520) < 3 and abs(y - 356) < 3) or rng.random() > 0.7:
                continue
            pallet_stack(g, 'goods', x, y, PI / 2, ('returns', y, x > 556))
    return g.write('Storage of Warehouse C (bulk storage and cross docking): high bay racks, '
                   'block stacking lanes, cross docking lanes in front of the yard docks, a '
                   'maintenance and charging area and a quality control area.')


def build_reception():
    g = Group('reception_furniture')
    L = 'furniture'
    # R1: lockers and break room (x 150-200)
    for x in (152.5, 158.5, 164.5):
        g.model(L, 'locker_big', (x, 437.5, 0, 0))
    for y in (436.0, 438.3):
        g.model(L, 'kitchen_countertop', (199.35, y, 0, 0), cluster='kitchen')
    for y in (441.0, 441.7):
        g.model(L, 'fridge', (199.4, y, 0, 0), cluster='kitchen')
    for x in (178.0, 179.0, 180.0, 181.0):
        g.model(L, 'vending_machine', (x, 449.4, 0, -PI / 2), cluster='vending')
    for i in range(3):
        for j in range(4):
            cx, cy = 178 + i * 5.0, 414 + j * 5.0
            g.model(L, 'cafe_table', (cx, cy, 0, 0), cluster=('cafe', i, j))
            for dx, dy, yaw in ((0.8, 0, 0.0), (-0.8, 0, PI), (0, 0.8, PI / 2), (0, -0.8, -PI / 2)):
                g.model(L, 'chair', (cx + dx, cy + dy, 0, yaw), cluster=('cafe', i, j))
    for x in (185.0, 195.0):
        g.model(L, 'trash_bin', (x, 449.6, 0, 0))

    def desk(x, y, yaw, cluster):
        """Office desk with the chair on the user side (-x of the desk)."""
        g.model(L, 'office_desk', (x, y, 0, yaw), cluster=cluster)
        ux, uy = -math.cos(yaw) * 0.95, -math.sin(yaw) * 0.95
        g.model(L, 'office_chair_black' if rng.random() < 0.5 else 'office_chair_grey',
                (x + ux, y + uy, 0, yaw + PI / 2 + rng.uniform(-0.3, 0.3)), cluster=cluster)

    def desk_benches(xs):
        for xc in xs:
            for y in (413.5, 415.8, 418.1, 420.4, 434.0, 436.3, 438.6, 440.9, 443.2):
                desk(xc - 0.45, y, 0.0, ('bench', xc, y > 427))   # back to back, users outside
                desk(xc + 0.45, y, PI, ('bench', xc, y > 427))

    # R2: open office (x 200-260)
    desk_benches((207, 217, 227, 237, 247))
    for k in range(20):
        g.model(L, 'white_cabinet', (202 + k * 0.95, 449.55, 0, 0), cluster='cabinets_r2')
    # R3: lobby with the reception counter (x 260-340)
    for x in (297.74, 300.0, 302.26):
        g.model(L, 'office_desk', (x, 426, 0, PI / 2), cluster='counter')
        g.model(L, 'office_chair_black', (x, 424.9, 0, PI), cluster='counter')
    for cx, cy in ((272, 440), (284, 416), (316, 416), (328, 440)):
        for m, dx, dy, yaw in (('coffee_table', 0, 0, 0), ('sofa', 1.5, 0, 0), ('sofa', -1.5, 0, PI),
                               ('mini_sofa', 0, 1.4, PI / 2), ('mini_sofa', 0, -1.4, -PI / 2)):
            g.model(L, m, (cx + dx, cy + dy, 0, yaw), cluster=('lounge', cx, cy))
    for k in range(10):
        g.model(L, 'bookshelf', (263 + k * 0.95, 449.6, 0, 0), cluster='books_w')
        g.model(L, 'bookshelf', (328 + k * 0.95, 449.6, 0, 0), cluster='books_e')
    for x in (295.5, 304.5):
        g.model(L, 'trash_bin', (x, 425.5, 0, 0))
    for k in range(6):
        g.model(L, 'visitor_chair', (264 + k * 0.9, 411.5, 0, PI), cluster='waiting_w')
        g.model(L, 'visitor_chair', (331 + k * 0.9, 411.5, 0, PI), cluster='waiting_e')
    # R4: open office and meeting area (x 340-400)
    desk_benches((347, 357, 367))
    for i in range(3):
        for j in range(2):
            g.model(L, 'cafe_table', (384 + i * 0.92, 438 + j * 0.92, 0, 0), cluster='meeting')
    for i in range(3):
        g.model(L, 'chair', (384 + i * 0.92, 436.75, 0, -PI / 2), cluster='meeting')
        g.model(L, 'chair', (384 + i * 0.92, 440.15, 0, PI / 2), cluster='meeting')
    g.model(L, 'chair', (382.3, 438.46, 0, PI), cluster='meeting')
    g.model(L, 'chair', (387.5, 438.46, 0, 0), cluster='meeting')
    # R5: management offices and archive (x 400-450)
    for x in (410, 425, 440):
        for y in (418, 432, 444):
            for m, dx, dy, yaw in (('office_desk', 0, 0, 0), ('office_chair_black', -0.95, 0, PI / 2),
                                   ('visitor_chair', 1.0, -0.6, -PI / 2), ('visitor_chair', 1.0, 0.6, -PI / 2)):
                g.model(L, m, (x + dx, y + dy, 0, yaw), cluster=('office', x, y))
    for k in range(30):
        g.model(L, 'white_cabinet', (449.55, 412 + k * 0.95, 0, -PI / 2), cluster='archive')
    for k in range(12):
        g.model(L, 'bookshelf', (403 + k * 0.95, 449.6, 0, 0), cluster='books_r5')
    # Exit signs over the doors of the reception building
    for x in (175, 250, 350, 425):
        g.model('signs', 'exit_sign', (x, 400.25, 3.55, 0), collision=False)
    for x in (300, 170):
        g.model('signs', 'exit_sign', (x, 449.75, 3.25, 0), collision=False)
    return g.write('Furniture of the reception and offices building: lockers and break room, '
                   'open offices, lobby with the reception counter and waiting areas, meeting '
                   'area and management offices.')


def build_loading_props():
    g = Group('loading_zone_props')
    L = 'props'
    # Lamp posts along the truck lanes and the yard (the arm points to -y in the model)
    for x in range(20, 180, 40):
        g.model(L, 'lamp_post', (x, 180.6, 0, PI))
    for y in range(20, 180, 40):
        g.model(L, 'lamp_post', (180.6, y, 0, PI / 2))
    for x in range(220, 400, 40):
        if abs(x - 300) > 10:
            g.model(L, 'lamp_post', (x, 0.6, 0, PI))
    # Jersey barriers protecting the fence corners and the gates
    for (x, y, yaw) in ((183, 183, PI / 4), (5, 183, 0), (183, 5, PI / 2), (205, 3, 0),
                        (395, 3, 0), (203, 50, PI / 2), (203, 95, PI / 2)):
        g.model(L, 'jersey_barrier', (x, y, 0, yaw))
    # Stacks of Euro pallets along the west fence of the yard
    for k in range(8):
        x, y = 204 + (k % 2) * 1.2, 36 + (k // 2) * 1.6
        for lvl in range(12):
            g.model(L, 'euro_pallet', (x, y, 0.07 + lvl * 0.14, 0), collision=False)
        g.box(L, 'pallet_stack_collision', (x, y, 0.84), (0.8, 1.2, 1.68), color_material((0, 0, 0)), visual=False)
    # Cones around the containers and a working area
    for (x, y) in ((242, 8), (258, 8), (242, 28), (258, 28), (236, 18), (264, 18),
                   (330, 30), (340, 30), (330, 40), (340, 40)):
        g.model(L, 'construction_cone', (x, y, 0, 0))
    return g.write('Props of the loading zone: lamp posts, jersey barriers, stacks of Euro '
                   'pallets and traffic cones.')


def write_charging_station():
    d = MODELS_DIR / 'charging_station'
    d.mkdir(parents=True, exist_ok=True)
    grey, dark = color_material((0.55, 0.57, 0.6)), color_material((0.15, 0.15, 0.17))
    green = color_material((0.1, 0.8, 0.3), emissive=(0.1, 0.8, 0.3))
    parts = [('base', '0 0 0.025 0 0 0', '1.0 1.2 0.05', dark),
             ('column', '0.3 0 0.8 0 0 0', '0.4 0.7 1.6', grey),
             ('screen', '0.09 0 1.3 0 0 0', '0.02 0.4 0.25', green),
             ('connector', '0.06 0 0.5 0 0 0', '0.08 0.3 0.3', dark)]
    vis = ''.join(f'<visual name="{n}"><pose>{p}</pose><geometry><box><size>{s}</size></box></geometry>{m}</visual>'
                  for n, p, s, m in parts)
    (d / 'model.sdf').write_text(
        '<?xml version="1.0" ?>\n<sdf version="1.9">\n  <model name="charging_station">\n'
        '    <static>true</static>\n    <link name="link">\n'
        '      <collision name="collision"><pose>0.3 0 0.8 0 0 0</pose><geometry><box><size>0.4 0.7 1.6'
        '</size></box></geometry></collision>\n      ' + vis + '\n    </link>\n  </model>\n</sdf>\n')
    (d / 'model.config').write_text(
        f'<?xml version="1.0"?>\n<model>\n  <name>charging_station</name>\n  <version>1.0</version>\n'
        f'  <sdf version="1.9">model.sdf</sdf>\n  <author>\n    <name>{AUTHOR[0]}</name>\n'
        f'    <email>{AUTHOR[1]}</email>\n  </author>\n  <description>\n    Wall charging station for '
        f'forklifts and mobile robots, made of primitive shapes. The front (screen) faces -x.\n'
        f'  </description>\n</model>\n')


# ---------------------------------------------------------------------------------------------
# World
# ---------------------------------------------------------------------------------------------
# Individual models: (model, name, x, y, z, yaw). Trucks: cab at +x. Forklift: forks at +y.
INCLUDES = [
    # Trucks backed up to the docks and driving on the truck lanes
    ('truck_box', 'truck_box_a1', 40, 197.5, 0, -PI / 2),
    ('truck_box', 'truck_box_a2', 115, 197.5, 0, -PI / 2),
    ('truck_delivery', 'truck_delivery_a1', 165, 196.9, 0, -PI / 2),
    ('truck_box', 'truck_box_b1', 197.5, 145, 0, PI),
    ('truck_delivery', 'truck_delivery_b1', 196.9, 120, 0, PI),
    ('truck_box', 'truck_box_b2', 245, 97.5, 0, -PI / 2),
    ('truck_box', 'truck_box_b3', 320, 97.5, 0, -PI / 2),
    ('truck_delivery', 'truck_delivery_b2', 270, 96.9, 0, -PI / 2),
    ('truck_delivery', 'truck_delivery_b3', 370, 96.9, 0, -PI / 2),
    ('truck_box', 'truck_box_c1', 397.5, 20, 0, PI),
    ('truck_delivery', 'truck_delivery_c1', 396.9, 70, 0, PI),
    ('truck_delivery', 'truck_delivery_lane_1', 70, 186, 0, PI),
    ('truck_box', 'truck_box_lane_1', 186, 60, 0, PI / 2),
    # Trucks waiting in the truck parking of the yard
    ('truck_box', 'truck_box_parking_1', 314.2, 8, 0, PI / 2),
    ('truck_delivery', 'truck_delivery_parking_1', 318.6, 8, 0, PI / 2),
    ('truck_box', 'truck_box_parking_2', 327.4, 8, 0, PI / 2),
    ('truck_box', 'truck_box_parking_3', 336.2, 8, 0, PI / 2),
    ('truck_delivery', 'truck_delivery_parking_2', 340.6, 8, 0, PI / 2),
    ('truck_delivery', 'truck_delivery_parking_3', 349.4, 8, 0, PI / 2),
    # Containers and dumpsters in the yard
    ('cargo_container_40ft', 'container_1', 250, 12, 0, 0),
    ('cargo_container_40ft', 'container_2', 250, 18, 0, 0),
    ('cargo_container_40ft', 'container_3', 250, 24, 0, 0),
    ('cargo_container_40ft', 'container_4', 225, 60, 0, 0),
    ('cargo_container_40ft', 'container_5', 225, 66, 0, 0),
    ('dumpster', 'dumpster_1', 214, 1.2, 0, 0),
    ('dumpster', 'dumpster_2', 220, 1.2, 0, 0),
    ('dumpster', 'dumpster_3', 386, 1.2, 0, 0),
    # Forklifts
    ('forklift', 'forklift_a1', 30, 226, 0, 0),
    ('forklift', 'forklift_a2', 80, 228, 0, PI),
    ('forklift', 'forklift_a3', 130, 226, 0, 0),
    ('forklift', 'forklift_a4', 100, 270, 0, 0),
    ('forklift', 'forklift_a5', 100, 355, 0, PI),
    ('forklift', 'forklift_b1', 232, 132, 0, 0),
    ('forklift', 'forklift_b2', 333, 132, 0, PI / 2),
    ('forklift', 'forklift_b3', 254, 182, 0, PI / 2),
    ('forklift', 'forklift_b4', 270, 342, 0, -PI / 2),
    ('forklift', 'forklift_c1', 480, 80, 0, PI / 2),
    ('forklift', 'forklift_c2', 587, 200, 0, 0),
    ('forklift', 'forklift_c3', 476, 300, 0, PI),
] + [('forklift', f'forklift_charging_{k}', 697.4, 15 + 7 * k, 0, PI / 2) for k in (0, 1, 3, 4, 6, 9)] + [
    # Pallet jacks, hand carts and hand trucks
    ('pallet_jack', 'pallet_jack_a1', 20, 224, 0, 0),
    ('pallet_jack_yellow', 'pallet_jack_a2', 145, 224, 0, PI / 2),
    ('pallet_jack', 'pallet_jack_a3', 100, 236, 0, PI),
    ('pallet_jack_yellow', 'pallet_jack_b1', 225, 128, 0, 0),
    ('pallet_jack', 'pallet_jack_b2', 345, 128, 0, 0),
    ('pallet_jack_yellow', 'pallet_jack_b3', 300, 236, 0, PI / 2),
    ('pallet_jack', 'pallet_jack_b4', 254, 160, 0, 0),
    ('pallet_jack_yellow', 'pallet_jack_c1', 420, 90, 0, 0),
    ('pallet_jack', 'pallet_jack_c2', 450, 32, 0, PI / 2),
    ('pallet_jack_yellow', 'pallet_jack_c3', 587, 180, 0, 0),
    ('hand_cart', 'hand_cart_b1', 276, 330, 0, 0),
    ('hand_cart', 'hand_cart_b2', 320, 355, 0, PI / 2),
    ('hand_cart', 'hand_cart_b3', 280, 376, 0, 0),
    ('hand_cart', 'hand_cart_c1', 520, 356, 0, 0),
    ('hand_cart', 'hand_cart_c2', 530, 380, 0, PI / 2),
    ('handtruck', 'handtruck_b1', 285, 343, 0, 0),
    ('handtruck', 'handtruck_b2', 318, 340, 0, PI),
    ('handtruck', 'handtruck_b3', 324, 380, 0, 0),
    ('handtruck', 'handtruck_a1', 60, 227, 0, 0),
    ('handtruck', 'handtruck_a2', 150, 228, 0, PI),
    # Wheelie bins
    ('wheelie_bin', 'wheelie_bin_a1', 5, 226, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_a2', 195, 390, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_b1', 205, 390, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_b2', 395, 330, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_b3', 395, 108, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_c1', 695, 130, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_c2', 695, 395, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_c3', 405, 395, 0, PI / 2),
    ('wheelie_bin', 'wheelie_bin_yard_1', 228, 1.2, 0, 0),
    ('wheelie_bin', 'wheelie_bin_yard_2', 380, 1.2, 0, 0),
]
CARS = ['hatchback', 'hatchback_blue', 'hatchback_red', 'pickup', 'suv']


def parked_cars():
    cars = []
    k = 0
    for row_y, yaw in ((458.25, -PI / 2), (463.75, PI / 2)):
        for i in range(104):
            x = 156 + i * 2.75 + 1.375
            if 288 < x < 312 or rng.random() > 0.22:
                continue
            k += 1
            cars.append((rng.choice(CARS), f'car_{k:02d}', x, row_y, 0, yaw))
    return cars


WORLD_HEADER = """<?xml version="1.0" ?>
<!-- Generated by scripts/generate_world.py. Large warehouse built from the plan of the
     facility: Warehouse A (200 x 200 m), Warehouse B (200 x 300 m), Warehouse C (300 x 400 m),
     Recepcion y oficinas (300 x 50 m) and the truck loading zone. -->
<sdf version="1.9">
  <world name="{name}">
    <!-- The Bullet collision detector of DART scales much better than FCL with the
         thousands of static collision boxes of the warehouse -->
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
      <dart>
        <collision_detector>bullet</collision_detector>
      </dart>
    </physics>

    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
    <plugin filename="gz-sim-navsat-system" name="gz::sim::systems::NavSat"/>

    <gravity>0 0 -9.8</gravity>
    <magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>
    <atmosphere type="adiabatic"/>

    <scene>
      <grid>false</grid>
      <ambient>0.55 0.55 0.55 1</ambient>
      <background>0.7 0.8 0.9 1</background>
      <shadows>true</shadows>
    </scene>

    <gui fullscreen="0">
      <camera name="user_camera">
        <pose>350 -260 260 0 0.75 1.5708</pose>
      </camera>
    </gui>

    <!-- Fictional location close to Mostoles (Madrid) -->
    <spherical_coordinates>
      <surface_model>EARTH_WGS84</surface_model>
      <world_frame_orientation>ENU</world_frame_orientation>
      <latitude_deg>40.3280</latitude_deg>
      <longitude_deg>-3.8870</longitude_deg>
      <elevation>660</elevation>
    </spherical_coordinates>

    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 100 0 0 0</pose>
      <diffuse>0.85 0.85 0.82 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.4 0.3 -0.85</direction>
    </light>
"""


def include(model, name, x, y, z, yaw):
    return (f'    <include>\n      <uri>model://{model}</uri>\n      <name>{name}</name>\n'
            f'      <pose>{pose_str([x, y, z, 0, 0, yaw])}</pose>\n    </include>\n')


def write_world(groups):
    s = WORLD_HEADER.format(name=WORLD_NAME)
    s += '\n    <!-- Structure, storage and furniture (grouped static models in world coordinates) -->\n'
    for gname in groups:
        s += include(gname, gname, 0, 0, 0, 0)
    sections = [('Vehicles, containers and dumpsters', lambda m: m[0] in (
                    'truck_box', 'truck_delivery', 'cargo_container_40ft', 'dumpster')),
                ('Handling equipment', lambda m: m[0] in (
                    'forklift', 'pallet_jack', 'pallet_jack_yellow', 'hand_cart', 'handtruck')),
                ('Wheelie bins', lambda m: m[0] == 'wheelie_bin')]
    for title, cond in sections:
        s += f'\n    <!-- {title} -->\n'
        for m in INCLUDES:
            if cond(m):
                s += include(*m)
    s += '\n    <!-- Cars in the parking of the reception -->\n'
    for m in parked_cars():
        s += include(*m)
    s += '  </world>\n</sdf>\n'
    WORLDS_DIR.mkdir(exist_ok=True)
    (WORLDS_DIR / f'{WORLD_NAME}.sdf').write_text(s)


def write_zones_yaml(doors):
    out = [f'# Zones and doors of {WORLD_NAME} (generated by scripts/generate_world.py)',
           '# Rectangles are [x_min, y_min, x_max, y_max] in meters, in the world frame.',
           '# Door centers are [x, y]; width and height in meters (gates have no lintel).',
           f'world: {WORLD_NAME}', 'zones:']
    for zid, z in ZONES.items():
        out.append(f'  {zid}:')
        out.append(f'    name: "{z["name"]}"')
        out.append('    rects:')
        for r in z['rects']:
            out.append(f'      - [{", ".join(f(v) for v in r)}]')
    out.append(f'doors:  # {len(doors)} openings')
    for d in doors:
        h = 'null' if d['height'] is None else f(d['height'])
        out.append(f'  - {{type: {d["type"]}, center: [{f(d["center"][0])}, {f(d["center"][1])}], '
                   f'width: {f(d["width"])}, height: {h}, connects: [{d["connects"][0]}, {d["connects"][1]}]}}')
    CONFIG_DIR.mkdir(exist_ok=True)
    (CONFIG_DIR / f'{WORLD_NAME}_zones.yaml').write_text('\n'.join(out) + '\n')


def main():
    write_charging_station()
    counts = {}
    counts['large_warehouse_building'], doors = build_building()
    counts['warehouse_a_storage'] = build_warehouse_a()
    counts['warehouse_b_storage'] = build_warehouse_b()
    counts['warehouse_c_storage'] = build_warehouse_c()
    counts['reception_furniture'] = build_reception()
    counts['loading_zone_props'] = build_loading_props()
    write_world(list(counts))
    write_zones_yaml(doors)
    for k, v in counts.items():
        print(f'{k:28s} {v:6d} visuals')
    print(f'{"total":28s} {sum(counts.values()):6d} visuals, {len(doors)} doors')


if __name__ == '__main__':
    main()
