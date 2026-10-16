# Reachability pilot (coordinator request 2026-10-16): the set of lateral offsets and headings the L1 plant can reach
# under ANY LKA torque command the panda passes, from fault onset to past the driver's correction.
#
#     julia --project=assurance/sim/reach assurance/sim/reach/reach.jl OUT.json
#
# Model: model.json, written by reach_inputs.py (the L1 plant linearised at 110 km/h): z' = A z + B u with z(0) = 0.
# The panda lets |u| grow by at most u_step per frame from 0 and drop at once, so in frame k (from t = 0)
# |u| <= e_k = min(u_max, u_step (k + 1)).
#
#   dt  The plant holds the command over each dynamics step (plant_step_s; commands change only at those steps).
#       For inputs held per step the reachable set at the step times is exactly the zonotope recursion
#           X_{j+1} = exp(A h) X_j  (+)  Phi1(A, h) B [-e, e],   X_0 = {0}
#       computed with LazySets without order reduction, so with no over-approximation.
#   ct  Continuous time, any measurable u within the envelope (covers commands that change between plant steps):
#       ReachabilityAnalysis.jl GLGM06 over consecutive segments with a constant input box (the envelope's value at the
#       segment end). Each discretisation model in CT_MODELS is tried; a failure is recorded, not fatal.
# Bounds of y and psi are written per output grid step. Synthetic data (DSR-12), no evidence credit (WP-V-02 §5.3).

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
hstep = Float64(model["plant_step_s"])
n = size(A, 1)
nsteps = round(Int, H / grid)
DIMS = (1, 2)             # y, psi
δ = 1e-3                  # GLGM06 time step (ct)
SEG = 0.02                # ct envelope segment length (s)
ORDER = 30                # ct zonotope order kept between segments (reduction over-approximates)

envelope_ct(t) = min(umax, ustep + ustep / frame * t)                    # continuous, >= the per-frame envelope
envelope_frame(t) = min(umax, ustep * (floor(Int, t / frame + 1e-9) + 1))
empty_bounds() = (fill(Inf, nsteps + 1, length(DIMS)), fill(-Inf, nsteps + 1, length(DIMS)))
unitvec(d) = (e = zeros(n); e[d] = 1.0; e)

# ---- dt: exact recursion for inputs held per plant step
function reach_dt()
    E = exp([A B; zeros(1, n + 1)] * hstep)
    Φ, Φ1B = E[1:n, 1:n], E[1:n, n+1]
    per = round(Int, grid / hstep)
    lo, hi = empty_bounds()
    X = Zonotope(zeros(n), zeros(n, 0))
    for j in 0:nsteps*per
        if j % per == 0
            k = j ÷ per
            for (i, d) in enumerate(DIMS)
                hi[k+1, i] = ρ(unitvec(d), X); lo[k+1, i] = -ρ(-unitvec(d), X)
            end
        end
        e = envelope_frame(j * hstep)
        X = Zonotope(Φ * center(X), hcat(Φ * genmat(X), Φ1B * e))
    end
    lo, hi, ngens(X)
end

# ---- ct: GLGM06 with a given discretisation model
function bounds!(lo, hi, sol, offset)
    for R in sol
        Z = set(R)
        ts, te = tstart(R) + offset, tend(R) + offset
        k0 = max(0, ceil(Int, ts / grid - 1e-9)); k1 = min(nsteps, floor(Int, te / grid + 1e-9))
        k0 > k1 && continue
        for (j, d) in enumerate(DIMS)
            h = ρ(unitvec(d), Z); l = -ρ(-unitvec(d), Z)
            for k in k0:k1
                lo[k+1, j] = min(lo[k+1, j], l); hi[k+1, j] = max(hi[k+1, j], h)
            end
        end
    end
end

function reach_ct(approx)
    sys(ub) = ConstrainedLinearControlContinuousSystem(A, B, Universe(n), Hyperrectangle(zeros(1), [ub]))
    lo, hi = empty_bounds()
    X0 = Singleton(zeros(n))
    t0 = 0.0
    while t0 < H - 1e-9
        ub = envelope_ct(t0 + SEG)
        T = ub >= umax ? H - t0 : SEG
        sol = solve(IVP(sys(ub), X0); T=T, alg=GLGM06(δ=δ, approx_model=approx))
        bounds!(lo, hi, sol, t0)
        X0 = reduce_order(set(sol[end]), ORDER)    # contains the state at t0 + T
        t0 += T
    end
    all(isfinite, lo) && all(isfinite, hi) || error("a grid time is not covered by any reach set")
    lo, hi
end

pack(l, h) = Dict("y_lo" => l[:, 1], "y_hi" => h[:, 1], "psi_lo" => l[:, 2], "psi_hi" => h[:, 2])
at(h, s) = round(h[round(Int, s / grid)+1, 1], sigdigits=4)

t_dt = @elapsed (lo_d, hi_d, gens = reach_dt())
println("reach dt: ", gens, " generators, ", round(t_dt, digits=2), " s; y bound at 0.2 / 1.0 / ", H, " s: ",
        at(hi_d, 0.2), " / ", at(hi_d, 1.0), " / ", at(hi_d, H), " m")

CT_MODELS = [("forward", () -> Forward()), ("correction-hull", () -> CorrectionHull(order=10))]
ct = Dict{String,Any}()
for (name, make) in CT_MODELS
    try
        t_ct = @elapsed (lo, hi = reach_ct(make()))
        ct[name] = merge(pack(lo, hi), Dict("seconds" => t_ct))
        println("reach ct ", name, ": ", round(t_ct, digits=2), " s; y bound at 0.2 / 1.0 / ", H, " s: ",
                at(hi, 0.2), " / ", at(hi, 1.0), " / ", at(hi, H), " m")
    catch err
        msg = first(sprint(showerror, err), 400)
        ct[name] = Dict("error" => msg)
        println("reach ct ", name, ": failed: ", msg)
    end
end

out = Dict(
    "about" => "bounds of y (m) and psi (rad) from fault onset; dt: inputs held per plant step (exact), ct: any input " *
               "within the envelope (GLGM06, per discretisation model)",
    "julia" => string(VERSION), "plant_step_s" => hstep, "delta_ct" => δ, "segment_s" => SEG, "order_ct" => ORDER,
    "t" => [round(k * grid, digits=6) for k in 0:nsteps],
    "dt" => pack(lo_d, hi_d), "ct" => ct,
)
outpath = length(ARGS) >= 1 ? ARGS[1] : joinpath(HERE, "bounds.json")
open(outpath, "w") do io
    JSON.print(io, out)
end
println("reach: wrote ", outpath, "; Julia ", VERSION)
