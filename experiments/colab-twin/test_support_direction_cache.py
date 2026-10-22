"""Compare optional storage with the original map, including forced overflow."""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

import support_native as native


PROBE = r'''
extern "C" int ns_probe_direction_cache(std::uint64_t* output) {
    Frame shape;
    std::unordered_map<Key,Interval,KeyHash> reference;
    Key missing{{0,0,0},false};
    if (frame_cache_find(shape,missing) || shape.small_dir || shape.overflow_cache) return 1;
    for (std::uint64_t step=0;step<160;++step) {
        // Repeated keys, distinct full flags, and exact zero/subnormal bit words.
        const auto id=step%67;
        Key key{{id,(id%2)?SIGN:id,id%3},id%2!=0};
        Interval answer{value(SIGN|step),value(step)};
        frame_cache_insert(shape,key,answer);
        reference.emplace(key,answer);
        for (const auto& entry:reference) {
            const auto* found=frame_cache_find(shape,entry.first);
            if (!found || bits(found->lo)!=bits(entry.second.lo) ||
                          bits(found->hi)!=bits(entry.second.hi)) return 2;
        }
        if (reference.size()<=Frame::small_dir_cap && shape.overflow_cache) return 3;
        if (reference.size()>Frame::small_dir_cap && (!shape.overflow_cache || shape.small_dir)) return 4;
    }
    output[0]=reference.size();output[1]=Frame::small_dir_cap;
    return 0;
}
'''


class DirectionCacheTests(unittest.TestCase):
    def test_original_map_semantics_and_lazy_storage_with_both_capacities(self):
        source = native._KERNEL_PATH.read_text()
        compiler = native._compiler_identity()['path']
        for capacity in (16, 1):
            with self.subTest(capacity=capacity), tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                body = source.replace('small_dir_cap = 16;', f'small_dir_cap = {capacity};', 1)
                cpp, library = folder/'kernel.cpp', folder/'kernel.so'
                cpp.write_text(body+PROBE)
                result = native._compile_process([compiler, *native._FLAGS,
                    '-DSUPPORT_SMALL_DIRECTION_CACHE', str(cpp), '-o', str(library)])
                self.assertEqual(result.returncode, 0, result.stderr)
                lib = C.CDLL(str(library))
                lib.ns_probe_direction_cache.argtypes = [C.POINTER(C.c_uint64)]
                lib.ns_probe_direction_cache.restype = C.c_int
                output = (C.c_uint64*2)()
                self.assertEqual(lib.ns_probe_direction_cache(output), 0)
                self.assertEqual(list(output), [67, capacity])


if __name__ == '__main__':
    unittest.main()
