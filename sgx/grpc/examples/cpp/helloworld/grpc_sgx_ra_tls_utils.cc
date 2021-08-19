/*
 *
 * Copyright 2019 gRPC authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

#include "grpc_sgx_ra_tls_utils.h"

namespace grpc {
namespace sgx {

void hexdump_mem(const void* data, size_t size) {
  uint8_t* ptr = (uint8_t*)data;
  for (size_t i = 0; i < size; i++)
      printf("%02x", ptr[i]);
  printf("\n");
}

int parse_hex(const char* hex, void* buffer, size_t buffer_size) {
  if (strlen(hex) != buffer_size * 2) {
    return -1;
  } else {
    for (size_t i = 0; i < buffer_size; i++) {
      if (!isxdigit(hex[i * 2]) || !isxdigit(hex[i * 2 + 1])) {
        return -1;
      }
      sscanf(hex + i * 2, "%02hhx", &((uint8_t*)buffer)[i]);
    }
    return 0;
  }
}

library_engine::library_engine() : handle(nullptr), error(nullptr) {};

library_engine::library_engine(const char* file, int mode) : handle(nullptr), error(nullptr) {
  open(file, mode);
}

library_engine::~library_engine() {
  close();
}

void library_engine::open(const char* file, int mode) {
  handle = dlopen(file, mode);
  if (!handle) {
    mbedtls_printf("Failed to open lib %s", file);
    throw std::runtime_error(std::string("dlopen error\n"));
  }
}

void library_engine::close() {
  if (handle) {
    dlclose(handle);
  }
  handle = nullptr;
  error = nullptr;
}

void* library_engine::get_func(const char* name) {
  auto func = dlsym(handle, name);
  error = dlerror();
  if (error != nullptr || func == nullptr) {
    throw std::runtime_error(std::string(std::string(error)+"\n"));
    return nullptr;
  } else {
    return func;
  }
}

void* library_engine::get_handle() {
  return handle;
}

}  // namespace sgx
}  // namespace grpc
