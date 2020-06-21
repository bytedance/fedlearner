import React from 'react';
import { useRouter } from 'next/router';
import Layout from '../components/Layout';
import FederationList from '../components/FederationList';
import UserList from '../components/UserList';

export default function Admin() {
  const router = useRouter();
  const tab = router.query.tab || 'federation';
  return (
    <Layout>
      {tab === 'federation' && <FederationList />}
      {tab === 'user' && <UserList />}
    </Layout>
  );
}
