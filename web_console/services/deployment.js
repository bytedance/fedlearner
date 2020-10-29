import { client } from '../libs/http';

export async function updateDeployment(deployment) {
  return client.put(`deployments/${deployment.metadata.name}`, { json: deployment }).json();
}

export async function foo() { }
