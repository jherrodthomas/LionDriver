# Reachability pilot (coordinator request 2026-10-16): the set of lateral offsets and headings the L1 plant can reach
# under ANY LKA torque command the panda passes, from fault onset to past the driver's correction.
#
#     julia --project=assurance/sim/reach assurance/sim/reach/reach.jl OUT.json
#
# Model: model.json, written by reach_inputs.py (the L1 plant linearised at 110 km/h): z' = A z + B u with z(0) = 0.
# The panda lets |u| grow by at most u_step per frame from 0 and drop at once, so |u(t)| <= min(u_max, u_step +
# u_step/frame_s * t). Two sound over-approximations of that input set, both computed with ReachabilityAnalysis.jl
# (GLGM06, zonotopes):
#   amp  |u| <= u_max over the whole horizon (ignores the panda's ramp)
#   env  the envelope above, as consecutive segments with a constant input box (the envelope's value at the segment's
#        end); each segment starts from the last reach set of the one before
# The reachable set lies inside both, so inside their intersection ("both"); its bounds are written per grid step.
# Synthetic data (DSR-12), no evidence credit (WP-V-02 §5.3).

using ReachabilityAnalysis, LazySets, JSON

const HERE = @__DIR__
model = JSON.parsefile(joinpath(HERE, "model.json"))
A = permutedims(reduce(hcat, [Float64.(r) for r in model["A"]]))      # rows -> matrix
B = permutedims(reduce(hcat, [Float64.(r) for r in model["B"]]))
H = Float64(model["horizon_s"])
grid = Float64(model["grid_s"])
umax = Float64(model["u_max"])
ustep = Float64(model["u_step"])
frame = Float64(model["frame_s"])
n = size(A, 1)
nsteps = round(Int, H / grid)
δ = 1e-3                  # GLGM06 time step
SEG = 0.02                # envelope segment length (s)
ORDER = 30                # zonotope order kept between segments (reduction over-approximates)
DIMS = (1, 2)             # y, psi

envelope(t) = min(umax, ustep + ustep / frame * t)

# lower and upper bound of each of DIMS at each grid time, over the reach sets whose time span contains it
function bounds!(lo, hi, sol, offset)
    for R in sol
        Z = set(R)
        ts, te = tstart(R) + offset, tend(R) + offset
        k0 = max(0, ceil(Int, ts / grid - 1e-9)); k1 = min(nsteps, floor(Int, te / grid + 1e-9))
        k0 > k1 && continue
        for (j, d) in enumerate(DIMS)
            e = zeros(n); e[d] = 1.0
            h = ρ(e, Z); l = -ρ(-e, Z)
            for k in k0:k1
                lo[k+1, j] = min(lo[k+1, j], l); hi[k+1, j] = max(hi[k+1, j], h)
            end
        end
    end
end

reach(X0, ub, T) = solve(IVP(ConstrainedLinearControlContinuousSystem(A, B, Universe(n), Hyperrectangle(zeros(1), [ub])),
                             X0); T=T, alg=GLGM06(δ=δ))

empty_bounds() = (fill(Inf, nsteps + 1, length(DIMS)), fill(-Inf, nsteps + 1, length(DIMS)))

# amp: one solve with the full amplitude
lo_a, hi_a = empty_bounds()
bounds!(lo_a, hi_a, reach(Singleton(zeros(n)), umax, H), 0.0)

# env: segments up to the end of the ramp, then one solve to the horizon
lo_e, hi_e = empty_bounds()
X0 = Singleton(zeros(n))
t0 = 0.0
while t0 < H - 1e-9
    global X0, t0
    ub = envelope(t0 + SEG)
    T = ub >= umax ? H - t0 : SEG
    sol = reach(X0, ub, T)
    bounds!(lo_e, hi_e, sol, t0)
    X0 = reduce_order(set(sol[end]), ORDER)    # contains the state at t0 + T
    t0 += T
end

for b in (lo_a, hi_a, lo_e, hi_e)
    all(isfinite, b) || error("a grid time is not covered by any reach set")
end
lo = max.(lo_a, lo_e); hi = min.(hi_a, hi_e)

pack(l, h) = Dict("y_lo" => l[:, 1], "y_hi" => h[:, 1], "psi_lo" => l[:, 2], "psi_hi" => h[:, 2])
out = Dict(
    "about" => "bounds of y (m) and psi (rad) from fault onset; amp: |u| <= u_max, env: the panda envelope, both: intersection",
    "julia" => string(VERSION), "delta" => δ, "segment_s" => SEG, "order" => ORDER,
    "t" => [round(k * grid, digits=6) for k in 0:nsteps],
    "amp" => pack(lo_a, hi_a), "env" => pack(lo_e, hi_e), "both" => pack(lo, hi),
)
outpath = length(ARGS) >= 1 ? ARGS[1] : joinpath(HERE, "bounds.json")
open(outpath, "w") do io
    JSON.print(io, out)
end
at(s) = round(hi[round(Int, s / grid)+1, 1], sigdigits=4)
println("reach: wrote ", outpath, "; Julia ", VERSION, "; y bound at 0.2 / 1.0 / ", H, " s: ", at(0.2), " / ", at(1.0),
        " / ", at(H), " m")
