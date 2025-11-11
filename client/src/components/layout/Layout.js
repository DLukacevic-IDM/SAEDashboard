import React, {useState} from 'react';
import {useSelector, useDispatch} from 'react-redux';
import {
  AppBar, IconButton, Menu, MenuItem, Toolbar, Typography,
  Snackbar, Select, Drawer,
} from '@mui/material';
import withStyles from '@mui/styles/withStyles';
import MenuIcon from '@mui/icons-material/Menu';
import Footer from './Footer';
import Dashboard from '../../views/Dashboard';
import About from '../../views/About';
import Welcome from '../../views/Welcome';
import Instructions from '../../views/Instructions';
import Libraries from '../../views/Libraries';
import SnackbarContentWrapper from '../uielements/SnackBarContentWrapper';
import {showStop} from '../../redux/actions/messaging';
import PropTypes from 'prop-types';
import {changeLanguage} from '../../redux/actions/filters';
import {IntlProvider, FormattedMessage} from 'react-intl';
import * as translations from '../../data/translation';
import AssistantIcon from '@mui/icons-material/Assistant';
import LLMClient from '../LLMClient';

const styles = (theme) => ({
  root: {
    marginBottom: 100,
  },
  grow: {
    flexGrow: 1,
  },
  content: {
    display: 'block', // Fix IE 11 issue.
    marginTop: 40,
    [theme.breakpoints.up(1500 + theme.spacing(3 * 2))]: {
      width: '100%',
      marginRight: 'auto',
    },
  },
  appbar: {
    position: 'fixed',
    backgroundColor: '#24323c',
  },
  menu: {
    'margin-top': 30,
    'padding-top': 0,
  },
  menuButton: {
    marginLeft: -12,
    marginRight: 20,
  },
  menuItem: {
    '& li p': {fontSize: 'large'},
  },
  github: {
    cursor: 'pointer',
    color: 'white',
  },
  llmButton: {
    marginLeft: theme.spacing(2),
  },
  drawer: {
    zIndex: 10000,
  },
});

/**
 * Layout component
 * @param {} props
 * @returns
 */

const Layout = (props) => {
  const {classes} = props;
  const [selectedView, setSelectedView] = useState(props.view);
  const [anchorEl, setAnchorEl] = useState(null);
  const [LLMOpen, setLLMOpen] = useState(false);
  const variant = useSelector((state) => state.showMsg.variant);
  const infoMsg = useSelector((state) => state.showMsg.msg);
  const showMsg = useSelector((state) => state.showMsg.open);
  const selectedLocale = useSelector((state) => state.filters.selectedLanguage);
  const dispatch = useDispatch();

  const menuEntries = [
    {urlFrag: 'welcome', id: 'dropdown_welcome'},
    {urlFrag: 'dashboard', id: 'dropdown_dashboard'},
    {urlFrag: 'about', id: 'dropdown_about'},
    {urlFrag: 'instructions', id: 'dropdown_instructions'},
    {urlFrag: 'libraries', id: 'dropdown_lib'},
  ];

  const showView = (target) => {
    return (() => {
      setAnchorEl(null);
      setSelectedView(target);
      window.location.href = target;
    });
  };

  const handleMenu = (event) => {
    setAnchorEl(event.target);
  };

  const handleClose = (url) => {
    setAnchorEl(null);
    if (url !== undefined) {

    }
  };

  const handleSnackBarClose = (event) => {
    dispatch(showStop());
  };

  const handleLanguage = (language) => {
    dispatch(changeLanguage(language));
  };

  const renderMenuItem = (entry, idx) => {
    return (
      <MenuItem key={idx} onClick={entry.func ? entry.func : showView(entry.urlFrag)}>
        <Typography variant="body1" className={classes.menuitem}>
          <FormattedMessage id={entry.id}/>
        </Typography>
      </MenuItem>
    );
  };

  let selectedTabContent;
  switch (selectedView) {
    case 'welcome':
      selectedTabContent = <Welcome />;
      break;
    case 'dashboard':
      selectedTabContent = <Dashboard />;
      break;
    case 'about':
      selectedTabContent = <About />;
      break;
    case 'libraries':
      selectedTabContent = <Libraries />;
      break;
    case 'instructions':
      selectedTabContent = <Instructions />;
      break;
    default:
      selectedTabContent = <div>Error!</div>;
  }

  const handleLLM = () => {
    setLLMOpen(true);
  };

  const closeLLM = () => {
    setLLMOpen(false);
  };

  const messages = translations[selectedLocale]; // get the translations for the locale


  return (
    <IntlProvider locale={selectedLocale} messages={messages}>
      <div className={classes.root} style={{width: LLMOpen ? 'calc(100% - 440px)' : '100%'}}>
        <AppBar className={classes.appbar}>
          <Toolbar>
            <IconButton
              className={classes.menuButton}
              color="inherit"
              aria-label="menu"
              edge="start"
              onClick={handleMenu}
              size="large">
              <MenuIcon />
            </IconButton>
            <Menu
              aria-label={'popover'}
              id="simple-menu"
              anchorEl={anchorEl}
              getContentAnchorEl={null}
              anchorOrigin={{vertical: 'bottom', horizontal: 'left'}}
              transformOrigin={{vertical: 'top', horizontal: 'left'}}
              open={Boolean(anchorEl)}
              onClose={handleClose}
            >
              {menuEntries.map((entry, index) =>
                renderMenuItem(entry, index))}
            </Menu>

            <Typography variant="h6" color="inherit" className={classes.grow}>
              <FormattedMessage id='title'/>
            </Typography>

            <Select value={selectedLocale}
              sx={{bgcolor: 'white'}}
              onChange={(e) => handleLanguage(e.target.value)}>
              <MenuItem value='en'>English</MenuItem>
              <MenuItem value='fr'>Français</MenuItem>
            </Select>

            <IconButton aria-label="delete" size="medium" onClick={handleLLM}
              className={classes.llmButton}>
              <AssistantIcon fontSize="medium" color="primary"/>
            </IconButton>

            {/* <Link title="small area estimation Github repo"
            href=
            "https://github.com/InstituteforDiseaseModeling/SmallAreaEstimationForSurveyIndicators"
            target="_blank">
            <GitHubIcon className={classes.github}/>
          </Link> */}
          </Toolbar>
        </AppBar>
        <main className={classes.content}>
          {selectedTabContent}
          <Snackbar
            anchorOrigin={{
              vertical: 'top',
              horizontal: 'center',
            }}
            open={showMsg}
            autoHideDuration={variant === 'error' ? null : 6000}
            onClose={handleSnackBarClose}
            className={classes.snackbar}
          >
            <SnackbarContentWrapper
              onClose={handleSnackBarClose}
              variant={variant}
              message={infoMsg}
            />
          </Snackbar>
          <Drawer open={LLMOpen} anchor="right" variant="persistent"
            classes={{
              paper: classes.drawer,
            }}
          >
            <LLMClient open={LLMOpen} closeDrawer={closeLLM}/>
          </Drawer>
        </main>
        <Footer />
      </div>
    </IntlProvider>
  );
};

Layout.propTypes = {
  classes: PropTypes.object,
  view: PropTypes.string,
};

export default withStyles(styles)(Layout);
