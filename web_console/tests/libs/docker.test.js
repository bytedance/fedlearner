const assert = require('assert');
const docker = require('../../libs/docker');
const { latest, versioned } = require('../fixtures/images');

const repo = 'fedlearner/fedlearner-web-console';

describe('Docker Client', () => {
  describe('getBaseUrl', () => {
    it('should get prefixUrl', async () => {
      const baseUrl = await docker.getBaseUrl();
      assert.strictEqual(baseUrl, docker.prefixUrl);
    });
  });

  describe('getImage', () => {
    it('should return image detail', async () => {
      const res = await docker.getImage(versioned.name, repo);
      assert.deepStrictEqual(res, versioned);
    });

    it('should return latest image detail', async () => {
      const res = await docker.getImage('latest', repo);
      assert.deepStrictEqual(res, latest);
    });
  });

  describe('listImageTags', () => {
    it('should return all images as expected', async () => {
      const { count, results } = await docker.listImageTags(repo);
      assert.strictEqual(count, 2);
      assert.deepStrictEqual(results, [latest, versioned]);
    });
  });
});
