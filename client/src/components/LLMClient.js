/* eslint-disable object-curly-spacing */
/* eslint-disable brace-style */
/* eslint-disable no-unused-vars */
/* eslint-disable max-len */
import React, {useState} from 'react';
import {Box, IconButton, Button, FormGroup, FormLabel,
  TextareaAutosize, CircularProgress, Typography,
  Link, Select, MenuItem, TextField, Collapse,
  List, ListItem, ListItemIcon, ListItemText, Chip} from '@mui/material';
import PropTypes from 'prop-types';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import BuildIcon from '@mui/icons-material/Build';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import PsychologyIcon from '@mui/icons-material/Psychology';
import withStyles from '@mui/styles/withStyles';
import SendIcon from '@mui/icons-material/Send';
import DeleteIcon from '@mui/icons-material/Delete';
import {handleResponse, handleError, getDefaultHeaders} from '../utils/utils';


const styles = {
  root: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: 20,
    width: '400px',
  },
  main: {
    padding: '20px',
    maxWidth: '400px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'right',
    padding: '10px 20px',
    backgroundColor: '#24323c',
    color: '#fff',
    minHeight: '64px',
  },
  spinner: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    position: 'fixed',
    top: 65,
    left: 'auto',
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.8)',
    width: 440,
    zIndex: 10001,
  },
  result: {
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    padding: '10px',
    backgroundColor: '#f5f5f5',
    borderRadius: '4px',
    marginTop: '20px',
    overflow: 'auto',
  },
  resultTitle: {
    display: 'flex',
    justifyContent: 'space-between',
    color: '#darkblue',
    fontSize: '1.2rem',
  },
  references: {

  },
  yellowTag: {
    color: 'blue',
    backgroundColor: 'yellow',
    borderRadius: '4px',
    padding: '2px 4px',
  },
  referenceLine: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: '10px',
    padding: '5px',
    backgroundColor: '#f5f5f5',
    borderRadius: '4px',
  },
};

const MODEL_OPTIONS = [
  { value: 'llama3.2:3b-instruct-q4_K_M', label: 'llama3.2:3b-instruct-q4_K_M (local)', disabled: true },
  //  { value: 'phi4-mini:3.8b-q4_K_M', label: 'phi4-mini:3.8b-q4_K_M (local)' },

  // { value: 'claude-sonnet-4-5-20250929', label: 'claude-sonnet-4-5 (Anthropic)' },
  { value: 'gpt-4o-mini', label: 'gpt-4o-mini (OpenAI)' },
  { value: 'gpt-4o', label: 'gpt-4o (OpenAI)' },
  // { value: 'gpt-oss-20b', label: 'gpt-oss-20b (Databricks)' },
  // { value: 'gpt-oss-120b', label: 'gpt-oss-120b (Databricks)' },

];

const LLMClient = (props) => {
  const {classes, closeDrawer} = props;
  const initialPrompt = ``;

  const [timeElasped, setTimeElasped] = useState();
  const [prompt, setPrompt] = useState(initialPrompt);
  const [result, setResult] = useState();
  const [running, setRunning] = useState(false);
  const [references, setReferences] = useState([]);
  const [selectedModel, setSelectedModel] = useState('gpt-4o');
  const [apiKey, setApiKey] = useState('');
  const [executionLog, setExecutionLog] = useState([]);
  const [showExecutionLog, setShowExecutionLog] = useState(false);
  const [ragUsed, setRagUsed] = useState(false);
  const [mcpUsed, setMcpUsed] = useState(false);
  const [showExamples, setShowExamples] = useState(false);
  let startTime = Date.now();


  const clickHandler = () => {
    const url='/llm/run';

    if (!prompt) {
      alert('Input cannot be empty!');
      return;
    }

    // Check if API key is required (for cloud provider models)
    const requiresApiKey = [
      'gpt-4o',
      'gpt-4o-mini',
      // 'claude-sonnet-4-5-20250929',
      // 'gpt-oss-20b',
      // 'gpt-oss-120b',
    ].includes(selectedModel);

    if (requiresApiKey && !apiKey) {
      alert('Please enter your API key for this model');
      return;
    }

    setRunning(true);
    startTime = Date.now();

    // Include API key and model in the request payload
    const requestBody = {
      'prompt': prompt,
      'api_key': apiKey || null,
      'model_name': selectedModel,
    };

    return fetch(url, {
      method: 'POST',
      body: JSON.stringify(requestBody),
      ...getDefaultHeaders(),
    })
        .then((response) => {
          handleResponse(response,
              (data) => {/* success handler */
                setRunning(false);
                const runtime = Math.round((Date.now() - startTime) / 1000);
                setTimeElasped(runtime);
                console.log('Backend response data:', data);
                console.log('References:', data.references);
                console.log('Execution log:', data.execution_log);
                console.log('RAG used:', data.rag_used);
                console.log('MCP used:', data.mcp_used);
                if (data.output) {
                  setResult(data.output);
                  setReferences(data.references || []);
                  setExecutionLog(data.execution_log || []);
                  setRagUsed(data.rag_used || false);
                  setMcpUsed(data.mcp_used || false);
                  // Auto-open execution log if RAG or MCP was used
                  if ((data.rag_used || data.mcp_used) && data.execution_log && data.execution_log.length > 0) {
                    setShowExecutionLog(true);
                  }
                };
              },
              (data) => {/* failure handler */
                setRunning(false);
                handleError(data);
              });
        });
  };

  const handleDrawerClose = () => {
    props.closeDrawer();
  };

  const clearHandler = () => {
    setPrompt('');
    setResult('');
    setReferences([]);
    setTimeElasped(0);
    setExecutionLog([]);
    setRagUsed(false);
    setMcpUsed(false);
    setShowExecutionLog(false);
  };

  const getReference = (source) => {
    const sourceParts = source.split('/');
    const fileName = sourceParts[sourceParts.length - 1];
    return '/references/'+fileName;
  };

  const handleModelChange = (event) => {
    const newModel = event.target.value;
    setSelectedModel(newModel);
    // Model is now passed with each request, no need to persist on backend
  };

  const getEventIcon = (eventType) => {
    switch (eventType) {
      case 'agent_start':
        return <PlayArrowIcon style={{ color: '#4caf50' }} />;
      case 'tool_call':
        return <BuildIcon style={{ color: '#2196f3' }} />;
      case 'tool_result':
        return <CheckCircleIcon style={{ color: '#4caf50' }} />;
      case 'agent_reasoning':
        return <PsychologyIcon style={{ color: '#ff9800' }} />;
      case 'agent_complete':
        return <CheckCircleIcon style={{ color: '#4caf50' }} />;
      default:
        return <PlayArrowIcon />;
    }
  };

  const formatTimestamp = (timestamp) => {
    return `${timestamp.toFixed(2)}s`;
  };

  console.log('Current state - result:', result);
  console.log('Current state - references:', references);
  console.log('Current state - executionLog:', executionLog);
  console.log('Current state - ragUsed:', ragUsed);
  console.log('Current state - mcpUsed:', mcpUsed);

  return (
    <main>
      <div className={classes.header}>
        <IconButton onClick={handleDrawerClose}>
          <ChevronRightIcon style={{color: 'gold'}}/>
        </IconButton>
        <div style={{marginLeft: 'auto', marginTop: 6}}>
          <Select
            value={selectedModel}
            onChange={handleModelChange}
            style={{backgroundColor: 'white', minWidth: 120}}
            MenuProps={{
              style: { zIndex: 10002 },
            }}
          >
            {MODEL_OPTIONS.map((option) => (
              <MenuItem key={option.value} value={option.value} disabled={option.disabled}>{option.label}</MenuItem>
            ))}
          </Select>
        </div>
      </div>

      <div className={classes.main}>
        {/* API Key Input for cloud providers */}
        {(() => {
          const requiresApiKey = [
            'gpt-4o',
            'gpt-4o-mini',
            // 'claude-sonnet-4-5-20250929',
            // 'gpt-oss-20b',
            // 'gpt-oss-120b',
          ].includes(selectedModel);

          // Determine provider name for label
          let providerName = 'API';
          if (selectedModel.startsWith('gpt-4')) providerName = 'OpenAI';
          // else if (selectedModel.startsWith('claude')) providerName = 'Anthropic';
          // else if (selectedModel.startsWith('gpt-oss')) providerName = 'Databricks';

          return requiresApiKey && (
            <div style={{marginBottom: '20px', padding: '10px', backgroundColor: '#fff3cd', borderRadius: '4px', border: '1px solid #ffc107'}}>
              <FormGroup>
                <FormLabel sx={{color: '#b18a14!important'}}>{providerName} API Key (Required)</FormLabel>
                <TextField
                  type='password'
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={`Enter your ${providerName} API key`}
                  fullWidth
                  size="small"
                  style={{backgroundColor: 'white'}}
                />
                <Typography variant='caption' style={{color: '#856404', marginTop: '5px', fontStyle: 'italic'}}>
                  Note: Your API key is sent securely with each request and is NEVER stored on the server or in browser storage.
                  You will need to re-enter it each session.
                </Typography>
              </FormGroup>
            </div>
          );
        })()}

        {/* controls */}
        <div>
          <div>
            <Button color='primary' variant='contained' endIcon={<SendIcon/>}
              onClick={clickHandler}
            >
              Run
            </Button>
            <Button color='primary' variant='contained' className='bg-amber-500 px-2 mx-2'
              endIcon={<DeleteIcon />}
              onClick={clearHandler} style={{marginLeft: 10}}
            >
              Clear
            </Button>
          </div>
        </div>

        {/* example questions */}
        <div style={{ maxWidth: '400px', marginTop: '20px' }}>
          <Button
            onClick={() => setShowExamples(!showExamples)}
            style={{
              backgroundColor: '#f0f0f0',
              color: '#333',
              padding: '8px 16px',
              borderRadius: '4px',
              marginBottom: '10px',
              textTransform: 'none',
              width: '100%',
              justifyContent: 'space-between',
            }}
          >
            <span>Example Questions</span>
            {showExamples ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </Button>
          <Collapse in={showExamples}>
            <div style={{
              backgroundColor: '#f5f5f5',
              borderRadius: '4px',
              padding: '15px',
              marginBottom: '10px',
            }}>

              <Typography variant='subtitle2' style={{fontWeight: 'bold', marginBottom: '8px'}}>
                MCP:
              </Typography>
              <Typography variant='body2' style={{margin: '0px 15px 10px 15px', cursor: 'pointer'}}
                onClick={() => setPrompt('use MCP, which region has highest coverage for modern method contraceptive in 2025.')}
              >
                • use MCP, which region has highest coverage for modern method contraceptive in 2025.
              </Typography>
              <Typography variant='body2' style={{margin: '0px 15px 10px 15px', cursor: 'pointer'}}
                onClick={() => setPrompt('use MCP, compare modern method with traditional method, which method is more effective and by how much in 2025. In the result, show by regions and effectiveness')}
              >
                • use MCP, compare modern method with traditional method, which method is more effective and by how much in 2025. In the result, show by regions and effectiveness
              </Typography>
            </div>
          </Collapse>
        </div>

        {/* input */}

        <div>
          <FormGroup>
            {/* <FormLabel>Input</FormLabel> */}
            <TextareaAutosize
              placeholder="Enter your question here."
              style={{ minWidth: '100%', minHeight: '100px' }}
              onChange={(e) => {setPrompt(e.target.value);}}
              value={prompt}
            />
          </FormGroup>
        </div>

        {/* result */}

        <div style={{ width: '400px'}}>
          <FormGroup className={classes.result}>
            <FormLabel className={classes.resultTitle}>
              <div style={{color: 'black'}}>
                {/* <Typography variant='h6'>Result</Typography> */}
                { timeElasped &&
                  <div>
                    <Typography className={classes.yellowTag}>{timeElasped}s</Typography>
                  </div>
                }
              </div>
            </FormLabel>
            { result &&
              <div className='result text-stone-950 p-2 bg-white overflow-auto'
                style={{ width: '100%', whiteSpace: 'pre-wrap' }}
                dangerouslySetInnerHTML={{ __html: result }}
              />
            }
          </FormGroup>
        </div>

        {/* execution log */}
        {executionLog.length > 0 && (
          <div style={{ maxWidth: '400px', marginTop: '20px' }}>
            <Button
              onClick={() => setShowExecutionLog(!showExecutionLog)}
              style={{
                backgroundColor: '#e3f2fd',
                color: '#1976d2',
                padding: '8px 16px',
                borderRadius: '4px',
                marginBottom: '10px',
                textTransform: 'none',
                width: '100%',
                justifyContent: 'space-between',
              }}
            >
              <span>
                Execution Details
                {ragUsed && <Chip label="RAG" size="small" color="primary" style={{marginLeft: '10px'}} />}
                {mcpUsed && <Chip label="MCP" size="small" color="secondary" style={{marginLeft: '10px'}} />}
              </span>
              {showExecutionLog ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </Button>
            <Collapse in={showExecutionLog}>
              <div style={{
                backgroundColor: '#f5f5f5',
                borderRadius: '4px',
                padding: '10px',
                maxHeight: '300px',
                overflow: 'auto',
              }}>
                <List dense>
                  {executionLog.map((event, index) => (
                    <ListItem key={index} style={{paddingLeft: 0, paddingRight: 0}}>
                      <ListItemIcon style={{minWidth: '40px'}}>
                        {getEventIcon(event.type)}
                      </ListItemIcon>
                      <ListItemText
                        primary={event.message}
                        secondary={
                          <span>
                            <span style={{color: '#666', fontSize: '0.85em'}}>
                              {formatTimestamp(event.timestamp)}
                            </span>
                            {event.tool && (
                              <Chip
                                label={event.tool}
                                size="small"
                                style={{marginLeft: '8px', height: '20px', fontSize: '0.75em'}}
                              />
                            )}
                            {event.preview && (
                              <div style={{
                                marginTop: '4px',
                                fontSize: '0.85em',
                                color: '#555',
                                fontStyle: 'italic',
                              }}>
                                {event.preview}
                              </div>
                            )}
                            {event.content && (
                              <div style={{
                                marginTop: '4px',
                                fontSize: '0.85em',
                                color: '#555',
                                fontStyle: 'italic',
                              }}>
                                {event.content}
                              </div>
                            )}
                          </span>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </div>
            </Collapse>
          </div>
        )}

        {/* references */}
        {references && references.length > 0 && (
          <div style={{ maxWidth: '400px'}} className={classes.result}>
            <Typography variant='h6' style={{marginBottom: '10px', color: '#1976d2'}}>
              References ({references.length})
            </Typography>
            {
              references.map((reference, index) => {
                const metadata = reference.metadata || reference;
                const source = metadata.source || 'Unknown';
                const pageLabel = metadata.page_label || metadata.page || 'Unknown';
                const chunkId = metadata.chunk_id || '';

                return (
                  <div key={index} className={classes.referenceLine}>
                    <div>
                      <Typography variant='body1'>
                        <Link href={getReference(source)} target='_blank'>
                          {source}
                        </Link>
                      </Typography>
                      <Typography variant='body2' style={{color: '#666'}}>
                        Page: {pageLabel}
                        {chunkId && ` | Chunk: ${chunkId}`}
                      </Typography>
                    </div>
                  </div>
                );
              })
            }
          </div>
        )}
      </div>

      {/* spinner */}
      {
        running &&
        <Box className={classes.spinner}
          style={{ display: 'flex', zIndex: 100, position: 'fixed' }}>
          <CircularProgress />
        </Box>
      }
    </main >

  );
};

LLMClient.propTypes = {
  classes: PropTypes.object,
  closeDrawer: PropTypes.func,
};

export default withStyles(styles)(LLMClient);
