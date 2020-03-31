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

#include "tensorflow/core/framework/op.h"
#include "tensorflow/core/framework/common_shape_fns.h"

namespace tensorflow {

REGISTER_OP("LagrangeMultiDevicePreprocessFid")
    .Attr("Tidx: {int64}")
    .Attr("num_weights: int >= 1")
    .Attr("num_shards: int >= 1")
    .Attr("total_weights: int >= 1")
    .Attr("use_fid_v2: bool = false")
    .Input("instance_ids: Tidx")
    .Input("fids: Tidx")
    .Input("slot_weight_index: Tidx")
    .Input("slot_hash_size: Tidx")
    .Input("slot_weight_offset: Tidx")
    .Output("output_instance_ids: num_shards * Tidx")
    .Output("output_fids: num_shards * Tidx")
    .Output("num_unique_fids_per_partition: num_shards * Tidx")
    .Output("fid_to_unique_index: num_shards * Tidx")
    .Output("unique_fid_hash: total_weights * Tidx");


REGISTER_OP("LagrangeEmbeddingPooling")
    .Attr("T: {float16, float32}")
    .Attr("Tidx: {int64}")
    .Attr("output_size: int")
    .Attr("num_weights: int >= 1")
    .Attr("num_shards: int = 1")
    .Attr("weight_sizes: list(int)")
    .Attr("use_fid_v2: bool = false")
    .Input("batch_size: Tidx")
    .Input("instance_ids: Tidx")
    .Input("fids: Tidx")
    .Input("slot_size: Tidx")
    .Input("slot_weight_index: Tidx")
    .Input("slot_output_offset: Tidx")
    .Input("slot_hash_size: Tidx")
    .Input("slot_weight_offset: Tidx")
    .Input("weights: num_weights * T")
    .Output("output: T")
    .SetShapeFn([](shape_inference::InferenceContext* c) {
        int64 output_size;
        TF_RETURN_IF_ERROR(c->GetAttr("output_size", &output_size));

        PartialTensorShape partial;
        int64 dim[2];
        dim[0] = -1;
        dim[1] = output_size;
        TF_RETURN_IF_ERROR(PartialTensorShape::MakePartialShape(dim, 2, &partial));

        shape_inference::ShapeHandle shape;
        TF_RETURN_IF_ERROR(c->MakeShapeFromPartialTensorShape(partial, &shape));

        c->set_output(0, shape);
        return Status::OK();
    });


REGISTER_OP("LagrangeEmbeddingUnpooling")
    .Attr("T: {float16, float32}")
    .Attr("Tidx: {int64}")
    .Attr("num_weights: int >= 1")
    .Attr("weight_sizes: list(int)")
    .Attr("num_shards: int = 1")
    .Attr("use_fid_v2: bool = false")
    .Input("output_grad: T")
    .Input("instance_ids: Tidx")
    .Input("fids: Tidx")
    .Input("fid_to_unique_index: Tidx")
    .Input("num_unique_fids_per_partition: Tidx")
    .Input("slot_size: Tidx")
    .Input("slot_weight_index: Tidx")
    .Input("slot_output_offset: Tidx")
    .Output("values: num_weights * T");


} // namespace tensorflow

