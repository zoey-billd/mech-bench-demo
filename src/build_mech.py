"""Mechanical-rig acceptance bench, built only from bpy.

One master custom property (``CTRL["deploy"]`` 0..1) drives four mechanisms
through drivers, and every mechanism is wrapped in a Limit constraint that is
deliberately asked to travel further than it is allowed to -- so the clip on
screen is the constraint doing its job, not a hand-authored pose.

Rendered in two passes because a rigid-body ball cannot be armed mid-sim:
    pass A  deploy sweep          frames 1..110
    pass B  ball dropped in drawer frames 1..60   (deploy pinned to 1)

Usage:
    blender -b -P build_mech.py -- [--quick]
"""
import json
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
QUICK = "--quick" in ARGS
NORENDER = "--no-render" in ARGS
# portrait build for short-form video: same scene, same bindings, same numbers.
# only the camera framing and the output resolution change.
VERTICAL = "--vertical" in ARGS

# set MECH_OUT to relocate the whole pipeline; the default assumes a D: drive
DEFAULT_OUT = os.path.join("D:\\", "mech_demo", "vert") if VERTICAL else os.path.join("D:\\", "mech_demo")
OUT = os.environ.get("MECH_OUT") or DEFAULT_OUT
FRAMES_A = os.path.join(OUT, "frames_a")
FRAMES_B = os.path.join(OUT, "frames_b")
RES_X, RES_Y, FPS = (1080, 1920, 30) if VERTICAL else (1920, 1080, 30)
D2R = math.pi / 180.0
BALL_R = 0.055

# ---------------------------------------------------------------- materials
def make_mat(name, rgb, metallic, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m


MATS = {}


def build_materials():
    MATS["frame"] = make_mat("M_Frame", (0.070, 0.076, 0.088), 0.70, 0.44)
    MATS["panel"] = make_mat("M_Panel", (0.40, 0.43, 0.47), 0.85, 0.34)
    MATS["drawer"] = make_mat("M_Drawer", (0.78, 0.44, 0.10), 0.20, 0.52)
    MATS["mast"] = make_mat("M_Mast", (0.62, 0.66, 0.70), 0.95, 0.26)
    MATS["bracket"] = make_mat("M_Bracket", (0.10, 0.52, 0.50), 0.35, 0.40)
    MATS["ball"] = make_mat("M_Ball", (0.94, 0.95, 0.97), 0.0, 0.26)
    MATS["beacon"] = make_mat("M_Beacon", (0.85, 0.12, 0.10), 0.0, 0.35)
    MATS["bench"] = make_mat("M_Bench", (0.030, 0.034, 0.042), 0.30, 0.60)


# ---------------------------------------------------------------- geometry
def box(name, size, geo_offset, mat, loc=(0, 0, 0), bevel=0.004, parent=None):
    """Axis-aligned box.

    ``loc`` is always local to ``parent`` (Blender's default) and ``geo_offset``
    shifts the mesh away from the object origin -- that is how every hinge and
    slider gets its origin sitting exactly on its own axis of motion.
    """
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector(size), verts=bm.verts)
    if bevel > 0.0:
        bmesh.ops.bevel(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
                        offset=bevel, segments=2, profile=0.5, affect="EDGES",
                        clamp_overlap=True)
    bmesh.ops.translate(bm, vec=Vector(geo_offset), verts=bm.verts)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    obj.data.materials.append(mat)
    if parent is not None:
        obj.parent = parent
    return obj


def sphere(name, radius, mat, world_loc):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=radius)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = world_loc
    obj.data.materials.append(mat)
    return obj


# ---------------------------------------------------------------- driver kit
def drive(obj, path, index, expression, ctrl):
    fc = obj.driver_add(path, index)
    fc.driver.type = "SCRIPTED"
    var = fc.driver.variables.new()
    var.name = "d"
    var.type = "SINGLE_PROP"
    var.targets[0].id = ctrl
    var.targets[0].data_path = '["deploy"]'
    fc.driver.expression = expression
    return fc


def ramp(lo, hi):
    """Normalised 0..1 slice of the master sweep, clamped at both ends.

    Kept inside Blender's simple-expression subset so the drivers still
    evaluate with Python auto-execution disabled.
    """
    return "min(max((d-%.3f)/%.3f,0.0),1.0)" % (lo, hi - lo)


def limit_rot(obj, axis, lo_deg, hi_deg):
    """Clamp one axis only. Locking the others would drag the object's own
    rest rotation to zero, which is a silent teleport for anything that is not
    already axis-aligned."""
    c = obj.constraints.new("LIMIT_ROTATION")
    c.name = "Limit Rotation"
    c.owner_space = "LOCAL"
    setattr(c, "use_limit_" + axis, True)
    setattr(c, "min_" + axis, lo_deg * D2R)
    setattr(c, "max_" + axis, hi_deg * D2R)
    return c


def limit_loc(obj, axis, lo, hi):
    """Same rule as limit_rot: one axis, untouched elsewhere."""
    c = obj.constraints.new("LIMIT_LOCATION")
    c.name = "Limit Location"
    c.owner_space = "LOCAL"
    setattr(c, "use_min_" + axis, True)
    setattr(c, "use_max_" + axis, True)
    setattr(c, "min_" + axis, lo)
    setattr(c, "max_" + axis, hi)
    return c


# ---------------------------------------------------------------- the bench
# Chassis bays (all metres). Walls are separate panels so the bays stay open
# and an interference test between a moving part and the frame is meaningful.
X0, X1 = -0.30, 0.30
Y0, Y1 = -0.22, 0.22
Z0, Z1 = 0.00, 0.56
T = 0.02

SCENE = {}


def build_frame():
    root = bpy.data.objects.new("CHASSIS", None)
    root.empty_display_size = 0.06
    bpy.context.scene.collection.objects.link(root)
    P = MATS["frame"]

    parts = [
        ("plinth", (0.68, 0.50, 0.03), (0, 0, 0.015), (0, 0, 0.015)),   # bench base
        ("floor", (X1 - X0, Y1 - Y0, T), (0, (Y0 + Y1) / 2, Z0 + T / 2), (0, 0, 0)),
        ("roof", (X1 - X0, Y1 - Y0, T), (0, (Y0 + Y1) / 2, Z1 - T / 2), (0, 0, 0)),
        ("wall_l", (T, Y1 - Y0, Z1 - Z0), (X0 + T / 2, (Y0 + Y1) / 2, (Z0 + Z1) / 2), (0, 0, 0)),
        ("wall_r", (T, Y1 - Y0, Z1 - Z0), (X1 - T / 2, (Y0 + Y1) / 2, (Z0 + Z1) / 2), (0, 0, 0)),
        ("wall_b", (X1 - X0, T, Z1 - Z0), (0, Y1 - T / 2, (Z0 + Z1) / 2), (0, 0, 0)),
        ("divider", (T, Y1 - Y0, Z1 - Z0 - 2 * T), (-0.01, (Y0 + Y1) / 2, (Z0 + Z1) / 2), (0, 0, 0)),
        ("shelf", (X1 - 0.00, Y1 - Y0, T), (0.15, (Y0 + Y1) / 2, 0.30), (0, 0, 0)),
    ]
    out = []
    for name, size, center, _ in parts:
        o = box(name, size, (0, 0, 0), P, center)
        out.append(o)
    return root, out


def build_door():
    """Revolute hinge on Z at the left edge of the left bay."""
    hinge = Vector((-0.28, -0.225, 0.0))
    door = box("DOOR", (0.255, 0.020, 0.500), (0.1300, 0.0, 0.280), MATS["panel"], hinge)
    box("DOOR_HANDLE", (0.014, 0.030, 0.120), (0.235, -0.024, 0.280),
        MATS["drawer"], (0, 0, 0), bevel=0.003, parent=door)
    return door


def build_drawer():
    """Prismatic slider: an open-top tray so a rigid body can actually land in it."""
    origin = Vector((0.14, 0.0, 0.33))
    D = MATS["drawer"]
    tray = box("DRAWER", (0.26, 0.36, 0.020), (0.0, 0.0, 0.010), D, origin, bevel=0.003)
    # no front wall on purpose: it would hide the tray floor from the camera
    walls = [
        ("dwall_back", (0.26, 0.012, 0.180), (0.0, 0.174, 0.100)),
        ("dwall_l", (0.012, 0.360, 0.180), (-0.124, 0.0, 0.100)),
        ("dwall_r", (0.012, 0.360, 0.180), (0.124, 0.0, 0.100)),
    ]
    for name, size, off in walls:
        box(name, size, off, D, (0, 0, 0), parent=tray)
    # a low lip, not a full front: a tall face hides the tray interior from
    # the camera and the drop-test ball would never be visible
    box("DRAWER_FACE", (0.272, 0.014, 0.060), (0.0, -0.207, 0.030), MATS["panel"],
        (0, 0, 0), parent=tray)
    return tray


def build_mast():
    """Two-stage telescoping mast, stage 2 riding on stage 1.

    Two rules make telescope read as a telescope instead of three floating
    blocks: every section is long enough to stay overlapped at full travel, and
    every origin stays at the base with the geometry offset instead of the
    origin travelling -- a driver *replaces* location.z, so an origin parked at
    0.22 m would snap to 0 the moment the driver kicks in.
    """
    base = Vector((-0.25, 0.02, Z1))  # far left keeps it clear of the drop-test line
    fixture = box("MAST_FIXTURE", (0.09, 0.09, 0.100), (0, 0, 0.050), MATS["frame"], base)
    s1 = box("MAST_STAGE1", (0.058, 0.058, 0.400), (0, 0, 0.140), MATS["mast"],
             (0, 0, 0), parent=fixture)
    s2 = box("MAST_STAGE2", (0.044, 0.044, 0.340), (0, 0, 0.270), MATS["mast"],
             (0, 0, 0), parent=s1)
    box("MAST_BEACON", (0.050, 0.050, 0.026), (0, 0, 0.453), MATS["beacon"],
        (0, 0, 0), parent=s2)
    return fixture, s1, s2


def build_bracket():
    """Two-link folding arm standing up off the roof.

    On the roof rather than in a bay: the drawer slides straight through the
    lower bay, which hid the whole mechanism from the camera.
    """
    hinge = Vector((-0.10, -0.16, Z1))
    mount = box("BRACKET_MOUNT", (0.070, 0.060, 0.026), (0, 0, 0.013), MATS["frame"], hinge)
    # link 1 lies flat along -Y on the roof, so a -80 deg rotation about X
    # stands it straight up instead of swinging it into the chassis
    l1 = box("BRACKET_LINK1", (0.036, 0.300, 0.028), (0, -0.150, 0.030), MATS["bracket"],
             (0, 0, 0), parent=mount)
    l2 = box("BRACKET_LINK2", (0.030, 0.260, 0.024), (0, -0.130, 0.0), MATS["bracket"],
             (0, -0.300, 0.026), parent=l1)
    box("BRACKET_PAD", (0.070, 0.012, 0.060), (0, 0, 0), MATS["panel"],
        (0, -0.260, 0), parent=l2)
    return mount, l1, l2


# ---------------------------------------------------------------- camera / light
def build_stage():
    bpy.ops.mesh.primitive_plane_add(size=30.0, location=(0, 0.2, -0.001))
    ground = bpy.context.object
    ground.name = "Ground"

    gm = bpy.data.materials.new("M_Ground")
    gm.use_nodes = True
    nt = gm.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.72
    bsdf.inputs["Metallic"].default_value = 0.0
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (1.0 / 0.2, 1.0 / 0.2, 1.0 / 0.2)
    checker = nt.nodes.new("ShaderNodeTexChecker")
    checker.inputs["Color1"].default_value = (0.016, 0.019, 0.024, 1.0)
    checker.inputs["Color2"].default_value = (0.042, 0.047, 0.056, 1.0)
    checker.inputs["Scale"].default_value = 1.0
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], checker.inputs["Vector"])
    nt.links.new(checker.outputs["Color"], bsdf.inputs["Base Color"])
    ground.data.materials.append(gm)

    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 34 if VERTICAL else 40
    if VERTICAL:
        # 9:16 fits the sensor to the short side, so the vertical FOV drives the
        # framing; a wider lens keeps the 1.2 m bench inside 1080 px of width
        cam_data.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    if VERTICAL:
        # aim low: the bench sits in the upper 2/3 and the readout stack owns
        # the bottom of the frame instead of covering the mechanism
        # pull back so the whole bench (1.43 m tall including the mast) fits the
        # 1320 px band above the readout grid, instead of running under it
        target = Vector((-0.05, -0.06, 0.70))
        cam.location = Vector((1.65, -2.42, 1.32))
    else:
        target = Vector((0.02, -0.06, 0.62))
        cam.location = Vector((1.95, -2.60, 1.70))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    # push the subject off-centre so the HUD column on the right stays clear
    cam.data.shift_x = -0.06 if VERTICAL else 0.115
    cam.data.shift_y = 0.02

    def area(name, energy, size, loc):
        li = bpy.data.lights.new(name, type="AREA")
        li.energy = energy
        li.size = size
        o = bpy.data.objects.new(name, li)
        o.location = loc
        o.rotation_euler = (target - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(o)

    area("Key", 340, 2.2, (1.5, -2.1, 2.4))
    area("Fill", 110, 3.4, (-2.2, -1.3, 1.1))
    area("Rim", 240, 1.6, (-1.0, 2.0, 1.9))

    world = bpy.data.worlds.new("W")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.020, 0.023, 0.030, 1.0)
    bg.inputs[1].default_value = 0.5
    bpy.context.scene.world = world


def render_settings(out_dir):
    scn = bpy.context.scene
    scn.render.engine = "BLENDER_EEVEE"
    scn.render.resolution_x = RES_X
    scn.render.resolution_y = RES_Y
    scn.render.resolution_percentage = 100
    scn.render.fps = FPS
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
    scn.eevee.taa_render_samples = 16
    for attr, value in (("use_raytracing", False), ("use_shadows", True)):
        if hasattr(scn.eevee, attr):
            setattr(scn.eevee, attr, value)
    scn.render.image_settings.file_format = "PNG"
    scn.render.filepath = os.path.join(out_dir, "f_")


# ---------------------------------------------------------------- measure
def bvh_world(obj, dg):
    ev = obj.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    faces = [list(p.vertices) for p in me.polygons]
    tree = BVHTree.FromPolygons(verts, faces, all_triangles=False, epsilon=0.0)
    ev.to_mesh_clear()
    return tree


def measured_angle(obj, dg, axis_index=2):
    """Angle of the constrained object about its own hinge axis.

    Read from the evaluated world matrix against the evaluated parent, not from
    rotation_euler: a Limit constraint clamps the *output*, and that clamp is
    exactly what we want to prove.
    """
    ev = obj.evaluated_get(dg)
    rel = ev.matrix_world.to_3x3()
    if obj.parent is not None:
        rel = obj.parent.evaluated_get(dg).matrix_world.to_3x3().inverted() @ rel
    return math.degrees(rel.to_euler("XYZ")[axis_index])


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.frame_start = 1
    build_materials()
    build_stage()

    frame_root, frame_parts = build_frame()
    door = build_door()
    drawer = build_drawer()
    mast_fix, mast1, mast2 = build_mast()
    br_mount, br_l1, br_l2 = build_bracket()

    # Blender 5.2 only clamps a LOCAL-space Limit Rotation when the object has a
    # parent; left rootless the constraint is silently a no-op. Rigging the door
    # onto the chassis is both physically right and the fix for that.
    door.parent = frame_root

    # ---- master control ------------------------------------------------
    ctrl = bpy.data.objects.new("CTRL", None)
    ctrl.empty_display_size = 0.10
    bpy.context.scene.collection.objects.link(ctrl)
    ctrl["deploy"] = 0.0
    ctrl.id_properties_ui("deploy").update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0,
                                           description="master deploy 0..1")
    ctrl.keyframe_insert('["deploy"]', frame=1)
    ctrl.keyframe_insert('["deploy"]', frame=12)
    ctrl["deploy"] = 1.0
    ctrl.keyframe_insert('["deploy"]', frame=110)

    # ---- door: driver asks for 140 deg, constraint allows 105 ----------
    drive(door, "rotation_euler", 2, "-%s*%.4f" % (ramp(0.00, 0.34), 140 * D2R), ctrl)
    limit_rot(door, "z", -105.0, 0.0)

    # ---- drawer: driver asks for 0.42 m, constraint allows 0.30 --------
    drive(drawer, "location", 1, "-%s*%.4f" % (ramp(0.18, 0.58), 0.42), ctrl)
    limit_loc(drawer, "y", -0.30, 0.0)

    # ---- mast: both stages overshoot their limit -----------------------
    drive(mast1, "location", 2, "%s*%.4f" % (ramp(0.38, 0.76), 0.24), ctrl)
    limit_loc(mast1, "z", 0.0, 0.16)
    drive(mast2, "location", 2, "%s*%.4f" % (ramp(0.52, 0.92), 0.22), ctrl)
    limit_loc(mast2, "z", 0.0, 0.14)

    # ---- bracket: fold past its stop -----------------------------------
    drive(br_l1, "rotation_euler", 0, "-%s*%.4f" % (ramp(0.44, 0.86), 95 * D2R), ctrl)
    limit_rot(br_l1, "x", -80.0, 0.0)
    drive(br_l2, "rotation_euler", 0, "%s*%.4f" % (ramp(0.58, 0.98), 145 * D2R), ctrl)
    limit_rot(br_l2, "x", 0.0, 120.0)

    # ---- pass A: deploy sweep + measurement ----------------------------
    render_settings(FRAMES_A)
    scn = bpy.context.scene
    scn.frame_end = 110
    os.makedirs(FRAMES_A, exist_ok=True)

    series = {"door": [], "drawer": [], "mast": [], "bracket1": [], "bracket2": [], "deploy": []}
    pairs = [("DOOR", "floor"), ("DOOR", "wall_l"), ("DRAWER", "shelf"),
             ("DRAWER", "DOOR"), ("BRACKET_LINK1", "roof"), ("BRACKET_LINK2", "MAST_STAGE1")]
    hits, checked = [], 0

    for f in range(1, 111):
        scn.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        series["deploy"].append(round(ctrl["deploy"], 4))
        series["door"].append(round(measured_angle(door, dg, 2), 2))
        series["drawer"].append(round(
            (drawer.evaluated_get(dg).matrix_world.translation.y - 0.0) * 1000.0, 1))  # mm
        top = mast2.evaluated_get(dg).matrix_world @ Vector((0, 0, 0.440))
        series["mast"].append(round((top.z - (Z1 + 0.440)) * 1000.0, 1))  # mm above rest
        series["bracket1"].append(round(measured_angle(br_l1, dg, 0), 2))
        series["bracket2"].append(round(measured_angle(br_l2, dg, 0), 2))

        if f % 4 == 1 or f in (110,):
            trees = {}
            for a, b in pairs:
                for n in (a, b):
                    if n not in trees:
                        trees[n] = bvh_world(bpy.data.objects[n], dg)
                checked += 1
                n_hit = len(trees[a].overlap(trees[b]))
                if n_hit:
                    hits.append({"frame": f, "pair": "%s/%s" % (a, b), "faces": n_hit})

    data = {
        "fps": FPS,
        "pass_a": 110,
        "pass_b": 60,
        "series": series,
        "interference": {"checked": checked, "hits": hits},
        "spec": [
            {"id": "door", "label": "HINGE DOOR", "kind": "REVOLUTE", "axis": "Z",
             "range": "0 - 105 deg", "input": "140 deg", "unit": "deg"},
            {"id": "drawer", "label": "SLIDE TRAY", "kind": "PRISMATIC", "axis": "Y",
             "range": "0 - 300 mm", "input": "420 mm", "unit": "mm"},
            {"id": "mast", "label": "TELESCOPIC MAST", "kind": "PRISMATIC x2", "axis": "Z",
             "range": "0 - 300 mm", "input": "460 mm", "unit": "mm"},
            {"id": "bracket1", "label": "FOLD BRACKET A", "kind": "REVOLUTE", "axis": "X",
             "range": "-80 - 0 deg", "input": "95 deg", "unit": "deg"},
            {"id": "bracket2", "label": "FOLD BRACKET B", "kind": "REVOLUTE", "axis": "X",
             "range": "0 - 120 deg", "input": "145 deg", "unit": "deg"},
        ],
    }
    print("INTERFERENCE checked=%d hits=%d" % (checked, len(hits)))
    for h in hits[:8]:
        print("  HIT", h)

    if QUICK:
        scn.frame_set(78)
        quick = os.path.join(OUT, "quick_a.png")
        scn.render.filepath = quick
        bpy.ops.render.render(write_still=True)
        scn.render.filepath = os.path.join(FRAMES_A, "f_")
        print("QUICK", quick)
    elif NORENDER:
        scn.frame_set(110)
        dg = bpy.context.evaluated_depsgraph_get()
        for name in ("DOOR", "DRAWER", "MAST_STAGE2", "BRACKET_LINK1", "BRACKET_LINK2"):
            o = bpy.data.objects[name]
            w = o.evaluated_get(dg).matrix_world.translation
            print("REST %-14s (%.3f %.3f %.3f)" % (name, w.x, w.y, w.z))
        print("PASS A skipped (no-render)")
    else:
        bpy.ops.render.render(animation=True)
        print("PASS A RENDERED")

    # ---- pass B: rigid-body ball into the open tray --------------------
    # Pin the master at 1 so the tray stays out while the ball falls. Clearing
    # the animation is simpler and more reliable than rewriting every key.
    ctrl.animation_data_clear()
    ctrl["deploy"] = 1.0

    bpy.ops.rigidbody.world_add()
    rbw = scn.rigidbody_world
    rbw.substeps_per_frame = 40
    rbw.solver_iterations = 60
    rbw.use_split_impulse = True
    rbw.time_scale = 0.4  # 0.4x so the 0.85 m fall reads at 30 fps

    ball = sphere("BALL", BALL_R, MATS["ball"], (0.14, -0.30, 1.02))

    def rigid(obj, kind, shape, mass=1.0, friction=0.6, restitution=0.1):
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.rigidbody.object_add(type=kind)
        obj.rigid_body.collision_shape = shape
        obj.rigid_body.mass = mass
        obj.rigid_body.friction = friction
        obj.rigid_body.restitution = restitution
        # default margin is ~4 cm; that reads as a ball hovering over the tray
        obj.rigid_body.use_margin = True
        obj.rigid_body.collision_margin = 0.002

    rigid(ball, "ACTIVE", "SPHERE", mass=0.6, restitution=0.25)
    # convex hull on the tray rather than a box proxy: the beveled rim is the
    # surface the ball actually touches, and a box proxy sits 10 mm inside it
    rigid(drawer, "PASSIVE", "CONVEX_HULL")
    for o in (bpy.data.objects["floor"], bpy.data.objects["plinth"]):
        rigid(o, "PASSIVE", "BOX")
    bpy.context.view_layer.update()
    print("PASS B tray at (%.3f %.3f %.3f)  ball at (%.3f %.3f %.3f)"
          % (tuple(drawer.matrix_world.translation) + tuple(ball.matrix_world.translation)))

    # swing the camera round for the drop test: from the wide angle the mast and
    # the falling ball land on the same screen column, and the tray interior is
    # hidden behind its own rim
    cam = bpy.context.scene.camera
    if VERTICAL:
        tgt = Vector((0.15, -0.26, 0.40))
        cam.location = Vector((0.86, -2.18, 1.12))
    else:
        tgt = Vector((0.15, -0.26, 0.52))
        cam.location = Vector((0.95, -2.35, 1.22))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()

    bpy.context.scene.frame_end = 60
    os.makedirs(FRAMES_B, exist_ok=True)
    render_settings(FRAMES_B)

    trail, path = [], []
    for f in range(1, 61):
        scn.frame_set(f)
        p = ball.matrix_world.translation
        trail.append(round(p.z, 4))
        path.append([round(p.x, 3), round(p.y, 3), round(p.z, 3)])
        if NORENDER and f % 5 == 1:
            print("  f%02d ball (%.3f %.3f %.3f)" % (f, p.x, p.y, p.z))
    floor_top = 0.35             # top face of the tray floor
    rest_z = floor_top + BALL_R  # ball centre when it sits on that floor
    worst = min(trail[8:]) if len(trail) > 8 else min(trail)
    data["ball"] = {"trail": trail, "path": path, "floor_top": floor_top,
                    "rest_z": round(rest_z, 4),
                    "penetration_mm": round((rest_z - worst) * 1000.0, 2),
                    "settle_z": trail[-1]}

    if QUICK:
        scn.frame_set(45)
        scn.render.filepath = os.path.join(OUT, "quick_b.png")
        bpy.ops.render.render(write_still=True)
        scn.render.filepath = os.path.join(FRAMES_B, "f_")
        print("QUICK B", scn.render.filepath)
    elif NORENDER:
        print("PASS B skipped (no-render)")
    else:
        bpy.ops.render.render(animation=True)
        print("PASS B RENDERED")

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "mech_data.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "mech_bench.blend"))
    print("DATA written; ball settle z=%.4f" % trail[-1])


main()
