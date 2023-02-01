/* istanbul ignore file */

import React, { FC, useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import { useTranslation } from 'react-i18next';
import { isEmpty, isNil } from 'lodash-es';

import { transformRegexSpecChar } from 'shared/helpers';
import { CONSTANTS } from 'shared/constants';

import { Input, Message, Select, Spin, Tooltip } from '@arco-design/web-react';
import GridRow from 'components/_base/GridRow';

import NoResult from 'components/NoResult';
import PictureList from './PictureList';

import { ImageDetail, PreviewData } from 'typings/dataset';
import { MixinEllipsis } from 'styles/mixins';

const { Option } = Select;

const Container = styled.div`
  display: grid;
  grid-template-columns: 180px 0.6fr 0.4fr;
  border: 1px solid var(--lineColor);
  width: 100%;
`;

const ColumnContainer = styled.div`
  display: grid;
  grid-template-rows: 36px 1fr;
  height: 100%;
`;

const Header = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 20px;
  border-bottom: 1px solid var(--lineColor);
  border-right: 1px solid var(--lineColor);
  color: #000000;
  font-size: 12px;
`;

const Body = styled.div`
  height: 557px;
  overflow-y: auto;
  border-right: 1px solid var(--lineColor);
`;

const StyledGridRow = styled(GridRow)`
  padding: 6px 20px;
  cursor: pointer;

  .itemNum {
    background-color: #f6f7fb;
    border-radius: 32px;
    padding: 0 6px;
  }

  &:hover,
  &[data-active='true'] {
    background-color: #f6f7fb;

    .itemValue {
      color: var(--primaryColor);
    }

    .itemNum {
      background-color: #ffffff;
    }
  }
`;

const StyledFileName = styled.div`
  ${MixinEllipsis()};
  width: 90%;
  color: var(--textColorStrong);
`;

const StyledSize = styled.span`
  background-color: #f6f7fb;
  border-radius: 8px;
  padding: 0 4px;
  color: var(--textColorStrongSecondary);
`;

type Props = {
  data?: PreviewData;
  loading?: boolean;
  isError?: boolean;
  noResultText?: string;
};
const PictureDataPreviewTable: FC<Props> = ({ data, loading, isError, noResultText }) => {
  const { t } = useTranslation();
  /** active label */
  const [active, setActive] = useState('');
  const [labelOrder, setLabelOrder] = useState('ascending');
  const [filterText, setFilterText] = useState('');
  const [pictureOnFocus, setPictureOnFocus] = useState<ImageDetail>();

  const formatData = useMemo(() => {
    if (!data) {
      return undefined;
    }

    const map: { [key: string]: ImageDetail[] } = {};

    data?.images?.forEach((item) => {
      const labelName = item?.annotation?.label ?? t('no_label');
      if (map[labelName] === undefined) {
        map[labelName] = [];
      }
      map[labelName].push({
        ...item,
        uri: `/api/v2/image?name=${item.path}`,
      });
    });

    return { ...data, formatImages: map };
  }, [data, t]);

  const labelList = useMemo(() => {
    const list: Array<{ count: number; value: string }> = [];
    const map: { [key: string]: number } = {};

    data?.images?.forEach((item) => {
      const labelName = item?.annotation?.label ?? t('no_label');

      if (map[labelName] === undefined) {
        map[labelName] = 0;
      }
      map[labelName]++;
    });

    Object.keys(map).forEach((key) => {
      const value = map[key];
      list.push({
        value: key,
        count: value,
      });
    });

    return list;
  }, [data, t]);

  useEffect(() => {
    if (labelList.length && !active) {
      setActive(labelList[0].value);
    }
  }, [active, labelList]);

  const filterTagList = useMemo(() => {
    const regx = new RegExp(`^.*${transformRegexSpecChar(filterText)}.*$`);
    return labelList.filter((item: any) => {
      return regx.test(item.value);
    });
  }, [filterText, labelList]);

  const tagShowList = useMemo(() => {
    if (filterTagList) {
      const list = [...filterTagList];
      switch (labelOrder) {
        case 'ascending':
          return list.sort((a: any, b: any) => {
            return a.count - b.count;
          });

        case 'descending':
          return list.sort((a: any, b: any) => {
            return b.count - a.count;
          });
        case 'beginA':
          return list.sort((a: any, b: any) => {
            return a.value.localeCompare(b.value);
          });
        case 'endA':
          return list.sort((a: any, b: any) => {
            return b.value.localeCompare(a.value);
          });
        default:
          Message.error('未知选项');
          return list;
      }
    }
    return [];
  }, [filterTagList, labelOrder]);

  const imageList = useMemo(() => {
    if (active && formatData && formatData.formatImages) {
      const list = [...formatData.formatImages[active]];

      return list;
    }
    return [];
  }, [active, formatData]);

  useEffect(() => {
    if (imageList && !pictureOnFocus) {
      setPictureOnFocus(imageList[0]);
    }
  }, [imageList, pictureOnFocus]);

  if (isError) {
    return <NoResult text={t('dataset.tip_state_error')} />;
  }

  if (loading) {
    return (
      <GridRow style={{ height: '100%' }} justify="center">
        <Spin loading={true} />
      </GridRow>
    );
  }

  if (isNil(data)) {
    return <NoResult text={t('dataset.tip_state_error')} />;
  }

  if (noResultText) {
    return <NoResult text={noResultText} />;
  }

  if (!labelList || isEmpty(labelList)) {
    return <NoResult text={t('dataset.tip_state_error')} />;
  }
  return (
    <Container>
      <ColumnContainer>
        <Header style={{ paddingLeft: '12px' }}>
          <Select
            defaultValue="ascending"
            bordered={false}
            size="small"
            style={{ color: '#000000', fontSize: 12 }}
            onChange={(value) => {
              setLabelOrder(value);
            }}
            value={labelOrder}
            dropdownMenuStyle={{ width: 'auto' }}
          >
            <Option value="ascending">数据量升序</Option>
            <Option value="descending">数据量降序</Option>
            <Option value="beginA">按字母 A-Z</Option>
            <Option value="endA">按字母 Z-A</Option>
          </Select>
        </Header>
        <Body>
          <div style={{ padding: '6px 13px' }}>
            <Input.Search
              placeholder="搜索..."
              allowClear
              size="small"
              onChange={(value) => {
                setFilterText(value);
              }}
            />
          </div>
          {tagShowList.map((item, index) => {
            if (!active && !index) {
              setActive(item.value);
            }
            return (
              <StyledGridRow
                justify="space-between"
                data-active={active === item.value}
                onClick={() => {
                  setActive(item.value);
                  setPictureOnFocus(undefined);
                }}
                key={`tag-${index}`}
              >
                <span className="itemValue">{item.value}</span>
                <span className="itemNum">{item.count}</span>
              </StyledGridRow>
            );
          })}
        </Body>
      </ColumnContainer>
      <ColumnContainer>
        <Header>
          <span style={{ color: 'var(--textColorStrongSecondary)' }}>
            以下展示该标签下的20张样例
          </span>
        </Header>
        <Body>
          <PictureList
            data={imageList}
            onClick={(item) => {
              setPictureOnFocus(item);
            }}
          />
        </Body>
      </ColumnContainer>
      <ColumnContainer>
        <Header style={{ borderRight: 0 }}>
          <GridRow gap={10}>
            <Tooltip content={pictureOnFocus?.name ?? ''}>
              <StyledFileName>{pictureOnFocus?.name ?? CONSTANTS.EMPTY_PLACEHOLDER}</StyledFileName>
            </Tooltip>
            <StyledSize>{`${pictureOnFocus?.width || 0} × ${
              pictureOnFocus?.height || 0
            } pixels`}</StyledSize>
          </GridRow>
          <span
            style={{ color: 'var(--textColorStrongSecondary)' }}
          >{`${pictureOnFocus?.file_name?.split('.').pop()}`}</span>
        </Header>
        <Body style={{ borderRight: 0 }}>
          <div style={{ height: '100%', minHeight: '100%', margin: '0 10%' }}>
            <GridRow justify="center" align="center" style={{ height: '100%' }}>
              <img
                alt={pictureOnFocus?.annotation?.caption || '照片显示错误'}
                src={pictureOnFocus?.uri}
                title={pictureOnFocus?.annotation?.caption}
              />
            </GridRow>
          </div>
        </Body>
      </ColumnContainer>
    </Container>
  );
};

export default PictureDataPreviewTable;
