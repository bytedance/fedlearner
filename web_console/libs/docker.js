/**
 * Docker Registry HTTP API V2 Client
 *
 * Reference: https://hub.docker.com
 */

const ky = require('ky-universal');
const parseStream = require('../utils/parse_stream');

const prefixUrl = 'https://hub.docker.com/v2';

const parseErrorResponse = async (e) => {
  if (e && e.response && e.response.body) {
    const body = await parseStream(e.response.body);
    if (body && body.error) {
      const error = new Error(body.error);
      error.status = e.response.status;
      throw error;
    }
  }
  throw e;
}

class DockerClient {
  constructor() {
    this.prefixUrl = prefixUrl;
    this.client = ky.create({
      prefixUrl,
    });
  }

  getBaseUrl() {
    return this.prefixUrl;
  }

  /**
   * get image detail
   *
   * @param {string} repo - registered image name from Docker Hub
   * @param {string} name - image tag
   * @return {Promise<Object>} - { creator, id, image_id, images, last_updated, last_updater, last_updater_username, name, repository, full_size, v2 }
   */
  async getImage(repo, name) {
    const response = await this.client.get(`repositories/${repo}/tags/${name}`).catch(parseErrorResponse);
    return response.json();
  }

  /**
   * search image tags for image
   *
   * @param {string} repo - registered image name from Docker Hub
   * @param {string} name - image tag
   * @param {number} page - current list page
   * @param {number} page_size - list size
   * @return {Promise<Object>} - { count, next, previous, results }
   */
  async listImageTags(repo, name = '', page = 1, page_size = 10) {
    const options = {
      searchParams: { name, page, page_size },
    };
    const response = await this.client.get(`repositories/${repo}/tags`, options).catch(parseErrorResponse);
    return response.json();
  }
}

module.exports = new DockerClient();
