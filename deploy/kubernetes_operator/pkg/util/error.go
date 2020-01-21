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
	"fmt"
	"strings"
)

type Errors struct {
	allErrors []error
}

func NewErrors(errors ...error) *Errors {
	e := &Errors{}
	for _, err := range errors {
		_ = e.Add(err)
	}
	return e
}

func (e *Errors) Add(err error) *Errors {
	if err != nil {
		e.allErrors = append(e.allErrors, err)
	}
	return e
}

func (e *Errors) AsError() error {
	if len(e.allErrors) == 0 {
		return nil
	}
	var errString []string
	for _, err := range e.allErrors {
		errString = append(errString, err.Error())
	}
	return fmt.Errorf("%s", strings.Join(errString, ","))
}
