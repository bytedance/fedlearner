import React, { FC, useState } from 'react';
import {
  Form,
  Input,
  Divider,
  Button,
  Popconfirm,
  Switch,
  Select,
  Grid,
} from '@arco-design/web-react';
import { MAX_COMMENT_LENGTH, validParticipantNamePattern } from 'shared/validator';
import GridRow from 'components/_base/GridRow';
import { Plus } from 'components/IconPark';
import { IconDelete } from '@arco-design/web-react/icon';
import { Participant } from 'typings/participant';
import FormLabel from 'components/FormLabel';
import { DOMAIN_PREFIX, DOMAIN_SUFFIX } from 'shared/project';
import { fetchDomainNameList } from 'services/participant';
import { useQuery } from 'react-query';
import { ParticipantType } from 'typings/participant';

import styles from './index.module.less';

const { Row } = Grid;

interface Props {
  onFinish: (value: any) => void;
  data?: Participant;
  isEdit: boolean;
  /**
   * @deprecated
   *
   * multi-add mode
   */
  needAdd: boolean;
}

const AddPartnerForm: FC<Props> = ({ onFinish, isEdit, needAdd, data }) => {
  const [form] = Form.useForm();
  const [isManual, setIsManual] = useState(data?.extra?.is_manual_configured);
  const [isLightClient, setIsLightClient] = useState(data?.type === ParticipantType.LIGHT_CLIENT);

  const domainNameListQuery = useQuery(['fetchDomainNameList'], () => fetchDomainNameList(), {
    retry: 2,
    refetchOnWindowFocus: false,
  });

  const dataInitial =
    isEdit && data
      ? [
          {
            ...data,
            domain_name: data.domain_name.slice(3, -4),
            type:
              (data.type ?? ParticipantType.PLATFORM) === ParticipantType.LIGHT_CLIENT
                ? true
                : false,
          },
        ]
      : [
          {
            extra: {
              is_manual_configured: false,
              grpc_ssl_server_host: 'x-host',
            },
            type: false,
          },
        ];

  const isShowManualInfo = isManual || isLightClient;

  return (
    <Form
      form={form}
      layout="vertical"
      onSubmit={(value: any) => {
        onFinish(
          value.participants.map((item: any) => {
            return isShowManualInfo
              ? {
                  ...item,
                  domain_name: `fl-${item.domain_name}.com`,
                  type: item.type ? ParticipantType.LIGHT_CLIENT : ParticipantType.PLATFORM,
                }
              : {
                  ...item,
                  type: item.type ? ParticipantType.LIGHT_CLIENT : ParticipantType.PLATFORM,
                };
          }),
        );
      }}
    >
      <Form.List field="participants" initialValue={dataInitial as any}>
        {(fields, { add, remove }) => {
          return (
            <>
              <div className={styles.form_list} id="add-modal">
                {fields.map((field, index) => (
                  <div className={styles.form_container} key={field.field + index}>
                    {needAdd && <p className={styles.title_container}>合作伙伴{index + 1}</p>}
                    <Form.Item
                      label="企业名称"
                      field={field.field + '.name'}
                      rules={[
                        {
                          required: true,
                          message: '请输入企业名称',
                        },
                        {
                          match: validParticipantNamePattern,
                          message:
                            '只支持大小写字母，数字，中文开头或结尾，可包含“_”和“-”，不超过 63 个字符',
                        },
                      ]}
                    >
                      <Input placeholder="请输入企业名称" />
                    </Form.Item>

                    <Form.Item
                      hidden={isEdit}
                      label="是否轻量级客户端"
                      field={field.field + '.type'}
                      triggerPropName="checked"
                    >
                      <Switch
                        onChange={(checked: boolean) => {
                          setIsLightClient(checked);
                          setIsManual(false);
                          // Reset field
                          const newData = [...form.getFieldValue('participants')];
                          newData[field.key] = {
                            ...newData[field.key],
                            domain_name: undefined,
                            host: undefined,
                            port: undefined,
                            extra: {
                              ...newData[field.key].extra,
                              is_manual_configured: false,
                            },
                          };
                          form.setFieldsValue({
                            participants: newData,
                          });
                        }}
                      />
                    </Form.Item>

                    {!isEdit && !isLightClient && (
                      <Form.Item
                        label={
                          <FormLabel
                            label="是否手动配置"
                            tooltip="默认将使用平台配置，若您有手动配置需求且对配置内容了解，可点击进行手动配置"
                          />
                        }
                        field={field.field + '.extra.is_manual_configured'}
                        triggerPropName="checked"
                      >
                        <Switch
                          onChange={(checked: boolean) => {
                            setIsManual(checked);
                            // Reset domain_name field
                            const newData = [...form.getFieldValue('participants')];
                            newData[field.key] = {
                              ...newData[field.key],
                              domain_name: undefined,
                            };
                            form.setFieldsValue({
                              participants: newData,
                            });
                          }}
                        />
                      </Form.Item>
                    )}

                    <Form.Item
                      label="泛域名"
                      field={field.field + '.domain_name'}
                      rules={
                        isShowManualInfo
                          ? [
                              {
                                required: true,
                                message: '请输入泛域名',
                              },
                              {
                                match: /^[0-9a-z-]+$/g,
                                message: '只允许小写英文字母/中划线/数字，请检查',
                              },
                            ]
                          : [
                              {
                                required: true,
                                message: '请选择泛域名',
                              },
                            ]
                      }
                    >
                      {isShowManualInfo ? (
                        <Input
                          placeholder="请输入泛域名"
                          addBefore={DOMAIN_PREFIX}
                          addAfter={DOMAIN_SUFFIX}
                        />
                      ) : (
                        <Select
                          loading={domainNameListQuery.isFetching}
                          placeholder="请选择泛域名"
                          showSearch
                          allowClear
                        >
                          {(domainNameListQuery.data?.data ?? []).map((item) => {
                            return (
                              <Select.Option key={item.domain_name} value={item.domain_name}>
                                {item.domain_name}
                              </Select.Option>
                            );
                          })}
                        </Select>
                      )}
                    </Form.Item>

                    {isShowManualInfo && (
                      <>
                        {!isLightClient && (
                          <>
                            <Form.Item
                              label="主机号"
                              field={field.field + '.host'}
                              style={{
                                width: '50%',
                                display: 'inline-block',
                                verticalAlign: 'top',
                              }}
                              rules={[
                                {
                                  required: true,
                                  message: '请输入主机号',
                                },
                              ]}
                            >
                              <Input placeholder="请输入主机号" />
                            </Form.Item>
                            <Form.Item
                              label="端口号"
                              field={field.field + '.port'}
                              style={{
                                marginLeft: '2%',
                                width: '48%',
                                display: 'inline-block',
                                verticalAlign: 'top',
                              }}
                              rules={[
                                {
                                  required: isManual,
                                  message: '请输入端口号',
                                },
                                {
                                  match: /^[0-9]*$/g,
                                  message: '端口号不合法，请检查',
                                },
                              ]}
                            >
                              <Input placeholder="请输入端口号" />
                            </Form.Item>
                          </>
                        )}
                      </>
                    )}
                    <Form.Item label="合作伙伴描述" field={field.field + '.comment'}>
                      <Input.TextArea
                        showWordLimit
                        maxLength={MAX_COMMENT_LENGTH}
                        placeholder="请为合作伙伴添加描述"
                      />
                    </Form.Item>

                    {needAdd && <Divider className={styles.think_divider} />}
                    {index !== 0 && (
                      <Row justify="end">
                        <Popconfirm
                          title="是否确定删除上面这个表单？"
                          onConfirm={() => remove(index)}
                        >
                          <Button className={styles.delete_button} icon={<IconDelete />}>
                            删除
                          </Button>
                        </Popconfirm>
                      </Row>
                    )}
                  </div>
                ))}
              </div>
              <div style={{ padding: '0px 20px' }}>
                <GridRow justify={needAdd ? 'space-between' : 'end'} align="center">
                  {needAdd && (
                    <GridRow
                      className={styles.row_container}
                      gap={5}
                      style={{ fontWeight: 500 }}
                      onClick={() => add()}
                    >
                      <Plus />
                      <span>继续添加</span>
                    </GridRow>
                  )}
                </GridRow>
                <GridRow justify="center" style={{ marginTop: 48 }}>
                  <Button type="primary" htmlType="submit" style={{ padding: '0 74px' }}>
                    {isLightClient ? '提交' : '发送请求'}
                  </Button>
                </GridRow>
              </div>
            </>
          );
        }}
      </Form.List>
    </Form>
  );
};

export default AddPartnerForm;
