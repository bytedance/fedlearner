import { Grid, Input, Button } from '@zeit-ui/react'
import { useState, useEffect } from 'react';
import css from 'styled-jsx/css';

function useStyles() {
  return css`
    .flex {
      display: flex;
    }
    .itemLabel {
      color: #444;
      padding: 8px;
    }
  `
}

function NameValuePair({value, onChange, onDelete, ...props}) {
  const style = useStyles()
  const {name, value: v} = value

  const [nameErr, setNameErr] = useState(false)
  const [nameErrMsg, setNameErrMsg] = useState('')
  const checkName = () => name === '' ? (setNameErr(true), setNameErrMsg('name reqiured')) : ''

  const [valueErr, setValueErr] = useState(false)
  const [valueErrMsg, setValueErrMsg] = useState('')
  const checkValue = () => v === '' ? (setValueErr(true), setValueErrMsg('value reqiured')) : ''

  return (
    <div {...props}>
      <Grid.Container gap={2} justify="left">
        <Grid xs={8} md={8} >
          <div className='flex'>
            <label className='itemLabel'>name</label>
            <Input
              width='100%'
              value={name}
              onChange={e => {setNameErr(false); onChange(e.target.value, v)}}
              onBlur={checkName}
              placeholder={nameErrMsg}
              status={nameErr ? "error" : 'default'}
            />
          </div>
        </Grid>
        <Grid xs={13} md={13}>
          <div className="flex">
            <label className='itemLabel'>value</label>
            <Input
              width='100%'
              value={v}
              onChange={e => {setValueErr(false); onChange(name, e.target.value)}}
              onBlur={checkValue}
              placeholder={valueErrMsg}
              status={valueErr ? "error" : 'default'}
            />
          </div>
        </Grid>
        <Grid>
          <Button
            auto
            ghost
            type="error"
            onClick={() => onDelete(name, value)}
          >delete</Button>
        </Grid>
        <style jsx>{style}</style>
      </Grid.Container>
    </div>
  )
}

export default function NameValueInput({value, onChange, ignoreKeys = [], ...props}) {
  let value_ = JSON.parse(value || '[]')
  const onItemChange = (idx, name, value) => {
    const copy = value_
    copy[idx] = {name, value}
    onChange(JSON.stringify(copy))
  }
  const onItemDelete = (idx) => {
    const copy = value_
    copy.splice(idx, 1)
    onChange(JSON.stringify(copy))
  }
  return (
    <div {...props}>
      {
        value_.map((el, idx) =>
          ignoreKeys.some(key => el.name === key)
          ? undefined
          : <NameValuePair
            style={{marginTop: '12px'}}
            value={el}
            onChange={(name, value) => onItemChange(idx, name, value)}
            onDelete={() => onItemDelete(idx)}
          />
        )
      }
    </div>
  )
}