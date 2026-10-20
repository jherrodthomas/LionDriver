/* Top-down scene kit for the browser: the canvas twin of scenekit.py.
 *
 * Same road, car, marks and pills as the generated scene figures, for pages that animate a scene live (mockups,
 * explorers). Draw in scene units: frame() scales the canvas so one unit is one unit of the SVG scenes.
 *   full scene  SK.W x SK.H (280 x 130)         lanes 30 wide, centre line at SK.CENTRE_LINE
 *   strip       SK.W x SK.STRIP_H (280 x 80)    the same road cropped to its lanes; stripRoad()
 *   large scene SK.LARGE_W x SK.LARGE_H         the full scene scaled by SK.LARGE_K (the STPA, TARA and FSC cards); largeRoad()
 * Text and pills keep their reading size; they are not scaled with the large scene.
 *
 * The constants block below is written by `python3 scenekit.py --js` and checked in CI (test_scenekit.py), so the
 * palette and geometry cannot drift from the SVG kit. The drawing functions are a hand port of scenekit.py; change
 * both together.
 *
 * Usage: load it with a script element (or inline it; it contains no closing script tag), then
 * scenekit.frame(canvas, SK.W, SK.H), scenekit.straightRoad(ctx), ... No dependencies.
 */
(function (root) {
"use strict";

/* constants: written by scenekit.py --js; do not edit */
const SK = {
  "INK": "#0F172A",
  "GRASS": "#C9DDBA",
  "VERGE": "#B9C7A6",
  "ASPHALT": "#565E69",
  "PAINT": "#F8FAFC",
  "ARROW": "#E5E7EB",
  "EGO": "#DC2626",
  "EGO_EDGE": "#450A0A",
  "OTHER": "#9CA3AF",
  "OTHER_EDGE": "#4B5563",
  "STOPPED": "#94A3B8",
  "HAZARD_LAMP": "#F59E0B",
  "GLASS": "#1F2937",
  "WHEEL": "#111827",
  "LAMP": "#FDE68A",
  "REQ": "#16A34A",
  "PERF": "#DC2626",
  "REQ_S": "#4ADE80",
  "PERF_S": "#F87171",
  "FAULT": "#FBBF24",
  "CALLOUT": "#FEF08A",
  "BADGE": {
    "bad": [
      "#7F1D1D",
      "#FEE2E2",
      "#FCA5A5"
    ],
    "ok": [
      "#14532D",
      "#DCFCE7",
      "#4ADE80"
    ],
    "info": [
      "#1E293B",
      "#E2E8F0",
      "#94A3B8"
    ],
    "drv": [
      "#1E3A8A",
      "#DBEAFE",
      "#93C5FD"
    ]
  },
  "W": 280,
  "H": 130,
  "HALF_LANE": 15,
  "TOP_EDGE": 39,
  "CENTRE_LINE": 69,
  "BOTTOM_EDGE": 99,
  "OTHER_LANE": 54,
  "EGO_LANE": 84,
  "CAR_L": 22,
  "STRIP_H": 80,
  "STRIP_DY": -29,
  "LARGE_W": 460,
  "LARGE_H": 250,
  "LARGE_K": 2.1,
  "LARGE_DY": -20,
  "DUR": 6,
  "DRIVE": 0.8
};
/* end constants */

const FONT = 'Inter, "Segoe UI", Helvetica, Arial, sans-serif';

// ---------------------------------------------------------------- canvas

/** Scale the canvas to its CSS width, keep the scene's aspect ratio, and draw in scene units from then on. */
function frame(canvas, sw, sh) {
  const w = canvas.getBoundingClientRect().width || sw, dpr = Math.min(root.devicePixelRatio || 1, 2), h = w * sh / sw;
  canvas.style.height = h + "px";
  canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
  const ctx = canvas.getContext("2d"), s = w / sw;
  ctx.setTransform(dpr * s, 0, 0, dpr * s, 0, 0);
  return { ctx, w: sw, h: sh, s: 1, px: s };
}

function poly(ctx, pts, close) {
  ctx.beginPath();
  pts.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  if (close) ctx.closePath();
}

function line(ctx, x1, y1, x2, y2, color, width, dash, alpha) {
  ctx.save();
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.setLineDash(dash || []);
  if (dash && dash.offset) ctx.lineDashOffset = dash.offset;
  if (alpha !== undefined) ctx.globalAlpha = alpha;
  ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke(); ctx.restore();
}

// ---------------------------------------------------------------- road

function directionArrow(ctx, x, y, angle = 0, k = 1) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle); ctx.scale(k, k); ctx.globalAlpha = 0.55; ctx.fillStyle = SK.ARROW;
  poly(ctx, [[-6, -2], [2, -2], [2, -4.5], [8, 0], [2, 4.5], [2, 2], [-6, 2]], true); ctx.fill(); ctx.restore();
}

/** straight_road(): grass, verge, asphalt, edge lines and the dashed centre line. dashOffset scrolls the centre line. */
function straightRoad(ctx, { arrowY = SK.OTHER_LANE, edgeRight = true, markings = true, width = SK.W, faded = false, dashOffset = 0 } = {}) {
  ctx.fillStyle = SK.GRASS; ctx.fillRect(0, 0, width, SK.H);
  ctx.fillStyle = SK.VERGE; ctx.fillRect(0, 32, width, 74);
  ctx.fillStyle = SK.ASPHALT; ctx.fillRect(0, 35, width, 68);
  const a = faded ? 0.35 : 1;
  if (markings) {
    if (edgeRight) line(ctx, 0, SK.BOTTOM_EDGE, width, SK.BOTTOM_EDGE, SK.PAINT, 1.5, null, a);
    line(ctx, 0, SK.TOP_EDGE, width, SK.TOP_EDGE, SK.PAINT, 1.5, null, a);
    const dash = [9, 9]; dash.offset = -dashOffset;
    line(ctx, 0, SK.CENTRE_LINE, width, SK.CENTRE_LINE, SK.PAINT, 1.3, dash, a);
  }
  directionArrow(ctx, 26, arrowY);
}

/** strip_road(): the straight road cropped to SK.W x SK.STRIP_H; draw on it with the strip coordinates (lanes at 25 / 55). */
function stripRoad(ctx, opts = {}) {
  ctx.save(); ctx.translate(0, SK.STRIP_DY); straightRoad(ctx, opts); ctx.restore();
}

/** large_road(): the straight road in the large scene (lane lines at 62 / 125 / 188). */
function largeRoad(ctx, opts = {}) {
  ctx.fillStyle = SK.GRASS; ctx.fillRect(0, 0, SK.LARGE_W, SK.LARGE_H);
  ctx.save(); ctx.translate(0, SK.LARGE_DY); ctx.scale(SK.LARGE_K, SK.LARGE_K);
  straightRoad(ctx, Object.assign({}, opts, { width: SK.LARGE_W / SK.LARGE_K, dashOffset: (opts.dashOffset || 0) / SK.LARGE_K }));
  ctx.restore();
}

/** curved_road(): two lanes along any centre line; edge(k) returns the points offset k from the ego lane centre. */
function curvedRoad(ctx, edge, { arrow = true } = {}) {
  const hl = SK.HALF_LANE;
  ctx.fillStyle = SK.GRASS; ctx.fillRect(0, 0, SK.W, SK.H);
  ctx.lineJoin = "round";
  [hl + 4, -3 * hl - 4].forEach(k => { ctx.strokeStyle = SK.VERGE; ctx.lineWidth = 7; poly(ctx, edge(k)); ctx.stroke(); });
  ctx.fillStyle = SK.ASPHALT; poly(ctx, edge(hl + 4).concat(edge(-3 * hl - 4).reverse()), true); ctx.fill();
  [hl, -3 * hl].forEach(k => { ctx.strokeStyle = SK.PAINT; ctx.lineWidth = 1.5; poly(ctx, edge(k)); ctx.stroke(); });
  ctx.save(); ctx.strokeStyle = SK.PAINT; ctx.lineWidth = 1.3; ctx.setLineDash([9, 9]); poly(ctx, edge(-hl)); ctx.stroke(); ctx.restore();
  if (arrow) { const c = edge(0), [x0, y0] = c[5], [x1, y1] = c[6]; directionArrow(ctx, x1, y1, Math.atan2(y1 - y0, x1 - x0)); }
}

/** single_lane_road(): one lane with edge lines along a polyline; k scales it like the scene. */
function singleLaneRoad(ctx, pts, k = 1) {
  const hl = SK.HALF_LANE;
  ctx.save(); ctx.lineJoin = "round";
  [[SK.VERGE, hl + 7.5], [SK.ASPHALT, hl + 4], [SK.PAINT, hl + 0.75], [SK.ASPHALT, hl - 0.75]].forEach(([c, r]) => {
    ctx.strokeStyle = c; ctx.lineWidth = 2 * r * k; poly(ctx, pts); ctx.stroke();
  });
  ctx.restore();
}

// ---------------------------------------------------------------- cars (22 x 10 plus wheels, facing +x, origin at the centre)

function rrect(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }

function carBody(ctx, body, stroke = SK.INK) {
  ctx.fillStyle = SK.WHEEL;
  [-8.5, 4.5].forEach(x => [-6, 3.6].forEach(y => { rrect(ctx, x, y, 4.5, 2.4, 1); ctx.fill(); }));
  rrect(ctx, -11, -5, 22, 10, 3.5); ctx.fillStyle = body; ctx.fill(); ctx.strokeStyle = stroke; ctx.lineWidth = 0.9; ctx.stroke();
  ctx.save(); ctx.fillStyle = SK.GLASS;
  ctx.globalAlpha = 0.75; poly(ctx, [[2.5, -4], [6.5, -3.2], [6.5, 3.2], [2.5, 4]], true); ctx.fill();
  ctx.globalAlpha = 0.6; poly(ctx, [[-6.5, -3.6], [-8.5, -3], [-8.5, 3], [-6.5, 3.6]], true); ctx.fill(); ctx.restore();
  ctx.fillStyle = SK.LAMP; ctx.fillRect(10, -4.2, 1.2, 2); ctx.fillRect(10, 2.2, 1.2, 2);
}

function brakeLights(ctx) { ctx.fillStyle = SK.PERF_S; ctx.fillRect(-12, -4.4, 1.6, 2.4); ctx.fillRect(-12, 2, 1.6, 2.4); }
function hazardLamps(ctx) { ctx.fillStyle = SK.HAZARD_LAMP; ctx.fillRect(-12, -5.5, 2, 2); ctx.fillRect(-12, 3.5, 2, 2); }

function ghostBody(ctx, stroke = SK.REQ_S) {
  ctx.save(); rrect(ctx, -11, -5, 22, 10, 3.5); ctx.strokeStyle = stroke; ctx.lineWidth = 1.3; ctx.setLineDash([3, 2]); ctx.stroke(); ctx.restore();
}

/** A car at (x, y) heading angle (radians). kind: "ego", "other", "stopped", "ghost" or "start" (the faded start). */
function car(ctx, x, y, angle = 0, kind = "ego", { scale = 1, brake = false, opacity = 1, stroke } = {}) {
  ctx.save(); ctx.translate(x, y); ctx.rotate(angle); ctx.scale(scale, scale); ctx.globalAlpha = opacity;
  if (kind === "ghost") ghostBody(ctx, stroke);
  else if (kind === "start") { ctx.globalAlpha = 0.45 * opacity; carBody(ctx, SK.PAINT); }
  else if (kind === "ego") { carBody(ctx, SK.EGO, SK.EGO_EDGE); if (brake) brakeLights(ctx); }
  else if (kind === "stopped") { carBody(ctx, SK.STOPPED, SK.OTHER_EDGE); hazardLamps(ctx); }
  else { carBody(ctx, SK.OTHER, SK.OTHER_EDGE); if (brake) brakeLights(ctx); }
  ctx.restore();
}

function pedestrian(ctx, x, y, k = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
  ctx.beginPath(); ctx.arc(0, 0, 3.2, 0, 7); ctx.fillStyle = SK.HAZARD_LAMP; ctx.fill(); ctx.strokeStyle = SK.INK; ctx.lineWidth = 0.8; ctx.stroke();
  ctx.beginPath(); ctx.arc(0, -0.5, 1.4, 0, 7); ctx.fillStyle = "#7C2D12"; ctx.fill(); ctx.restore();
}

// ---------------------------------------------------------------- marks

/** What should happen: dashed green. k: the scene's scale (SK.LARGE_K in the large scene). */
function intendedPath(ctx, pts, k = 1) {
  ctx.save(); ctx.strokeStyle = SK.REQ_S; ctx.lineWidth = 2.2 * k; ctx.setLineDash([5 * k, 3 * k]); ctx.lineCap = "round";
  poly(ctx, pts); ctx.stroke(); ctx.restore();
}

/** What does happen: solid red (or another colour, such as the green of a modification). */
function performedPath(ctx, pts, k = 1, color = SK.PERF_S, width = 2.6) {
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = width * k; ctx.lineJoin = "round"; ctx.lineCap = "round";
  poly(ctx, pts); ctx.stroke(); ctx.restore();
}

/** The gap between intended and actual, shaded. */
function gapBand(ctx, upper, lower) {
  ctx.save(); ctx.globalAlpha = 0.22; ctx.fillStyle = SK.PERF_S; poly(ctx, upper.concat(lower.slice().reverse()), true); ctx.fill(); ctx.restore();
}

function faultMarker(ctx, x, y, k = 1) {
  ctx.save(); ctx.translate(x, y); ctx.scale(k, k);
  ctx.beginPath(); ctx.arc(0, 0, 4.2, 0, 7); ctx.fillStyle = SK.FAULT; ctx.fill(); ctx.strokeStyle = SK.INK; ctx.lineWidth = 0.9; ctx.stroke();
  ctx.fillStyle = SK.INK; poly(ctx, [[0.6, -2.8], [-1.6, 0.4], [0, 0.4], [-0.6, 2.8], [1.6, -0.4], [0, -0.4]], true); ctx.fill(); ctx.restore();
}

/** Light text with a dark halo, for labels on the asphalt. */
function roadLabel(ctx, x, y, text, { color = "#334155", size = 7, weight = 600, align = "center", halo = false, sceneW } = {}) {
  ctx.save(); ctx.font = `${weight} ${size}px ${FONT}`; ctx.textAlign = align;
  if (sceneW && align === "center") { const half = ctx.measureText(text).width / 2 + 5; x = Math.min(sceneW - half, Math.max(half, x)); }
  if (halo) { ctx.strokeStyle = SK.INK; ctx.lineWidth = 2.4; ctx.lineJoin = "round"; ctx.strokeText(text, x, y); }
  ctx.fillStyle = color; ctx.fillText(text, x, y); ctx.restore();
}

/** The moment it matters: a yellow ring and its label. */
function callout(ctx, x, y, r, label, labelY, { k = 1, size = 8, sceneW = SK.W } = {}) {
  ctx.save(); ctx.beginPath(); ctx.arc(x, y, r * k, 0, 7); ctx.strokeStyle = SK.CALLOUT; ctx.lineWidth = 1.6 * k; ctx.stroke(); ctx.restore();
  roadLabel(ctx, x, labelY, label, { color: SK.CALLOUT, size, halo: true, sceneW });
}

/** One status pill, as scenekit.pill(); with num, a numbered disc keyed to a mark on the card's chart. Returns its width. */
function pill(ctx, x, y, text, style, { size = 7.5, h = 13, num = null, weight = 700 } = {}) {
  const [fill, fg, stroke] = SK.BADGE[style];
  ctx.save(); ctx.font = `700 ${size}px ${FONT}`;
  const lead = num !== null ? h + 3 : 6, w = ctx.measureText(text).width + lead + 6;
  rrect(ctx, x, y, w, h, h / 2); ctx.fillStyle = fill; ctx.fill(); ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.stroke();
  if (num !== null) {
    ctx.beginPath(); ctx.arc(x + h / 2 + 1, y + h / 2, h / 2 - 3, 0, 7); ctx.fillStyle = fg; ctx.fill();
    ctx.font = `700 ${size * 0.95}px ${FONT}`; ctx.textAlign = "center"; ctx.fillStyle = fill; ctx.fillText(String(num), x + h / 2 + 1, y + h / 2 + size * 0.36);
  }
  ctx.font = `${weight} ${size}px ${FONT}`; ctx.textAlign = "left"; ctx.fillStyle = fg; ctx.fillText(text, x + lead, y + h / 2 + size * 0.374);
  ctx.restore();
  return w;
}

/** Status pills down the scene's top-left corner: items [text, style] or [num, text, style]. */
function badges(ctx, items, { x = 6, y = 6, size = 7.5, h = 13, gap = 3 } = {}) {
  items.forEach((it, i) => {
    const [num, text, style] = it.length === 3 ? it : [null, it[0], it[1]];
    pill(ctx, x, y + i * (h + gap), text, style, { size, h, num });
  });
}

const scenekit = { SK, FONT, frame, directionArrow, straightRoad, stripRoad, largeRoad, curvedRoad, singleLaneRoad,
  carBody, brakeLights, hazardLamps, ghostBody, car, pedestrian, intendedPath, performedPath, gapBand, faultMarker,
  roadLabel, callout, pill, badges };
if (typeof module !== "undefined" && module.exports) module.exports = scenekit;
else root.scenekit = scenekit;
})(typeof window !== "undefined" ? window : globalThis);
