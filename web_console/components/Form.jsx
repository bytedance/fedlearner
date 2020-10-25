import React, { useState, useReducer, useMemo, useCallback, useEffect, useRef } from 'react';
import css from 'styled-jsx/css';
import { Button, ButtonGroup, Card, Grid, Text, Input, Toggle, Textarea, Note, useTheme, Collapse, useToasts, Select } from '@zeit-ui/react';
import FederationSelect from './FederationSelect';
import JobTypeSelect from './JobTypeSelect';
import JobRoleSelect from './JobRoleSelect';
import ServerTicketSelect from './ServerTicketSelect';
import ClientTicketSelect from './ClientTicketSelect';
import DataPortalTypeSelect from './DataPortalTypeSelect';
import NameValueInput from './NameValueGroup';
import RawDataSelect from './RawDataSelect'
import BooleanSelect from './BooleanSelect'
import DataSourceSelect from './DataSourceSelect'
import produce from 'immer'

function useStyles() {
  return css`
    .footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      width: 100%;
    }
  `;
}

const formatGroupFieldKey = (groupName, key) => `[group:${groupName}].${key}`

// mark group name to handle conflicts
// TODO: handle conflict between form types in one group
const handleFieldsToRender = fields => produce(fields, draft => {
  draft.forEach(curr => {
    if (!curr.groupName) return

    const handleGroupFields = fields => {
      fields.forEach(field => {
        if (field.type === 'label') return
        field.label = field.label || field.key
        field.key = formatGroupFieldKey(curr.groupName, field.key)
      })
    }
    if (Array.isArray(curr.fields)) {
      handleGroupFields(curr.fields)
    } else {
      Object.values(curr.fields).forEach(el => handleGroupFields(el))
    }
  })
})

function deepEqual(x, y) {
  if (x === y) {
      return true;
  }
  if (!(typeof x == "object" && x != null) || !(typeof y == "object" && y != null)){
      return false;
  }
  if (Object.keys(x).length != Object.keys(y).length){
      return false;
  }
  for (var prop in x) {
      if (y.hasOwnProperty(prop))
      {
          if (!deepEqual(x[prop], y[prop])){
              return false;
          }
      }
      else{
          return false;
      }
  }
  return true;
}

const mapFields2Form = (fields, groupType) => {
  // flat all group fileds
  fields = fields.reduce((total, curr) => {
    if (curr.groupName) {
      if (Array.isArray(curr.fields)) {
        total.push(...curr.fields)
      } else {
        groupType
        ? total.push(...curr.fields[groupType])
        : Object.values(curr.fields).forEach(el => total.push(...el))
      }
    } else {
      total.push(curr)
    }
    return total
  }, [])
  const formData = fields.reduce((total, current) => {
    total[current.key] = current.hasOwnProperty('value')
      ? current.value
      : current.value || current.default || '';
    return total;
  }, {})
  return [fields, formData]
}

const groupFormType = {}
let fieldsCache

/**
 * interface IField {
 *   key: string;
 *   value?: any;
 *   type?: 'string' | 'boolean' | 'text' | 'password';
 *   label?: string;
 *   required?: boolean;
 *   span?: number; // Grid layout prop
 *   props?: any;
 *   callback?: (updateForm: function) => (value: any) => any
 * }
 */
export default function Form({
  title, onOk, onSubmit, onCancel, gap = 2,
  fields = [], okText = 'Submit', cancelText = 'Cancel',
  message = 'Please fill out the form before submitting.',
}) {
  // cache raw fields data
  const rawFields = fields
  const fieldsToRender = handleFieldsToRender(fields)

  useEffect(() => {
    rawFields.forEach(field => {
      if (field.groupName && field.formTypes) {
        groupFormType[field.groupName] = field.formTypes[0]
      }
    })
  }, [])

  const theme = useTheme();
  const styles = useStyles(theme);

  let formData
  [fields, formData] = mapFields2Form(fieldsToRender)
  const [form, setForm] = useState(formData);

  // update form value in rendering
  useEffect(() => {
    if (!deepEqual(fields, fieldsCache)) {
      fieldsCache = fields
      setForm(formData)
    }
  })

  const getFormatFormData = () =>
    rawFields.reduce((total, curr) => {
      if (curr.groupName) {
        total[curr.groupName] = {}
        const fillGroupFields = fields => {
          for (let field of fields) {
            total[curr.groupName][field.key] = form[formatGroupFieldKey(curr.groupName, field.key)]
          }
        }
        // handle multi formType
        if (Array.isArray(curr.fields)) {
          fillGroupFields(curr.fields)
        } else {
          for (let formType in curr.fields) {
            fillGroupFields(curr.fields[formType])
          }
        }
      } else {
          total[curr.key] = form[curr.key]
      }
      return total
    }, {})

  const disabled = fields.filter((x) => x.required).some((x) => !form[x.key]);
  const updateForm = (key, value) => {
    setForm(form => ({
      ...form,
      [key]: value,
    }));
  };

  const renderField = ({ key, label, props, type, onChange, hideLabel, callback }) => {
    const valueProps = {
      ...props,
      style: {
        width: '100%',
        ...(props || {}).style,
      },
    };

    if (type === 'password') {
      return (
        <Input.Password
          value={form[key]}
          onChange={(e) => updateForm(key, e.target.value)}
          {...valueProps}
        >{label || key}</Input.Password>
      );
    }

    if (type === 'text' || type === 'json') {
      return (
        <div className="formItemWithLabel">
          { !hideLabel ? <label className="formItemLabel" htmlFor={key}>{label || key}</label> : undefined }
          <Textarea
            value={form[key]}
            onChange={(e) => updateForm(key, e.target.value)}
            {...valueProps}
          />
        </div>
      );
    }

    if (type === 'boolean') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <Toggle
              size="large"
              checked={form[key]}
              onChange={(e) => updateForm(key, e.target.checked)}
              {...valueProps}
            />
          </div>
        </div>
      );
    }

    if (type === 'federation') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <FederationSelect
              value={form[key]}
              onChange={(value) => {
                updateForm(key, value)
                let formData = getFormatFormData()
                formData[key] = value
                if (onChange) {
                  onChange(value, formData);
                }
              }}
              {...valueProps}
            />
          </div>
        </div>
      );
    }

    if (type === 'jobType') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <JobTypeSelect
              value={form[key]}
              onChange={(value) => {
                updateForm(key, value)
                let data = getFormatFormData()
                data[key] = value
                if (onChange) {
                  onChange(value, data, groupFormType);
                }
              }}
              {...valueProps}
            />
          </div>
        </div>
      );
    }

    if (type === 'jobRole') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <JobRoleSelect
              value={form[key]}
              onChange={(value) => updateForm(key, value)}
              {...valueProps}
            />
          </div>
        </div>
      );
    }

    if (type === 'serverTicket') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <ServerTicketSelect
              value={form[key]}
              onChange={(value) => updateForm(key, value)}
              {...valueProps}
            />
          </div>
        </div>
      );
    }

    if (type === 'clientTicket') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <ClientTicketSelect
              value={form[key]}
              onChange={(value) => updateForm(key, value)}
              {...valueProps}
            />
          </div>
        </div>
      );
    }

    if (type === 'dataPortalType') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <DataPortalTypeSelect
              value={form[key]}
              onChange={(value) => updateForm(key, value)}
              {...valueProps}
            />
          </div>
        </div>
      );
    }

    if (type === 'name-value') {
      const btnStyle = {
        margin: '20px 0 0 0',
        width: '100%',
        fontSize: '16px',
        fontWeight: 'bolder'
      }

      const onAddNameValue = () => {
        // NOTE form[key] is string
        let preValue = JSON.parse(form[key] || '[]')
        preValue.push({name: '', value: ''})
        updateForm(key, JSON.stringify(preValue))
      }
      return (
        <>
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <NameValueInput
            value={form[key]}
            onChange={value => updateForm(key, value)}
            {...valueProps}
          />
          <Button
            className="addNameValueBtn"
            style={btnStyle}
            onClick={onAddNameValue}
          >add</Button>
        </>
      )
    }

    if (type === 'rawData') {
      return (
        <>
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <RawDataSelect
              value={form[key]}
              onChange={(value) => {
                updateForm(key, value)
                setTimeout(() => {
                  callback && callback(updateForm)(value)
                })
                if (onChange) {
                  onChange(value);
                }
              }}
              {...valueProps}
            />
          </div>
        </>
      )
    }

    if (type === 'label') {
      return (
        <div style={{fontWeight: 'bolder', padding: '12px 0'}}>{label || key}</div>
      )
    }

    if (type === 'select') {
      return (
        <div className="formItemWithLabel">
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <Select initialValue={form[key]} onChange={value => updateForm(key, value)}>
              {props?.options && props.options.map(opt =>
                <Select.Option key={opt.label} value={opt.value}>{opt.label}</Select.Option>
              )}
            </Select>
          </div>
        </div>
      )
    }

    if (type === 'bool-select') {
      return (
        <>
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <BooleanSelect
              value={form[key]}
              onChange={(value) => {
                updateForm(key, value)
                if (onChange) {
                  onChange(value);
                }
              }}
              {...valueProps}
            />
          </div>
        </>
      )
    }

    if (type === 'datasource') {
      return (
        <>
          <label className="formItemLabel" htmlFor={key}>{label || key}</label>
          <div className="formItemValue">
            <DataSourceSelect
              value={form[key]}
              onChange={(value) => {
                updateForm(key, value)
                if (onChange) {
                  onChange(value);
                }
              }}
              {...valueProps}
            />
          </div>
        </>
      )
    }

    return (
      <Input
        value={form[key]}
        onChange={(e) => updateForm(key, e.target.value)}
        {...valueProps}
      >{label || key}</Input>
    );
  };
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const handleSubmit = async () => {
    setSubmitting(true);
    const formData = getFormatFormData()
    try {
      const res = await onSubmit(formData, groupFormType);
      if (res.error) {
        throw new Error(res.error);
      }
      setSubmitting(false);
      onOk(res.data);
    } catch (err) {
      setSubmitting(false);
      setError(err.message);
    }
  };

  const renderFieldInGrid = x => {
    const span = x.type === 'label' ? 24 : x.span || 8
    return <Grid key={x.key} xs={span} md={span}>{renderField(x)}</Grid>
  }

  const renderGroup = group => {
    // const [, setToast] = useToasts()
    const formTypeReducer = (_, value) => {
      groupFormType[group.groupName] = value
      return value
    }
    const [formType, setFormType] = useReducer(formTypeReducer, group.formTypes && group.formTypes[0])
    let groupFields = Array.isArray(group.fields) ? group.fields : group.fields[formType]

    /**
     * form type switch
     * - set `formTypes` to active form type switch
     * - fileds must be object with key as form type, value as fields of group
     * - set `onFormTypeChange` to convert data between types
     *    - (data, currType, targetType) => object
     *    - data is an object with TOTAL form data (json fields as string)
     *    - if `error` field in the returned object, switching will be prevented and show error msg
     *    - updated fields need to be returned if no error
     */
    const onFormTypeChange = (e, type) => {

      e.stopPropagation()

      if (formType === type) return
      let res = group.onFormTypeChange && group.onFormTypeChange(getFormatFormData(), formType, type)
      if (res.error) {
        // TODO: figure out why this not working
        // setToast({ text: res.error, type: 'error' })
        alert(res.error)
        return
      }
      const [, formData] = mapFields2Form(handleFieldsToRender(res.newFields), type)
      setForm({...form, ...formData})

      groupFields = group.fields[type]
      setFormType(type)
    }
    const collapseTitle = () => {
      return <>
        {group.groupName}
        { formType
          ? <ButtonGroup className="formTypeBtns" size="small" style={{marginLeft: '20px'}}>
            { group.formTypes.map(type =>
                <Button
                  className={formType === type ? 'selecetedType' : 'formTypeBtn'}
                  onClick={e => onFormTypeChange(e, type)}
                >
                  {type}
                </Button>
              ) }
            <style jsx global>{`
              .formTypeBtns > .selecetedType, .formTypeBtns > .selecetedType:hover {
                background: #000;
                color: #fff;
                border-color: #000;
              }
              .formTypeBtns > .formTypeBtn:hover {
                background: #eee;
              }
            `}</style>
          </ButtonGroup>
          : undefined
        }
      </>
    }

    const initialVisible = group.initialVisible === undefined ? true : group.initialVisible
    return <Grid xs={24}>
      <Collapse title={collapseTitle()} initialVisible={initialVisible}>
        <Grid.Container gap={2}>
          { groupFields.map(field => field && renderFieldInGrid(field)) }
        </Grid.Container>
      </Collapse>
    </Grid>
  }

  return (
    <>
      <div className="heading">
        <Text h2>{title}</Text>
        <Button auto onClick={onCancel}>{cancelText}</Button>
      </div>
      <Card shadow>
        <Grid.Container gap={gap}>
          {fieldsToRender.map((x) => (x.groupName ? renderGroup(x) : x && renderFieldInGrid(x)))}
        </Grid.Container>
        <Card.Footer className="formCardFooter">
          {error ? <Note small label="error" type="error">{error}</Note> : <Text p>{message}</Text>}
          <Button auto disabled={disabled} loading={submitting} type="secondary" onClick={handleSubmit}>
            {okText}
          </Button>
        </Card.Footer>
      </Card>

      <style jsx>{styles}</style>
    </>
  );
}