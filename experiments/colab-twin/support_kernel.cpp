// Diagnostic-only binary64 support certificates. No fast math, FMA or threads.
// Compile: -O3 -fno-fast-math -ffp-contract=off -frounding-math -std=c++17.
#include <algorithm>
#include <array>
#include <cfenv>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <new>
#include <unordered_map>
#include <vector>
#if defined(__SSE__)
#include <xmmintrin.h>
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

struct Geometry {
    std::vector<double> points;
    Vec low{}, high{};
    int kind=0; // 0 finite box, 1 original mesh.
};
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
    Vec p{}; std::array<double,9> R{};
    std::unordered_map<Key,Interval,KeyHash> cache;
};

bool project(Frame& shape, const Vec& n, bool full, Interval& answer) {
    Key key{{bits(n[0]),bits(n[1]),bits(n[2])},full};
    // Python float cache keys identify +0 and -0. Keep that exact equality.
    for (auto& raw:key.n) if ((raw&~SIGN)==0) raw=0;
    const auto cached=shape.cache.find(key);
    if (cached!=shape.cache.end()) { answer=cached->second; return true; }
    std::array<Interval,3> ni{exact(n[0]),exact(n[1]),exact(n[2])},local;
    for (int j=0;j<3;++j) {
        std::array<Interval,3> column{exact(shape.R[j]),exact(shape.R[3+j]),exact(shape.R[6+j])};
        local[j]=dot(column,ni);
    }
    const Interval center=dot({exact(shape.p[0]),exact(shape.p[1]),exact(shape.p[2])},ni);
    if (!finite(center) || !finite(local[0]) || !finite(local[1]) || !finite(local[2])) return false;
    Interval extrema;
    if (!full || shape.geom->kind==0) {
        std::array<Interval,3> bounds;
        for (int j=0;j<3;++j) bounds[j]={shape.geom->low[j],shape.geom->high[j]};
        extrema=dot(bounds,local);
    } else {
        double minimum=INF,maximum=-INF;
        const auto& points=shape.geom->points;
        for (std::size_t v=0;v<points.size();v+=3) {
            double low=0.,high=0.;
            for (int j=0;j<3;++j) {
                const double first=points[v+j]*local[j].lo;
                const double second=points[v+j]*local[j].hi;
                if (!std::isfinite(first)||!std::isfinite(second)) return false;
                // NumPy minimum/maximum choose the second operand on a tie.
                const double term_low=down(first<second?first:second);
                const double term_high=up(first>second?first:second);
                low=down(low+term_low);
                high=up(high+term_high);
                // Do not allow a later NaN to disappear in an extrema reduce.
                // Original NumPy full-array support refuses that whole shape.
                if (!std::isfinite(low)||!std::isfinite(high)) return false;
            }
            minimum=std::min(minimum,low); maximum=std::max(maximum,high);
        }
        extrema={minimum,maximum};
    }
    answer=add(center,extrema);
    if (!finite(answer)) return false;
    shape.cache.emplace(key,answer);
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
    std::array<bool,19> valid;
    fixed[0]={1.,0.,0.}; fixed[1]={0.,1.,0.}; fixed[2]={0.,0.,1.};
    fixed[3]={b.p[0]-a.p[0],b.p[1]-a.p[1],b.p[2]-a.p[2]};
    for (int j=0;j<3;++j) { fixed[4+j]=column(a,j); fixed[7+j]=column(b,j); }
    for (int j=0;j<3;++j) for (int k=0;k<3;++k) fixed[10+3*j+k]=cross(column(a,j),column(b,k));
    for (int i=0;i<19;++i) valid[i]=normalize(fixed[i]);
    Result best; bool has_best=false; std::int64_t count=0;
    for (bool full:{false,true}) for (int i=0;i<19;++i) {
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
} // extern C
