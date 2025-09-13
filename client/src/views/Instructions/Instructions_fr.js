/* eslint-disable max-len */

import React from 'react';
import withStyles from '@mui/styles/withStyles';
import {Typography} from '@mui/material';
import PropTypes from 'prop-types';

const styles = ({
  content: {
    // maxWidth: '700px',
    width: '90%',
    margin: '5rem auto',
  },
  contentText: {
    fontFamily: '"Times", "Saira Condensed","Roboto", "Helvetica", "Arial", "sans-serif"',
    fontSize: 16,
    textAlign: 'justify',
    textJustify: 'inter-word',
    marginBottom: '1rem',
  },
  titleText: {
    fontFamily: '"Saira Condensed","Roboto", "Helvetica", "Arial", "sans-serif"',
    margin: '20px 20px 10px 0px',
    color: '#F1815E',
  },
  link: {
    fontFamily: '"Saira Condensed"',
  },
  row: {
    display: 'flex',
    width: '100%',
    // position: 'relative',
    flexDirection: 'row',
    // justifyContent: 'space-between',
    border: '1px solid #ddd',
  },
  image: {
    maxWidth: '100%',
    maxHeight: '100%',
  },
  ul: {
    'listStyleType': 'decimal',
    '& li': {
      marginBottom: '1rem',
    },
  },
  ul2: {
    'listStyleType': 'lower-alpha',
  },
});

const Instructions = (props) => {
  const {classes} = props;

  return (
    <div className={classes.content}>

      <Typography variant="h5" className={classes.titleText}>
        Instructions d’utilisation du tableau de bord
      </Typography>

      <div>
        <Typography className={classes.contentText}>
          à ajouter…
        </Typography>
      </div>

    </div>);
};

Instructions.propTypes = {
  classes: PropTypes.object,
};

export default withStyles(styles)(Instructions);
