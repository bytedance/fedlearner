// Copyright 2020 The FedLearner Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef FEDLEARNER_CC_OPERATORS_UTILS_COMMON_H_
#define FEDLEARNER_CC_OPERATORS_UTILS_COMMON_H_

namespace neo {

constexpr uint64_t SLOT_BIT = 10;
constexpr uint64_t SLOT_BIT_v2 = 15;

constexpr uint64_t FEATURE_BIT = sizeof(uint64_t) * 8 - SLOT_BIT;
constexpr uint64_t FEATURE_BIT_v2 = sizeof(uint64_t) * 8 - SLOT_BIT_v2 - 1;

constexpr uint64_t FEATURE_MASK = (((uint64_t)1) << FEATURE_BIT) - 1;
constexpr uint64_t FEATURE_MASK_v2 = (((uint64_t)1) << FEATURE_BIT_v2) - 1;

constexpr uint64_t MAX_SLOT = 1 << SLOT_BIT;
constexpr uint64_t MAX_SLOT_v2 = 1 << SLOT_BIT_v2;

inline uint64_t get_slot_v2(uint64_t fid) {
    return fid >> FEATURE_BIT_v2;
}

inline uint64_t get_slot(uint64_t fid, bool use_fid_v2=false) {
    if (use_fid_v2) return get_slot_v2(fid);
    return fid >> FEATURE_BIT;
}

inline uint64_t hash_fid_v2(uint64_t fid, uint64_t hash_size) {
    return (fid & FEATURE_MASK_v2) % hash_size;
}

inline uint64_t hash_fid(uint64_t fid, uint64_t hash_size, bool use_fid_v2=false) {
    if (use_fid_v2) return hash_fid_v2(fid, hash_size);
    return (fid & FEATURE_MASK) % hash_size;
}

inline uint64_t to_fid_v2(uint64_t fid_v1) {
    uint64_t feature = fid_v1 & FEATURE_MASK_v2;
    uint64_t slot = get_slot(fid_v1);
    uint64_t fid_v2 = (slot << FEATURE_BIT_v2) | feature;
    return fid_v2;
}

inline float atomic_addf(std::atomic<float> &f, float d){
    float old = f.load(std::memory_order_consume);
    float desired = old + d;
    while (!f.compare_exchange_weak(old, desired,
        std::memory_order_release, std::memory_order_consume))
    {
        desired = old + d;
    }
    return desired;
}

}  // namespace

#endif // LAGRANGE_LITE_OPERATORS_COMMON_H_
