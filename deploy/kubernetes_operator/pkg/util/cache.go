/* Copyright 2020 The FedLearner Authors. All Rights Reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package util

import (
	"sync"
	"time"
)

const (
	DefaultExpiration = time.Duration(30) * time.Second
)

type ExpirationCache struct {
	mutex      sync.RWMutex
	lastSeen   map[string]time.Time
	expiration time.Duration
}

func NewExpirationCache() *ExpirationCache {
	return NewExpirationCacheWithExpirationDuration(DefaultExpiration)
}

func NewExpirationCacheWithExpirationDuration(duration time.Duration) *ExpirationCache {
	return &ExpirationCache{
		lastSeen:   make(map[string]time.Time),
		expiration: duration,
	}
}

func (c *ExpirationCache) Has(key string) bool {
	c.mutex.RLock()
	defer c.mutex.RUnlock()
	_, ok := c.lastSeen[key]
	return ok
}

func (c *ExpirationCache) Expired(key string) bool {
	c.mutex.RLock()
	defer c.mutex.RUnlock()
	if lastSeen, ok := c.lastSeen[key]; ok {
		now := time.Now()
		return now.Sub(lastSeen) >= c.expiration
	}
	return false
}

func (c *ExpirationCache) PutIfAbsent(key string) bool {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	if _, ok := c.lastSeen[key]; !ok {
		c.lastSeen[key] = time.Now()
		return true
	}
	return false
}

func (c *ExpirationCache) Delete(key string) bool {
	c.mutex.Lock()
	defer c.mutex.Unlock()
	if _, ok := c.lastSeen[key]; ok {
		delete(c.lastSeen, key)
		return true
	}
	return false
}