/* Copyright 2023 The FedLearner Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.bytedance.aml.enterprise.sparkudaf

import org.apache.spark.sql.expressions.Aggregator
import org.apache.spark.sql.{Encoder, Encoders}

case class HistIn(var value: Double, var min: Double, var max: Double, var binsNum: Int, var interval: Double)
case class Bucket(var bins: Array[Double], var counts: Array[Int])

object HistUDAF extends Aggregator[HistIn, Bucket, Bucket]{

  def zero: Bucket = Bucket(bins = new Array[Double](0), counts = new Array[Int](0))

  def reduce(buffer: Bucket, data: HistIn): Bucket = {
    if (buffer.bins.length == 0) {
      buffer.bins = new Array[Double](data.binsNum + 1)
      for (i <- 0 until data.binsNum) {
        buffer.bins(i) = i * data.interval + data.min
      }
      buffer.bins(data.binsNum) = data.max
      buffer.counts = new Array[Int](data.binsNum)
    }
    if (data.interval != 0.0){
      var bucket_idx = ((data.value - data.min) / data.interval).toInt
      if (bucket_idx < 0) {
        bucket_idx = 0
      } else if (bucket_idx > (data.binsNum - 1)){
        bucket_idx = data.binsNum - 1
      }
      buffer.counts(bucket_idx) += 1
    }
    buffer
  }


  def merge(b1: Bucket, b2: Bucket): Bucket = {
    (b1.bins.length, b2.bins.length) match {
      case (_, 0) => b1
      case (0, _) => b2
      case _ => b1.counts = (b1.counts zip b2.counts) map (x => x._1 + x._2)
        b1
    }
  }

  def finish(reduction: Bucket): Bucket = reduction

  def bufferEncoder: Encoder[Bucket] = Encoders.product

  def outputEncoder: Encoder[Bucket] = Encoders.product

}