// Optional sequential sweep bridge: per-sample FK (via Python closure callback) + the
// original native query, in one C call. No globals or model mutation; never
// direct mj_kinematics here. Optional direction hints are invocation-local.
//
// Error semantics: FK runs inside the caller's original mujoco.mj_kinematics
// call so Python error scope stays in force; the callback catches BaseException
// and returns nonzero, and sb_run stops without a native query. The owner then
// applies the original RuntimeError/ValueError -> invalid-sample predicate and
// re-raises any other (incl. FatalError) exception object.
#include <mujoco/mujoco.h>
#include <cstdint>
#include <cmath>
#include <algorithm>
#include <memory>
#include <vector>

extern "C" {

int sb_mj_version(void) {
    return mj_version();
}

typedef int (*Kinematics)(void*);

typedef int (*NativeEval)(void*, const double*, const double*, const int64_t*,
                          int64_t, double, double*, int64_t*, const int64_t*, int64_t*);

int sb_run(const mjModel* model, mjData* data,
           const double* states, int64_t state_count,
           const int64_t* geometry_ids, int64_t geometry_count,
           void* native_handle, NativeEval evaluate,
           Kinematics kinematics, void* kinematics_context,
           const int64_t* pairs, int64_t pair_count,
           double margin,
           double* positions, double* rotations,
           double* numeric, int64_t* flags,
           int64_t* hint_in, int64_t* hint_out,
           int64_t* committed_hints, int64_t* info) {

    // ---- Preflight: nonzero only on bad precondition, before any mutation.
    if (!model || !data || !states || !geometry_ids || !evaluate || !kinematics || !pairs ||
        !positions || !rotations || !numeric || !flags ||
        !hint_in || !hint_out || !committed_hints || !info) {
        return 1;
    }
    if (state_count <= 0 || pair_count <= 0 || geometry_count <= 0) return 1;
    if (!(std::isfinite(margin) && margin > 0.0)) return 1;
    // Fixed six-dof rig; nq==njnt==6 additionally implies all 1-dof joints
    // (no ball/free joint, hence no quaternion normalization in mj_kinematics).
    if (model->nq != 6 || model->nv != 6 || model->njnt != 6) return 1;
    if (model->ngeom <= 0) return 1;
    for (int64_t g = 0; g < geometry_count; ++g) {
        const int64_t id = geometry_ids[g];
        if (id < 0 || id >= (int64_t)model->ngeom) return 1;
    }

    // ---- Result info (checked_states, first_invalid_index, native_calls,
    //      successful_frames, reason).
    info[0] = 0;   // checked_states
    info[1] = -1;  // first_invalid_index (-1 if all valid)
    info[2] = 0;   // native_calls
    info[3] = 0;   // successful_frames
    info[4] = 0;   // reason: 0 all valid, 1 badq, 2 native_error, 3 uncertified, 4 kinematics

    for (int64_t s = 0; s < state_count; ++s) {
        const double* q = states + 6 * s;

        // Exact original finite + joint-range validation before touching data.
        bool bad_q = false;
        for (int j = 0; j < 6; ++j) {
            const double x = q[j];
            if (!std::isfinite(x)) { bad_q = true; break; }
            if (x < model->jnt_range[2 * j + 0] ||
                x > model->jnt_range[2 * j + 1]) {
                bad_q = true; break;
            }
        }
        if (bad_q) {
            info[0] = (int64_t)(s + 1);
            info[1] = s;
            info[4] = 1;   // badq; data/raw/hints unchanged
            return 0;
        }

        data->qpos[0] = q[0]; data->qpos[1] = q[1]; data->qpos[2] = q[2];
        data->qpos[3] = q[3]; data->qpos[4] = q[4]; data->qpos[5] = q[5];
        for (int v = 0; v < 6; ++v) data->qvel[v] = 0.0;

        const int fk_status = kinematics(kinematics_context);
        if (fk_status != 0) {
            info[0] = (int64_t)(s + 1);
            info[1] = s;
            info[4] = 4;   // kinematics error; data.qpos/qvel already written
            return 0;
        }

        for (int64_t g = 0; g < geometry_count; ++g) {
            const int64_t id = geometry_ids[g];
            positions[3 * g + 0] = data->geom_xpos[3 * id + 0];
            positions[3 * g + 1] = data->geom_xpos[3 * id + 1];
            positions[3 * g + 2] = data->geom_xpos[3 * id + 2];
            for (int k = 0; k < 9; ++k) {
                rotations[9 * g + k] = data->geom_xmat[9 * id + k];
            }
        }

        // Incoming hints for this frame = latest committed hints.
        for (int64_t c = 0; c < geometry_count * 3 * 2; ++c) {
            hint_in[c] = committed_hints[c];
        }

        info[0] = (int64_t)(s + 1);
        info[2] += 1;  // native_calls

        const int status = evaluate(native_handle, positions, rotations,
                                    pairs, pair_count, margin,
                                    numeric, flags, hint_in, hint_out);
        if (status != 0) {
            info[1] = s;
            info[4] = 2;   // native error; no commit
            return 0;
        }

        // Original "all certified" gate: every flags[row*6+0] nonzero.
        bool all_certified = true;
        for (int64_t r = 0; r < pair_count; ++r) {
            if (flags[r * 6 + 0] == 0) { all_certified = false; break; }
        }
        if (!all_certified) {
            info[1] = s;
            info[4] = 3;   // uncertified; no commit
            return 0;
        }

        for (int64_t c = 0; c < geometry_count * 3 * 2; ++c) {
            committed_hints[c] = hint_out[c];
        }
        info[3] += 1;  // successful_frames
    }

    info[1] = -1;
    info[4] = 0;  // all valid
    return 0;
}

typedef int (*NativeDirectionEval)(void*, const double*, const double*, const int64_t*,
    int64_t, double, double*, int64_t*, const int64_t*, int64_t*, const int64_t*, int64_t*);
struct DirectionBridge {
    void* native_handle;
    NativeDirectionEval evaluate;
    std::vector<int64_t> in, out;
    int64_t attempts=0, certificates=0;
    DirectionBridge(void* handle,NativeDirectionEval fn,int64_t count)
      :native_handle(handle),evaluate(fn),in(static_cast<std::size_t>(count)*2,-1),out(in.size()+2,-1) {}
};
static int evaluate_direction_bridge(void* raw,const double* positions,const double* rotations,
    const int64_t* pairs,int64_t count,double margin,double* numeric,int64_t* flags,
    const int64_t* hint_in,int64_t* hint_out) {
    auto* work=static_cast<DirectionBridge*>(raw);
    const int status=work->evaluate(work->native_handle,positions,rotations,pairs,count,margin,
        numeric,flags,hint_in,hint_out,work->in.data(),work->out.data());
    if (status==0) {
        work->attempts+=work->out[static_cast<std::size_t>(count)*2];
        work->certificates+=work->out[static_cast<std::size_t>(count)*2+1];
        bool all_valid=true;
        for (int64_t i=0;i<count;++i) all_valid &= flags[6*i]!=0;
        if (all_valid) std::copy(work->out.begin(),work->out.begin()+work->in.size(),work->in.begin());
    }
    return status;
}
int sb_run_direction(const mjModel* model,mjData* data,const double* states,int64_t state_count,
    const int64_t* ids,int64_t geometry_count,void* native_handle,NativeDirectionEval evaluate,
    Kinematics kinematics,void* context,const int64_t* pairs,int64_t pair_count,double margin,
    double* positions,double* rotations,double* numeric,int64_t* flags,int64_t* hint_in,
    int64_t* hint_out,int64_t* committed,int64_t* info,int64_t* strategy_work) {
    if (!native_handle || !evaluate || pair_count<=0 || !strategy_work) return 1;
    std::unique_ptr<DirectionBridge> work;
    try { work=std::make_unique<DirectionBridge>(native_handle,evaluate,pair_count); }
    catch (...) { return 1; } // Before original sb_run changes any state.
    // Delegate every FK, bounds check, first-failure prefix and error callback
    // to the original engine. No second sweep loop or execution scheduler.
    const int status=sb_run(model,data,states,state_count,ids,geometry_count,work.get(),
        evaluate_direction_bridge,kinematics,context,pairs,pair_count,margin,positions,
        rotations,numeric,flags,hint_in,hint_out,committed,info);
    if (status==0) {
        strategy_work[0]=work->attempts;
        strategy_work[1]=work->certificates;
    }
    return status;
}

} // extern "C"
