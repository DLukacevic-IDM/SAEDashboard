/* eslint-disable max-len */
import React from 'react';
import withStyles from '@mui/styles/withStyles';
import PropTypes from 'prop-types';
import {Typography, Button, Box} from '@mui/material';

const styles = ({
  content: {
    maxWidth: '900px',
    width: '70%',
    margin: '5rem auto',
  },
  contentText: {
    fontFamily: '"Roboto condensed","Roboto", "Times", "Helvetica", "Arial", "sans-serif"',
    fontSize: 16,
    textAlign: 'justify',
    textJustify: 'inter-word',
    marginBottom: '1rem',
  },
  titleText: {
    fontFamily: '"Roboto Condensed","Roboto", "Helvetica", "Arial", "sans-serif"',
    margin: '20px 20px 10px 0px',
    fontSize: '1.25rem',
    // color: '#F1815E',
  },
  link: {
    fontFamily: '"Saira Condensed"',
  },
  buttonContainer: {
    marginTop: '2rem',
    width: '100%',
    display: 'flex',
    justifyContent: 'center',
  },
  image: {
    width: '100%',
    height: 'auto',
    border: '1px solid #ddd',
  },
  customTextStyleOne: {
    fontStyle: 'italic',
  },
});

const Welcome = ({classes}) => {
  const handleClick = () => {
    window.location.href = '/dashboard';
  };

  return (
    <div className={classes.content}>
      <Typography variant="h6" className={classes.titleText}>
        Bienvenue sur le Outil d’estimation de la planification familiale infranationale
      </Typography>
      <Typography variant="body1" className={classes.contentText}>
        Ce tableau de bord a été conçu pour permettre…
      </Typography>

      <Box className={classes.buttonContainer}>
        <Button variant="contained" onClick={handleClick}>GO</Button>
      </Box>

    </div>
  );
};

Welcome.propTypes = {
  classes: PropTypes.object,
};

export default withStyles(styles)(Welcome);
