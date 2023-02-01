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

package com.bytedance.aml.enterprise.sm4;

import com.bytedance.aml.enterprise.util.Util;
import org.apache.commons.codec.binary.Base64;

import java.nio.charset.StandardCharsets;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class SM4Utils {

    public String secretKey = "";
    public String iv = "";
    public boolean hexString = false;

    public String encryptDataECB(String plainText) {
        try {
            SM4Context ctx = new SM4Context();
            ctx.isPadding = true;
            ctx.mode = SM4.SM4_ENCRYPT;

            byte[] keyBytes;
            keyBytes = Util.hexStringToBytes(secretKey);

            SM4 sm4 = new SM4();
            sm4.sm4SetKeyEnc(ctx, keyBytes);
            byte[] encrypted = sm4.sm4CryptECB(ctx, plainText.getBytes(StandardCharsets.UTF_8));
            return Util.byteToHex(encrypted);
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public String decryptDataECB(String cipherText) {
        try {
            byte[] encrypted = Util.hexToByte(cipherText);
            cipherText= Base64.encodeBase64String(encrypted);
            if (cipherText != null && cipherText.trim().length() > 0) {
                Pattern p = Pattern.compile("\\s*|\t|\r|\n");
                Matcher m = p.matcher(cipherText);
                cipherText = m.replaceAll("");
            }

            SM4Context ctx = new SM4Context();
            ctx.isPadding = true;
            ctx.mode = SM4.SM4_DECRYPT;

            byte[] keyBytes;
            if (hexString) {
                keyBytes = Util.hexStringToBytes(secretKey);
            } else {
                keyBytes = secretKey.getBytes();
            }

            SM4 sm4 = new SM4();
            sm4.sm4SetKeyDec(ctx, keyBytes);
            byte[] decrypted = sm4.sm4CryptECB(ctx, Base64.decodeBase64(cipherText));
            return new String(decrypted, StandardCharsets.UTF_8);
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public String encryptDataCBC(String plainText) {
        try {
            SM4Context ctx = new SM4Context();
            ctx.isPadding = true;
            ctx.mode = SM4.SM4_ENCRYPT;

            byte[] keyBytes;
            byte[] ivBytes;
            if (hexString) {
                keyBytes = Util.hexStringToBytes(secretKey);
                ivBytes = Util.hexStringToBytes(iv);
            } else {
                keyBytes = secretKey.getBytes();
                ivBytes = iv.getBytes();
            }

            SM4 sm4 = new SM4();
            sm4.sm4SetKeyEnc(ctx, keyBytes);
            byte[] encrypted = sm4.sm4CryptCBC(ctx, ivBytes, plainText.getBytes("UTF-8"));
            return Util.byteToHex(encrypted);
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }

    public String decryptDataCBC(String cipherText) {
        try {
            byte[] encrypted = Util.hexToByte(cipherText);
            cipherText= Base64.encodeBase64String(encrypted);;
            if (cipherText != null && cipherText.trim().length() > 0) {
                Pattern p = Pattern.compile("\\s*|\t|\r|\n");
                Matcher m = p.matcher(cipherText);
                cipherText = m.replaceAll("");
            }
            SM4Context ctx = new SM4Context();
            ctx.isPadding = true;
            ctx.mode = SM4.SM4_DECRYPT;

            byte[] keyBytes;
            byte[] ivBytes;
            if (hexString) {
                keyBytes = Util.hexStringToBytes(secretKey);
                ivBytes = Util.hexStringToBytes(iv);
            } else {
                keyBytes = secretKey.getBytes();
                ivBytes = iv.getBytes();
            }

            SM4 sm4 = new SM4();
            sm4.sm4SetKeyDec(ctx, keyBytes);
            byte[] decrypted = sm4.sm4CryptCBC(ctx, ivBytes, Base64.decodeBase64(cipherText));
            return new String(decrypted, StandardCharsets.UTF_8);
        } catch (Exception e) {
            e.printStackTrace();
            return null;
        }
    }
}
