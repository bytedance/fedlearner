import React from 'react';
import { Route } from 'react-router-dom';
import PartnerList from './PartnerList';
import CreatePartner from './CreatePartner';
import EditPartner from './EditPartner';

function PartnerPage() {
  return (
    <>
      <Route path="/partners" exact component={PartnerList} />
      <Route path="/partners/create" exact component={CreatePartner} />
      <Route path="/partners/edit/:id" exact component={EditPartner} />
    </>
  );
}

export default PartnerPage;
