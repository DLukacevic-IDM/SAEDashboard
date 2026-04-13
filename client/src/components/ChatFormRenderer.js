import React, {useState} from 'react';
import {
  Box, Button, TextField, FormControl, InputLabel, Select, MenuItem,
  RadioGroup, Radio, FormControlLabel, FormLabel, Checkbox, Typography,
} from '@mui/material';
import PropTypes from 'prop-types';

const ChatFormRenderer = ({form, onSubmit, disabled}) => {
  const [values, setValues] = useState(() => {
    const init = {};
    (form.fields || []).forEach((f) => {
      init[f.name] = f.default != null ? f.default : (f.type === 'checkbox' ? false : '');
    });
    return init;
  });

  const handleChange = (name, val) => {
    setValues((prev) => ({...prev, [name]: val}));
  };

  const allRequiredFilled = (form.fields || []).every((f) => {
    if (!f.required) return true;
    const v = values[f.name];
    return f.type === 'checkbox' ? true : (v != null && v !== '');
  });

  const handleSubmit = () => {
    onSubmit({form_id: form.id, values});
  };

  const renderField = (field) => {
    const val = values[field.name];
    switch (field.type) {
      case 'select':
        return (
          <FormControl fullWidth size="small" key={field.name} sx={{mb: 1.5}} disabled={disabled}>
            <InputLabel>{field.label}</InputLabel>
            <Select
              value={val}
              label={field.label}
              onChange={(e) => handleChange(field.name, e.target.value)}
            >
              {(field.options || []).map((opt) => (
                <MenuItem key={opt} value={opt}>{opt}</MenuItem>
              ))}
            </Select>
            {field.helperText && <Typography variant="caption" color="textSecondary" sx={{mt: 0.25, ml: 1.5}}>{field.helperText}</Typography>}
          </FormControl>
        );
      case 'radio':
        return (
          <FormControl key={field.name} sx={{mb: 1.5}} disabled={disabled}>
            <FormLabel sx={{fontSize: '0.85rem'}}>{field.label}</FormLabel>
            <RadioGroup
              value={val}
              onChange={(e) => handleChange(field.name, e.target.value)}
              row={field.options && field.options.length <= 4}
            >
              {(field.options || []).map((opt) => (
                <FormControlLabel key={opt} value={opt} control={<Radio size="small" />} label={opt} />
              ))}
            </RadioGroup>
            {field.helperText && <Typography variant="caption" color="textSecondary" sx={{ml: 1.5}}>{field.helperText}</Typography>}
          </FormControl>
        );
      case 'textarea':
        return (
          <TextField
            key={field.name}
            fullWidth size="small"
            multiline minRows={2} maxRows={4}
            label={field.label}
            value={val}
            onChange={(e) => handleChange(field.name, e.target.value)}
            helperText={field.helperText}
            disabled={disabled}
            sx={{mb: 1.5}}
          />
        );
      case 'checkbox':
        return (
          <FormControlLabel
            key={field.name}
            control={
              <Checkbox
                size="small"
                checked={!!val}
                onChange={(e) => handleChange(field.name, e.target.checked)}
                disabled={disabled}
              />
            }
            label={field.label}
            sx={{mb: 1}}
          />
        );
      default:
        return (
          <TextField
            key={field.name}
            fullWidth size="small"
            label={field.label}
            value={val}
            onChange={(e) => handleChange(field.name, e.target.value)}
            helperText={field.helperText}
            disabled={disabled}
            sx={{mb: 1.5}}
          />
        );
    }
  };

  return (
    <Box sx={{mt: 1, p: 1.5, backgroundColor: '#fff', borderRadius: 1, border: '1px solid #e0e0e0'}}>
      {form.title && <Typography variant="subtitle2" sx={{mb: 1}}>{form.title}</Typography>}
      {(form.fields || []).map(renderField)}
      {!disabled && (
        <Button
          variant="contained" size="small" fullWidth
          onClick={handleSubmit}
          disabled={!allRequiredFilled}
          sx={{mt: 0.5}}
        >
          {form.submitLabel || 'Submit'}
        </Button>
      )}
    </Box>
  );
};

ChatFormRenderer.propTypes = {
  form: PropTypes.shape({
    id: PropTypes.string.isRequired,
    title: PropTypes.string,
    submitLabel: PropTypes.string,
    fields: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.string.isRequired,
      label: PropTypes.string.isRequired,
      options: PropTypes.array,
      default: PropTypes.any,
      required: PropTypes.bool,
      helperText: PropTypes.string,
    })).isRequired,
  }).isRequired,
  onSubmit: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

export default ChatFormRenderer;
