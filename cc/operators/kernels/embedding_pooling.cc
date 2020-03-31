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

#include "tensorflow/core/framework/register_types.h"
#include "tensorflow/core/framework/op_kernel.h"
#include "embedding_pooling.h"

#include "../utils/common.h"

namespace tensorflow {

using CPUDevice = Eigen::ThreadPoolDevice;
using GPUDevice = Eigen::GpuDevice;

namespace functor {

template <typename T, typename Tidx>
struct LagrangeEmbeddingPoolingFunctor<CPUDevice, T, Tidx> {
    static Status Compute(OpKernelContext *context,
                          int num_shards,
                          bool use_fid_v2,
                          typename TTypes<Tidx, 1>::ConstTensor &instance_ids,
                          typename TTypes<Tidx, 1>::ConstTensor &fids,
                          const std::vector<typename TTypes<T, 2>::ConstTensor> &weights,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_size,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_weight_index,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_output_offset,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_hash_size,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_weight_offset,
                          typename TTypes<T, 2>::Tensor &output) {
        auto fid_count = instance_ids.dimension(0);
        output.setZero();
        // #pragma omp parallel for
        for (Tidx i = 0; i < fid_count; ++i) {
            Tidx instance_id = instance_ids(i);
            uint64 fid = static_cast<uint64>(fids(i));
            uint64 slot_id = neo::get_slot(fid, use_fid_v2);

            Tidx size = slot_size(slot_id);
            if (size == 0) continue;
            Tidx weight_index = slot_weight_index(slot_id);
            Tidx output_offset = slot_output_offset(slot_id);

            // partition strategy is 'mod' strategy
            // divide the num_shards when partition the emb table
            Tidx vec_offset = (slot_weight_offset(slot_id) + neo::hash_fid(fid, slot_hash_size(slot_id), use_fid_v2)) / num_shards;
            for (Tidx j = 0; j < size; ++j) {
                output(instance_id, output_offset + j) += weights[weight_index](vec_offset, j);
                // neo::atomic_addf(reinterpret_cast<std::atomic<T>&>(output(instance_id, output_offset + j)), 
                //                                                    weights[weight_index](vec_offset, j));
            }
        }
        return Status::OK();
    }
};

template <typename T, typename Tidx>
struct LagrangeEmbeddingUnpoolingFunctor<CPUDevice, T, Tidx> {
    static Status Compute(OpKernelContext *context,
                          bool use_fid_v2,
                          typename TTypes<T, 2>::ConstTensor &output_grads,
                          typename TTypes<Tidx, 1>::ConstTensor &instance_ids,
                          typename TTypes<Tidx, 1>::ConstTensor &fids,
                          typename TTypes<Tidx, 1>::ConstTensor &fid_to_unique_index,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_size,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_weight_index,
                          typename TTypes<Tidx, 1>::ConstTensor &slot_output_offset,
                          std::vector<typename TTypes<T, 2>::Tensor> &output) {
        auto num_fids = fids.dimension(0);
        for (auto value: output) {
            value.setZero();
        }
        // #pragma omp parallel for
        for (Tidx i = 0; i < num_fids; ++i) {
            Tidx instance_id = instance_ids(i);
            uint64 fid = static_cast<uint64>(fids(i));
            Tidx idx = fid_to_unique_index(i);

            uint64 slot_id = neo::get_slot(fid, use_fid_v2);
            Tidx size = slot_size(slot_id);
            Tidx weight_index = slot_weight_index(slot_id);
            Tidx output_offset = slot_output_offset(slot_id);

            for (Tidx j = 0; j < size; ++j) {
                output[weight_index](idx, j) += output_grads(instance_id, output_offset + j);
            }
        }

        return Status::OK();
    }
};

} // namespace functor

// Partition fids to multiple devices
template <typename Device, typename Tidx>
class LagrangeMultiDevicePreprocessFidOp : public OpKernel {
public:
    explicit LagrangeMultiDevicePreprocessFidOp(OpKernelConstruction *context) : 
        OpKernel(context) {
        OP_REQUIRES_OK(context, context->GetAttr("num_weights", &num_weights_));
        OP_REQUIRES_OK(context, context->GetAttr("num_shards", &num_shards_));
        OP_REQUIRES_OK(context, context->GetAttr("use_fid_v2", &use_fid_v2_));
    }

    void Compute(OpKernelContext *context) override {
        auto instance_ids = context->input(0).flat<Tidx>();
        auto fids = context->input(1).flat<Tidx>();
        auto slot_weight_index = context->input(2).flat<Tidx>();
        auto slot_hash_size = context->input(3).flat<Tidx>();
        auto slot_weight_offset = context->input(4).flat<Tidx>();
        
        std::vector<std::pair<uint64, int64> > sorted_fids;
        sorted_fids.reserve(fids.dimension(0));
        std::vector<int> num_fids_per_device(num_shards_, 0);

        for (Tidx i = 0; i < fids.dimension(0); ++i) {
            uint64 fid = static_cast<uint64>(fids(i));
            uint64 slot_id = neo::get_slot(fid, use_fid_v2_);
            Tidx weight_index = slot_weight_index(slot_id);
            if (weight_index < 0) continue;
            Tidx instance_id = instance_ids(i);
            sorted_fids.emplace_back(fid, instance_id);

            // Partition strategy: mod strategy
            Tidx vec_offset = slot_weight_offset(slot_id) + neo::hash_fid(fid, slot_hash_size(slot_id), use_fid_v2_); 
            auto device_id = vec_offset % num_shards_;
            num_fids_per_device[device_id]++;
        }
        std::sort(sorted_fids.begin(), sorted_fids.end(),
            [](const std::pair<uint64, int64>& a, const std::pair<uint64, int64>& b) {
                return a.first < b. first;
            });
        
        int64 num_fids = static_cast<int64>(sorted_fids.size());

        OpOutputList output_instance_ids_list;
        OpOutputList output_fids_list;
        OpOutputList num_unique_fids_per_partition_list;
        OpOutputList fid_to_unique_index_list;
        
        OP_REQUIRES_OK(context, context->output_list("output_instance_ids", 
                                                     &output_instance_ids_list));
        OP_REQUIRES_OK(context, context->output_list("output_fids", 
                                                     &output_fids_list));
        OP_REQUIRES_OK(context, context->output_list("num_unique_fids_per_partition", 
                                                     &num_unique_fids_per_partition_list));
        OP_REQUIRES_OK(context, context->output_list("fid_to_unique_index", 
                                                     &fid_to_unique_index_list));

        std::vector<typename TTypes<Tidx, 1>::Tensor> output_instance_ids;
        std::vector<typename TTypes<Tidx, 1>::Tensor> output_fids;
        std::vector<typename TTypes<Tidx, 1>::Tensor> num_unique_fids_per_partition;
        std::vector<typename TTypes<Tidx, 1>::Tensor> fid_to_unique_index;
        
        // Allocate output for each device
        for (int i = 0; i < num_shards_; ++i) {
            Tensor* instance_id_tensor = nullptr;
            Tensor* fid_tensor = nullptr;
            Tensor* num_unique_fids_per_partition_tensor = nullptr;
            Tensor* fid_to_unique_index_tensor = nullptr;
            OP_REQUIRES_OK(context, 
                           output_instance_ids_list.allocate(i, {num_fids_per_device[i]}, &instance_id_tensor));
            OP_REQUIRES_OK(context,
                           output_fids_list.allocate(i, {num_fids_per_device[i]}, &fid_tensor));
            OP_REQUIRES_OK(context,
                           num_unique_fids_per_partition_list.allocate(i, {num_weights_},
                           &num_unique_fids_per_partition_tensor));
            OP_REQUIRES_OK(context,
                           fid_to_unique_index_list.allocate(i, {num_fids_per_device[i]},
                           &fid_to_unique_index_tensor));
            output_instance_ids.push_back(instance_id_tensor->tensor<Tidx, 1>());
            output_fids.push_back(fid_tensor->tensor<Tidx, 1>());
            num_unique_fids_per_partition.push_back(num_unique_fids_per_partition_tensor->tensor<Tidx, 1>());
            fid_to_unique_index.push_back(fid_to_unique_index_tensor->flat<Tidx>());
        }

        for (auto& partition: num_unique_fids_per_partition) {
            partition.setZero();
        }

        uint64 last_fid;
        std::vector<int> device_index(num_shards_, 0);
        for (size_t i = 0; i < sorted_fids.size(); ++i) {
            uint64 fid = sorted_fids[i].first;
            uint64 slot_id = neo::get_slot(fid, use_fid_v2_);
            Tidx weight_index = slot_weight_index(slot_id);
            int device_id = (slot_weight_offset(slot_id) + neo::hash_fid(fid, slot_hash_size(slot_id), use_fid_v2_)) % num_shards_; 
            int index = device_index[device_id]++;
            output_instance_ids[device_id](index) = sorted_fids[i].second;
            output_fids[device_id](index) = static_cast<Tidx>(sorted_fids[i].first);
            if (i == 0 || sorted_fids[i].first != last_fid) {
                last_fid = fid;
                num_unique_fids_per_partition[device_id](weight_index)++;
            }
        }

        OP_REQUIRES(context, std::accumulate(device_index.begin(), device_index.end(), 0) == sorted_fids.size(),
                    errors::InvalidArgument("Error in device index"));

        OpOutputList unique_fid_hash_list;
        OP_REQUIRES_OK(context, context->output_list("unique_fid_hash", 
              /* num_shards * num_weights * Tidx */ &unique_fid_hash_list)); 
        std::vector<typename TTypes<Tidx, 1>::Tensor> unique_fid_hash;
        for (int i = 0; i < num_shards_; ++i) {
            for (int j = 0; j < num_weights_; ++j) {
                Tensor* unique_fid_hash_tensor = nullptr;
                OP_REQUIRES_OK(context,
                    unique_fid_hash_list.allocate(i*num_weights_+j, {num_unique_fids_per_partition[i](j)},
                                                  &unique_fid_hash_tensor));
                unique_fid_hash.push_back(unique_fid_hash_tensor->tensor<Tidx, 1>());
            }
        }

        for (int i = 0; i < num_shards_; ++i) {
            std::vector<int64_t> counts(num_weights_, -1);
            auto& fid_shard = output_fids[i];
            uint64 last_fid;
            for (int j = 0; j < num_fids_per_device[i]; ++j) {
                uint64 slot_id = neo::get_slot(fid_shard(j), use_fid_v2_);
                Tidx weight_index = slot_weight_index(slot_id);
                if (j == 0 || fid_shard(j) != last_fid) {
                    last_fid = fid_shard(j);
                    ++counts[weight_index];
                    unique_fid_hash[i * num_weights_ + weight_index](counts[weight_index]) = 
                        (slot_weight_offset(slot_id) + neo::hash_fid(fid_shard(j), slot_hash_size(slot_id), use_fid_v2_)) / num_shards_;
                }
                fid_to_unique_index[i](j) = counts[weight_index];
            }
            for (int k = 0; k < num_weights_; ++k) {
                OP_REQUIRES(context, counts[k] == num_unique_fids_per_partition[i](k) - 1,
                    errors::InvalidArgument("invalid count ", counts[i], " vs ", num_unique_fids_per_partition[i](k)));
            }
        }
    }

private:
    int num_weights_;
    int num_shards_;
    bool use_fid_v2_;
};

template <typename Device, typename T, typename Tidx>
class LagrangeEmbeddingPoolingOp : public OpKernel {
public:
    explicit LagrangeEmbeddingPoolingOp(OpKernelConstruction *context) : OpKernel(context) {
        OP_REQUIRES_OK(context, context->GetAttr("output_size", &output_size_));
        OP_REQUIRES_OK(context, context->GetAttr("num_shards", &num_shards_));
        OP_REQUIRES_OK(context, context->GetAttr("use_fid_v2", &use_fid_v2_));
    }

    void Compute(OpKernelContext *context) override {
        auto batch_size = context->input(0).flat<Tidx>()(0);
        auto instance_ids = context->input(1).flat<Tidx>();
        auto fids = context->input(2).flat<Tidx>();
        auto slot_size = context->input(3).flat<Tidx>();
        auto slot_weight_index = context->input(4).flat<Tidx>();
        auto slot_output_offset = context->input(5).flat<Tidx>();
        auto slot_hash_size = context->input(6).flat<Tidx>();
        auto slot_weight_offset = context->input(7).flat<Tidx>();

        OpInputList weight_list;
        OP_REQUIRES_OK(context, context->input_list("weights", &weight_list));
        auto num_weights = weight_list.size();
        std::vector<typename TTypes<T, 2>::ConstTensor> weights;
        for (int i = 0; i < weight_list.size(); ++i) {
            weights.push_back(weight_list[i].tensor<T, 2>());
        }
        Tensor *output_tensor = nullptr;
        OP_REQUIRES_OK(context,
                       context->allocate_output(0, {batch_size, output_size_}, &output_tensor));
        auto output = output_tensor->tensor<T, 2>();

        OP_REQUIRES_OK(
             context,
             functor::LagrangeEmbeddingPoolingFunctor<Device, T, Tidx>::Compute(
                 context,
                 num_shards_,
                 use_fid_v2_,
                 instance_ids,
                 fids,
                 weights,
                 slot_size,
                 slot_weight_index,
                 slot_output_offset,
                 slot_hash_size,
                 slot_weight_offset,
                 output));
    }

private:
    int64 output_size_;
    int num_shards_;
    bool use_fid_v2_;
};


template <typename Device, typename T, typename Tidx>
class LagrangeEmbeddingUnpoolingOp : public OpKernel {
public:
    explicit LagrangeEmbeddingUnpoolingOp(OpKernelConstruction *context) : OpKernel(context) {
        OP_REQUIRES_OK(context, context->GetAttr("num_weights", &num_weights_));
        OP_REQUIRES_OK(context, context->GetAttr("weight_sizes", &weight_sizes_));
        OP_REQUIRES_OK(context, context->GetAttr("use_fid_v2", &use_fid_v2_));
    }

    void Compute(OpKernelContext *context) override {
        auto output_grad = context->input(0).tensor<T, 2>();
        auto instance_ids = context->input(1).flat<Tidx>();
        auto fids = context->input(2).flat<Tidx>();
        auto fid_to_unique_index = context->input(3).flat<Tidx>();
        auto num_unique_fids_per_partition = context->input(4).flat<Tidx>();
        auto slot_size = context->input(5).flat<Tidx>();
        auto slot_weight_index = context->input(6).flat<Tidx>();
        auto slot_output_offset = context->input(7).flat<Tidx>();

        OpOutputList values_list;
        OP_REQUIRES_OK(context, context->output_list("values", &values_list));
        std::vector<typename TTypes<T, 2>::Tensor> values;
        for (int i = 0; i < num_weights_; ++i) {
            Tensor* value_tensor = nullptr;
            OP_REQUIRES_OK(context,
                           values_list.allocate(i, {num_unique_fids_per_partition(i), weight_sizes_[i]}, &value_tensor));
            values.push_back(value_tensor->tensor<T, 2>());
        }

        OP_REQUIRES_OK(
             context,
             functor::LagrangeEmbeddingUnpoolingFunctor<Device, T, Tidx>::Compute(
                 context,
                 use_fid_v2_,
                 output_grad,
                 instance_ids,
                 fids,
                 fid_to_unique_index,
                 slot_size,
                 slot_weight_index,
                 slot_output_offset,
                 values));
    }

private:
    int num_weights_;
    std::vector<int64> weight_sizes_;
    bool use_fid_v2_;
};


REGISTER_KERNEL_BUILDER(Name("LagrangeMultiDevicePreprocessFid")
                            .Device(DEVICE_CPU)
                            .TypeConstraint<int64>("Tidx"),
                        LagrangeMultiDevicePreprocessFidOp<CPUDevice, int64>);

REGISTER_KERNEL_BUILDER(Name("LagrangeEmbeddingPooling")
                            .Device(DEVICE_CPU)
                            .TypeConstraint<float>("T")
                            .TypeConstraint<int64>("Tidx"),
                        LagrangeEmbeddingPoolingOp<CPUDevice, float, int64>);

REGISTER_KERNEL_BUILDER(Name("LagrangeEmbeddingUnpooling")
                            .Device(DEVICE_CPU)
                            .TypeConstraint<float>("T")
                            .TypeConstraint<int64>("Tidx"),
                        LagrangeEmbeddingUnpoolingOp<CPUDevice, float, int64>);

} // namespace tensorflow

