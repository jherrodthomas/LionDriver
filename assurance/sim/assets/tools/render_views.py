"""Offscreen Panda3D renders of the Corolla GLB: three-quarter, side, top. Usage: python render_views.py assurance/sim/assets/1450755-gltf-extended.glb assurance/sim/figures  (needs panda3d and panda3d-gltf)
Documentation renders: the paint is recoloured to a neutral silver and glass made translucent for legibility."""
import os, sys
from panda3d.core import (loadPrcFileData, AmbientLight, DirectionalLight, Vec4, Point3, AntialiasAttrib, OrthographicLens,
                          PNMImage, Filename, CardMaker, TransparencyAttrib, LColor)
loadPrcFileData("", "window-type offscreen\naudio-library-name null\nload-display pandagl\nwin-size 1600 1000\n"
                    "framebuffer-multisample 1\nmultisamples 8\nnotify-level warning\nnotify-level-gltf error\ntextures-power-2 none")
from direct.showbase.ShowBase import ShowBase
glb, outdir = sys.argv[1], sys.argv[2]; os.makedirs(outdir, exist_ok=True)
base = ShowBase()
base.render.setShaderAuto()
base.setBackgroundColor(0.965, 0.962, 0.955, 1)
base.render.setAntialias(AntialiasAttrib.MMultisample)
car = base.loader.loadModel(Filename.fromOsSpecific(glb)); car.reparentTo(base.render)
lo, hi = car.getTightBounds(); car.setScale(4.656 / (hi.y - lo.y))
lo, hi = car.getTightBounds(); ctr = (lo + hi) * 0.5; L = hi.y - lo.y
# material overrides for legibility
GLASS = {"glass_white", "glass_red", "glass_orange", "glass_white_2", "glass", "liense_glass"}
for mat in car.findAllMaterials():
    n = mat.getName()
    if n == "body":
        mat.setBaseColor(LColor(0.56, 0.58, 0.61, 1)); mat.setMetallic(0.1); mat.setRoughness(0.45)
    if n in GLASS:
        c = mat.getBaseColor(); mat.setBaseColor(LColor(c[0] * 0.75, c[1] * 0.8, c[2] * 0.85, 0.35)); mat.setMetallic(0.0); mat.setRoughness(0.05)
for gn in car.findAllMatches("**/+GeomNode"):
    mats = {gs.getAttrib(0) for i in range(gn.node().getNumGeoms()) for gs in [gn.node().getGeomState(i)] if gs.hasAttrib(0)}
    for np_ in [gn]:
        name = np_.getName().lower()
        if any(k in name for k in ("window", "glass", "lenses", "interier_glass")):
            np_.setTransparency(TransparencyAttrib.MAlpha); np_.setColorScale(0.55, 0.6, 0.68, 0.45)
cm = CardMaker("ground"); cm.setFrame(-8, 8, -8, 8); g = base.render.attachNewNode(cm.generate()); g.setP(-90); g.setZ(lo.z - 0.003)
g.setColor(0.86, 0.855, 0.845, 1)
amb = AmbientLight("amb"); amb.setColor(Vec4(0.30, 0.30, 0.33, 1)); base.render.setLight(base.render.attachNewNode(amb))
for hpr, col in (((35, -50, 0), (0.95, 0.92, 0.86, 1)), ((-120, -25, 0), (0.35, 0.37, 0.42, 1)), ((160, -70, 0), (0.25, 0.25, 0.25, 1))):
    d = DirectionalLight("d"); d.setColor(Vec4(*col)); n = base.render.attachNewNode(d); n.setHpr(*hpr); base.render.setLight(n)
ASPECT = 1.6
def shoot(name, pos, look, ortho_w=None):
    cam = base.cam
    if ortho_w:
        lens = OrthographicLens(); lens.setFilmSize(ortho_w, ortho_w / ASPECT); lens.setNearFar(0.1, 200); cam.node().setLens(lens)
    else:
        lens = base.camLens; lens.setFov(30); lens.setNearFar(0.1, 200); lens.setAspectRatio(ASPECT); cam.node().setLens(lens)
    cam.setPos(pos); cam.lookAt(look)
    for _ in range(3): base.graphicsEngine.renderFrame()
    img = PNMImage(); base.win.getScreenshot(img)
    f = os.path.join(outdir, name); print(name, "written" if img.write(Filename.fromOsSpecific(f)) else "FAILED")
c = Point3(ctr.x, ctr.y, ctr.z - 0.1)
shoot("corolla-e210-render-three-quarter.png", Point3(ctr.x + 7.6, ctr.y - 8.4, ctr.z + 2.8), c)   # front is -y
shoot("corolla-e210-render-side.png", Point3(ctr.x + 60, ctr.y, ctr.z + 0.2), Point3(ctr.x, ctr.y, ctr.z + 0.2), ortho_w=L * 1.15)
shoot("corolla-e210-render-top.png", Point3(ctr.x, ctr.y, ctr.z + 60), Point3(ctr.x, ctr.y + 0.001, ctr.z), ortho_w=L * 1.15 * ASPECT)
