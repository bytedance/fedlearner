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

bool parse_hex(const char* hex, void* buffer, size_t buffer_size) {
  if (strlen(hex) < buffer_size * 2) {
    return false;
  } else {
    for (size_t i = 0; i < buffer_size; i++) {
      if (!isxdigit(hex[i * 2]) || !isxdigit(hex[i * 2 + 1])) {
        return false;
      }
      sscanf(hex + i * 2, "%02hhx", &((uint8_t*)buffer)[i]);
    }
    return true;
  }
}

void hexdump_mem(const void* data, size_t size) {
  uint8_t* ptr = (uint8_t*)data;
  for (size_t i = 0; i < size; i++)
      printf("%02x", ptr[i]);
  printf("\n");
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

json_engine::json_engine() : handle(nullptr){};

json_engine::json_engine(const char *file) : handle(nullptr)
{
    this->open(file);
}

json_engine::~json_engine()
{
    this->close();
}

bool json_engine::open(const char *file)
{
    if (!file)
    {
        printf("wrong json file path\n");
        return false;
    }

    this->close();

    auto file_ptr = fopen(file, "r");
    fseek(file_ptr, 0, SEEK_END);
    auto length = ftell(file_ptr);
    fseek(file_ptr, 0, SEEK_SET);
    auto buffer = malloc(length + 1);
    memset(buffer, 0, length);
    fread(buffer, 1, length, file_ptr);
    fclose(file_ptr);

    this->handle = cJSON_Parse((const char*)buffer);

    if (buffer)
    {
      free(buffer);
      buffer = nullptr;
    }

    if (this->handle)
    {
        return true;
    }
    else
    {
        printf("cjson open %s error: %s", file, cJSON_GetErrorPtr());
        return false;
    }
}

void json_engine::close()
{
    if (this->handle)
    {
        cJSON_Delete(this->handle);
        this->handle = nullptr;
    }
}

cJSON *json_engine::get_handle()
{
    return this->handle;
}

cJSON *json_engine::get_item(cJSON *obj, const char *item)
{
    return cJSON_GetObjectItem(obj, item);
};

bool json_engine::compare_item(cJSON *obj, const char *item)
{
    if (!obj || !cJSON_IsString(obj)){
        return false;
    }
    auto obj_item = obj->valuestring;
    return strncmp(obj_item, item, std::min(strlen(item), strlen(obj_item))) == 0;
};

const char* json_engine::get_item_string(cJSON *obj, const char* item){
    auto item_json = get_item(obj, item);
    return cJSON_IsString(item_json) ? item_json->valuestring : "";
}

}  // namespace sgx
}  // namespace grpc
