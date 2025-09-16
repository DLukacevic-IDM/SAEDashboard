import React from 'react';
import {default as En} from './Instructions_en.js';
import {default as Fr} from './Instructions_fr.js';
import PropTypes from 'prop-types';
import {injectIntl} from 'react-intl';

const Instructions = (props) => {
  const {intl} = props;
  if (intl.locale === 'en') {
    return (<En/>);
  } else if (intl.locale === 'fr') {
    return (<Fr/>);
  }
};

Instructions.propTypes = {
  intl: PropTypes.func,
};

export default injectIntl(Instructions);
