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

package com.bytedance.aml.enterprise.sparkudf;

import org.apache.spark.sql.api.java.UDF1;
import com.bytedance.aml.enterprise.sm4.SM4Utils;

public class SM4 implements UDF1<String, String> {
    private static final String SECRET_STR = "64EC7C763AB7BF64E2D75FF83A319910";

    @Override
    public String call(String raw) throws Exception {
        SM4Utils sm4 = new SM4Utils();
        sm4.secretKey = SECRET_STR;
        sm4.hexString = true;
        return sm4.encryptDataECB(raw);
    }
}
