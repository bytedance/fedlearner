/* istanbul ignore file */

import React, { FC, useMemo } from 'react';
import ClickToCopy from 'components/ClickToCopy';
import styled from 'styled-components';
import { useQuery } from 'react-query';
import { Branch } from 'components/IconPark';
import { fetchSystemVersion } from 'services/system';
import { CONSTANTS } from 'shared/constants';
import { Popover } from '@arco-design/web-react';
import { omitBy, isNull } from 'lodash-es';

const Container = styled.div`
  display: flex;
  grid-area: version;
  align-items: center;
  padding: 5px 8px;
  color: rgb(var(--gray-10));
  line-height: 1;
  font-size: 12px;
  border-radius: 5px;
  font-weight: bold;
  overflow: hidden;
  opacity: 0.5;
  transition: 0.12s ease-in;
  background-color: rgb(var(--gray-3));
  border: 1px solid rgb(var(--gray-3));

  &:hover {
    opacity: 0.9;
  }
`;
const VersionIcon = styled(Branch)`
  font-size: 12px;
`;
const VersionText = styled.div`
  padding: 5px 8px 5px 6px;
  margin: -5px -8px -5px 5px;
  background-color: #fff;
`;
const DetailList = styled.ul`
  list-style: none;
`;
const DetailItem = styled.li`
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 250px;
  height: 30px;
`;

const HeaderVersion: FC = () => {
  const versionQuery = useQuery('fetchVersion', fetchSystemVersion, {
    refetchOnWindowFocus: false,
    staleTime: 100 * 60 * 1000,
  });

  const version = useMemo(() => {
    if (!versionQuery.data?.data) {
      return CONSTANTS.EMPTY_PLACEHOLDER;
    }

    if (versionQuery.data.data.version) {
      return versionQuery.data.data.version;
    }

    if (versionQuery.data.data.revision) {
      return versionQuery.data.data.revision.slice(-6);
    }

    return CONSTANTS.EMPTY_PLACEHOLDER;
  }, [versionQuery.data]);

  const sha = useMemo(() => {
    if (!versionQuery.data?.data) {
      return CONSTANTS.EMPTY_PLACEHOLDER;
    }

    if (versionQuery.data.data.revision) {
      return versionQuery.data.data.revision.slice(0, 12);
    }

    return CONSTANTS.EMPTY_PLACEHOLDER;
  }, [versionQuery.data]);

  const pubDate = useMemo(() => {
    if (!versionQuery.data?.data) {
      return CONSTANTS.EMPTY_PLACEHOLDER;
    }
    if (versionQuery.data.data.pub_date) {
      return versionQuery.data.data.pub_date;
    }

    return CONSTANTS.EMPTY_PLACEHOLDER;
  }, [versionQuery.data]);

  const infoToBeCopy = useMemo(() => {
    if (!versionQuery.data?.data) {
      return '';
    }
    const { revision, pub_date, version } = versionQuery.data.data;

    // Filter null field
    return omitBy(
      {
        revision: revision,
        pub_date: pub_date,
        version: version,
      },
      isNull,
    );
  }, [versionQuery.data]);

  if (!versionQuery.data) {
    return null;
  }

  return (
    <ClickToCopy text={JSON.stringify(infoToBeCopy ?? '')}>
      <Popover trigger={['hover']} content={renderDetails()} title={'当前版本'} position="br">
        <Container>
          <VersionIcon />
          <VersionText>{version}</VersionText>
        </Container>
      </Popover>
    </ClickToCopy>
  );

  function renderDetails() {
    return (
      <DetailList>
        <DetailItem>
          <strong>Version</strong>
          <span>{version}</span>
        </DetailItem>
        <DetailItem>
          <strong>SHA</strong>
          <span>{sha}</span>
        </DetailItem>
        <DetailItem>
          <strong>发布日期</strong>
          <span>{pubDate}</span>
        </DetailItem>
      </DetailList>
    );
  }
};

export default HeaderVersion;
