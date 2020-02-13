#!/bin/bash

export NGINX_VERSION="1.16.1"
export LUA_NGX_VERSION="0.10.13"
export NDK_VERSION="0.3.1rc1"
export LUA_UPSTREAM_VERSION="0.07"
export LUA_SSL_VERSION="0.01rc3"
export MORE_HEADERS_VERSION="0.33"
export ECHO_VERSION="0.61rc1"
export LUAJIT_VERSION="2.1-20200102"
export PCRE_VERSION="8.39"

export LUA_RESTY_BALANCER="0.03"
export LUA_RESTY_CORE="0.1.15"
export LUA_CJSON_VERSION="2.1.0.7"
export LUA_RESTY_ETCD="0.8"
export LUA_RESTY_HTTP="0.14"
export LUA_RESTY_STRING="0.11"
export LUA_RESTY_TYPEOF="0.1"
export LUA_RESTY_LRUCACHE="0.08"

export ROOT_DIR=$(pwd)

#preare build dir;
rm -rf ./build/ && mkdir ./build/ && cd ./build/

#prepare patches 
cp ../patches ./ -rf
export BUILD_ROOT=$(pwd)

get_src()
{
  url="$1"
  f=$(basename "$url")

  echo "Downloading $url"

  curl -sSL "$url" -o "$f"
  tar xzf "$f"
  rm -rf "$f"
}

#get the main sourcecode
get_src "http://nginx.org/download/nginx-$NGINX_VERSION.tar.gz"

#get additional modules
mkdir modules && cd modules
get_src "https://github.com/simpl/ngx_devel_kit/archive/v$NDK_VERSION.tar.gz"
get_src "https://github.com/openresty/lua-nginx-module/archive/v$LUA_NGX_VERSION.tar.gz"
get_src "https://github.com/openresty/lua-upstream-nginx-module/archive/v$LUA_UPSTREAM_VERSION.tar.gz"
get_src "https://github.com/openresty/lua-ssl-nginx-module/archive/v$LUA_SSL_VERSION.tar.gz"
get_src "https://github.com/openresty/headers-more-nginx-module/archive/v$MORE_HEADERS_VERSION.tar.gz"
get_src "https://github.com/openresty/echo-nginx-module/archive/v$ECHO_VERSION.tar.gz"
cd ..

#get liblua sourcecode
mkdir -p libs/src && cd libs/src/
get_src "https://github.com/openresty/luajit2/archive/v$LUAJIT_VERSION.tar.gz"
get_src "https://ftp.pcre.org/pub/pcre/pcre-$PCRE_VERSION.tar.gz"
cd ../../

#build luajit sourcecode
LUAJIT_SRC=$BUILD_ROOT/libs/src/luajit2-$LUAJIT_VERSION
LUAJIT_INSTALL_PREFIX=$BUILD_ROOT/libs/install/luajit

export LUAJIT_LIB="$BUILD_ROOT/libs/install/luajit/lib/"
export LUAJIT_INC="$BUILD_ROOT/libs/install/luajit/include/luajit-2.1/"
cd $LUAJIT_SRC && make -j4 && make install PREFIX=$LUAJIT_INSTALL_PREFIX
#end for build luajit sourcecode


#build nginx bin
LogPath=/var/log/

PathConfigs="--prefix=$Prefix/"

PcreBuildDir=$BUILD_ROOT/libs/src/pcre-$PCRE_VERSION
Modules="--with-http_ssl_module \
        --with-http_addition_module \
        --with-http_gunzip_module \
        --with-http_gzip_static_module \
        --with-http_v2_module \
        --with-http_sub_module \
        --with-http_xslt_module \
        --with-stream \
        --with-stream_ssl_module \
        --with-stream_ssl_preread_module \
        --with-pcre-jit \
        --with-pcre=$PcreBuildDir \
        --with-threads"

ThirdModules="--add-module=$BUILD_ROOT/modules/lua-nginx-module-$LUA_NGX_VERSION \
              --add-module=$BUILD_ROOT/modules/lua-upstream-nginx-module-$LUA_UPSTREAM_VERSION \
              --add-module=$BUILD_ROOT/modules/lua-ssl-nginx-module-$LUA_SSL_VERSION \
              --add-module=$BUILD_ROOT/modules/headers-more-nginx-module-$MORE_HEADERS_VERSION \
              --add-module=$BUILD_ROOT/modules/ngx_devel_kit-$NDK_VERSION \
              --add-module=$BUILD_ROOT/modules/echo-nginx-module-$ECHO_VERSION "

LD_OPT='-z,now'
CC_OPT="-g -O0"

cd $BUILD_ROOT
cd ./nginx-$NGINX_VERSION

#first patch the grpc module
patch -p1 < ../patches/ngx_http_grpc_module/nginx__grpc_pass_variable_1.16.1+.patch

./configure --with-debug \
            --with-ld-opt="${LD_OPT}" \
            --with-cc-opt="${CC_OPT}" \
            ${Modules} \
            ${ThirdModules}
make 
#end for build nginx bin

#prepare lua-resty and libso
cd  $BUILD_ROOT

#get ngx_lua resty plugins
mkdir -p liblua/resty liblua/ngx
get_src "https://github.com/iresty/lua-resty-etcd/archive/v$LUA_RESTY_ETCD.tar.gz"
cp -rf lua-resty-etcd-$LUA_RESTY_ETCD/lib/resty/* ./liblua//resty/
#dirty fake: etcd/v3.lua disable decode_json.
sed -i "s|kv.value = decode_json(kv.value)|--kv.value = decode_json(kv.value)|g" ./liblua/resty/etcd/v3.lua

get_src "https://github.com/openresty/lua-resty-core/archive/v$LUA_RESTY_CORE.tar.gz"
cp -rf lua-resty-core-$LUA_RESTY_CORE/lib/resty/* ./liblua/resty/
cp -rf lua-resty-core-$LUA_RESTY_CORE/lib/ngx/* ./liblua/ngx/

cd $BUILD_ROOT
mkdir -p libso
get_src "https://github.com/openresty/lua-cjson/archive/$LUA_CJSON_VERSION.tar.gz"
cd lua-cjson-$LUA_CJSON_VERSION
sed -i "s|PREFIX =            /usr/local|PREFIX = $LUAJIT_INSTALL_PREFIX|g" Makefile
sed -i "s|(PREFIX)/include|(PREFIX)/include/luajit-2.1|g" Makefile
make all
chmod 755 cjson.so
cp cjson.so ../libso/
cd  $BUILD_ROOT

get_src "https://github.com/ledgetech/lua-resty-http/archive/v$LUA_RESTY_HTTP.tar.gz"
cp -rf lua-resty-http-$LUA_RESTY_HTTP/lib/resty/* ./liblua/resty/

get_src "https://github.com/openresty/lua-resty-string/archive/v$LUA_RESTY_STRING.tar.gz"
cp -rf lua-resty-string-$LUA_RESTY_STRING/lib/resty/* ./liblua/resty/

get_src "https://github.com/iresty/lua-typeof/archive/v$LUA_RESTY_TYPEOF.tar.gz"
cp -rf lua-typeof-$LUA_RESTY_TYPEOF/lib/* ./liblua/

get_src "https://github.com/openresty/lua-resty-lrucache/archive/v$LUA_RESTY_LRUCACHE.tar.gz"
cp -rf lua-resty-lrucache-$LUA_RESTY_LRUCACHE/lib/resty/* ./liblua/resty/

#end for prepare lua-resty and libso



#install bin&lua-file&so to runtime dir
cd $ROOT_DIR
rm output -rf && mkdir output

#copy nginx bin
mkdir -p ./output/bin/ && mkdir -p ./output/liblua/ 
mkdir -p ./output/libso/ && mkdir -p ./output/configs/

cp $BUILD_ROOT/nginx-$NGINX_VERSION/objs/nginx ./output/bin/
cp $BUILD_ROOT/nginx-$NGINX_VERSION/conf/* ./output/configs/ -rf

#overide configs
cp ./runtime/* ./output/ -rf

cp $BUILD_ROOT/liblua/* ./output/liblua/ -rf
cp $BUILD_ROOT/libso/*  ./output/libso/ -rf

