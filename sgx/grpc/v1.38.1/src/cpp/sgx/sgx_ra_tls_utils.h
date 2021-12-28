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

#ifndef SGX_RA_TLS_UTILS_H
#define SGX_RA_TLS_UTILS_H

#include <string>
#include <vector>
#include <memory>
#include <iostream>
#include <fstream>
#include <sstream>
#include <mutex>

#include <dlfcn.h>

#include <grpcpp/grpcpp.h>
#include <grpc/grpc_security.h>
#include <grpc/grpc_security_constants.h>
#include <grpcpp/security/credentials.h>
#include <grpcpp/security/tls_certificate_provider.h>
#include <grpcpp/security/tls_credentials_options.h>
#include <grpcpp/security/server_credentials.h>
#include <grpcpp/security/sgx/sgx_ra_tls_options.h>

#define grpc_printf printf
#define grpc_fprintf fprintf

#define PEM_BEGIN_CRT "-----BEGIN CERTIFICATE-----\n"
#define PEM_END_CRT   "-----END CERTIFICATE-----\n"

namespace grpc {
namespace sgx {

#include <mbedtls/config.h>
#include <mbedtls/certs.h>
#include <mbedtls/ctr_drbg.h>
#include <mbedtls/debug.h>
#include <mbedtls/entropy.h>
#include <mbedtls/error.h>
#include <mbedtls/net_sockets.h>
#include <mbedtls/ssl.h>
#include <mbedtls/x509.h>
#include <mbedtls/x509_crt.h>
#include <mbedtls/pk.h>
#include <mbedtls/pem.h>
#include <mbedtls/base64.h>
#include <mbedtls/ecdsa.h>
#include <mbedtls/rsa.h>

#include <cjson/cJSON.h>

class library_engine {
  public:
    library_engine();

    library_engine(const char*, int);

    ~library_engine();

    void open(const char*, int);

    void close();

    void* get_func(const char*);

    void* get_handle();

  private:
    void* handle;
    char* error;
};

class json_engine {
  public:
    json_engine();

    json_engine(const char*);

    ~json_engine();

    bool open(const char*);

    void close();

    cJSON * get_handle();

    cJSON * get_item(cJSON *obj, const char *item);

    char * print_item(cJSON *obj);

    bool compare_item(cJSON *obj, const char *item);

  private:
    cJSON* handle;
};

class TlsAuthorizationCheck
    : public grpc::experimental::TlsServerAuthorizationCheckInterface {
  int Schedule(grpc::experimental::TlsServerAuthorizationCheckArg* arg) override;

  void Cancel(grpc::experimental::TlsServerAuthorizationCheckArg* arg) override;
};

struct sgx_measurement {
  char mr_enclave[32];
  char mr_signer[32];
  uint16_t isv_prod_id;
  uint16_t isv_svn;
};

struct sgx_config {
  bool verify_in_enclave  = true;
  bool verify_mr_enclave  = true;
  bool verify_mr_signer   = true;
  bool verify_isv_prod_id = true;
  bool verify_isv_svn     = true;
  std::vector<sgx_measurement> sgx_mrs;
};

struct ra_tls_context {
  class library_engine verify_lib;
  class library_engine attest_lib;
  class library_engine sgx_urts_lib;

  struct sgx_config sgx_cfg;
  std::mutex mtx;

  int (*ra_tls_verify_callback_f)(uint8_t* der_crt, size_t der_crt_size) = nullptr;
  std::shared_ptr<TlsAuthorizationCheck> authorization_check = nullptr;
  std::shared_ptr<grpc::experimental::TlsServerAuthorizationCheckConfig> authorization_check_config = nullptr;
  std::shared_ptr<grpc::experimental::StaticDataCertificateProvider> certificate_provider = nullptr;
};

sgx_config parse_sgx_config_json(const char* file);

bool ra_tls_verify_measurement(const char* mr_enclave, const char* mr_signer,
                               const char* isv_prod_id, const char* isv_svn);

int ra_tls_verify_measurements_callback(const char* mr_enclave, const char* mr_signer,
                                        const char* isv_prod_id, const char* isv_svn);

void ra_tls_verify_init();

void ra_tls_verify_init(sgx_config sgx_cfg);

void ra_tls_verify_init(const char* config_json);

std::vector<std::string> ra_tls_get_key_cert();

std::vector<grpc::experimental::IdentityKeyCertPair> get_identity_key_cert_pairs(std::vector<std::string> key_cert);

void credential_option_set_certificate_provider(grpc::sgx::CredentialsOptions& options);

void credential_option_set_authorization_check(grpc::sgx::CredentialsOptions& options);

}  // namespace sgx
}  // namespace grpc

/*
// Format of pem crt
#define TEST_CRT_PEM                                                      \
  "-----BEGIN CERTIFICATE-----\r\n"                                       \
  "MIIW4TCCFUmgAwIBAgIBATANBgkqhkiG9w0BAQsFADA6MQ4wDAYDVQQDDAVSQVRM\r\n"  \
  "UzEbMBkGA1UECgwSR3JhcGhlbmVEZXZlbG9wZXJzMQswCQYDVQQGEwJVUzAeFw0w\r\n"  \
  "MTAxMDEwMDAwMDBaFw0zMDEyMzEyMzU5NTlaMDoxDjAMBgNVBAMMBVJBVExTMRsw\r\n"  \
  "GQYDVQQKDBJHcmFwaGVuZURldmVsb3BlcnMxCzAJBgNVBAYTAlVTMIIBojANBgkq\r\n"  \
  "hkiG9w0BAQEFAAOCAY8AMIIBigKCAYEA1Yvii4iVMKHLGHFxtjagJEaNYuli0tSZ\r\n"  \
  "Gfqgq+BLILF7mcDaGGF3X9wWUuu+xVP8N1s48+uQ6Ki5/fQ59vzqXXOS6LG7Apkq\r\n"  \
  "R9rstlRscnm9DnYeT7Nri8AXexL0RTqisbgRn8KLIqquNbmV7TArO7jWUftPsjlA\r\n"  \
  "K968gKbI+qQ+FQPiho3yLdPdRg5pip6cKeHrjT7629JoGGCDVECaGVgwqYiBcYyp\r\n"  \
  "oVCZmGemGOee30tymfrxKWLUIqov5PNvRNF0KvTVYMldebXnn4IOJtJM15vvAZwT\r\n"  \
  "aKgCA14JrRrOPfjSd4JDbzQSg+ais2dveDOatvuWKNP9MxwNiWAcryMXkklruiFu\r\n"  \
  "clFXYr376Bg5G3WOGSss0zN4Qs0lljdtaaA7GCNuI6NDPuXjX8IqO2ATbfyCwM1l\r\n"  \
  "vcgNtrmT4hDTW9CmlLOZRFeki+n4YqbXDx/85UWwDKg0mrwIt+2LUv44t3dPuvIW\r\n"  \
  "XImeFxQkDg4mFoXsgXcz7jIQKGceTs3/AgMBAAGjghLwMIIS7DAJBgNVHRMEAjAA\r\n"  \
  "MB0GA1UdDgQWBBTA+Ea+oNAjPIT4F7uhg7Dwp9JMYjAfBgNVHSMEGDAWgBTA+Ea+\r\n"  \
  "oNAjPIT4F7uhg7Dwp9JMYjCCEp0GCwYJKoZIhvhNijkGBIISjAMAAgAAAAAABgAL\r\n"  \
  "AJOacjP3nEyplAoNs5V/Bgc5qzHmdaA6pmT8XGeFZK9YAAAAAAMDBAb//wAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAcAAAAAAAAA5wIA\r\n"  \
  "AAAAAADR0so9p0O1cu0/ZkZk4f8RDqyZE8rryjjwNOyagqG9GAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAdfredRISu8eqkT+CyQPI8j7f/+CZQUpvLSAg\r\n"  \
  "e1PrnbsAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAQOeu3WxZqxSQv2BnBSRk9S35u5U433tVBFyf\r\n"  \
  "dOLbemcAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANgQAADyVRDyFJOE\r\n"  \
  "h8UoHzA1lXwtxfqCiltBzLQqH2DRfRLJlnO2CqfWFUgVNM2EHFwNGxJLagJOoV/U\r\n"  \
  "0dojT5dZ6N4EYPG9Ekgrv1yBb8uIvGg3PEASXEEA4AGEM8YCbdiSH1lrcg8DhyIl\r\n"  \
  "nBQXjcdFKa8FPRHEvGkxbPC7AENChemu/gMDBAb//wAAAAAAAAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABUAAAAAAAAA5wAAAAAAAABcYGk7k4JS\r\n"  \
  "A21jz4CdrQXSqh3NGk4N3/kRUTC62iQmPgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAjE9XddeWUD6WE393xoqCmgBWrI3tcBQLCBsJRJDFe/8AAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAYAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAaHHu8fwO94iKd+Nd/nnDc6cn0VlfWZEbRVdnqqL2YLYAAAAAAAAA\r\n"  \
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADLk4a0E8J+eE/tZxID53/DUJP6E+0g\r\n"  \
  "4v4HZmmBo2Gd4sOZLg0/c+1j+BRDmFc3yL60o9kbzWX/uGTQ9OGZh1ggAAABAgME\r\n"  \
  "BQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fBQBwDgAALS0tLS1CRUdJTiBDRVJU\r\n"  \
  "SUZJQ0FURS0tLS0tCk1JSUU5VENDQkp1Z0F3SUJBZ0lWQU00ZGtCODhoazRvTm1G\r\n"  \
  "OTQvVi9vMG1IWUVXL01Bb0dDQ3FHU000OUJBTUNNSEF4SWpBZ0JnTlYKQkFNTUdV\r\n"  \
  "bHVkR1ZzSUZOSFdDQlFRMHNnVUd4aGRHWnZjbTBnUTBFeEdqQVlCZ05WQkFvTUVV\r\n"  \
  "bHVkR1ZzSUVOdmNuQnZjbUYwYVc5dQpNUlF3RWdZRFZRUUhEQXRUWVc1MFlTQkRi\r\n"  \
  "R0Z5WVRFTE1Ba0dBMVVFQ0F3Q1EwRXhDekFKQmdOVkJBWVRBbFZUTUI0WERUSXhN\r\n"  \
  "RGN5Ck1UQTJNRE15T0ZvWERUSTRNRGN5TVRBMk1ETXlPRm93Y0RFaU1DQUdBMVVF\r\n"  \
  "QXd3WlNXNTBaV3dnVTBkWUlGQkRTeUJEWlhKMGFXWnAKWTJGMFpURWFNQmdHQTFV\r\n"  \
  "RUNnd1JTVzUwWld3Z1EyOXljRzl5WVhScGIyNHhGREFTQmdOVkJBY01DMU5oYm5S\r\n"  \
  "aElFTnNZWEpoTVFzdwpDUVlEVlFRSURBSkRRVEVMTUFrR0ExVUVCaE1DVlZNd1dU\r\n"  \
  "QVRCZ2NxaGtqT1BRSUJCZ2dxaGtqT1BRTUJCd05DQUFTT3Rwbk83K3FICmJYL2c4\r\n"  \
  "WXN1TE56TzBYRGJMek0xQ3RCakJFK3Q5UG02bnV4aXFkVEtHV3grVXZEV0twUUdR\r\n"  \
  "WTVZOFdqdWhxV3k1Tk1EOHNzbEFDbmIKbzRJREVEQ0NBd3d3SHdZRFZSMGpCQmd3\r\n"  \
  "Rm9BVVdTUFRwMHFvWTFRdU9YQ3Q0QThISzFja0tyY3did1lEVlIwZkJHZ3daakJr\r\n"  \
  "b0dLZwpZSVplYUhSMGNITTZMeTl6WW5ndVlYQnBMblJ5ZFhOMFpXUnpaWEoyYVdO\r\n"  \
  "bGN5NXBiblJsYkM1amIyMHZjMmQ0TDJObGNuUnBabWxqCllYUnBiMjR2ZGpNdmNH\r\n"  \
  "TnJZM0pzUDJOaFBYQnNZWFJtYjNKdEptVnVZMjlrYVc1blBXUmxjakFkQmdOVkhR\r\n"  \
  "NEVGZ1FVejZ0Q2p3RWYKUGlqcnVMeGFpdTNya204cGVkMHdEZ1lEVlIwUEFRSC9C\r\n"  \
  "QVFEQWdiQU1Bd0dBMVVkRXdFQi93UUNNQUF3Z2dJNUJna3Foa2lHK0UwQgpEUUVF\r\n"  \
  "Z2dJcU1JSUNKakFlQmdvcWhraUcrRTBCRFFFQkJCQUtpeHJXSTRNSk5VMkNXc2xj\r\n"  \
  "bnJQdU1JSUJZd1lLS29aSWh2aE5BUTBCCkFqQ0NBVk13RUFZTEtvWklodmhOQVEw\r\n"  \
  "QkFnRUNBUU13RUFZTEtvWklodmhOQVEwQkFnSUNBUU13RUFZTEtvWklodmhOQVEw\r\n"  \
  "QkFnTUMKQVFBd0VBWUxLb1pJaHZoTkFRMEJBZ1FDQVFBd0VBWUxLb1pJaHZoTkFR\r\n"  \
  "MEJBZ1VDQVFBd0VBWUxLb1pJaHZoTkFRMEJBZ1lDQVFBdwpFQVlMS29aSWh2aE5B\r\n"  \
  "UTBCQWdjQ0FRQXdFQVlMS29aSWh2aE5BUTBCQWdnQ0FRQXdFQVlMS29aSWh2aE5B\r\n"  \
  "UTBCQWdrQ0FRQXdFQVlMCktvWklodmhOQVEwQkFnb0NBUUF3RUFZTEtvWklodmhO\r\n"  \
  "QVEwQkFnc0NBUUF3RUFZTEtvWklodmhOQVEwQkFnd0NBUUF3RUFZTEtvWkkKaHZo\r\n"  \
  "TkFRMEJBZzBDQVFBd0VBWUxLb1pJaHZoTkFRMEJBZzRDQVFBd0VBWUxLb1pJaHZo\r\n"  \
  "TkFRMEJBZzhDQVFBd0VBWUxLb1pJaHZoTgpBUTBCQWhBQ0FRQXdFQVlMS29aSWh2\r\n"  \
  "aE5BUTBCQWhFQ0FRb3dId1lMS29aSWh2aE5BUTBCQWhJRUVBTURBQUFBQUFBQUFB\r\n"  \
  "QUFBQUFBCkFBQXdFQVlLS29aSWh2aE5BUTBCQXdRQ0FBQXdGQVlLS29aSWh2aE5B\r\n"  \
  "UTBCQkFRR0VHQnFBQUFBTUE4R0NpcUdTSWI0VFFFTkFRVUsKQVFFd0hnWUtLb1pJ\r\n"  \
  "aHZoTkFRMEJCZ1FRdHlVMjN6NGdKMWxOSGhGQmdPMmVkakJFQmdvcWhraUcrRTBC\r\n"  \
  "RFFFSE1EWXdFQVlMS29aSQpodmhOQVEwQkJ3RUJBZjh3RUFZTEtvWklodmhOQVEw\r\n"  \
  "QkJ3SUJBZjh3RUFZTEtvWklodmhOQVEwQkJ3TUJBZjh3Q2dZSUtvWkl6ajBFCkF3\r\n"  \
  "SURTQUF3UlFJaEFJZGN3UmZyUmNiL1E1dmpqUVVydTAwR3dyT3F4M09UcWx1MWN1\r\n"  \
  "eGwwMjZEQWlCVHg5RFBleTF3TDJ3L1JsbXoKd0tUc2JaUENSdTMvQ2RFTllhWUFy\r\n"  \
  "L2JiMnc9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tLS0tLS1CRUdJTiBDRVJU\r\n"  \
  "SUZJQ0FURS0tLS0tCk1JSUNtakNDQWtDZ0F3SUJBZ0lVV1NQVHAwcW9ZMVF1T1hD\r\n"  \
  "dDRBOEhLMWNrS3Jjd0NnWUlLb1pJemowRUF3SXcKYURFYU1CZ0dBMVVFQXd3UlNX\r\n"  \
  "NTBaV3dnVTBkWUlGSnZiM1FnUTBFeEdqQVlCZ05WQkFvTUVVbHVkR1ZzSUVOdgpj\r\n"  \
  "bkJ2Y21GMGFXOXVNUlF3RWdZRFZRUUhEQXRUWVc1MFlTQkRiR0Z5WVRFTE1Ba0dB\r\n"  \
  "MVVFQ0F3Q1EwRXhDekFKCkJnTlZCQVlUQWxWVE1CNFhEVEU1TVRBek1URXlNek0w\r\n"  \
  "TjFvWERUTTBNVEF6TVRFeU16TTBOMW93Y0RFaU1DQUcKQTFVRUF3d1pTVzUwWld3\r\n"  \
  "Z1UwZFlJRkJEU3lCUWJHRjBabTl5YlNCRFFURWFNQmdHQTFVRUNnd1JTVzUwWld3\r\n"  \
  "ZwpRMjl5Y0c5eVlYUnBiMjR4RkRBU0JnTlZCQWNNQzFOaGJuUmhJRU5zWVhKaE1R\r\n"  \
  "c3dDUVlEVlFRSURBSkRRVEVMCk1Ba0dBMVVFQmhNQ1ZWTXdXVEFUQmdjcWhrak9Q\r\n"  \
  "UUlCQmdncWhrak9QUU1CQndOQ0FBUXdwK0xjK1RVQnRnMUgKK1U4SklzTXNiakhq\r\n"  \
  "Q2tUdFhiOGpQTTZyMmRodTl6SWJsaERaN0lOZnF0M0l4OFhjRktEOGswTkVYcmta\r\n"  \
  "NjZxSgpYYTFLekxJS280Ry9NSUc4TUI4R0ExVWRJd1FZTUJhQUZPbm9SRkpUTmx4\r\n"  \
  "TEdKb1IvRU1ZTEtYY0lJQklNRllHCkExVWRId1JQTUUwd1M2QkpvRWVHUldoMGRI\r\n"  \
  "QnpPaTh2YzJKNExXTmxjblJwWm1sallYUmxjeTUwY25WemRHVmsKYzJWeWRtbGpa\r\n"  \
  "WE11YVc1MFpXd3VZMjl0TDBsdWRHVnNVMGRZVW05dmRFTkJMbVJsY2pBZEJnTlZI\r\n"  \
  "UTRFRmdRVQpXU1BUcDBxb1kxUXVPWEN0NEE4SEsxY2tLcmN3RGdZRFZSMFBBUUgv\r\n"  \
  "QkFRREFnRUdNQklHQTFVZEV3RUIvd1FJCk1BWUJBZjhDQVFBd0NnWUlLb1pJemow\r\n"  \
  "RUF3SURTQUF3UlFJaEFKMXErRlR6K2dVdVZmQlF1Q2dKc0ZyTDJUVFMKZTFhQlo1\r\n"  \
  "M081MlRqRmllNkFpQXJpUGFSYWhVWDlPYTlrR0xsQWNoV1hLVDZqNFJXU1I1MEJx\r\n"  \
  "aHJOM1VUNEE9PQotLS0tLUVORCBDRVJUSUZJQ0FURS0tLS0tCi0tLS0tQkVHSU4g\r\n"  \
  "Q0VSVElGSUNBVEUtLS0tLQpNSUlDbERDQ0FqbWdBd0lCQWdJVkFPbm9SRkpUTmx4\r\n"  \
  "TEdKb1IvRU1ZTEtYY0lJQklNQW9HQ0NxR1NNNDlCQU1DCk1HZ3hHakFZQmdOVkJB\r\n"  \
  "TU1FVWx1ZEdWc0lGTkhXQ0JTYjI5MElFTkJNUm93R0FZRFZRUUtEQkZKYm5SbGJD\r\n"  \
  "QkQKYjNKd2IzSmhkR2x2YmpFVU1CSUdBMVVFQnd3TFUyRnVkR0VnUTJ4aGNtRXhD\r\n"  \
  "ekFKQmdOVkJBZ01Ba05CTVFzdwpDUVlEVlFRR0V3SlZVekFlRncweE9URXdNekV3\r\n"  \
  "T1RRNU1qRmFGdzAwT1RFeU16RXlNelU1TlRsYU1HZ3hHakFZCkJnTlZCQU1NRVVs\r\n"  \
  "dWRHVnNJRk5IV0NCU2IyOTBJRU5CTVJvd0dBWURWUVFLREJGSmJuUmxiQ0JEYjNK\r\n"  \
  "d2IzSmgKZEdsdmJqRVVNQklHQTFVRUJ3d0xVMkZ1ZEdFZ1EyeGhjbUV4Q3pBSkJn\r\n"  \
  "TlZCQWdNQWtOQk1Rc3dDUVlEVlFRRwpFd0pWVXpCWk1CTUdCeXFHU000OUFnRUdD\r\n"  \
  "Q3FHU000OUF3RUhBMElBQkUvNkQvMVdITnJXd1BtTk1JeUJLTVc1Cko2SnpNc2pv\r\n"  \
  "NnhQMnZrSzFjZFpHYjFQR1JQL0MvOEVDZ2lEa21rbG16d0x6TGkrMDAwbTdMTHJ0\r\n"  \
  "S0pBM29DMmoKZ2I4d2did3dId1lEVlIwakJCZ3dGb0FVNmVoRVVsTTJYRXNZbWhI\r\n"  \
  "OFF4Z3NwZHdnZ0Vnd1ZnWURWUjBmQkU4dwpUVEJMb0VtZ1I0WkZhSFIwY0hNNkx5\r\n"  \
  "OXpZbmd0WTJWeWRHbG1hV05oZEdWekxuUnlkWE4wWldSelpYSjJhV05sCmN5NXBi\r\n"  \
  "blJsYkM1amIyMHZTVzUwWld4VFIxaFNiMjkwUTBFdVpHVnlNQjBHQTFVZERnUVdC\r\n"  \
  "QlRwNkVSU1V6WmMKU3hpYUVmeERHQ3lsM0NDQVNEQU9CZ05WSFE4QkFmOEVCQU1D\r\n"  \
  "QVFZd0VnWURWUjBUQVFIL0JBZ3dCZ0VCL3dJQgpBVEFLQmdncWhrak9QUVFEQWdO\r\n"  \
  "SkFEQkdBaUVBenc5emRVaVVIUE1VZDBDNG14NDFqbEZaa3JNM3k1ZjFsZ25WCk83\r\n"  \
  "RmJqT29DSVFDb0d0VW1UNGNYdDdWK3lTSGJKOEhvYjlBYW5wdlhOSDFFUisvZ1pG\r\n"  \
  "K29wUT09Ci0tLS0tRU5EIENFUlRJRklDQVRFLS0tLS0KMA0GCSqGSIb3DQEBCwUA\r\n"  \
  "A4IBgQCuYf+3FXNepEjTlmcaXn35w3Oq9ge+We0YsO8y/dfI4S4AU5Vo8J5xkr+M\r\n"  \
  "ZrJYrJqsSNmSiB94fQQ3Z9drRiS2pqwG+qSDjM/7oU+54bcFesSiZwhcxEAcTYae\r\n"  \
  "Etss/L8vuqKyt+jHxnRE74F+a38hmqhcYV84K+zNwaxG6H5fsj5Qa3Nrdrx7UDbO\r\n"  \
  "8wvmof8+4CisZRvVbStAebhHYQNYmgt+DdF2FxgGtxiZR8DEtWI94gxQNDXBeoGv\r\n"  \
  "ixBQ3WfxclWN0Iktar+Us97LopLH0t39K+l9D7lm/vkjZV/hTSGyOOJBiIkfmr2K\r\n"  \
  "3U5b3mn5eqrAZq48K8oRqsdfj2CH30sB7yz1MQeI3rPKb+uT5tTn9fuIOcfThiCt\r\n"  \
  "woMWzk9xW/VkghBlMl1YCXzQfOhAr83/fWczfKx/AmZ7C9/OgYJ029/CPqTGzLqV\r\n"  \
  "LQHAvnx5bWCP3h0YazM6SqmtqKHXGBJogT4ZHo1ZsN3C6kj9vpFQmpNZ1R78KJB9\r\n"  \
  "EJaIecY=\r\n"                                                          \
  "-----END CERTIFICATE-----\r\n"                                         \
*/

#endif  // SGX_RA_TLS_UTILS_H
