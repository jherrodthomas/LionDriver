// The comma 3X behind a sun-loaded windshield, and the safety MCU next to its SoC (WP-A-03 DFI-04, TSR-509).
// D: the device heat model's steady results (assurance/sim/results/mcu-heat.json). The page interpolates them and
// eases between settings for display; every temperature on screen is the model's.
const { THREE, Lab, MAT, GEO, clamp, lerp, approach, table, fmt } = window.LabKit
const deg = Math.PI / 180

/* The real thing, as the heat model has it (assurance/sim/thermal/params.yaml, estimates until T1 measures them):
   comma 3X box 120 x 60 x 25 mm; the SoC under an aluminium spreader; the panda STM32H725 lower right; a fan on the
   right face; road cameras on the face toward the glass; a bracket to the windshield, raked 25.8 deg from horizontal
   on the Corolla E210 (measured on the 3D model, sim/figures/corolla-e210-geometry.json). */
const lab = new Lab({
  prompt: 'the comma 3X behind a sun-loaded windshield, and the safety MCU next to its SoC',
  no: 1, title: 'comma 3X', sub: 'behind the windshield, in the sun',
  size: 0.42, ground: -0.04,
  view: { az: -150, el: 12, dist: 1.25, target: [0, 0.16, -0.05] },
  cut: { a: [0, 0, -1], b: [0, 1, 0], center: [0, 0.165, -0.06], reach: 0.2 },
  pills: ['Synthetic (DSR-12)', 'Device heat model', 'No credit'],
})

// windshield (with its black band at the top edge) and dash
const RAKE = 25.8 * deg
const glass = new THREE.Group(); glass.position.set(0, 0.195, 0); glass.rotation.set(RAKE, 0, 0)
lab.add(glass, { name: 'Windshield', explode: [0, 0.12, 0] })
lab.mesh(GEO.rbox(0.62, 0.006, 0.9, 0.002), MAT.glass({ color: [0.62, 0.8, 0.74], transmission: 0.7, roughness: 0.05, thickness: 0.006 }),
  { name: 'Glass', parent: glass, xray: 'shell' })
lab.mesh(GEO.rbox(0.62, 0.0065, 0.12, 0.002), MAT.satin({ color: [0.02, 0.02, 0.022] }), { name: 'Frit band', parent: glass, pos: [0, 0, -0.39] })
lab.mesh(GEO.rbox(0.62, 0.04, 0.55, 0.008), MAT.satin({ color: [0.05, 0.05, 0.055] }), { name: 'Dashboard', pos: [0, -0.02, 0.15] })

// mount: adhesive pad on the glass, bracket down to the device's top
const glassY = (z) => 0.195 - z * Math.tan(RAKE) - 0.003 / Math.cos(RAKE)
lab.mesh(GEO.rbox(0.06, 0.002, 0.03, 0.0008), MAT.rubber(), { name: 'Mount pad', pos: [0, glassY(-0.06) - 0.001, -0.06], rot: [RAKE, 0, 0], explode: [0, 0.08, 0] })
lab.mesh(GEO.rbox(0.05, glassY(-0.06) - 0.002 - 0.195, 0.018, 0.003), MAT.plastic(),
  { name: 'Mount bracket', pos: [0, (0.195 + glassY(-0.06) - 0.002) / 2, -0.06], explode: [0, 0.06, 0] })

// the device: local frame = params.yaml (x across, y up, z from the screen to the glass)
const dev = new THREE.Group(); dev.position.set(-0.06, 0.135, -0.0725); lab.add(dev, { name: 'comma 3X' })
const P = (o, p) => ({ parent: dev, ...o, pos: p })
lab.mesh(GEO.rbox(0.12, 0.06, 0.025, 0.004), MAT.plastic({ color: [0.06, 0.06, 0.065] }), P({ name: 'Housing', xray: 'shell', explode: [0, 0.055, 0] }, [0.06, 0.03, 0.0125]))
lab.mesh(GEO.rbox(0.104, 0.05, 0.0012, 0.0006), MAT.glass({ color: [0.2, 0.22, 0.25], roughness: 0.02 }), P({ name: 'Screen', explode: [0, 0, -0.1] }, [0.06, 0.03, -0.0006]))
lab.mesh(GEO.rbox(0.108, 0.05, 0.0016, 0.0005), MAT.paint({ color: [0.04, 0.16, 0.09], clearcoat: 0.3 }), P({ name: 'Board' }, [0.06, 0.03, 0.008]))
const socMat = MAT.ceramic({ color: [0.12, 0.12, 0.13] }), mcuMat = MAT.ceramic({ color: [0.12, 0.12, 0.13] })
const S = D.sources
const soc = lab.mesh(GEO.rbox(S.soc.size[0], S.soc.size[1], S.soc.size[2], 0.0006), socMat, P({ name: 'SoC', explode: [0, 0, 0.012] }, [S.soc.centre[0], S.soc.centre[1], 0.0108]))
lab.mesh(GEO.rbox(0.06, 0.04, 0.002, 0.0008), MAT.aluminiumMachined(), P({ name: 'Heat spreader', explode: [0, 0, 0.05] }, [0.052, 0.032, 0.0138]))
const mcu = lab.mesh(GEO.rbox(S.mcu.size[0], S.mcu.size[1], S.mcu.size[2], 0.0005), mcuMat, P({ name: 'panda MCU', explode: [0, 0, -0.03] }, [S.mcu.centre[0], S.mcu.centre[1], 0.0057]))
// fan on the right face (x1), axis along x
const fanHub = new THREE.Group(); fanHub.position.set(0.1125, 0.03, 0.0125)
const fan = new THREE.Mesh(GEO.rotor({ count: 7, axis: 'y', r0: 0.003, r1: 0.0105, chord: [0.007, 0.009], thick: 0.1, camber: 0.05, twist: 0.4, pitch: 0.5 }), MAT.plastic({ color: [0.1, 0.1, 0.11] }))
fan.rotation.z = Math.PI / 2; fanHub.add(fan)
lab.add(fanHub, { name: 'Fan', parent: dev, explode: [0.06, 0, 0] })
lab.mesh(GEO.tube(0.0118, 0.0110, 0.012), MAT.plastic(), P({ name: 'Fan shroud', rot: [0, 0, Math.PI / 2], explode: [0.06, 0, 0] }, [0.1125, 0.03, 0.0125]))
for (const [i, x] of [[0, 0.045], [1, 0.06], [2, 0.075]]) {
  lab.mesh(GEO.disc(0.0045, 0.003), MAT.glass({ color: [0.15, 0.17, 0.2] }), P({ name: `Camera ${i + 1}`, rot: [Math.PI / 2, 0, 0], explode: [0, 0, 0.04] }, [x, 0.045, 0.0262]))
}

// temperature colour: the kit's heat glow starts near 750 K, so 40-100 C get their own scale
const ramp = [[40, [0.1, 0.25, 0.55]], [70, [0.95, 0.62, 0.15]], [96, [0.9, 0.12, 0.08]]]
function tint(m, T) {
  let c = ramp[0][1]
  for (let i = 1; i < ramp.length; i++) if (T >= ramp[i - 1][0]) { const [a, ca] = ramp[i - 1], [b, cb] = ramp[i]; const t = clamp((T - a) / (b - a)); c = ca.map((v, k) => lerp(v, cb[k], t)) }
  m.emissive.setRGB(...c); m.emissiveIntensity = 0.9
}

// the numbers: interpolated from the committed results, nothing computed here
const targets = (a, broken) => {
  const s = broken ? D.setups.fan_stalled : D.setups.as_built
  return { soc: table(D.air, s.soc, a), mcu: table(D.air, s.mcu_block, a) + D.rise.nominal }
}
lab.hero({ label: 'Hottest SoC point', unit: '°C', max: 110 })
const air = lab.slider({ id: 'air', label: 'Cabin air at the mount', min: D.air[0], max: D.air[D.air.length - 1], value: 35, unit: '°C', ends: ['Spring', 'Parked in July'] })
let Ts = 70, Tm = 55, fanSpin = 0
// read by check_pages.mjs; settle() jumps the eased display to the results, for stills
window.__ld = { targets, data: D, settle: () => { const t = targets(air.value, lab.broken); Ts = t.soc; Tm = t.mcu } }
lab.label(soc, 'SoC', { value: () => `${fmt(Ts)} °C` })
lab.label(mcu, 'panda MCU junction', { value: () => `${fmt(Tm)} °C` })
lab.label(fanHub, 'Fan', { at: [0.002, 0.012, 0], value: () => (lab.broken ? 'stalled' : '100 %') })
lab.onTick((dt) => {
  const t = targets(air.value, lab.broken)
  Ts = approach(Ts, t.soc, 1.2, dt); Tm = approach(Tm, t.mcu, 1.2, dt)
  tint(socMat, Ts); tint(mcuMat, Tm - D.rise.nominal)
  fanSpin = approach(fanSpin, lab.broken ? 0 : 1, lab.broken ? 2.5 : 0.6, dt)
  fanHub.rotation.x += dt * fanSpin * 18          // spin shown slowed
  const over = Ts > D.soc_limit
  lab.setHero(Ts, { state: over ? 'overheated: soft disable' : (lab.broken ? 'fan stalled' : 'driving, fan on'),
    bad: over, sub: `MCU junction <b>${fmt(Tm)} °C</b> · host stops at ${fmt(D.soc_limit)} °C` })
})

lab.breakIt({ label: 'Stall the fan', run: () => {}, reset: () => {} })
lab.how('Every temperature here is the device heat model\'s (FEniCSx, cross-checked with FiPy): '
  + '<code>assurance/sim/results/mcu-heat.json</code>, steady state at the end of a long drive, the windshield 15 K above the '
  + 'cabin air and the sun on the device. The page interpolates the committed results and eases between settings; the '
  + 'fan\'s spin is shown slowed. Inputs are estimates until the device is measured (T1). '
  + '<b>Synthetic (DSR-12), design aid, no evidence credit.</b>',
  ['T_SoC = interp(cabin air, mcu-heat.json)', `T_j,MCU = T_block + P·Θ_JB  (${D.rise.low}–${D.rise.high} K over the board, DS13311)`,
   `host stops above ${D.soc_limit} °C on the SoC (hardwared.py)`, `TSR-509 candidate: trip at a DTS reading ≤ ${D.trip} °C`])
lab.autoFilm({ runBeat: 'Turn up the cabin heat.', runSub: 'The SoC follows the device model\'s results.', sliderTo: 0.55,
  breakBeat: 'Stall the fan.', breakSub: 'The SoC passes 96 °C; the MCU stays in range.' })
lab.start()
