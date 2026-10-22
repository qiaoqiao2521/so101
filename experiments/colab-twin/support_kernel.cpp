// Diagnostic-only binary64 support certificates. No fast math, FMA or threads.
// Compile: -O3 -fno-fast-math -ffp-contract=off -frounding-math -std=c++17.
#include <algorithm>
#include <array>
#include <cfenv>
#include <fenv.h>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <new>
#include <numeric>
#if defined(SUPPORT_SMALL_DIRECTION_CACHE)
#include <memory>
#include <utility>
#endif
#include <unordered_map>
#include <vector>
#if defined(__SSE__)
#include <xmmintrin.h>
#endif
#if defined(SUPPORT_VERTEX_QUAD_ENABLED) && (defined(__x86_64__) || defined(__i386__) || defined(_M_X64) || defined(_M_IX86))
#include <immintrin.h>
#endif

// Extra speculative vertex arithmetic is permitted only with masked traps.
// The original environment gate and original scalar arithmetic stay intact.
bool witness_traps_masked() {
#if defined(__GLIBC__) && defined(__USE_GNU)
    if (fegetexcept()!=0) return false;
#else
    return false; // Unknown x87/platform mask state: retain the legacy path.
#endif
#if defined(__SSE__)
    if ((_mm_getcsr() & UINT32_C(0x1f80))!=UINT32_C(0x1f80)) return false;
#endif
    return true;
}

#if defined(SUPPORT_TREE_TESTS)
struct WitnessTrace { std::int64_t attempted=0,finite_points=0,discarded=0,merged=0; };
thread_local WitnessTrace* witness_trace=nullptr;
#define WITNESS_RECORD(member) do { if (witness_trace) ++witness_trace->member; } while (false)
#else
#define WITNESS_RECORD(member) do {} while (false)
#endif

namespace {
constexpr double INF = std::numeric_limits<double>::infinity();
constexpr double NAN_VALUE = std::numeric_limits<double>::quiet_NaN();
constexpr std::uint64_t SIGN = UINT64_C(0x8000000000000000);
constexpr std::uint64_t EXP = UINT64_C(0x7ff0000000000000);
constexpr std::uint64_t FRAC = UINT64_C(0x000fffffffffffff);
constexpr std::size_t NFLOAT = 12, NINT = 6;
struct Interval { double lo, hi; };
using Vec = std::array<double, 3>;

inline std::uint64_t bits(double value) {
    std::uint64_t result;
    std::memcpy(&result, &value, sizeof(result));
    return result;
}
inline double value(std::uint64_t raw) {
    double result;
    std::memcpy(&result, &raw, sizeof(result));
    return result;
}

// Exact nextafter(x,+/-infinity) VALUES for IEEE binary64, including signed
// zero, subnormals, normal boundaries, finite extremes and infinities. Signed
// magnitudes are monotone within each sign, so one integer ULP step suffices.
// NaN remains NaN (payload is not part of any certificate). Unlike libm this
// helper does not synthesize underflow/overflow flags; it never changes fenv.
inline double neighbor(double x, bool upward) {
    auto raw = bits(x);
    const auto magnitude = raw & ~SIGN;
    if ((raw & EXP) == EXP && (raw & FRAC)) return x+x;
    if (magnitude == 0) return value(upward ? UINT64_C(1) : SIGN|UINT64_C(1));
    if (raw == EXP && upward) return x;
    if (raw == (SIGN|EXP) && !upward) return x;
    if (raw & SIGN) raw += upward ? UINT64_C(-1) : UINT64_C(1);
    else raw += upward ? UINT64_C(1) : UINT64_C(-1);
    return value(raw);
}
inline double down(double x) { return neighbor(x, false); }
inline double up(double x) { return neighbor(x, true); }
inline Interval exact(double x) { return {x,x}; }
inline Interval add(Interval a, Interval b) { return {down(a.lo+b.lo),up(a.hi+b.hi)}; }
inline Interval mul(Interval a, Interval b) {
    const double products[4] = {a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};
    double low = products[0], high = products[0];
    // The same left-to-right, first-on-tie scalar extrema as Python min/max.
    for (int k=1;k<4;++k) {
        if (products[k] < low) low = products[k];
        if (products[k] > high) high = products[k];
    }
    return {down(low),up(high)};
}
inline Interval dot(const std::array<Interval,3>& a, const std::array<Interval,3>& b) {
    Interval result{0.,0.};
    for (int j=0;j<3;++j) result = add(result,mul(a[j],b[j]));
    return result;
}
inline bool finite(Interval x) { return std::isfinite(x.lo) && std::isfinite(x.hi); }
inline bool normalize(Vec& n) {
    double scale=0.;
    for (double x:n) {
        if (!std::isfinite(x)) return false;
        scale=std::max(scale,std::abs(x));
    }
    if (scale==0.) return false;
    for (double& x:n) x=x/scale;
    return true;
}

bool environment(int* rounding=nullptr, std::uint32_t* control=nullptr,
                 int* preserved_input=nullptr,int* preserved_output=nullptr) {
    const int mode=std::fegetround();
    std::uint32_t csr=0;
#if defined(__SSE__)
    csr=_mm_getcsr();
#endif
    volatile double small=value(UINT64_C(1)), one=1.;
    volatile double normal=std::numeric_limits<double>::min(), half=.5;
    const bool input=small*one==small;
    const bool output=normal*half!=0.;
    if (rounding) *rounding=mode;
    if (control) *control=csr;
    if (preserved_input) *preserved_input=input;
    if (preserved_output) *preserved_output=output;
    return sizeof(double)==8 && std::numeric_limits<double>::is_iec559 &&
           std::numeric_limits<double>::digits==53 && mode==FE_TONEAREST &&
           !(csr&(UINT32_C(1)<<15)) && !(csr&(UINT32_C(1)<<6)) && input && output;
}

constexpr std::size_t LEAF_SIZE=16, NO_CHILD=std::numeric_limits<std::size_t>::max();
struct Node {
    Vec low{},high{};
    std::size_t begin=0,end=0,left=NO_CHILD,right=NO_CHILD;
};
struct Geometry {
    std::vector<double> points;
    Vec low{}, high{};
    int kind=0; // 0 finite box, 1 original mesh.
    // All original vertices remain owned. The tree indexes every vertex once.
    std::vector<std::size_t> order;
    std::vector<Node> nodes;
};

std::size_t build_node(Geometry& geom,std::size_t begin,std::size_t end) {
    Node node; node.begin=begin;node.end=end;
    for (int j=0;j<3;++j) node.low[j]=node.high[j]=geom.points[3*geom.order[begin]+j];
    for (std::size_t k=begin;k<end;++k) for (int j=0;j<3;++j) {
        const auto x=geom.points[3*geom.order[k]+j];
        node.low[j]=std::min(node.low[j],x);node.high[j]=std::max(node.high[j],x);
    }
    const auto index=geom.nodes.size();geom.nodes.push_back(node);
    if (end-begin>LEAF_SIZE) {
        int axis=0;
        for (int j=1;j<3;++j)
            if (node.high[j]-node.low[j]>node.high[axis]-node.low[axis]) axis=j;
        const auto middle=begin+(end-begin)/2;
        std::nth_element(geom.order.begin()+begin,geom.order.begin()+middle,geom.order.begin()+end,
            [&geom,axis](std::size_t a,std::size_t b) {
                const auto x=geom.points[3*a+axis],y=geom.points[3*b+axis];
                return x<y || (x==y && a<b);
            });
        const auto left=build_node(geom,begin,middle),right=build_node(geom,middle,end);
        geom.nodes[index].left=left;geom.nodes[index].right=right;
    }
    return index;
}

bool vertex_interval(const Geometry& geom,std::size_t vertex,
                     const std::array<Interval,3>& local,Interval& out) {
    double low=0.,high=0.;
    for (int j=0;j<3;++j) {
        const double first=geom.points[3*vertex+j]*local[j].lo;
        const double second=geom.points[3*vertex+j]*local[j].hi;
        if (!std::isfinite(first)||!std::isfinite(second)) return false;
        const double term_low=down(first<second?first:second);
        const double term_high=up(first>second?first:second);
        low=down(low+term_low);high=up(high+term_high);
        if (!std::isfinite(low)||!std::isfinite(high)) return false;
    }
    out={low,high};return true;
}

bool full_scan(const Geometry& geom,const std::array<Interval,3>& local,Interval& out) {
    double minimum=INF,maximum=-INF;
    for (std::size_t v=0;v<geom.points.size()/3;++v) {
        Interval point;
        if (!vertex_interval(geom,v,local,point)) return false;
        minimum=std::min(minimum,point.lo);maximum=std::max(maximum,point.hi);
    }
    out={minimum,maximum};return true;
}

// Seed from real vertices in two greedily selected leaves. The child bounds
// only choose work order; they never supply the returned support extrema.
// Failed exploratory arithmetic discards both seeds before the original DFS.
#if defined(SUPPORT_VERTEX_QUAD_ENABLED)
#if defined(__GNUC__) && (defined(__x86_64__) || defined(__i386__)) && !defined(SUPPORT_VERTEX_QUAD_DISABLED)
// Four finite lanes. Each 64-bit integer lane performs the original neighbor
// bit step; ordered per-lane comparisons preserve the scalar second-on-tie.
__attribute__((target("avx2")))
inline __m256d neighbor4(__m256d x, bool upward) {
    const auto raw = _mm256_castpd_si256(x);
    const auto one = _mm256_set1_epi64x(1);
    const auto twice_sign = _mm256_slli_epi64(_mm256_srli_epi64(raw, 63), 1);
    const auto delta = upward ? _mm256_sub_epi64(one, twice_sign)
                              : _mm256_sub_epi64(twice_sign, one);
    const auto stepped = _mm256_add_epi64(raw, delta);
    const auto magnitude = _mm256_and_si256(raw, _mm256_set1_epi64x(INT64_MAX));
    const auto zero_words = _mm256_cmpeq_epi32(magnitude, _mm256_setzero_si256());
    const auto zero = _mm256_and_si256(zero_words,
        _mm256_shuffle_epi32(zero_words, _MM_SHUFFLE(2, 3, 0, 1)));
    const auto tiny = upward ? one : _mm256_set1_epi64x(INT64_MIN + 1);
    return _mm256_castsi256_pd(_mm256_or_si256(_mm256_and_si256(zero, tiny),
                                               _mm256_andnot_si256(zero, stepped)));
}

__attribute__((target("avx2")))
inline bool finite4(__m256d x) {
    const auto exponent = _mm256_set1_epi64x(static_cast<std::int64_t>(EXP));
    const auto same = _mm256_cmpeq_epi32(
        _mm256_and_si256(_mm256_castpd_si256(x), exponent), exponent);
    return (_mm256_movemask_epi8(same) & UINT32_C(0xf0f0f0f0)) == 0;
}

__attribute__((target("avx2")))
inline __m256d select4(__m256d mask, __m256d first, __m256d second) {
    return _mm256_or_pd(_mm256_and_pd(mask, first), _mm256_andnot_pd(mask, second));
}

__attribute__((target("avx2")))
bool vertex_interval_quad(const Geometry& geom, std::size_t v0, std::size_t v1,
                          std::size_t v2, std::size_t v3,
                          const std::array<Interval, 3>& local,
                          Interval& out0, Interval& out1, Interval& out2, Interval& out3) {
    __m256d low = _mm256_setzero_pd(), high = _mm256_setzero_pd();
    for (int j = 0; j < 3; ++j) {
        const auto points = _mm256_set_pd(geom.points[3 * v3 + j], geom.points[3 * v2 + j],
                                          geom.points[3 * v1 + j], geom.points[3 * v0 + j]);
        const auto first = _mm256_mul_pd(points, _mm256_set1_pd(local[j].lo));
        const auto second = _mm256_mul_pd(points, _mm256_set1_pd(local[j].hi));
        if (!finite4(first) || !finite4(second)) return false;
        const auto term_low = neighbor4(select4(_mm256_cmp_pd(first, second, _CMP_LT_OQ), first, second), false);
        const auto term_high = neighbor4(select4(_mm256_cmp_pd(first, second, _CMP_GT_OQ), first, second), true);
        if (!finite4(term_low) || !finite4(term_high)) return false;
        const auto sum_low = _mm256_add_pd(low, term_low);
        const auto sum_high = _mm256_add_pd(high, term_high);
        if (!finite4(sum_low) || !finite4(sum_high)) return false;
        low = neighbor4(sum_low, false);
        high = neighbor4(sum_high, true);
        if (!finite4(low) || !finite4(high)) return false;
    }
    alignas(32) double lows[4], highs[4];
    _mm256_store_pd(lows, low);
    _mm256_store_pd(highs, high);
    out0 = {lows[0], highs[0]};
    out1 = {lows[1], highs[1]};
    out2 = {lows[2], highs[2]};
    out3 = {lows[3], highs[3]};
    return true;
}
#endif

// Buffers only the next three already-computed independent vertices within a
// single leaf; no cross-leaf, frame or model state.
struct LeafQuadCache {
    bool packed = false;
    unsigned count = 0;
    Interval second{};
    Interval third{};
    Interval fourth{};
    LeafQuadCache() {
#if defined(__GNUC__) && (defined(__x86_64__) || defined(__i386__)) && !defined(SUPPORT_VERTEX_QUAD_DISABLED)
        // Four-lane speculation only on AVX2-capable hardware with traps masked.
        packed = __builtin_cpu_supports("avx2") && witness_traps_masked();
#else
        packed = false;
#endif
    }
};

bool leaf_vertex_interval_quad(const Geometry& geom, const Node& leaf, std::size_t k,
                               const std::array<Interval, 3>& local, LeafQuadCache& cache,
                               Interval& out) {
    static_cast<void>(leaf); // Scalar-only builds do not use the leaf bound.
    if (cache.count > 0) {
        out = cache.second;
        cache.second = cache.third;
        cache.third = cache.fourth;
        --cache.count;
        return true;
    }
#if defined(__GNUC__) && (defined(__x86_64__) || defined(__i386__)) && !defined(SUPPORT_VERTEX_QUAD_DISABLED)
    if (cache.packed && k + 3 < leaf.end) {
        Interval first, second, third, fourth;
        if (vertex_interval_quad(geom, geom.order[k], geom.order[k + 1],
                                 geom.order[k + 2], geom.order[k + 3], local,
                                 first, second, third, fourth)) {
            out = first;
            cache.second = second;
            cache.third = third;
            cache.fourth = fourth;
            cache.count = 3;
            return true;
        }
        // Replay from this original vertex, then keep the whole leaf scalar.
        cache.packed = false;
        cache.count = 0;
    }
#endif
    return vertex_interval(geom, geom.order[k], local, out);
}

#endif

#if !defined(SUPPORT_TREE_SEED_DISABLED)
bool seed_extreme(const Geometry& geom,const std::array<Interval,3>& local,
                  bool minimum,std::size_t& vertex,Interval& point) {
    std::size_t index=0;
    while (geom.nodes[index].left!=NO_CHILD) {
        const auto& node=geom.nodes[index];
        const auto& a=geom.nodes[node.left];const auto& b=geom.nodes[node.right];
        const Interval first=dot({Interval{a.low[0],a.high[0]},
                                  Interval{a.low[1],a.high[1]},
                                  Interval{a.low[2],a.high[2]}},local);
        const Interval second=dot({Interval{b.low[0],b.high[0]},
                                   Interval{b.low[1],b.high[1]},
                                   Interval{b.low[2],b.high[2]}},local);
        if (!finite(first)||!finite(second)) return false;
        const bool choose_first=minimum?first.lo<=second.lo:first.hi>=second.hi;
        index=choose_first?node.left:node.right;
    }
    const auto& leaf=geom.nodes[index];
#if defined(SUPPORT_VERTEX_QUAD_ENABLED)
    LeafQuadCache cache;
#endif
    vertex=geom.order[leaf.begin];
#if defined(SUPPORT_VERTEX_QUAD_ENABLED)
    if (!leaf_vertex_interval_quad(geom,leaf,leaf.begin,local,cache,point)) return false;
#else
    if (!vertex_interval(geom,vertex,local,point)) return false;
#endif
    for (std::size_t k=leaf.begin+1;k<leaf.end;++k) {
        const auto v=geom.order[k];Interval candidate;
#if defined(SUPPORT_VERTEX_QUAD_ENABLED)
        if (!leaf_vertex_interval_quad(geom,leaf,k,local,cache,candidate)) return false;
#else
        if (!vertex_interval(geom,v,local,candidate)) return false;
#endif
        const double a=minimum?candidate.lo:candidate.hi;
        const double b=minimum?point.lo:point.hi;
        if ((minimum?a<b:a>b)||(a==b && v<vertex)) { vertex=v;point=candidate; }
    }
    return true;
}
#endif

bool full_tree(const Geometry& geom,const std::array<Interval,3>& local,Interval& out,
               bool* scan_fallback=nullptr,const std::int64_t* hint_in=nullptr,
               std::int64_t* hint_out=nullptr) {
    if (geom.nodes.empty()) return full_scan(geom,local,out);
    Interval first;
    if (!vertex_interval(geom,0,local,first)) return false;
    double minimum=first.lo,maximum=first.hi;
    std::size_t min_index=0,max_index=0;
#if !defined(SUPPORT_TREE_SEED_DISABLED)
    std::size_t low_vertex=0,high_vertex=0;Interval low_point,high_point;
    if (seed_extreme(geom,local,true,low_vertex,low_point) &&
        seed_extreme(geom,local,false,high_vertex,high_point)) {
        const auto consider=[&](std::size_t v,Interval point) {
            if (point.lo<minimum || (point.lo==minimum && v<min_index)) {
                minimum=point.lo;min_index=v;
            }
            if (point.hi>maximum || (point.hi==maximum && v<max_index)) {
                maximum=point.hi;max_index=v;
            }
        };
        consider(low_vertex,low_point);consider(high_vertex,high_point);
    }
#endif
    // IDs are work-order hints only. Every value uses the current local DAG.
    // Both original seeds have already run; speculative failure discards all
    // additional points without changing the original failure/fallback path.
    if (hint_in) {
        std::array<std::size_t,2> vertices{};
        std::array<Interval,2> points{};
        std::size_t used=0;bool usable=true;
        for (int k=0;k<2;++k) {
            const auto raw=hint_in[k];
            if (raw<0 || static_cast<std::uint64_t>(raw)>=geom.points.size()/3) continue;
            const auto v=static_cast<std::size_t>(raw);
            if (v==min_index || v==max_index || (used && vertices[0]==v)) continue;
            WITNESS_RECORD(attempted);
            if (!vertex_interval(geom,v,local,points[used])) {
                WITNESS_RECORD(discarded);usable=false;break;
            }
            WITNESS_RECORD(finite_points);vertices[used++]=v;
        }
        if (usable) for (std::size_t k=0;k<used;++k) {
            const auto v=vertices[k];const auto point=points[k];
            if (point.lo<minimum || (point.lo==minimum && v<min_index)) {
                minimum=point.lo;min_index=v;
            }
            if (point.hi>maximum || (point.hi==maximum && v<max_index)) {
                maximum=point.hi;max_index=v;
            }
            WITNESS_RECORD(merged);
        }
    }
    std::vector<std::size_t> pending{0};
    while (!pending.empty()) {
        const auto index=pending.back();pending.pop_back();
        const auto& node=geom.nodes[index];
        const Interval bound=dot({Interval{node.low[0],node.high[0]},
                                  Interval{node.low[1],node.high[1]},
                                  Interval{node.low[2],node.high[2]}},local);
        // An overly wide nonfinite bound does not imply nonfinite vertices.
        // Restart the original scan in its original order, without tree state.
        if (!finite(bound)) {
            if (scan_fallback) *scan_fallback=true;
            return full_scan(geom,local,out);
        }
        // Strict comparisons retain all ties, including the first signed zero.
        if (bound.lo>minimum && bound.hi<maximum) continue;
        if (node.left==NO_CHILD) {
#if defined(SUPPORT_VERTEX_QUAD_ENABLED)
            LeafQuadCache cache;
#endif
            for (std::size_t k=node.begin;k<node.end;++k) {
                const auto v=geom.order[k];Interval point;
#if defined(SUPPORT_VERTEX_QUAD_ENABLED)
                if (!leaf_vertex_interval_quad(geom,node,k,local,cache,point)) return false;
#else
                if (!vertex_interval(geom,v,local,point)) return false;
#endif
                if (point.lo<minimum || (point.lo==minimum && v<min_index)) {
                    minimum=point.lo;min_index=v;
                }
                if (point.hi>maximum || (point.hi==maximum && v<max_index)) {
                    maximum=point.hi;max_index=v;
                }
            }
        } else {
            pending.push_back(node.right);pending.push_back(node.left);
        }
    }
    if (hint_out) {
        hint_out[0]=static_cast<std::int64_t>(min_index);
        hint_out[1]=static_cast<std::int64_t>(max_index);
    }
    out={minimum,maximum};return true;
}
struct Context { std::vector<Geometry> geoms; };
struct Key {
    std::uint64_t n[3]; bool full;
    bool operator==(const Key& other) const {
        return full==other.full && n[0]==other.n[0] && n[1]==other.n[1] && n[2]==other.n[2];
    }
};
struct KeyHash {
    std::size_t operator()(const Key& key) const {
        std::uint64_t h=key.full?UINT64_C(0x9e3779b97f4a7c15):0;
        for (auto x:key.n) h^=x+UINT64_C(0x9e3779b97f4a7c15)+(h<<6)+(h>>2);
        return static_cast<std::size_t>(h);
    }
};
struct Frame {
    const Geometry* geom=nullptr;
    const std::int64_t* hint_in=nullptr;
    std::int64_t* hint_out=nullptr;
    Vec p{}; std::array<double,9> R{};
#if defined(SUPPORT_SMALL_DIRECTION_CACHE)
    static constexpr std::size_t small_dir_cap = 16;
    std::unique_ptr<std::array<std::pair<Key,Interval>,small_dir_cap>> small_dir;
    std::size_t small_dir_count = 0;
    std::unique_ptr<std::unordered_map<Key,Interval,KeyHash>> overflow_cache;
#else
    std::unordered_map<Key,Interval,KeyHash> cache;
#endif
    std::array<std::array<Interval,3>,2> world{};
    std::array<std::array<bool,3>,2> world_ready{};
    std::array<std::array<Interval,3>,3> local_world{};
    std::array<Interval,3> center_world{};
    std::array<bool,3> terms_ready{};
};

#if defined(SUPPORT_SMALL_DIRECTION_CACHE)
// Exact per-frame non-axis direction cache: lazily owned 16-slot inline
// block, spilling to the original unordered_map only for 17+ unique keys.
inline const Interval* frame_cache_find(const Frame& shape, const Key& key) {
    if (shape.small_dir) {
        for (std::size_t i = 0; i < shape.small_dir_count; ++i) {
            const auto& entry = (*shape.small_dir)[i];
            if (entry.first == key) return &entry.second;
        }
    }
    if (shape.overflow_cache) {
        const auto it = shape.overflow_cache->find(key);
        if (it != shape.overflow_cache->end()) return &it->second;
    }
    return nullptr;
}

inline void frame_cache_insert(Frame& shape, const Key& key, const Interval& answer) {
    if (!shape.overflow_cache) {
        if (!shape.small_dir) {
            shape.small_dir =
                std::make_unique<std::array<std::pair<Key,Interval>,Frame::small_dir_cap>>();
            shape.small_dir_count = 0;
        }
        if (shape.small_dir_count < Frame::small_dir_cap) {
            // No-op on an existing key, matching unordered_map::emplace.
            for (std::size_t i = 0; i < shape.small_dir_count; ++i)
                if ((*shape.small_dir)[i].first == key) return;
            (*shape.small_dir)[shape.small_dir_count++] = std::make_pair(key, answer);
            return;
        }
        // Capacity reached: spill all inline entries into the original map once.
        shape.overflow_cache = std::make_unique<std::unordered_map<Key,Interval,KeyHash>>();
        for (std::size_t i = 0; i < shape.small_dir_count; ++i) {
            const auto& entry = (*shape.small_dir)[i];
            shape.overflow_cache->emplace(entry.first, entry.second);
        }
        shape.small_dir.reset();
        shape.small_dir_count = 0;
    }
    shape.overflow_cache->emplace(key, answer);
}

#endif

bool project(Frame& shape, const Vec& n, bool full, Interval& answer) {
    int axis=-1;
    for (int j=0;j<3;++j)
        if (n[j]==1. && n[(j+1)%3]==0. && n[(j+2)%3]==0.) axis=j;
    const int bucket=full && shape.geom->kind==1?1:0;
    if (axis>=0 && shape.world_ready[bucket][axis]) {
        answer=shape.world[bucket][axis];return true;
    }
    Key key{{bits(n[0]),bits(n[1]),bits(n[2])},full};
    // Python float cache keys identify +0 and -0. Keep that exact equality.
    for (auto& raw:key.n) if ((raw&~SIGN)==0) raw=0;
    if (axis<0) {
#if defined(SUPPORT_SMALL_DIRECTION_CACHE)
        const auto* cached=frame_cache_find(shape,key);
        if (cached) { answer=*cached; return true; }
#else
        const auto cached=shape.cache.find(key);
        if (cached!=shape.cache.end()) { answer=cached->second; return true; }
#endif
    }
    std::array<Interval,3> ni{exact(n[0]),exact(n[1]),exact(n[2])},local;
    Interval center;
    if (axis>=0 && shape.terms_ready[axis]) {
        local=shape.local_world[axis];center=shape.center_world[axis];
    } else {
        for (int j=0;j<3;++j) {
            std::array<Interval,3> column{exact(shape.R[j]),exact(shape.R[3+j]),exact(shape.R[6+j])};
            local[j]=dot(column,ni);
        }
        center=dot({exact(shape.p[0]),exact(shape.p[1]),exact(shape.p[2])},ni);
    }
    if (!finite(center) || !finite(local[0]) || !finite(local[1]) || !finite(local[2])) return false;
    if (axis>=0) {
        shape.local_world[axis]=local;shape.center_world[axis]=center;shape.terms_ready[axis]=true;
    }
    Interval extrema;
    if (!full || shape.geom->kind==0) {
        std::array<Interval,3> bounds;
        for (int j=0;j<3;++j) bounds[j]={shape.geom->low[j],shape.geom->high[j]};
        extrema=dot(bounds,local);
    } else {
        if (!full_tree(*shape.geom,local,extrema,nullptr,
                       axis>=0 && shape.hint_in?shape.hint_in+2*axis:nullptr,
                       axis>=0 && shape.hint_out?shape.hint_out+2*axis:nullptr)) return false;
    }
    answer=add(center,extrema);
    if (!finite(answer)) return false;
    if (axis>=0) { shape.world[bucket][axis]=answer;shape.world_ready[bucket][axis]=true; }
#if defined(SUPPORT_SMALL_DIRECTION_CACHE)
    else frame_cache_insert(shape,key,answer);
#else
    else shape.cache.emplace(key,answer);
#endif
    return true;
}

struct Result {
    bool certified=false;
    Vec n{NAN_VALUE,NAN_VALUE,NAN_VALUE};
    Interval a{NAN_VALUE,NAN_VALUE},b{NAN_VALUE,NAN_VALUE};
    double gap=NAN_VALUE,norm=NAN_VALUE,left=NAN_VALUE,right=NAN_VALUE,bound=NAN_VALUE;
    std::int64_t mode=0,index=-1,evaluations=0,reason=0,orientation=0;
};

bool gate(double gap,double norm,double margin,double& left,double& right) {
    left=right=NAN_VALUE;
    if (!std::isfinite(gap)||!std::isfinite(norm)||!std::isfinite(margin)||gap<=0.||norm<=0.||margin<=0.) return false;
    left=down(gap*gap);
    right=up(up(margin*margin)*norm);
    return std::isfinite(left)&&std::isfinite(right)&&left>=right;
}

bool certificate(Frame& a,Frame& b,Vec n,double margin,bool full,Result& r) {
    if (!normalize(n)) return false;
    r.n=n; r.mode=full?2:1;
    if (!project(a,n,full,r.a)||!project(b,n,full,r.b)) return false;
    const double forward=down(r.b.lo-r.a.hi),reverse=down(r.a.lo-r.b.hi);
    r.orientation=forward>=reverse?1:-1;
    r.gap=std::max(forward,reverse);
    const std::array<Interval,3> exact_n{exact(n[0]),exact(n[1]),exact(n[2])};
    r.norm=dot(exact_n,exact_n).hi;
    r.certified=gate(r.gap,r.norm,margin,r.left,r.right);
    r.bound=r.gap<=0.?0.:std::max(0.,down(r.gap/up(std::sqrt(r.norm))));
    return std::isfinite(r.gap)&&std::isfinite(r.norm)&&std::isfinite(r.bound);
}

Vec column(const Frame& shape,int axis) { return {shape.R[axis],shape.R[3+axis],shape.R[6+axis]}; }
Vec cross(Vec a,Vec b) {
    return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]};
}
Result pair_result(Frame& a,Frame& b,double margin) {
    std::array<Vec,19> fixed;
    std::array<bool,19> valid{};
    fixed[0]={1.,0.,0.}; fixed[1]={0.,1.,0.}; fixed[2]={0.,0.,1.};
    for (int i=0;i<3;++i) valid[i]=normalize(fixed[i]);
    bool rest_ready=false;
    Result best; bool has_best=false; std::int64_t count=0;
    for (bool full:{false,true}) for (int i=0;i<19;++i) {
        if (i==3 && !rest_ready) {
            fixed[3]={b.p[0]-a.p[0],b.p[1]-a.p[1],b.p[2]-a.p[2]};
            for (int j=0;j<3;++j) { fixed[4+j]=column(a,j); fixed[7+j]=column(b,j); }
            for (int j=0;j<3;++j) for (int k=0;k<3;++k) fixed[10+3*j+k]=cross(column(a,j),column(b,k));
            for (int j=3;j<19;++j) valid[j]=normalize(fixed[j]);
            rest_ready=true;
        }
        if (!valid[i]) continue;
        Result current;
        if (!certificate(a,b,fixed[i],margin,full,current)) {
            Result failed; failed.evaluations=count; failed.reason=3; return failed;
        }
        ++count;
        if (!has_best || current.bound>best.bound) { best=current; has_best=true; }
        if (current.certified) { current.index=i; current.evaluations=count; current.reason=1; return current; }
    }
    // Old Python's final uncertified 'best' lacks direction_index. Preserve -1.
    best.certified=false; best.index=-1; best.evaluations=count; best.reason=2;
    return best;
}
void write_result(const Result& r,double* output,std::int64_t* flags) {
    for (int j=0;j<3;++j) output[j]=r.n[j];
    output[3]=r.a.lo; output[4]=r.a.hi; output[5]=r.b.lo; output[6]=r.b.hi;
    output[7]=r.gap; output[8]=r.norm; output[9]=r.left; output[10]=r.right; output[11]=r.bound;
    flags[0]=r.certified; flags[1]=r.mode; flags[2]=r.index; flags[3]=r.evaluations; flags[4]=r.reason; flags[5]=r.orientation;
}
} // namespace

extern "C" {
int ns_environment(int* rounding,std::uint32_t* control,int* input,int* output) {
    return environment(rounding,control,input,output)?0:1;
}
double ns_down(double x) { return environment()?down(x):NAN_VALUE; }
double ns_up(double x) { return environment()?up(x):NAN_VALUE; }
void ns_add(const double* a,const double* b,double* out) {
    if (!environment()) { out[0]=out[1]=NAN_VALUE; return; }
    auto r=add({a[0],a[1]},{b[0],b[1]}); out[0]=r.lo;out[1]=r.hi;
}
void ns_mul(const double* a,const double* b,double* out) {
    if (!environment()) { out[0]=out[1]=NAN_VALUE; return; }
    auto r=mul({a[0],a[1]},{b[0],b[1]}); out[0]=r.lo;out[1]=r.hi;
}
void ns_dot3(const double* a,const double* b,double* out) {
    if (!environment()) { out[0]=out[1]=NAN_VALUE; return; }
    auto r=dot({exact(a[0]),exact(a[1]),exact(a[2])},{exact(b[0]),exact(b[1]),exact(b[2])}); out[0]=r.lo;out[1]=r.hi;
}
int ns_gate(double gap,double norm,double margin,double* out) {
    if (!environment()) { out[0]=out[1]=NAN_VALUE; return 0; }
    return gate(gap,norm,margin,out[0],out[1])?1:0;
}
void* ns_create(std::int64_t count,const std::int64_t* offsets,const double* points,const std::int32_t* kinds) {
    if (count<=0||!offsets||!points||!kinds||!environment()) return nullptr;
    try {
        auto* context=new Context;
        try {
            context->geoms.reserve(static_cast<std::size_t>(count));
            for (std::int64_t g=0;g<count;++g) {
                if (offsets[g]<0||offsets[g+1]<=offsets[g]||!(kinds[g]==0||kinds[g]==1)) throw std::bad_alloc();
                Geometry geom; geom.kind=kinds[g];
                geom.points.assign(points+offsets[g]*3,points+offsets[g+1]*3);
                for (int j=0;j<3;++j) geom.low[j]=geom.high[j]=geom.points[j];
                for (std::size_t v=0;v<geom.points.size();v+=3) for (int j=0;j<3;++j) {
                    const double x=geom.points[v+j];
                    if (!std::isfinite(x)) throw std::bad_alloc();
                    if (x<=geom.low[j]) geom.low[j]=x;
                    if (x>=geom.high[j]) geom.high[j]=x;
                }
                if (geom.kind==1) {
                    geom.order.resize(geom.points.size()/3);
                    std::iota(geom.order.begin(),geom.order.end(),std::size_t{0});
                    geom.nodes.reserve(geom.order.size()*2/LEAF_SIZE+1);
                    build_node(geom,0,geom.order.size());
                }
                context->geoms.push_back(std::move(geom));
            }
        } catch (...) { delete context; return nullptr; }
        return context;
    } catch (...) { return nullptr; }
}
void ns_destroy(void* raw) { delete static_cast<Context*>(raw); }
int ns_evaluate(void* raw,const double* positions,const double* rotations,
                const std::int64_t* pairs,std::int64_t count,double margin,double* output,std::int64_t* flags) {
    if (!raw||!positions||!rotations||!pairs||!output||!flags||count<0) return 1;
    auto* context=static_cast<Context*>(raw);
    Result failed;
    if (!environment()) failed.reason=5;
    else if (!std::isfinite(margin)||margin<=0.) failed.reason=4;
    bool frame_valid=failed.reason==0;
    for (std::size_t g=0;g<context->geoms.size()&&frame_valid;++g) {
        for (int j=0;j<3;++j) frame_valid &= std::isfinite(positions[g*3+j]);
        for (int j=0;j<9;++j) frame_valid &= std::isfinite(rotations[g*9+j]);
    }
    if (!frame_valid) {
        if (!failed.reason) failed.reason=3;
        for (std::int64_t i=0;i<count;++i) write_result(failed,output+i*NFLOAT,flags+i*NINT);
        return 0;
    }
    try {
        // Every call creates a fresh frame and fresh per-shape support caches.
        std::vector<Frame> frames(context->geoms.size());
        for (std::size_t g=0;g<frames.size();++g) {
            frames[g].geom=&context->geoms[g];
            std::copy(positions+3*g,positions+3*g+3,frames[g].p.begin());
            std::copy(rotations+9*g,rotations+9*g+9,frames[g].R.begin());
        }
        for (std::int64_t i=0;i<count;++i) {
            const auto a=pairs[2*i],b=pairs[2*i+1];
            Result result;
            if (a<0||b<0||static_cast<std::size_t>(a)>=frames.size()||static_cast<std::size_t>(b)>=frames.size()) result.reason=6;
            else result=pair_result(frames[a],frames[b],margin);
            write_result(result,output+i*NFLOAT,flags+i*NINT);
        }
        return 0;
    } catch (...) {
        // Allocation/arithmetic exceptions invalidate the entire result frame.
        failed.reason=3;
        for (std::int64_t i=0;i<count;++i) write_result(failed,output+i*NFLOAT,flags+i*NINT);
        return 0;
    }
}

// Caller-owned G x 3 x 2 IDs. Context retains no mutable witness state.
// All input/output regions must be nonoverlapping and have their ABI lengths.
// Equal hint pointers are rejected; partial overlap is outside this contract.
// A malformed ID is discarded without altering the original result policy.
int ns_evaluate_hinted(void* raw,const double* positions,const double* rotations,
                       const std::int64_t* pairs,std::int64_t count,double margin,
                       double* output,std::int64_t* flags,
                       const std::int64_t* hint_in,std::int64_t* hint_out) {
    if (!raw||!positions||!rotations||!pairs||!output||!flags||!hint_in||!hint_out||
            hint_in==hint_out||count<0) return 1;
    auto* context=static_cast<Context*>(raw);
    Result failed;
    if (!environment()) failed.reason=5;
    else if (!std::isfinite(margin)||margin<=0.) failed.reason=4;
    bool frame_valid=failed.reason==0;
    for (std::size_t g=0;g<context->geoms.size()&&frame_valid;++g) {
        for (int j=0;j<3;++j) frame_valid &= std::isfinite(positions[g*3+j]);
        for (int j=0;j<9;++j) frame_valid &= std::isfinite(rotations[g*9+j]);
    }
    std::fill(hint_out,hint_out+6*context->geoms.size(),std::int64_t{-1});
    if (!frame_valid) {
        if (!failed.reason) failed.reason=3;
        for (std::int64_t i=0;i<count;++i) write_result(failed,output+i*NFLOAT,flags+i*NINT);
        return 0;
    }
    try {
        const bool enabled=witness_traps_masked();
        std::vector<Frame> frames(context->geoms.size());
        for (std::size_t g=0;g<frames.size();++g) {
            frames[g].geom=&context->geoms[g];
            std::copy(positions+3*g,positions+3*g+3,frames[g].p.begin());
            std::copy(rotations+9*g,rotations+9*g+9,frames[g].R.begin());
            if (context->geoms[g].kind==1) {
                for (int k=0;k<6;++k) {
                    const auto id=hint_in[6*g+k];
                    if (id>=0 && static_cast<std::uint64_t>(id)<context->geoms[g].points.size()/3)
                        hint_out[6*g+k]=id;
                }
                if (enabled) {
                    frames[g].hint_in=hint_in+6*g;
                    frames[g].hint_out=hint_out+6*g;
                }
            }
        }
        for (std::int64_t i=0;i<count;++i) {
            const auto a=pairs[2*i],b=pairs[2*i+1];
            Result result;
            if (a<0||b<0||static_cast<std::size_t>(a)>=frames.size()||static_cast<std::size_t>(b)>=frames.size()) result.reason=6;
            else result=pair_result(frames[a],frames[b],margin);
            write_result(result,output+i*NFLOAT,flags+i*NINT);
        }
        return 0;
    } catch (...) {
        failed.reason=3;
        std::fill(hint_out,hint_out+6*context->geoms.size(),std::int64_t{-1});
        for (std::int64_t i=0;i<count;++i) write_result(failed,output+i*NFLOAT,flags+i*NINT);
        return 0;
    }
}
#if defined(SUPPORT_TREE_TESTS)
// Isolated test builds only: force the full-support branch independently of
// the preceding coarse-AABB gate, and inspect complete leaf coverage.
int ns_test_full_vertices(std::int64_t count,const double* points,const double* coefficients,
                          int tree,double* output,std::int64_t* info) {
    if (count<=0||!points||!coefficients||!output||!info||!environment()) return 2;
    try {
        Geometry geom;geom.kind=1;geom.points.assign(points,points+3*count);
        for (double x:geom.points) if (!std::isfinite(x)) return 2;
        geom.order.resize(static_cast<std::size_t>(count));
        std::iota(geom.order.begin(),geom.order.end(),std::size_t{0});
        build_node(geom,0,geom.order.size());
        std::vector<int> seen(geom.order.size(),0);
        std::size_t largest=0;
        for (const auto& node:geom.nodes) if (node.left==NO_CHILD) {
            largest=std::max(largest,node.end-node.begin);
            for (std::size_t k=node.begin;k<node.end;++k) ++seen[geom.order[k]];
        }
        info[0]=std::all_of(seen.begin(),seen.end(),[](int x){return x==1;});
        info[1]=static_cast<std::int64_t>(geom.nodes.size());
        info[2]=static_cast<std::int64_t>(largest);
        std::array<Interval,3> local;
        for (int j=0;j<3;++j) local[j]={coefficients[2*j],coefficients[2*j+1]};
        Interval result{NAN_VALUE,NAN_VALUE};bool fallback=false;
        const bool valid=tree?full_tree(geom,local,result,&fallback):full_scan(geom,local,result);
        output[0]=result.lo;output[1]=result.hi;info[3]=fallback;
        return valid?0:1;
    } catch (...) { return 2; }
}

int ns_test_full_vertices_hinted(std::int64_t count,const double* points,const double* coefficients,
                                const std::int64_t* hints,double* output,
                                std::int64_t* winners,std::int64_t* info) {
    if (count<=0||!points||!coefficients||!hints||!output||!winners||!info||!environment()) return 2;
    struct TraceGuard {
        WitnessTrace* previous;
        explicit TraceGuard(WitnessTrace* trace):previous(witness_trace) { witness_trace=trace; }
        ~TraceGuard() { witness_trace=previous; }
    };
    try {
        Geometry geom;geom.kind=1;geom.points.assign(points,points+3*count);
        for (double x:geom.points) if (!std::isfinite(x)) return 2;
        geom.order.resize(static_cast<std::size_t>(count));
        std::iota(geom.order.begin(),geom.order.end(),std::size_t{0});
        build_node(geom,0,geom.order.size());
        std::array<Interval,3> local;
        for (int j=0;j<3;++j) local[j]={coefficients[2*j],coefficients[2*j+1]};
        WitnessTrace trace;TraceGuard guard(&trace);
        Interval result{NAN_VALUE,NAN_VALUE};bool fallback=false;
        winners[0]=winners[1]=-1;
        const bool enabled=witness_traps_masked();
        const bool valid=full_tree(geom,local,result,&fallback,enabled?hints:nullptr,
                                  enabled?winners:nullptr);
        output[0]=result.lo;output[1]=result.hi;
        info[0]=enabled;info[1]=trace.attempted;info[2]=trace.finite_points;
        info[3]=trace.discarded;info[4]=trace.merged;info[5]=fallback;
        return valid?0:1;
    } catch (...) { return 2; }
}

std::uint32_t ns_test_witness_get_mxcsr() {
#if defined(__SSE__)
    return _mm_getcsr();
#else
    return 0;
#endif
}
void ns_test_witness_set_mxcsr(std::uint32_t csr) {
#if defined(__SSE__)
    _mm_setcsr(csr);
#else
    (void)csr;
#endif
}
int ns_test_witness_traps_masked() { return witness_traps_masked()?1:0; }
#endif
} // extern C
