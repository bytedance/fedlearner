-- Copyright 2020 The FedLearner Authors. All Rights Reserved.
--
--  Licensed under the Apache License, Version 2.0 (the "License");
--  you may not use this file except in compliance with the License.
--  You may obtain a copy of the License at
--
--      http://www.apache.org/licenses/LICENSE-2.0
--
--  Unless required by applicable law or agreed to in writing, software
--  distributed under the License is distributed on an "AS IS" BASIS,
--  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
--  See the License for the specific language governing permissions and
--  limitations under the License.


local resty_md5 = require "resty.md5"
local str = require "resty.string"
local http = require "resty.http"
local cjson = require "cjson"
local util = require "util.util"
local etcd_resolver = require "fl_router.etcd_resolver"

--FIXME: maybe need use share memory for future.
--local shared_upstream = ngx.shared.upstream

local _M = {
    _VERSION = '0.0.1',

    --lua table key must be alpha start
    --format for upstreams_dict:
    --{   
    --  "addr_1": {
    --      "last_ts": timestamp,
    --      "backends": {},
    --      "rr_count": 1,
    --  } 
    --  "addr_2": {...}
    --}
    upstreams = {},
    rr_count = 1,
}

function _M.local_lookup_route(self, route_key)
    --lua idx start with 1
    if #self.upstreams == 0 then
        return nil
    end

    local ups = self.upstreams[route_key]
    if ups == nil then
        return nil
    end

    local now = ngx.now()
    --extend to support multi backend
    local idx = ups["rr_count"] % (#ups["backends"] + 1)
    
    if now - ups["last_ts"] > 3 then
       return nil
    end

    ngx.log(ngx.INFO, "select_backend choose,idx: ", idx)
    if ups["backends"][idx] == nil then
        ngx.log(ngx.ERR, "select_backend failed: ", idx,
                         "rr_count: ", ups["rr_count"],
                         "backends count: ", #ups["backends"])
        return nil
    end
    --update rr_count 
    ups["rr_count"] = ups["rr_count"] + 1
    return ups["backends"][idx]
end


function _M.get_router_key(self)
    --URI default starts with /
    local uri = ngx.var.uri
    if uri:find("^/") == nil  then
        ngx.log(ngx.ERR, "invalid grpc: ", uri)
        return nil 
    end

    --Path → ":path" "/" Service-Name "/" {method name} # But see note below. grpc protocal
    --get svc_name and method_name
    local items = util.split(ngx.var.uri, "/")
    local svc_name = items[2]
    local func_name = items[3]
    ngx.log(ngx.ERR, "debug grpc svc_name: ", svc_name,
                     ", method_name: ", func_name)

    --get uuid:
    local route_id = ngx.var.http_route_id
    if route_id == nil then
        ngx.log(ngx.ERR, "empty route_id: ", ngx.var.uri)
        return nil
    end
    ngx.var.svc_name = svc_name
    ngx.var.func_name = func_name
    ngx.log(ngx.ERR, "debug grpc service: ", svc_name)
    ngx.log(ngx.ERR, "debug grpc function:", func_name)
    ngx.log(ngx.ERR, "debug grpc addressid:", route_id)
    return uuid
end

--@call phase: call by the access_by_lua_file;
function _M.route(self)
    local route_key = self:get_router_key()
    if route_key == nil then
        ngx.var.backend_addr = ""
        return
    end

    --[[ 
    local ups_addr = self:local_lookup_route(route_key)
    if ups_addr ~= nil then
        ngx.var.backend_addr = ups_addr
        return
    end
    ]]--

    --always retrive from backend name service;
    local ups_addr, err = etcd_resolver:get(route_key)
    if ups_addr == nil or err ~= nil then    
        ngx.log(ngx.ERR, "etcd_resolver error for :", route_key)
    else
        ngx.log(ngx.INFO, "etcd_lookup succ:", tostring(ups_addr))
        ngx.var.backend_addr = ups_addr 
        return
    end
end

return _M
