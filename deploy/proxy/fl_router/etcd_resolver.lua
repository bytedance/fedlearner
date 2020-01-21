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
local etcd = require "resty.etcd"
local util = require "util.util"
local cjson = require "cjson"

--FIXME: maybe need use share memory for future.
--local shared_upstream = ngx.shared.upstream

local _M = {
    _VERSION = '0.0.1',
    hosts = {"127.0.0.1:3379"},
    rr_count = 1,
    cli = nil,
    init = false,
}

function _M.init(self)
    if self.init == true then
        return
    end
    if ngx.var.etcd_hosts == nil then  
        ngx.log(ngx.ERR, "no etcd_hosts configed")
        return
    end
    ngx.log(ngx.ERR, "hello etcd_hosts: ", ngx.var.ectd_hosts)
    local hosts = util.split(ngx.var.ectd_hosts, ",")
    if hosts == nil then
        ngx.log(ngx.ERR, "etcd_hosts format eror: ", ngx.var.ectd_hosts)
        return
    end
    self.hosts = hosts
    self.init = true
end

function _M.new(self)
    --lua idx start with 1
    if self.hosts == nil then
        return "no etcd_hosts"
    end 
    local idx = self.rr_count % #self.hosts + 1
    local etcd_addr = self.hosts[idx]
    ngx.log(ngx.INFO, "select etcd idx: ", idx,
                      ", addr: ", self.hosts[idx])

    local cli, err = etcd.new({
                protocol = "v3",
                http_host = "http://"..etcd_addr,
                key_prefix = "/service_discovery/",
            })
    if err ~= nil then
        return err
    end
    --update rr_count 
    self.rr_count = self.rr_count + 1
    self.cli = cli
    return nil
end


--@call phase: call by the access_by_lua_file;
function _M.get(self, key)
    --not init client;
    local i = 0
    local new_cli = false
    local retry_err = ""
    repeat
        --first-time access, need new cli
        if self.cli == nil then
            new_cli = true
        end
        if new_cli == true then
            local err = self:new()
            if err ~= nil then
                return nil, err
            end
        end
        local res, err = self.cli:get(key)
        if err ~= nil then
            new_cli = true            
            retry_err = err
        else
            if res.body.node ~= nil and res.body.node.value ~= nil then
                local val = res.body.node.value
                return val, nil
            elseif res.body.kvs ~= nil and #res.body.kvs >= 1 then
                local kvs = res.body.kvs
                local item = kvs[1]
                ngx.log(ngx.ERR, "debug, succ etcd key:", key,
                                 ", endpoints: ", tostring(item.value))
                return item.value, nil
            else
                new_cli = true
                retry_err = "etcd body empty"
            end
        end 
        i = i + 1 
    until(i>2)
    return nil, "retry 3 times with err:" + tostring(retry_err)
end
return _M
