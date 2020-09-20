import React from 'react';
import { useRouter } from 'next/router';

import Job from '../../../components/Job';

export default function Jobs() {
  const router = useRouter();
  return <Job id={router.query.id}></Job>
}
